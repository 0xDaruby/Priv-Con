import { useRef } from "react";
import {
  NUMBER_POSITIONS, OVERLAY_POSITIONS, pageNumberSample,
  type PageNumberOptionFields, type WatermarkOptionFields,
} from "@/lib/pdf-overlay-options";

interface PagesProps {
  readonly pages: string;
  readonly onPagesChange: (value: string) => void;
  readonly pageError?: string;
}

function PagesField({ pages, onPagesChange, pageError }: PagesProps) {
  return <div className="range-field">
    <label htmlFor="overlay-pages">Pages (optional)</label>
    <input id="overlay-pages" aria-describedby="overlay-pages-guidance" aria-invalid={Boolean(pageError)} maxLength={16_384} onChange={(event) => onPagesChange(event.target.value)} placeholder="All pages, or 1-3,5" value={pages} />
    <p id="overlay-pages-guidance" className={pageError ? "range-error" : undefined}>{pageError || "Leave blank for all pages. Use ranges like 1-3,5 without duplicates. Original page order is preserved."}</p>
  </div>;
}

function PositionField({ value, onChange, numbers = false }: { readonly value: string; readonly onChange: (value: string) => void; readonly numbers?: boolean }) {
  return <div className="range-field">
    <label htmlFor="overlay-position">Position</label>
    <select id="overlay-position" value={value} onChange={(event) => onChange(event.target.value)}>
      {(numbers ? NUMBER_POSITIONS : OVERLAY_POSITIONS).map((position) => <option key={position} value={position}>{position === "center" ? "Center" : position.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ")}</option>)}
    </select>
  </div>;
}

interface WatermarkOptionsProps extends PagesProps {
  readonly options: WatermarkOptionFields;
  readonly onChange: (options: WatermarkOptionFields) => void;
  readonly image?: File;
  readonly onImageChange: (image?: File) => void;
  readonly optionError?: string;
}

export function WatermarkOptions({ options, onChange, image, onImageChange, optionError, ...pages }: WatermarkOptionsProps) {
  const imageInput = useRef<HTMLInputElement>(null);
  return <fieldset className="split-options pdf-overlay-options">
    <legend>Watermark options</legend>
    <PagesField {...pages} />
    <div className="split-mode-options">
      <label><input type="radio" name="watermark-kind" checked={options.kind === "text"} onChange={() => { onChange({ ...options, kind: "text" }); onImageChange(undefined); }} /> Text watermark</label>
      <label><input type="radio" name="watermark-kind" checked={options.kind === "image"} onChange={() => onChange({ ...options, kind: "image" })} /> Image watermark</label>
    </div>
    {options.kind === "text" ? <div className="range-field">
      <label htmlFor="watermark-text">Watermark text</label>
      <input id="watermark-text" aria-describedby="watermark-text-guidance overlay-options-error" maxLength={120} onChange={(event) => onChange({ ...options, text: event.target.value })} value={options.text} />
      <p id="watermark-text-guidance">Built-in Helvetica supports English and Western Latin text. For other scripts, choose an image watermark.</p>
    </div> : <div className="range-field watermark-image-field">
      <label htmlFor="watermark-image">Watermark image</label>
      <input ref={imageInput} id="watermark-image" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" aria-describedby="watermark-image-guidance overlay-options-error" onChange={(event) => { const selected = event.target.files?.[0]; if (selected) onImageChange(selected); event.target.value = ""; }} />
      <p id="watermark-image-guidance">One PNG, JPG, JPEG or WEBP; up to 50 MB and 16 million pixels. Transparency is preserved. Animated images use their first frame.</p>
      {image ? <div className="watermark-selected-image"><span>{image.name}</span><button className="remove-file" type="button" onClick={() => { onImageChange(undefined); imageInput.current?.focus(); }}>Remove image</button></div> : null}
    </div>}
    <div className="overlay-controls">
      <PositionField value={options.position} onChange={(position) => onChange({ ...options, position })} />
      <div className="range-field"><label htmlFor="watermark-angle">Counterclockwise angle (degrees)</label><input id="watermark-angle" type="number" min={-180} max={180} step="any" value={options.angle} onChange={(event) => onChange({ ...options, angle: event.target.value })} aria-describedby="overlay-options-error" /></div>
      <div className="range-field"><label htmlFor="watermark-opacity">Opacity (0.1–1)</label><input id="watermark-opacity" type="number" min={0.1} max={1} step={0.05} value={options.opacity} onChange={(event) => onChange({ ...options, opacity: event.target.value })} aria-describedby="overlay-options-error" /></div>
      <div className="range-field"><label htmlFor="watermark-scale">Scale (0.1–1)</label><input id="watermark-scale" type="number" min={0.1} max={1} step={0.05} value={options.scale} onChange={(event) => onChange({ ...options, scale: event.target.value })} aria-describedby="overlay-options-error" /></div>
      <div className="range-field"><label htmlFor="watermark-margin">Margin (PDF points)</label><input id="watermark-margin" type="number" min={12} max={144} step="any" value={options.margin} onChange={(event) => onChange({ ...options, margin: event.target.value })} aria-describedby="overlay-options-error" /></div>
    </div>
    <p id="overlay-options-error" className={optionError ? "range-error" : "expected-output"} role={optionError ? "alert" : undefined}>{optionError || "Options are ready. The watermark is placed over existing content."}</p>
    <p className="expected-output">Scale is the maximum fraction of available width and height, after margins. The watermark fits without stretching. Source text remains selectable. Digitally signed PDFs cannot be changed.</p>
  </fieldset>;
}

interface PageNumbersOptionsProps extends PagesProps {
  readonly options: PageNumberOptionFields;
  readonly onChange: (options: PageNumberOptionFields) => void;
  readonly optionError?: string;
}

export function PageNumbersOptions({ options, onChange, optionError, ...pages }: PageNumbersOptionsProps) {
  const sample = pageNumberSample(options);
  return <fieldset className="split-options pdf-overlay-options">
    <legend>Page number options</legend>
    <PagesField {...pages} />
    <div className="overlay-controls">
      <PositionField numbers value={options.position} onChange={(position) => onChange({ ...options, position })} />
      <div className="range-field"><label htmlFor="page-number-start">Starting number</label><input id="page-number-start" type="number" min={1} max={999999} step={1} value={options.start} onChange={(event) => onChange({ ...options, start: event.target.value })} aria-describedby="number-options-error" /></div>
      <div className="range-field"><label htmlFor="page-number-format">Label format</label><select id="page-number-format" value={options.format} onChange={(event) => onChange({ ...options, format: event.target.value })}><option value="number">Number only</option><option value="page">Page n</option></select></div>
      <div className="range-field"><label htmlFor="page-number-size">Font size (PDF points)</label><input id="page-number-size" type="number" min={8} max={48} step="any" value={options.font_size} onChange={(event) => onChange({ ...options, font_size: event.target.value })} aria-describedby="number-options-error" /></div>
      <div className="range-field"><label htmlFor="page-number-margin">Margin (PDF points)</label><input id="page-number-margin" type="number" min={12} max={144} step="any" value={options.margin} onChange={(event) => onChange({ ...options, margin: event.target.value })} aria-describedby="number-options-error" /></div>
    </div>
    <p className="expected-output" aria-live="polite"><strong>First label:</strong> {sample ?? "Enter a valid starting number."}</p>
    <p id="number-options-error" className={optionError ? "range-error" : "expected-output"} role={optionError ? "alert" : undefined}>{optionError || "Numbers advance once per selected page in original document order. For pages 1,3 starting at 5, the labels are 5 and 6."}</p>
    <p className="expected-output">Labels are added over existing content in Helvetica. Source text, page dimensions and order are preserved. Digitally signed PDFs cannot be changed.</p>
  </fieldset>;
}
