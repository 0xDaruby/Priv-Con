import { BACKEND_LIMITS } from "./constants";
import { getErrorMessage } from "./errors";
import { formatBytes } from "./format";
import type {
  ClientValidationIssue,
  FileSelectionResult,
  SelectedFile,
  ToolConfig,
} from "./types";

function getExtension(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase();
}

function fileIdentity(file: File): string {
  return [file.name, file.size, file.lastModified, file.type].join("\u0000");
}

function issue(code: ClientValidationIssue["code"], message: string): ClientValidationIssue {
  return { code, message };
}

export function validateFileSelection(
  config: ToolConfig,
  incomingFiles: readonly File[],
  currentFiles: readonly SelectedFile[],
): FileSelectionResult {
  if (incomingFiles.length === 0) {
    return { files: currentFiles };
  }

  const filesToAdd = config.multiple ? incomingFiles : incomingFiles.slice(0, 1);

  const candidateFiles = config.multiple
    ? [...currentFiles.map(({ file }) => file), ...filesToAdd]
    : [filesToAdd[0]];

  if (candidateFiles.length > config.maxFiles) {
    return {
      files: currentFiles,
      issue: issue(
        "invalid_input",
        `You can select up to ${config.maxFiles} files at a time.`,
      ),
    };
  }

  const existingIdentities = new Set(currentFiles.map(({ file }) => fileIdentity(file)));
  const incomingIdentities = new Set<string>();

  for (const file of filesToAdd) {
    if (!config.acceptedExtensions.includes(getExtension(file.name))) {
      return {
        files: currentFiles,
        issue: issue(
          "unsupported_file_type",
          getErrorMessage("unsupported_file_type", {
            expectedType: config.acceptedFormatLabel,
          }),
        ),
      };
    }

    if (file.size > BACKEND_LIMITS.maxFileBytes) {
      return {
        files: currentFiles,
        issue: issue(
          "oversized_file",
          getErrorMessage("oversized_file", {
            maxFileSizeLabel: formatBytes(BACKEND_LIMITS.maxFileBytes),
          }),
        ),
      };
    }

    const identity = fileIdentity(file);
    if (
      (config.multiple && existingIdentities.has(identity)) ||
      incomingIdentities.has(identity)
    ) {
      return {
        files: currentFiles,
        issue: issue("invalid_input", "This file is already selected."),
      };
    }
    incomingIdentities.add(identity);
  }

  const totalBytes = candidateFiles.reduce((total, file) => total + file.size, 0);
  if (totalBytes > BACKEND_LIMITS.maxCombinedUploadBytes) {
    return {
      files: currentFiles,
      issue: issue(
        "oversized_request",
        getErrorMessage("oversized_request"),
      ),
    };
  }

  const newSelections = filesToAdd.map((file) => ({
    id: crypto.randomUUID(),
    file,
  }));

  return {
    files: config.multiple ? [...currentFiles, ...newSelections] : newSelections.slice(0, 1),
  };
}

export function hasMinimumFiles(
  config: ToolConfig,
  files: readonly SelectedFile[],
): boolean {
  return files.length >= config.minFiles;
}

interface PageInterval {
  readonly start: number;
  readonly end: number;
}

export function validateSplitRanges(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Enter at least one page or range, such as 1-3,5,8-10.";
  }

  const tokens = trimmed.split(",");
  if (tokens.some((token) => !token.trim())) {
    return "Remove empty entries and use a format like 1-3,5,8-10.";
  }

  const intervals: PageInterval[] = [];
  for (const token of tokens) {
    const match = token.trim().match(/^(\d+)(?:-(\d+))?$/);
    if (!match) {
      return "Use whole page numbers and ranges like 1-3,5,8-10.";
    }

    const start = Number(match[1]);
    const end = Number(match[2] ?? match[1]);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < 1) {
      return "Page numbers must start at 1.";
    }
    if (end < start) {
      return "A page range must run from a lower page to a higher page.";
    }

    if (intervals.some((interval) => start <= interval.end && end >= interval.start)) {
      return "Page ranges cannot contain duplicate or overlapping pages.";
    }
    intervals.push({ start, end });
  }

  return undefined;
}
