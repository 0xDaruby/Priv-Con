import type { PdfToWordMode } from "@/lib/types";

interface PdfToWordOptionsProps {
  readonly mode: PdfToWordMode;
  readonly onModeChange: (mode: PdfToWordMode) => void;
}

export function PdfToWordOptions({
  mode,
  onModeChange,
}: PdfToWordOptionsProps) {
  return (
    <fieldset className="pdf-word-options">
      <legend>Choose the Word output</legend>
      <label className="conversion-mode-choice">
        <input
          checked={mode === "editable"}
          name="pdf-to-word-mode"
          onChange={() => onModeChange("editable")}
          type="radio"
        />
        <span>
          <strong>Editable Word</strong>
          <small>
            Best for editing. Reconstructs text, colors, images, tables, columns,
            links, and positioning where possible.
          </small>
          <em>Recommended</em>
        </span>
      </label>
      <label className="conversion-mode-choice">
        <input
          checked={mode === "preserve_appearance"}
          name="pdf-to-word-mode"
          onChange={() => onModeChange("preserve_appearance")}
          type="radio"
        />
        <span>
          <strong>Preserve Appearance</strong>
          <small>
            Best for difficult PDFs. Keeps every page visually faithful, but
            page content is not directly editable.
          </small>
        </span>
      </label>
    </fieldset>
  );
}
