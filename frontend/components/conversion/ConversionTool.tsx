"use client";

import { useState } from "react";

import { FileListPreview } from "@/components/conversion/FileListPreview";
import { ErrorMessage } from "@/components/conversion/ErrorMessage";
import { PdfToWordOptions } from "@/components/conversion/PdfToWordOptions";
import { PdfPageOptions } from "@/components/conversion/PdfPageOptions";
import { PageNumbersOptions } from "@/components/conversion/PdfOverlayOptions";
import { WatermarkWorkspace } from "@/components/conversion/WatermarkWorkspace";
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
import { BACKEND_LIMITS } from "@/lib/constants";
import { validatePdfPages, validateJpgOptions } from "@/lib/pdf-options";
import {
  DEFAULT_WATERMARK_OPTIONS, DEFAULT_PAGE_NUMBER_OPTIONS,
  validateWatermarkOptions, validatePageNumberOptions,
  buildWatermarkFields, buildPageNumberFields,
  type WatermarkOptionFields, type PageNumberOptionFields,
} from "@/lib/pdf-overlay-options";
import type {
  ClientValidationIssue,
  ConversionExtraFields,
  PdfToWordMode,
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
  const [pdfToWordMode, setPdfToWordMode] = useState<PdfToWordMode>("editable");
  const [pages, setPages] = useState("");
  const [angle, setAngle] = useState("90");
  const [dpi, setDpi] = useState("144");
  const [quality, setQuality] = useState("85");
  const [watermarkOptions, setWatermarkOptions] = useState<WatermarkOptionFields>(DEFAULT_WATERMARK_OPTIONS);
  const [numberOptions, setNumberOptions] = useState<PageNumberOptionFields>(DEFAULT_PAGE_NUMBER_OPTIONS);
  const [watermarkImage, setWatermarkImage] = useState<File>();
  const [watermarkPageCount, setWatermarkPageCount] = useState<number>();
  const conversion = useConversion(config);

  const handleFilesSelected = (incomingFiles: readonly File[]) => {
    const result = validateFileSelection(config, incomingFiles, files);
    setValidationIssue(result.issue);
    setFiles(result.files);
    if (!result.issue && config.id === "watermark" && result.files !== files) setWatermarkPageCount(undefined);
    if (!result.issue && config.id === "watermark" && files.length > 0 && result.files !== files) {
      setWatermarkImage(undefined);
    }
    if (!result.issue && conversion.phase === "error") {
      conversion.retry();
    }
  };

  const handleRemove = (id: string) => {
    setFiles((current) => current.filter((item) => item.id !== id));
    setValidationIssue(undefined);
    if (config.id === "watermark") setWatermarkImage(undefined);
    if (config.id === "watermark") setWatermarkPageCount(undefined);
  };

  const isReady = hasMinimumFiles(config, files);
  const rangeError = splitMode === "ranges"
    ? validateSplitRanges(splitRanges)
    : undefined;
  const splitReady = config.id !== "split" ||
    splitMode === "every_page" ||
    (splitMode === "ranges" && !rangeError);
  const hasOverlayOptions = config.id === "watermark" || config.id === "pageNumbers";
  const hasPageOptions = config.id === "rotate" || config.id === "pdfToJpg" || hasOverlayOptions;
  const pageError = hasPageOptions ? validatePdfPages(pages, config.id === "watermark" ? watermarkPageCount : undefined) : undefined;
  const imageError = config.id === "pdfToJpg" ? validateJpgOptions(dpi, quality) : undefined;
  const rotationReady = config.id !== "rotate" || ["90", "180", "270"].includes(angle);
  const overlayError = config.id === "watermark"
    ? validateWatermarkOptions(watermarkOptions, watermarkImage, BACKEND_LIMITS.maxFileBytes)
    : config.id === "pageNumbers" ? validatePageNumberOptions(numberOptions) : undefined;
  const canConvert = isReady && splitReady && !pageError && !imageError && !overlayError && rotationReady;
  const fileHint = isReady
    ? config.id === "split"
      ? canConvert
        ? "Split options are ready to process locally."
        : "Choose how to split this PDF to continue."
      : config.id === "pdfToWord"
        ? pdfToWordMode === "editable"
          ? "Editable layout reconstruction is ready to run locally."
          : "Appearance-preserving conversion is ready to run locally."
      : hasPageOptions
        ? canConvert
          ? "PDF options are ready to process locally."
          : "Check the PDF options to continue."
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
    setPdfToWordMode("editable");
    setPages("");
    setAngle("90");
    setDpi("144");
    setQuality("85");
    setWatermarkOptions(DEFAULT_WATERMARK_OPTIONS);
    setNumberOptions(DEFAULT_PAGE_NUMBER_OPTIONS);
    setWatermarkImage(undefined);
    setWatermarkPageCount(undefined);
  };

  const startConversion = () => {
    if (!canConvert) return;
    const extraFields: ConversionExtraFields = config.id === "watermark"
      ? buildWatermarkFields(watermarkOptions, pages, watermarkImage)
      : config.id === "pageNumbers"
        ? buildPageNumberFields(numberOptions, pages)
      : config.id === "split" && splitMode
      ? {
          mode: splitMode,
          ...(splitMode === "ranges" ? { ranges: splitRanges.trim() } : {}),
        }
      : config.id === "pdfToWord"
        ? { mode: pdfToWordMode }
        : config.id === "rotate"
          ? { pages: pages.trim(), angle }
          : config.id === "pdfToJpg"
            ? { pages: pages.trim(), dpi, quality }
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
    <AppShell currentStep={currentStep} navigationState={isConverting ? "processing" : files.length > 0 && conversion.phase !== "success" ? "draft" : "idle"}>
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
      ) : config.id === "watermark" ? (
        <WatermarkWorkspace
          config={config} selected={files[0]} onFilesSelected={handleFilesSelected}
          onRemove={() => handleRemove(files[0].id)} options={watermarkOptions}
          onOptionsChange={setWatermarkOptions} image={watermarkImage} onImageChange={setWatermarkImage}
          pages={pages} onPagesChange={setPages} onPageCount={setWatermarkPageCount}
          pageError={pageError} optionError={overlayError} validationError={validationIssue?.message}
          canConvert={canConvert} onConvert={startConversion}
        />
      ) : (
        <section
          aria-labelledby="configuration-title"
          className="configuration-surface"
          data-tool={config.id}
        >
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

          {config.id === "pdfToWord" ? (
            <PdfToWordOptions
              mode={pdfToWordMode}
              onModeChange={setPdfToWordMode}
            />
          ) : null}

          {config.id === "rotate" || config.id === "pdfToJpg" ? (
            <PdfPageOptions
              angle={angle}
              dpi={dpi}
              imageError={imageError}
              kind={config.id}
              onAngleChange={setAngle}
              onDpiChange={setDpi}
              onPagesChange={setPages}
              onQualityChange={setQuality}
              pageError={pageError}
              pages={pages}
              quality={quality}
            />
          ) : null}

          {config.id === "pageNumbers" ? <PageNumbersOptions
            options={numberOptions} onChange={setNumberOptions}
            optionError={overlayError} pages={pages} onPagesChange={setPages} pageError={pageError}
          /> : null}

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
