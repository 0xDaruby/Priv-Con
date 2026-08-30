import type { SplitMode } from "@/lib/types";

interface SplitOptionsProps {
  readonly mode: SplitMode | "";
  readonly onModeChange: (mode: SplitMode) => void;
  readonly onRangesChange: (value: string) => void;
  readonly rangeError?: string;
  readonly ranges: string;
}

export function SplitOptions({
  mode,
  onModeChange,
  onRangesChange,
  rangeError,
  ranges,
}: SplitOptionsProps) {
  const rangeCount = ranges.trim() ? ranges.split(",").length : 0;
  const expectedOutput = mode === "every_page"
    ? "A ZIP containing one PDF per page"
    : mode === "ranges" && rangeCount === 1
      ? "One PDF containing the selected range"
      : mode === "ranges" && rangeCount > 1
        ? "A ZIP containing one PDF per range"
        : "Choose an option to see the expected output";

  return (
    <fieldset className="split-options">
      <legend>How should this PDF be split?</legend>
      <label className="split-choice">
        <input
          checked={mode === "every_page"}
          name="split-mode"
          onChange={() => onModeChange("every_page")}
          type="radio"
        />
        <span>
          <strong>Split every page into separate files</strong>
          <small>Each page becomes its own PDF inside a ZIP.</small>
        </span>
      </label>
      <label className="split-choice">
        <input
          checked={mode === "ranges"}
          name="split-mode"
          onChange={() => onModeChange("ranges")}
          type="radio"
        />
        <span>
          <strong>Split by page range(s)</strong>
          <small>Use 1-based pages, preserving the order you enter.</small>
        </span>
      </label>

      {mode === "ranges" ? (
        <div className="range-field">
          <label htmlFor="page-ranges">Page ranges</label>
          <input
            aria-describedby="range-guidance"
            aria-invalid={Boolean(rangeError)}
            id="page-ranges"
            onChange={(event) => onRangesChange(event.target.value)}
            placeholder="1-3,5,8-10"
            type="text"
            value={ranges}
          />
          <p id="range-guidance" className={rangeError ? "range-error" : undefined}>
            {rangeError || "Separate ranges with commas. Duplicate and overlapping pages are not allowed."}
          </p>
        </div>
      ) : null}

      <p className="expected-output">
        <strong>Expected output:</strong> {expectedOutput}.
      </p>
    </fieldset>
  );
}
