import type { ProgressStep } from "@/lib/types";

const STAGES = [
  { step: 1, label: "Choose tool", compactLabel: "Choose" },
  { step: 2, label: "Add files", compactLabel: "Files" },
  { step: 3, label: "Convert & download", compactLabel: "Convert" },
] as const;

interface ProgressRailProps {
  readonly currentStep?: ProgressStep;
}

export function ProgressRail({ currentStep = 1 }: ProgressRailProps) {
  return (
    <nav className="progress-rail" aria-label="Conversion progress">
      <ol className="progress-list">
        {STAGES.map((stage, index) => {
          const isActive = stage.step === currentStep;
          const isComplete = stage.step < currentStep;

          return (
            <li className="progress-entry" key={stage.step}>
              {index > 0 ? (
                <span className="progress-connector" aria-hidden="true" />
              ) : null}
              <span
                aria-current={isActive ? "step" : undefined}
                className="progress-stage"
                data-active={isActive || undefined}
                data-complete={isComplete || undefined}
              >
                <span className="step-number">{stage.step}</span>
                <span className="progress-label-full">{stage.label}</span>
                <span className="progress-label-compact">{stage.compactLabel}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
