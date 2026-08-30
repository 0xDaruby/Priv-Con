"use client";

import {
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
  useRef,
  useState,
} from "react";

import {
  ErrorAlertIcon,
  PrivacyShieldCheckIcon,
  ToolFileIcon,
  UploadTrayIcon,
} from "@/components/icons/PrivConIcons";
import type { ToolConfig } from "@/lib/types";

interface UploadDropzoneProps {
  readonly config: ToolConfig;
  readonly compact?: boolean;
  readonly errorMessage?: string;
  readonly onFilesSelected: (files: readonly File[]) => void;
}

export function UploadDropzone({
  config,
  compact = false,
  errorMessage,
  onFilesSelected,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const openPicker = () => inputRef.current?.click();

  const acceptFiles = (files: FileList | null) => {
    if (files?.length) {
      onFilesSelected(Array.from(files));
    }
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    acceptFiles(event.target.files);
    event.target.value = "";
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    acceptFiles(event.dataTransfer.files);
  };

  return (
    <>
      <input
        accept={config.acceptAttribute}
        hidden
        multiple={config.multiple}
        onChange={handleInputChange}
        ref={inputRef}
        tabIndex={-1}
        type="file"
      />
      <div
        aria-label={`${config.chooseLabel}. ${config.acceptedFormatLabel} files only.`}
        className={compact ? "compact-dropzone" : "dropzone interactive-dropzone"}
        data-dragging={isDragging || undefined}
        onClick={openPicker}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
            setIsDragging(false);
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
      >
        {compact ? (
          <>
            <UploadTrayIcon />
            <span>{config.multiple ? "Add more files" : "Replace file"}</span>
          </>
        ) : (
          <div className="empty-state">
            <div className="hero-icon" aria-hidden="true">
              <ToolFileIcon name={config.icon} />
            </div>
            <h1 className="page-title">{config.title}</h1>
            <p className="accepted-format">
              {config.acceptedExtensions.length > 1
                ? "Accepted formats:"
                : "Accepted format:"}{" "}
              <strong>{config.acceptedFormatLabel}</strong>
            </p>
            <span className="primary-action" aria-hidden="true">
              <UploadTrayIcon />
              <span>{config.chooseLabel}</span>
            </span>
            {errorMessage ? (
              <div className="dropzone-validation" role="alert">
                <ErrorAlertIcon />
                <span>{errorMessage}</span>
              </div>
            ) : null}
            <div className="privacy-statement">
              <PrivacyShieldCheckIcon />
              <p className="privacy-copy">
                Files are processed entirely on this machine.
                <br />
                Nothing is uploaded anywhere.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
