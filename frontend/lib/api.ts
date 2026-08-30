import { DEFAULT_API_BASE_URL } from "./constants";
import {
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  getErrorMessage,
  isApiErrorPayload,
} from "./errors";
import type {
  ConversionExtraFields,
  ConversionOutputType,
  ConversionResult,
  ToolConfig,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);

export class PrivConApiError extends Error {
  readonly code: string;
  readonly status?: number;

  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "PrivConApiError";
    this.code = code;
    this.status = status;
  }
}

function getLocalApiBaseUrl(): string {
  const parsed = new URL(API_BASE_URL);
  if (!LOCAL_HOSTNAMES.has(parsed.hostname)) {
    throw new PrivConApiError(
      "backend_unavailable",
      "PrivCon is configured to use a non-local backend, so the request was blocked.",
    );
  }
  return parsed.toString().replace(/\/$/, "");
}

function fallbackFilename(
  config: ToolConfig,
  files: readonly File[],
  outputType: ConversionOutputType,
): string {
  if (config.id === "merge") return "merged.pdf";
  if (config.id === "images") return "images.pdf";
  if (config.id === "split") return outputType === "zip" ? "split.zip" : "split.pdf";

  const sourceName = files[0]?.name || config.slug;
  const dotIndex = sourceName.lastIndexOf(".");
  const basename = dotIndex > 0 ? sourceName.slice(0, dotIndex) : sourceName;
  return `${basename || config.slug}.pdf`;
}

function sanitizeFilename(filename: string): string {
  const leaf = filename.split(/[\\/]/).pop()?.trim();
  return leaf && leaf !== "." && leaf !== ".." ? leaf : "download";
}

function parseContentDisposition(value: string | null): string | undefined {
  if (!value) return undefined;

  const encodedMatch = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return sanitizeFilename(decodeURIComponent(encodedMatch[1].trim()));
    } catch {
      return sanitizeFilename(encodedMatch[1].trim());
    }
  }

  const plainMatch = value.match(/filename="([^"]+)"|filename=([^;]+)/i);
  const filename = (plainMatch?.[1] || plainMatch?.[2] || "").trim();
  return filename ? sanitizeFilename(filename) : undefined;
}

function getOutputType(
  contentType: string,
  filename?: string,
): ConversionOutputType {
  return contentType.includes("zip") || filename?.toLowerCase().endsWith(".zip")
    ? "zip"
    : "pdf";
}

async function toApiError(
  response: Response,
  config: ToolConfig,
): Promise<PrivConApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = undefined;
  }

  if (isApiErrorPayload(payload)) {
    return new PrivConApiError(
      payload.error,
      getErrorMessage(payload.error, {
        backendMessage: payload.message,
        expectedType: config.acceptedFormatLabel,
        maxFileSizeLabel: "50 MB",
      }),
      response.status,
    );
  }

  return new PrivConApiError(
    "internal_error",
    GENERIC_ERROR_MESSAGE,
    response.status,
  );
}

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch(`${getLocalApiBaseUrl()}/api/health`, {
      cache: "no-store",
      method: "GET",
      signal,
    });
    if (!response.ok) return false;
    const payload = (await response.json()) as { status?: unknown };
    return payload.status === "ok";
  } catch {
    return false;
  }
}

export async function submitConversion(
  config: ToolConfig,
  files: readonly File[],
  extraFields: ConversionExtraFields = {},
  signal?: AbortSignal,
): Promise<ConversionResult> {
  const formData = new FormData();
  for (const file of files) {
    formData.append(config.fileFieldName, file, file.name);
  }
  for (const [name, value] of Object.entries(extraFields)) {
    formData.append(name, value);
  }

  let response: Response;
  try {
    response = await fetch(`${getLocalApiBaseUrl()}${config.endpoint}`, {
      body: formData,
      method: "POST",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new PrivConApiError("backend_unavailable", NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) {
    throw await toApiError(response, config);
  }

  const contentType = response.headers.get("content-type") || "application/pdf";
  const headerFilename = parseContentDisposition(
    response.headers.get("content-disposition"),
  );
  const outputType = getOutputType(contentType, headerFilename);
  const blob = await response.blob();

  return {
    blob,
    contentType,
    filename: headerFilename || fallbackFilename(config, files, outputType),
    outputType,
  };
}
