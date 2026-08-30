import { ErrorAlertIcon } from "@/components/icons/PrivConIcons";

interface ErrorMessageProps {
  readonly fileCount: number;
  readonly message: string;
  readonly onEditFiles: () => void;
}

export function ErrorMessage({ fileCount, message, onEditFiles }: ErrorMessageProps) {
  return (
    <section className="state-panel error-panel" aria-live="assertive">
      <ErrorAlertIcon className="state-icon" />
      <div className="state-heading">
        <p className="configuration-eyebrow">Conversion stopped</p>
        <h1>We couldn&apos;t finish this file</h1>
        <p>{message}</p>
        <p className="retained-files">
          {fileCount === 1 ? "Your selected file is still ready." : `${fileCount} selected files are still ready.`}
        </p>
      </div>
      <button className="primary-action state-primary" onClick={onEditFiles} type="button">
        Try again
      </button>
      <button className="secondary-action" onClick={onEditFiles} type="button">
        Edit selected files
      </button>
    </section>
  );
}
