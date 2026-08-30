interface ProgressStateProps {
  readonly files: readonly File[];
  readonly onCancel: () => void;
}

export function ProgressState({ files, onCancel }: ProgressStateProps) {
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
      <div className="processing-summary">
        <strong>{files.length === 1 ? files[0]?.name : `${files.length} files selected`}</strong>
        <span>Selected files are being processed in memory.</span>
      </div>
      <div className="indeterminate-progress" aria-hidden="true">
        <span />
      </div>
      <button className="secondary-action" onClick={onCancel} type="button">
        Cancel
      </button>
    </section>
  );
}
