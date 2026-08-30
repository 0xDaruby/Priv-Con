interface ProgressProps {
  readonly label: string;
  readonly status: string;
}

export function Progress({ label, status }: ProgressProps) {
  return (
    <div className="conversion-progress">
      <div className="conversion-progress-caption">
        <strong>{label}</strong>
        <span>{status}</span>
      </div>
      <div
        aria-label={label}
        aria-valuetext={status}
        className="conversion-progress-track"
        role="progressbar"
      >
        <span aria-hidden="true" className="conversion-progress-indicator" />
      </div>
    </div>
  );
}
