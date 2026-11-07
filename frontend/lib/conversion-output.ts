import type { ConversionOutputKind, ConversionOutputType } from "./types";

const MIME_OUTPUT_TYPES = new Map<string, ConversionOutputType>([
  ["application/pdf", "pdf"],
  ["application/zip", "zip"],
  ["image/jpeg", "jpg"],
  ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"],
]);

/** Never infer a safe download format from a filename or an unknown MIME type. */
export function resolveOutputType(contentType: string, filename?: string): ConversionOutputType | undefined {
  const type = MIME_OUTPUT_TYPES.get(contentType.split(";")[0].trim().toLowerCase());
  if (!type) return undefined;
  if (filename) {
    const extension = filename.slice(filename.lastIndexOf(".") + 1).toLowerCase();
    if (extension !== type && !(type === "jpg" && extension === "jpeg")) return undefined;
  }
  return type;
}

export function isOutputTypeAllowed(kind: ConversionOutputKind, type: ConversionOutputType): boolean {
  if (kind === "pdf-or-zip") return type === "pdf" || type === "zip";
  if (kind === "jpg-or-zip") return type === "jpg" || type === "zip";
  return kind === type;
}

/** Restore the real result MIME from job metadata when using our private fetch transport. */
export function resolveResultMetadata(
  transportContentType: string,
  declaredContentType: string,
  filename: string | undefined,
  kind: ConversionOutputKind,
): { readonly contentType: string; readonly outputType: ConversionOutputType } | undefined {
  const transportMime = transportContentType.split(";")[0].trim().toLowerCase();
  const declaredMime = declaredContentType.split(";")[0].trim().toLowerCase();
  const privateTransport = transportMime === "application/x-privcon-result";
  if (privateTransport && (!declaredMime || !filename)) return undefined;

  const contentType = privateTransport ? declaredMime : transportMime || declaredMime;
  const outputType = resolveOutputType(contentType, filename);
  if (!outputType || !isOutputTypeAllowed(kind, outputType)) return undefined;
  if (declaredMime && resolveOutputType(declaredMime, filename) !== outputType) return undefined;
  return { contentType, outputType };
}
