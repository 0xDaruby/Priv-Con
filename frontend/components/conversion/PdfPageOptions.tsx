interface PdfPageOptionsProps {
  readonly pages: string;
  readonly onPagesChange: (value: string) => void;
  readonly pageError?: string;
  readonly kind: "rotate" | "pdfToJpg";
  readonly angle: string;
  readonly onAngleChange: (value: string) => void;
  readonly dpi: string;
  readonly onDpiChange: (value: string) => void;
  readonly quality: string;
  readonly onQualityChange: (value: string) => void;
  readonly imageError?: string;
}

export function PdfPageOptions({
  pages,
  onPagesChange,
  pageError,
  kind,
  angle,
  onAngleChange,
  dpi,
  onDpiChange,
  quality,
  onQualityChange,
  imageError,
}: PdfPageOptionsProps) {
  return (
    <fieldset className="split-options pdf-page-options">
      <legend>{kind === "rotate" ? "Rotation options" : "JPG options"}</legend>
      <div className="range-field">
        <label htmlFor="selected-pages">Pages (optional)</label>
        <input
          aria-describedby="selected-pages-guidance"
          aria-invalid={Boolean(pageError)}
          id="selected-pages"
          maxLength={16_384}
          onChange={(event) => onPagesChange(event.target.value)}
          placeholder="All pages, or 1-3,5"
          type="text"
          value={pages}
        />
        <p id="selected-pages-guidance" className={pageError ? "range-error" : undefined}>
          {pageError || "Leave blank for all pages. Use 1-based ranges like 1-3,5 without duplicates. Original page order is preserved."}
        </p>
      </div>
      {kind === "rotate" ? (
        <>
          <div className="range-field">
            <label htmlFor="rotation-angle">Clockwise rotation</label>
            <select id="rotation-angle" onChange={(event) => onAngleChange(event.target.value)} value={angle}>
              <option value="90">90 degrees clockwise</option>
              <option value="180">180 degrees</option>
              <option value="270">270 degrees clockwise</option>
            </select>
          </div>
          <p className="expected-output">Rotation is added to each selected page&apos;s existing orientation. Digitally signed PDFs cannot be rotated.</p>
        </>
      ) : (
        <>
          <div className="range-field image-option-field">
            <label htmlFor="render-dpi">Resolution (DPI)</label>
            <input
              aria-describedby="image-options-guidance"
              aria-invalid={Boolean(imageError)}
              id="render-dpi"
              min={72}
              max={300}
              step={1}
              onChange={(event) => onDpiChange(event.target.value)}
              type="number"
              value={dpi}
            />
          </div>
          <div className="range-field image-option-field">
            <label htmlFor="jpg-quality">JPG quality</label>
            <input
              aria-describedby="image-options-guidance"
              aria-invalid={Boolean(imageError)}
              id="jpg-quality"
              min={40}
              max={95}
              step={1}
              onChange={(event) => onQualityChange(event.target.value)}
              type="number"
              value={quality}
            />
          </div>
          <p className="expected-output" id="image-options-guidance" role={imageError ? "alert" : undefined}>
            {imageError || "Resolution: 72-300 DPI. Quality: 40-95. Higher settings use more memory and create larger images."}
          </p>
          <p className="expected-output"><strong>Expected output:</strong> one selected page becomes a JPG; multiple pages become a ZIP. Pages are rendered on a white background. This does not extract individual embedded images.</p>
        </>
      )}
    </fieldset>
  );
}
