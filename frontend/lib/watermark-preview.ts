import type { WatermarkOptionFields } from "./pdf-overlay-options";

export const PREVIEW_WINDOW_SIZE = 12;
const POSITIONS = new Set(["top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"]);

export interface PreviewSize { readonly width: number; readonly height: number }
export interface HelveticaMetrics {
  readonly advances: Readonly<Record<number, number>>;
  readonly ascender: number;
  readonly descender: number;
}

/** Read only bounded binary headers; never decode an unbounded watermark image. */
export function watermarkImageDimensions(input: Uint8Array): (PreviewSize & { readonly mime: string }) | undefined {
  const bytes = input.subarray(0, 1024 * 1024);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const ascii = (start: number, length: number) => String.fromCharCode(...bytes.subarray(start, start + length));
  const result = (width: number, height: number, mime: string) => width > 0 && height > 0 && width * height <= 16_000_000 ? { width, height, mime } : undefined;
  if (bytes.length >= 24 && [137, 80, 78, 71, 13, 10, 26, 10].every((byte, index) => bytes[index] === byte) && ascii(12, 4) === "IHDR") {
    return result(view.getUint32(16), view.getUint32(20), "image/png");
  }
  if (bytes.length >= 30 && ascii(0, 4) === "RIFF" && ascii(8, 4) === "WEBP") {
    const type = ascii(12, 4);
    if (type === "VP8X") return result(1 + bytes[24] + (bytes[25] << 8) + (bytes[26] << 16), 1 + bytes[27] + (bytes[28] << 8) + (bytes[29] << 16), "image/webp");
    if (type === "VP8L" && bytes[20] === 47) {
      const bits = view.getUint32(21, true);
      return result((bits & 0x3fff) + 1, ((bits >>> 14) & 0x3fff) + 1, "image/webp");
    }
    if (type === "VP8 " && bytes[23] === 157 && bytes[24] === 1 && bytes[25] === 42) return result(view.getUint16(26, true) & 0x3fff, view.getUint16(28, true) & 0x3fff, "image/webp");
    return undefined;
  }
  if (bytes.length >= 4 && bytes[0] === 255 && bytes[1] === 216) {
    const frames = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]);
    let offset = 2;
    while (offset < bytes.length) {
      if (bytes[offset++] !== 255) return undefined;
      while (offset < bytes.length && bytes[offset] === 255) offset++;
      if (offset >= bytes.length) return undefined;
      const marker = bytes[offset++];
      if (marker === 0xd9 || marker === 0xda) return undefined;
      if (marker === 1 || marker >= 0xd0 && marker <= 0xd7) continue;
      if (offset + 2 > bytes.length) return undefined;
      const length = view.getUint16(offset);
      if (length < 2 || offset + length > bytes.length) return undefined;
      if (frames.has(marker)) return length >= 8 ? result(view.getUint16(offset + 5), view.getUint16(offset + 3), "image/jpeg") : undefined;
      offset += length;
    }
  }
  return undefined;
}

export function previewPageWindow(pageCount: number, windowIndex: number) {
  const count = Number.isSafeInteger(pageCount) && pageCount > 0 && pageCount <= 2_000 ? pageCount : 0;
  const windows = Math.ceil(count / PREVIEW_WINDOW_SIZE);
  const index = windows ? Math.min(windows - 1, Math.max(0, Number.isFinite(windowIndex) ? Math.floor(windowIndex) : 0)) : 0;
  const first = count ? index * PREVIEW_WINDOW_SIZE + 1 : 0;
  const last = Math.min(count, first + PREVIEW_WINDOW_SIZE - 1);
  return { first, last, pages: count ? Array.from({ length: last - first + 1 }, (_, offset) => first + offset) : [], index, windows };
}

/** Invalid scopes never show a misleading partially applied watermark. */
export function selectedPreviewPage(value: string, page: number, pageCount: number): boolean {
  if (!Number.isSafeInteger(page) || page < 1 || page > pageCount || value.length > 16_384) return false;
  if (!value.trim()) return true;
  const ranges: { start: number; end: number }[] = [];
  for (const token of value.split(",")) {
    const match = token.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) return false;
    const start = Number(match[1]), end = Number(match[2] ?? match[1]);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < start || end > pageCount) return false;
    if (ranges.some((range) => start <= range.end && end >= range.start)) return false;
    ranges.push({ start, end });
  }
  return ranges.some((range) => page >= range.start && page <= range.end);
}

export function watermarkTextSize(text: string, metrics: HelveticaMetrics): PreviewSize | undefined {
  if (!text.trim() || text.length > 120 || !/^[\x20-\x7e\u00a0-\u00ff]+$/.test(text)) return undefined;
  let advance = 0;
  for (const char of text) {
    const width = metrics.advances[char.charCodeAt(0)];
    if (!Number.isFinite(width)) return undefined;
    advance += width;
  }
  return { width: advance * 100 + 0.01, height: (metrics.ascender - metrics.descender) * 100 + 0.01 };
}

export interface WatermarkPlacementOptions {
  readonly position: string;
  readonly angle: number;
  readonly scale: number;
  readonly margin: number;
}

/** Backend-equivalent rotated bounds, expressed in displayed top-left SVG space. */
export function watermarkPlacement(mark: PreviewSize, page: PreviewSize, options: WatermarkPlacementOptions) {
  const { angle, scale: fraction, margin, position } = options;
  if (![mark.width, mark.height, page.width, page.height, angle, fraction, margin].every(Number.isFinite)
    || Math.min(mark.width, mark.height, page.width, page.height) <= 0 || page.width > 14_400 || page.height > 14_400
    || !POSITIONS.has(position) || angle < -180 || angle > 180 || fraction < 0.1 || fraction > 1 || margin < 12 || margin > 144) return undefined;
  const availableWidth = page.width - 2 * margin, availableHeight = page.height - 2 * margin;
  if (availableWidth <= 0 || availableHeight <= 0) return undefined;
  const radians = -angle * Math.PI / 180;
  const cosine = Math.cos(radians), sine = Math.sin(radians);
  const corners = [[0, 0], [mark.width, 0], [0, mark.height], [mark.width, mark.height]].map(([x, y]) => [x * cosine - y * sine, x * sine + y * cosine]);
  const minX = Math.min(...corners.map(([x]) => x)), minY = Math.min(...corners.map(([, y]) => y));
  const boxWidth = Math.max(...corners.map(([x]) => x)) - minX;
  const boxHeight = Math.max(...corners.map(([, y]) => y)) - minY;
  const scale = Math.min(availableWidth * fraction / boxWidth, availableHeight * fraction / boxHeight);
  const width = boxWidth * scale, height = boxHeight * scale;
  const x = position.endsWith("left") ? margin : position.endsWith("right") ? page.width - margin - width : (page.width - width) / 2;
  const y = position.startsWith("top") ? margin : position.startsWith("bottom") ? page.height - margin - height : (page.height - height) / 2;
  return {
    x, y, width, height, scale,
    matrix: [cosine * scale, sine * scale, -sine * scale, cosine * scale, x - minX * scale, y - minY * scale] as const,
  };
}

export function numericWatermarkPlacement(options: WatermarkOptionFields): WatermarkPlacementOptions {
  return { position: options.position, angle: Number(options.angle), scale: Number(options.scale), margin: Number(options.margin) };
}
