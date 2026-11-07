import type { ConversionExtraFields } from "./types";

export const OVERLAY_POSITIONS = [
  "top-left", "top-center", "top-right", "center-left", "center", "center-right",
  "bottom-left", "bottom-center", "bottom-right",
] as const;
export const NUMBER_POSITIONS = OVERLAY_POSITIONS.filter((position) => !position.startsWith("center"));

export interface WatermarkOptionFields {
  readonly kind: "text" | "image";
  readonly text: string;
  readonly position: string;
  readonly angle: string;
  readonly opacity: string;
  readonly scale: string;
  readonly margin: string;
}

export interface PageNumberOptionFields {
  readonly position: string;
  readonly margin: string;
  readonly font_size: string;
  readonly start: string;
  readonly format: string;
}

export const DEFAULT_WATERMARK_OPTIONS: WatermarkOptionFields = {
  kind: "text", text: "CONFIDENTIAL", position: "center", angle: "0", opacity: "0.25", scale: "0.5", margin: "18",
};
export const DEFAULT_PAGE_NUMBER_OPTIONS: PageNumberOptionFields = {
  position: "bottom-center", margin: "18", font_size: "12", start: "1", format: "number",
};

function boundedNumber(value: string, minimum: number, maximum: number, integer = false): boolean {
  if (!/^-?(?:\d+(?:\.\d+)?|\.\d+)$/.test(value)) return false;
  const number = Number(value);
  return Number.isFinite(number) && number >= minimum && number <= maximum && (!integer || Number.isInteger(number));
}

export function validateWatermarkOptions(
  options: WatermarkOptionFields,
  image: Pick<File, "name" | "size"> | undefined,
  maxImageBytes: number,
): string | undefined {
  if (!OVERLAY_POSITIONS.some((position) => position === options.position)) return "Choose a valid watermark position.";
  if (!boundedNumber(options.angle, -180, 180)) return "Use an angle from -180 to 180 degrees.";
  if (!boundedNumber(options.opacity, 0.1, 1)) return "Use opacity from 0.1 to 1.";
  if (!boundedNumber(options.scale, 0.1, 1)) return "Use scale from 0.1 to 1.";
  if (!boundedNumber(options.margin, 12, 144)) return "Use a margin from 12 to 144 PDF points.";
  if (options.kind === "text") {
    if (!options.text.trim() || options.text.length > 120 || !/^[\x20-\x7e\u00a0-\u00ff]+$/.test(options.text)) {
      return "Use 1–120 printable English or Western Latin characters. Use an image for other scripts.";
    }
  } else if (options.kind === "image") {
    if (!image) return "Choose one local PNG, JPG, JPEG or WEBP watermark image.";
    if (!/\.(?:png|jpe?g|webp)$/i.test(image.name)) return "The watermark image must be PNG, JPG, JPEG or WEBP.";
    if (image.size <= 0 || image.size > maxImageBytes) return `Choose a non-empty watermark image up to ${maxImageBytes / (1024 * 1024)} MB. The image must also be at most 16 million pixels.`;
  } else {
    return "Choose a text or image watermark.";
  }
  return undefined;
}

export function validatePageNumberOptions(options: PageNumberOptionFields): string | undefined {
  if (!NUMBER_POSITIONS.some((position) => position === options.position)) return "Choose a top or bottom page-number position.";
  if (!boundedNumber(options.margin, 12, 144)) return "Use a margin from 12 to 144 PDF points.";
  if (!boundedNumber(options.font_size, 8, 48)) return "Use a font size from 8 to 48 PDF points.";
  if (!boundedNumber(options.start, 1, 999999, true)) return "Use a whole starting number from 1 to 999,999.";
  if (options.format !== "number" && options.format !== "page") return "Choose numbers or Page n labels.";
  return undefined;
}

export function pageNumberSample(options: PageNumberOptionFields): string | undefined {
  if (!boundedNumber(options.start, 1, 999999, true)) return undefined;
  return options.format === "page" ? `Page ${Number(options.start)}` : String(Number(options.start));
}

export function buildWatermarkFields(options: WatermarkOptionFields, pages: string, image?: File): ConversionExtraFields {
  return {
    pages: pages.trim(),
    options: JSON.stringify({
      kind: options.kind,
      ...(options.kind === "text" ? { text: options.text } : {}),
      position: options.position, angle: Number(options.angle), opacity: Number(options.opacity),
      scale: Number(options.scale), margin: Number(options.margin),
    }),
    ...(options.kind === "image" && image ? { watermark_image: image } : {}),
  };
}

export function buildPageNumberFields(options: PageNumberOptionFields, pages: string): ConversionExtraFields {
  return { pages: pages.trim(), options: JSON.stringify({ position: options.position, margin: Number(options.margin), font_size: Number(options.font_size), start: Number(options.start), format: options.format }) };
}
