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
  ConversionProgress,
  ConversionResult,
  JobStage,
  JobStatusPayload,
  ToolConfig,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);
const JOB_POLL_INTERVAL_MS = 300;

const JOB_STAGE_LABELS: Readonly<Record<Exclude<JobStage, "uploading">, string>> = {
  queued: "Queued locally",
  validating: "Validating files",
  converting: "Converting locally",
  finalizing: "Finalizing result",
  ready: "Conversion complete",
  cancelling: "Cancelling conversion",
  cancelled: "Conversion cancelled",
  failed: "Conversion stopped",
};

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
  const extension = outputType === "docx" ? "docx" : "pdf";
  return `${basename || config.slug}.${extension}`;
}

function getOutputType(
  contentType: string,
  filename?: string,
): ConversionOutputType {
  if (contentType.includes("zip") || filename?.toLowerCase().endsWith(".zip")) {
    return "zip";
  }
  if (
    contentType.includes("wordprocessingml") ||
    filename?.toLowerCase().endsWith(".docx")
  ) {
    return "docx";
  }
  return "pdf";
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

function payloadToApiError(
  payload: unknown,
  status: number,
  config: ToolConfig,
): PrivConApiError {
  if (isApiErrorPayload(payload)) {
    return new PrivConApiError(
      payload.error,
      getErrorMessage(payload.error, {
        backendMessage: payload.message,
        expectedType: config.acceptedFormatLabel,
        maxFileSizeLabel: "50 MB",
      }),
      status,
    );
  }

  return new PrivConApiError("internal_error", GENERIC_ERROR_MESSAGE, status);
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return undefined;
  }
}

function isJobStatusPayload(value: unknown): value is JobStatusPayload {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.job_id === "string" &&
    typeof candidate.status === "string" &&
    typeof candidate.stage === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.result_available === "boolean"
  );
}

function uploadMessage(files: readonly File[], percent?: number): string {
  const fileLabel = files.length === 1 ? "file" : "files";
  return typeof percent === "number"
    ? `Uploading ${files.length} ${fileLabel} to the local backend: ${percent}%.`
    : `Uploading ${files.length} ${fileLabel} to the local backend.`;
}

function createConversionJob(
  config: ToolConfig,
  files: readonly File[],
  extraFields: ConversionExtraFields,
  signal: AbortSignal | undefined,
  onProgress: (progress: ConversionProgress) => void,
): Promise<JobStatusPayload> {
  const formData = new FormData();
  for (const file of files) {
    formData.append(config.fileFieldName, file, file.name);
  }
  for (const [name, value] of Object.entries(extraFields)) {
    formData.append(name, value);
  }

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    let settled = false;

    const cleanup = () => {
      signal?.removeEventListener("abort", handleAbort);
    };
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      cleanup();
      callback();
    };
    const handleAbort = () => request.abort();

    if (signal?.aborted) {
      reject(new DOMException("The request was aborted.", "AbortError"));
      return;
    }

    onProgress({
      stage: "uploading",
      label: "Uploading files",
      message: uploadMessage(files, 0),
      mode: "determinate",
      percent: 0,
    });

    request.open("POST", `${getLocalApiBaseUrl()}${config.jobEndpoint}`);
    request.responseType = "text";
    request.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        const percent = Math.max(
          0,
          Math.min(100, Math.round((event.loaded / event.total) * 100)),
        );
        onProgress({
          stage: "uploading",
          label: "Uploading files",
          message: uploadMessage(files, percent),
          mode: "determinate",
          percent,
        });
      } else {
        onProgress({
          stage: "uploading",
          label: "Uploading files",
          message: uploadMessage(files),
          mode: "indeterminate",
        });
      }
    };
    request.onerror = () => finish(() => reject(
      new PrivConApiError("backend_unavailable", NETWORK_ERROR_MESSAGE),
    ));
    request.onabort = () => finish(() => reject(
      new DOMException("The request was aborted.", "AbortError"),
    ));
    request.onload = () => finish(() => {
      const payload = parseJson(request.responseText);

      if (request.status < 200 || request.status >= 300) {
        reject(payloadToApiError(payload, request.status, config));
        return;
      }

      if (!isJobStatusPayload(payload)) {
        reject(new PrivConApiError("internal_error", GENERIC_ERROR_MESSAGE));
        return;
      }

      resolve(payload);
    });
    signal?.addEventListener("abort", handleAbort, { once: true });
    request.send(formData);
  });
}

