import type { ApiErrorCode, ApiErrorPayload } from "./types";

export const NETWORK_ERROR_MESSAGE =
  "Couldn't reach PrivCon's backend. Make sure it's running at localhost:8000.";

export const GENERIC_ERROR_MESSAGE = "Something went wrong. Please try again.";

const ERROR_MESSAGES: Readonly<Partial<Record<ApiErrorCode, string>>> = {
  invalid_input: "That file doesn't look right. Please check it and try again.",
  file_type_mismatch:
    "This file's contents don't match its extension. Please check the file and try again.",
  corrupted_file: "This file appears to be damaged and can't be opened.",
  password_protected:
    "This file is password-protected. Please remove the password and try again.",
  empty_pdf: "This PDF has no pages.",
  oversized_request:
    "These files together are too large to process at once. Try fewer or smaller files.",
  output_too_large:
    "The result would be too large to generate. Try fewer or smaller files.",
  too_many_pages: "This PDF has more pages than PrivCon can process at once.",
  unsafe_document_content:
    "This PDF contains content PrivCon doesn't allow (such as embedded scripts or files) and can't be processed.",
  invalid_split_mode: "Please choose a valid split option.",
  invalid_page_ranges:
    "That page range isn't valid. Use a format like 1-3,5,8-10.",
  origin_not_allowed:
    "PrivCon couldn't verify this request. Please reload the page and try again.",
  server_busy:
    "PrivCon is busy with another conversion. Please wait a moment and try again.",
  backend_unavailable:
    "PrivCon's local backend isn't reachable. Make sure it's running.",
  conversion_timeout:
    "This conversion took too long and was stopped. Try a smaller or simpler file.",
  conversion_failed:
    "Something went wrong while processing this file. Please try again.",
  split_failed:
    "Something went wrong while processing this file. Please try again.",
  file_processing_failed:
    "Something went wrong while processing this file. Please try again.",
  not_found: GENERIC_ERROR_MESSAGE,
  method_not_allowed: GENERIC_ERROR_MESSAGE,
  internal_error: "An unexpected error occurred. Please try again.",
};

interface ErrorMessageOptions {
  readonly expectedType?: string;
  readonly maxFileSizeLabel?: string;
  readonly backendMessage?: string;
}

export function getErrorMessage(
  errorCode: string | undefined,
  options: ErrorMessageOptions = {},
): string {
  if (errorCode === "unsupported_file_type") {
    const expectedType = options.expectedType ?? "the supported file type";
    return `This tool only accepts ${expectedType}. Please choose a different file.`;
  }

  if (errorCode === "oversized_file") {
    const limit = options.maxFileSizeLabel ?? "50 MB";
    return `This file is larger than the ${limit} limit for a single file.`;
  }

  const knownMessage = ERROR_MESSAGES[errorCode as ApiErrorCode];
  if (knownMessage) {
    return knownMessage;
  }

  const backendMessage = options.backendMessage?.trim();
  return backendMessage || GENERIC_ERROR_MESSAGE;
}

export function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.error === "string" && typeof candidate.message === "string"
  );
}
