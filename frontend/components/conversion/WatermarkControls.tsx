"use client";

import { useRef } from "react";

import { OVERLAY_POSITIONS, type WatermarkOptionFields } from "@/lib/pdf-overlay-options";

interface WatermarkControlsProps {
  readonly options: WatermarkOptionFields;
  readonly onChange: (options: WatermarkOptionFields) => void;
  readonly image?: File;
  readonly onImageChange: (image?: File) => void;
  readonly optionError?: string;
  readonly pages: string;
  readonly onPagesChange: (value: string) => void;
  readonly pageError?: string;
}

const ROTATIONS = [
  { value: "0", label: "No rotation" },
  { value: "-45", label: "45° clockwise" },
  { value: "45", label: "45° counterclockwise" },
  { value: "-90", label: "90° clockwise" },
  { value: "90", label: "90° counterclockwise" },
  { value: "180", label: "180°" },
] as const;

function positionLabel(position: string): string {
  return position.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

function percentage(value: string): string {
  if (!value.trim()) return "";
  const number = Number(value);
  return Number.isFinite(number) ? String(Number((number * 100).toPrecision(12))) : "";
}

function fraction(value: string): string {
  return value.trim() ? String(Number(value) / 100) : "";
}

function PercentControl({ id, label, value, onChange }: {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
}) {
  const percent = percentage(value);
  const sliderValue = percent === "" || !Number.isFinite(Number(percent)) ? 10 : Math.min(100, Math.max(10, Number(percent)));
  return (
    <div className="watermark-control-field">
      <div className="watermark-control-label-row">
        <label htmlFor={id}>{label}</label>
        <div className="watermark-percent-input">
          <input id={id} type="number" min={10} max={100} step="any" value={percent} onChange={(event) => onChange(fraction(event.target.value))} aria-describedby="watermark-options-feedback" />
          <span aria-hidden="true">%</span>
        </div>
      </div>
      <input className="watermark-range" type="range" min={10} max={100} step={1} value={sliderValue} aria-label={`${label} slider`} onChange={(event) => onChange(fraction(event.target.value))} />
    </div>
  );
}

export function WatermarkControls({ options, onChange, image, onImageChange, optionError, pages, onPagesChange, pageError }: WatermarkControlsProps) {
  const imageInput = useRef<HTMLInputElement>(null);
  const selectedPages = pages.trim().length > 0;
  const rotationPreset = ROTATIONS.find((rotation) => Number(rotation.value) === Number(options.angle))?.value ?? "custom";

  return (
    <div className="watermark-controls">
      <fieldset className="watermark-control-group watermark-type-group">
        <legend className="watermark-sr-only">Watermark type</legend>
        <div className="watermark-type-choices">
          <label className="watermark-type-choice">
            <input type="radio" name="watermark-type" value="text" checked={options.kind === "text"} onChange={() => { onChange({ ...options, kind: "text" }); onImageChange(undefined); }} />
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M4 5h16M12 5v15M8 20h8M4 5v3M20 5v3" /></svg>
            <span>Text</span>
          </label>
          <label className="watermark-type-choice">
            <input type="radio" name="watermark-type" value="image" checked={options.kind === "image"} onChange={() => onChange({ ...options, kind: "image" })} />
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="3" y="4" width="18" height="16" rx="1" /><circle cx="8" cy="9" r="1.5" /><path d="m4 18 6-6 4 4 3-3 4 5" /></svg>
            <span>Image</span>
          </label>
        </div>
      </fieldset>

      {options.kind === "text" ? (
        <div className="watermark-control-field">
          <label htmlFor="watermark-text">Watermark text</label>
          <input id="watermark-text" type="text" maxLength={120} value={options.text} onChange={(event) => onChange({ ...options, text: event.target.value })} aria-describedby="watermark-text-guidance watermark-options-feedback" />
          <p id="watermark-text-guidance" className="watermark-control-hint">Helvetica · English and Western Latin. Use an image for other scripts.</p>
        </div>
      ) : (
        <div className="watermark-control-field">
          <label htmlFor="watermark-image">Watermark image</label>
          <input ref={imageInput} id="watermark-image" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" aria-describedby="watermark-image-guidance watermark-options-feedback" onChange={(event) => { const file = event.target.files?.[0]; if (file) onImageChange(file); event.target.value = ""; }} />
          {image ? <div className="watermark-chosen-image"><span title={image.name}>{image.name}</span><button type="button" onClick={() => { onImageChange(undefined); imageInput.current?.focus(); }}>Remove image</button></div> : null}
          <p id="watermark-image-guidance" className="watermark-control-hint">PNG, JPG or WEBP · up to 50 MB and 16 million pixels. Animated images use the first frame.</p>
        </div>
      )}

      <fieldset className="watermark-control-group">
        <legend>Position</legend>
        <div className="watermark-position-row">
          <div className="watermark-position-grid">
            {OVERLAY_POSITIONS.map((position) => <label key={position} className="watermark-position-choice" title={positionLabel(position)}>
              <input type="radio" name="watermark-position" value={position} checked={options.position === position} onChange={() => onChange({ ...options, position })} />
              <span aria-hidden="true" className="watermark-position-dot" />
              <span className="watermark-sr-only">{positionLabel(position)}</span>
            </label>)}
          </div>
          <p className="watermark-control-hint">{positionLabel(options.position)}<br />Over PDF content</p>
        </div>
      </fieldset>

      <PercentControl id="watermark-opacity" label="Opacity" value={options.opacity} onChange={(opacity) => onChange({ ...options, opacity })} />
      <PercentControl id="watermark-scale" label="Size" value={options.scale} onChange={(scale) => onChange({ ...options, scale })} />

      <div className="watermark-control-field">
        <label htmlFor="watermark-rotation">Rotation</label>
        <select id="watermark-rotation" value={rotationPreset} onChange={(event) => { if (event.target.value !== "custom") onChange({ ...options, angle: event.target.value }); }}>
          {ROTATIONS.map((rotation) => <option key={rotation.value} value={rotation.value}>{rotation.label}</option>)}
          <option value="custom" disabled>Custom angle</option>
        </select>
      </div>

      <fieldset className="watermark-control-group">
        <legend>Pages</legend>
        <div className="watermark-page-choices">
          <label><input type="radio" name="watermark-page-scope" checked={!selectedPages} onChange={() => onPagesChange("")} /> All pages</label>
          <label><input type="radio" name="watermark-page-scope" checked={selectedPages} onChange={() => { if (!selectedPages) onPagesChange("1"); }} /> Selected pages</label>
        </div>
        <div className="watermark-control-field">
          <label htmlFor="watermark-pages" className="watermark-sr-only">Page ranges (optional)</label>
          <input id="watermark-pages" type="text" maxLength={16_384} placeholder="All pages, or 1-3,5" value={pages} aria-invalid={Boolean(pageError)} aria-describedby="watermark-pages-guidance" onChange={(event) => onPagesChange(event.target.value)} />
        </div>
        <p id="watermark-pages-guidance" className={`watermark-control-hint${pageError ? " watermark-control-error" : ""}`}>{pageError || (selectedPages ? "Use page numbers or ranges, such as 1-3,5." : "The watermark will appear on every page.")}</p>
      </fieldset>

      <details className="watermark-more-options">
        <summary>Precise adjustments</summary>
        <div className="watermark-control-field">
          <label htmlFor="watermark-angle">Angle (degrees counterclockwise)</label>
          <input id="watermark-angle" type="number" min={-180} max={180} step="any" value={options.angle} onChange={(event) => onChange({ ...options, angle: event.target.value })} aria-describedby="watermark-options-feedback" />
        </div>
        <div className="watermark-control-field">
          <label htmlFor="watermark-margin">Margin (PDF points)</label>
          <input id="watermark-margin" type="number" min={12} max={144} step="any" value={options.margin} onChange={(event) => onChange({ ...options, margin: event.target.value })} aria-describedby="watermark-options-feedback" />
        </div>
      </details>
      <p id="watermark-options-feedback" className={`watermark-control-hint${optionError ? " watermark-control-error" : ""}`} role={optionError ? "alert" : undefined}>{optionError || "Watermarks are placed over existing content. Signed PDFs cannot be changed."}</p>
    </div>
  );
}