function toConversionProgress(status: JobStatusPayload): ConversionProgress {
  const hasPercentage = typeof status.progress_percent === "number";
  return {
    stage: status.stage,
    label: JOB_STAGE_LABELS[status.stage],
    message: status.message,
    mode: hasPercentage ? "determinate" : "indeterminate",
    ...(hasPercentage ? { percent: status.progress_percent } : {}),
    ...(typeof status.completed_units === "number"
      ? { completedUnits: status.completed_units }
      : {}),
    ...(typeof status.total_units === "number"
      ? { totalUnits: status.total_units }
      : {}),
    ...(status.unit_label ? { unitLabel: status.unit_label } : {}),
  };
}

async function getJobStatus(
  jobId: string,
  config: ToolConfig,
  signal?: AbortSignal,
): Promise<JobStatusPayload> {
  let response: Response;
  try {
    response = await fetch(`${getLocalApiBaseUrl()}/api/jobs/${jobId}`, {
      cache: "no-store",
      method: "GET",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new PrivConApiError("backend_unavailable", NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) throw await toApiError(response, config);
  const payload = (await response.json()) as unknown;
  if (!isJobStatusPayload(payload)) {
    throw new PrivConApiError("internal_error", GENERIC_ERROR_MESSAGE);
  }
  return payload;
}

function abortableDelay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("The request was aborted.", "AbortError"));
      return;
    }

    const handleAbort = () => {
      window.clearTimeout(timeoutId);
      reject(new DOMException("The request was aborted.", "AbortError"));
    };
    const timeoutId = window.setTimeout(() => {
      signal?.removeEventListener("abort", handleAbort);
      resolve();
    }, milliseconds);
    signal?.addEventListener("abort", handleAbort, { once: true });
  });
}

async function cancelJob(jobId: string): Promise<void> {
  try {
    await fetch(`${getLocalApiBaseUrl()}/api/jobs/${jobId}`, {
      cache: "no-store",
      method: "DELETE",
    });
  } catch {
    // The expiry sweep is the final cleanup guard if the local backend stops
    // before it can acknowledge this cancellation request.
  }
}

async function downloadJobResult(
  jobId: string,
  status: JobStatusPayload,
  config: ToolConfig,
  files: readonly File[],
  signal?: AbortSignal,
): Promise<ConversionResult> {
  let response: Response;
  try {
    response = await fetch(`${getLocalApiBaseUrl()}/api/jobs/${jobId}/result`, {
      cache: "no-store",
      method: "GET",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new PrivConApiError("backend_unavailable", NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) throw await toApiError(response, config);
  const contentType = status.result_content_type || "application/pdf";
  const filename = status.result_filename || undefined;
  const outputType = getOutputType(contentType, filename);
  const transportBlob = await response.blob();
  const blob = new Blob([transportBlob], { type: contentType });
  return {
    blob,
    contentType,
    filename: filename || fallbackFilename(config, files, outputType),
    outputType,
  };
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
  onProgress: (progress: ConversionProgress) => void = () => undefined,
): Promise<ConversionResult> {
  let jobId: string | undefined;

  try {
    let status = await createConversionJob(
      config,
      files,
      extraFields,
      signal,
      onProgress,
    );
    jobId = status.job_id;
    onProgress(toConversionProgress(status));

    while (status.status !== "succeeded") {
      if (status.status === "failed") {
        throw payloadToApiError(status.error, 422, config);
      }

      if (status.status === "cancelled") {
        throw new PrivConApiError(
          "job_cancelled",
          getErrorMessage("job_cancelled"),
        );
      }

      await abortableDelay(JOB_POLL_INTERVAL_MS, signal);
      status = await getJobStatus(jobId, config, signal);
      onProgress(toConversionProgress(status));
    }

    if (!status.result_available) {
      throw new PrivConApiError(
        "result_unavailable",
        getErrorMessage("result_unavailable"),
      );
    }

    return await downloadJobResult(jobId, status, config, files, signal);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      if (jobId) await cancelJob(jobId);
      throw error;
    }
    throw error;
  }
}
