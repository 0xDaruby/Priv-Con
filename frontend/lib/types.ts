export type ToolId =
  | "pdfToWord"
  | "word"
  | "powerpoint"
  | "excel"
  | "merge"
  | "split"
  | "images";

export type ToolSlug =
  | "pdf-to-word"
  | "word-to-pdf"
  | "ppt-to-pdf"
  | "excel-to-pdf"
  | "merge-pdf"
  | "split-pdf"
  | "images-to-pdf";

export type ToolRoute = `/${ToolSlug}`;

export type ToolIconName =
  | "word-file"
  | "powerpoint-file"
  | "spreadsheet-file"
  | "merge-file"
  | "split-file"
  | "image-file";

export type ConversionOutputKind = "docx" | "pdf" | "pdf-or-zip";

export type ConversionOutputType = "docx" | "pdf" | "zip";

export type FileFieldName = "file" | "files";

export type ConversionPhase =
  | "idle"
  | "files-selected"
  | "ready"
  | "uploading"
  | "processing"
  | "success"
  | "error";

export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelling"
  | "cancelled";

export type JobStage =
  | "uploading"
  | "queued"
  | "validating"
  | "converting"
  | "finalizing"
  | "ready"
  | "cancelling"
  | "cancelled"
  | "failed";

export type ProgressMode = "determinate" | "indeterminate";

export type ProgressStep = 1 | 2 | 3;

export type SplitMode = "every_page" | "ranges";

export type PdfToWordMode = "editable" | "preserve_appearance";

export type BackendHealthState =
  | "checking"
  | "running"
  | "unavailable";

export type ApiErrorCode =
  | "invalid_input"
  | "unsupported_file_type"
  | "file_type_mismatch"
  | "corrupted_file"
  | "password_protected"
  | "empty_pdf"
  | "oversized_file"
  | "oversized_request"
  | "output_too_large"
  | "too_many_pages"
  | "unsafe_document_content"
  | "invalid_split_mode"
  | "invalid_conversion_mode"
  | "invalid_page_ranges"
  | "origin_not_allowed"
  | "server_busy"
  | "backend_unavailable"
  | "conversion_timeout"
  | "conversion_failed"
  | "layout_conversion_failed"
  | "split_failed"
  | "file_processing_failed"
  | "not_found"
  | "method_not_allowed"
  | "job_not_ready"
  | "result_unavailable"
  | "job_cancelled"
  | "internal_error";

export interface ToolConfig {
  readonly id: ToolId;
  readonly slug: ToolSlug;
  readonly route: ToolRoute;
  readonly title: string;
  readonly description: string;
  readonly icon: ToolIconName;
  readonly endpoint: string;
  readonly jobEndpoint: string;
  readonly acceptedExtensions: readonly string[];
  readonly acceptedFormatLabel: string;
  readonly acceptAttribute: string;
  readonly multiple: boolean;
  readonly minFiles: number;
  readonly maxFiles: number;
  readonly fileFieldName: FileFieldName;
  readonly outputKind: ConversionOutputKind;
  readonly reorderable: boolean;
  readonly chooseLabel: string;
  readonly convertLabel: string;
}

export interface ApiErrorPayload {
  readonly error: string;
  readonly message: string;
}

export interface JobStatusPayload {
  readonly job_id: string;
  readonly tool: string;
  readonly status: JobStatus;
  readonly stage: Exclude<JobStage, "uploading">;
  readonly message: string;
  readonly progress_percent: number | null;
  readonly completed_units: number | null;
  readonly total_units: number | null;
  readonly unit_label: string | null;
  readonly result_available: boolean;
  readonly result_filename: string | null;
  readonly result_content_type: string | null;
  readonly error: ApiErrorPayload | null;
}

export interface ConversionProgress {
  readonly stage: JobStage;
  readonly label: string;
  readonly message: string;
  readonly mode: ProgressMode;
  readonly percent?: number;
  readonly completedUnits?: number;
  readonly totalUnits?: number;
  readonly unitLabel?: string;
}

export interface ConversionResult {
  readonly blob: Blob;
  readonly filename: string;
  readonly contentType: string;
  readonly outputType: ConversionOutputType;
}

export interface DownloadableConversionResult extends ConversionResult {
  readonly url: string;
}

export interface ConversionFailure {
  readonly code: string;
  readonly message: string;
}

export type ConversionExtraFields = Readonly<Record<string, string>>;

export interface SelectedFile {
  readonly id: string;
  readonly file: File;
}

export interface ClientValidationIssue {
  readonly code: ApiErrorCode;
  readonly message: string;
}

export interface FileSelectionResult {
  readonly files: readonly SelectedFile[];
  readonly issue?: ClientValidationIssue;
}
