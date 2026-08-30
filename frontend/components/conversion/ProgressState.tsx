import { Progress } from "@/components/ui/progress";

interface ProgressStateProps {
  readonly files: readonly File[];
  readonly onCancel: () => void;
}

export function ProgressState({ files, onCancel }: ProgressStateProps) {
  const selectedFilesLabel =
    files.length === 1 ? files[0]?.name : `${files.length} files selected`;
  const processingMessage =
    files.length === 1
      ? "This file is being processed locally in memory."
      : "These files are being processed locally in memory.";

  return (
    <section
      aria-busy="true"
      aria-live="polite"
      className="state-panel processing-panel"
    >
      <div className="state-heading">
        <p className="configuration-eyebrow">Convert &amp; download</p>
        <h1>Processing locally…</h1>
        <p>This usually takes less than a minute. Keep this tab open.</p>
      </div>
      <div className="processing-details">
        <div className="processing-summary">
          <span className="processing-summary-label">Currently processing</span>
          <strong title={selectedFilesLabel}>{selectedFilesLabel}</strong>
          <p>{processingMessage}</p>
        </div>
        <Progress label="Conversion progress" status="Processing locally…" />
      </div>
      <button className="secondary-action" onClick={onCancel} type="button">
        Cancel
      </button>
    </section>
  );
}
