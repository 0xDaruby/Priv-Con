"use client";

import { PdfWatermarkPreview } from "@/components/conversion/PdfWatermarkPreview";
import { UploadDropzone } from "@/components/conversion/UploadDropzone";
import { WatermarkControls } from "@/components/conversion/WatermarkControls";
import type { WatermarkOptionFields } from "@/lib/pdf-overlay-options";
import type { SelectedFile, ToolConfig } from "@/lib/types";

interface WatermarkWorkspaceProps {
  readonly config: ToolConfig;
  readonly selected: SelectedFile;
  readonly onFilesSelected: (files: readonly File[]) => void;
  readonly onRemove: () => void;
  readonly options: WatermarkOptionFields;
  readonly onOptionsChange: (options: WatermarkOptionFields) => void;
  readonly image?: File;
  readonly onImageChange: (image?: File) => void;
  readonly pages: string;
  readonly onPagesChange: (pages: string) => void;
  readonly onPageCount: (count: number | undefined) => void;
  readonly pageError?: string;
  readonly optionError?: string;
  readonly validationError?: string;
  readonly canConvert: boolean;
  readonly onConvert: () => void;
}

export function WatermarkWorkspace(props: WatermarkWorkspaceProps) {
  return (
    <section className="watermark-workspace" aria-label="Watermark PDF workspace">
      <div className="watermark-document">
        <header className="watermark-document-toolbar">
          <div>
            <h1>Watermark PDF</h1>
            <p title={props.selected.file.name}>{props.selected.file.name}</p>
          </div>
          <div className="watermark-document-actions">
            <UploadDropzone compact config={props.config} onFilesSelected={props.onFilesSelected} />
            <button className="watermark-remove-document" type="button" onClick={props.onRemove} aria-label={`Remove ${props.selected.file.name}`}>Remove PDF</button>
          </div>
        </header>
        {props.validationError ? <p className="inline-validation" role="alert">{props.validationError}</p> : null}
        <PdfWatermarkPreview file={props.selected.file} options={props.options} image={props.image} pages={props.pages} pageError={props.pageError} onPageCount={props.onPageCount} />
      </div>
      <aside className="watermark-settings" aria-labelledby="watermark-settings-title">
        <header className="watermark-settings-heading"><h2 id="watermark-settings-title">Watermark options</h2></header>
        <WatermarkControls options={props.options} onChange={props.onOptionsChange} image={props.image} onImageChange={props.onImageChange} pages={props.pages} onPagesChange={props.onPagesChange} pageError={props.pageError} optionError={props.optionError} />
        <footer className="watermark-submit">
          <button className="primary-action" disabled={!props.canConvert} type="button" onClick={props.onConvert}>Add watermark <span aria-hidden="true">→</span></button>
          <p>Processed on your device. Nothing is uploaded elsewhere.</p>
        </footer>
      </aside>
    </section>
  );
}
