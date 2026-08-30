"use client";

import { useState } from "react";

import { FileListPreview } from "@/components/conversion/FileListPreview";
import { ErrorMessage } from "@/components/conversion/ErrorMessage";
import { ProgressState } from "@/components/conversion/ProgressState";
import { ReorderList } from "@/components/conversion/ReorderList";
import { SplitOptions } from "@/components/conversion/SplitOptions";
import { SuccessDownload } from "@/components/conversion/SuccessDownload";
import { UploadDropzone } from "@/components/conversion/UploadDropzone";
import { ErrorAlertIcon, PrivacyShieldCheckIcon } from "@/components/icons/PrivConIcons";
import { AppShell } from "@/components/shell/AppShell";
import { useConversion } from "@/hooks/useConversion";
import {
  hasMinimumFiles,
  validateFileSelection,
  validateSplitRanges,
} from "@/lib/file-validation";
import { formatFileCount } from "@/lib/format";
import type {
  ClientValidationIssue,
  SelectedFile,
  SplitMode,
  ToolConfig,
} from "@/lib/types";

interface ConversionToolProps {
  readonly config: ToolConfig;
}

export function ConversionTool({ config }: ConversionToolProps) {
  const [files, setFiles] = useState<readonly SelectedFile[]>([]);
  const [validationIssue, setValidationIssue] = useState<ClientValidationIssue>();
  const [splitMode, setSplitMode] = useState<SplitMode | "">("");
  const [splitRanges, setSplitRanges] = useState("");
  const conversion = useConversion(config);

  const handleFilesSelected = (incomingFiles: readonly File[]) => {
    const result = validateFileSelection(config, incomingFiles, files);
    setValidationIssue(result.issue);
    setFiles(result.files);
    if (!result.issue && conversion.phase === "error") {
      conversion.retry();
    }
  };

  const handleRemove = (id: string) => {
    setFiles((current) => current.filter((item) => item.id !== id));
    setValidationIssue(undefined);
  };

  const isReady = hasMinimumFiles(config, files);
  const rangeError = splitMode === "ranges"
    ? validateSplitRanges(splitRanges)
    : undefined;
  const splitReady = config.id !== "split" ||
    splitMode === "every_page" ||
    (splitMode === "ranges" && !rangeError);
  const canConvert = isReady && splitReady;
  const fileHint = isReady
    ? config.id === "split"
      ? canConvert
        ? "Split options are ready to process locally."
        : "Choose how to split this PDF to continue."
      : `${formatFileCount(files.length)} ready to process locally.`
    : config.minFiles > 1
      ? `Choose at least ${config.minFiles} files to continue.`
      : "Choose a file to continue.";

  const resetTool = () => {
    conversion.reset();
    setFiles([]);
    setValidationIssue(undefined);
    setSplitMode("");
    setSplitRanges("");
  };

  const startConversion = () => {
    const extraFields = config.id === "split" && splitMode
      ? {
          mode: splitMode,
          ...(splitMode === "ranges" ? { ranges: splitRanges.trim() } : {}),
        }
      : {};
    return conversion.convert(files.map(({ file }) => file), extraFields);
  };

  const isConverting = conversion.phase === "uploading" ||
    conversion.phase === "processing";
  const currentStep = isConverting ||
    conversion.phase === "success" ||
    conversion.phase === "error"
    ? 3
    : files.length > 0
      ? 2
      : 1;

  return (
    <AppShell currentStep={currentStep}>
      {isConverting && conversion.progress ? (
        <ProgressState
          files={files.map(({ file }) => file)}
          onCancel={conversion.cancel}
          progress={conversion.progress}
        />
      ) : conversion.phase === "success" && conversion.result ? (
        <SuccessDownload
          downloadUrl={conversion.result.url}
          filename={conversion.result.filename}
          onConvertAgain={resetTool}
          outputType={conversion.result.outputType}
        />
      ) : conversion.phase === "error" && conversion.error ? (
        <ErrorMessage
          fileCount={files.length}
          message={conversion.error.message}
          onEditFiles={conversion.retry}
        />
      ) : files.length === 0 ? (
        <UploadDropzone
          config={config}
          errorMessage={validationIssue?.message}
          onFilesSelected={handleFilesSelected}
        />
      ) : (
        <section className="configuration-surface" aria-labelledby="configuration-title">
          <header className="configuration-header">
            <div>
              <p className="configuration-eyebrow">Add files</p>
              <h1 id="configuration-title">{config.title}</h1>
              <p>
                {config.description} Accepted: <strong>{config.acceptedFormatLabel}</strong>
              </p>
            </div>
            <UploadDropzone
              compact
              config={config}
              onFilesSelected={handleFilesSelected}
            />
          </header>

          {validationIssue ? (
            <div className="inline-validation" role="alert">
              <ErrorAlertIcon />
              <p>{validationIssue.message}</p>
            </div>
          ) : null}

          {config.reorderable ? (
            <ReorderList
              config={config}
              items={files}
              onRemove={handleRemove}
              onReorder={setFiles}
            />
          ) : (
            <FileListPreview config={config} files={files} onRemove={handleRemove} />
          )}

          {config.id === "split" ? (
            <SplitOptions
              mode={splitMode}
              onModeChange={setSplitMode}
              onRangesChange={setSplitRanges}
              rangeError={rangeError}
              ranges={splitRanges}
            />
          ) : null}

          <footer className="configuration-actions">
            <div className="configuration-guidance">
              <p aria-live="polite">{fileHint}</p>
              <div className="compact-privacy">
                <PrivacyShieldCheckIcon />
                <span>
                  Files are processed entirely on this machine.
                  <br />
                  Nothing is uploaded anywhere.
                </span>
              </div>
            </div>
            <button
              className="primary-action convert-action"
              disabled={!canConvert}
              onClick={() => void startConversion()}
              type="button"
            >
              {config.convertLabel}
            </button>
          </footer>
        </section>
      )}
    </AppShell>
  );
}
