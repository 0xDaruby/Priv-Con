import { Progress } from "@/components/ui/progress";
import type { ConversionProgress } from "@/lib/types";

interface ProgressStateProps {
  readonly files: readonly File[];
  readonly onCancel: () => void;
  readonly progress: ConversionProgress;
}

export function ProgressState({ files, onCancel, progress }: ProgressStateProps) {
  const selectedFilesLabel =
    files.length === 1 ? files[0]?.name : `${files.length} files selected`;
  const processingMessage =
    files.length === 1
      ? "This file is being processed locally on this machine."
      : "These files are being processed locally on this machine.";
  const heading = progress.stage === "uploading"
    ? "Uploading locally…"
    : progress.stage === "validating"
      ? "Validating locally…"
      : progress.stage === "finalizing"
        ? "Finalizing locally…"
        : progress.stage === "cancelling"
          ? "Cancelling locally…"
          : "Processing locally…";

  return (
    <section
      aria-busy="true"
      aria-live="polite"
      className="state-panel processing-panel"
    >
      <div className="state-heading">
        <p className="configuration-eyebrow">Convert &amp; download</p>
        <h1>{heading}</h1>
        <p>This usually takes less than a minute. Keep this tab open.</p>
      </div>
      <div className="processing-details">
        <div className="processing-summary">
          <span className="processing-summary-label">Currently processing</span>
          <strong title={selectedFilesLabel}>{selectedFilesLabel}</strong>
          <p>{processingMessage}</p>
        </div>
        <Progress
          label={progress.label}
          status={progress.message}
          value={progress.mode === "determinate" ? progress.percent : undefined}
        />
      </div>
      <button
        className="secondary-action"
        disabled={progress.stage === "cancelling"}
        onClick={onCancel}
        type="button"
      >
        {progress.stage === "cancelling" ? "Cancelling…" : "Cancel"}
      </button>
    </section>
  );
}
