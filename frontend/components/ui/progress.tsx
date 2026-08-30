interface ProgressProps {
  readonly label: string;
  readonly status: string;
  readonly value?: number;
}

export function Progress({ label, status, value }: ProgressProps) {
  const normalizedValue = typeof value === "number"
    ? Math.max(0, Math.min(100, Math.round(value)))
    : undefined;
  const valueLabel = typeof normalizedValue === "number"
    ? `${normalizedValue}%`
    : "In progress";

  return (
    <div className="conversion-progress">
      <div className="conversion-progress-caption">
        <strong>{label}</strong>
        <span>{valueLabel}</span>
      </div>
      <div
        aria-label={label}
        aria-valuemax={normalizedValue === undefined ? undefined : 100}
        aria-valuemin={normalizedValue === undefined ? undefined : 0}
        aria-valuenow={normalizedValue}
        aria-valuetext={`${valueLabel}. ${status}`}
        className="conversion-progress-track"
        role="progressbar"
      >
        <span
          aria-hidden="true"
          className={`conversion-progress-indicator ${
            normalizedValue === undefined
              ? "conversion-progress-indicator--indeterminate"
              : "conversion-progress-indicator--determinate"
          }`}
          style={normalizedValue === undefined
            ? undefined
            : { width: `${normalizedValue}%` }}
        />
      </div>
      <p className="conversion-progress-status">{status}</p>
    </div>
  );
}
