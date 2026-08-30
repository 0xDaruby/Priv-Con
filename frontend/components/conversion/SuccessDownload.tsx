"use client";

import { useEffect, useRef } from "react";

import {
  PrivacyShieldCheckIcon,
  SuccessCheckIcon,
} from "@/components/icons/PrivConIcons";
import type { ConversionOutputType } from "@/lib/types";

interface SuccessDownloadProps {
  readonly downloadUrl: string;
  readonly filename: string;
  readonly outputType: ConversionOutputType;
  readonly onConvertAgain: () => void;
}

export function SuccessDownload({
  downloadUrl,
  filename,
  outputType,
  onConvertAgain,
}: SuccessDownloadProps) {
  const downloadRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    downloadRef.current?.click();
  }, [downloadUrl]);

  return (
    <section className="state-panel success-panel" aria-live="polite">
      <SuccessCheckIcon className="state-icon" />
      <div className="state-heading">
        <p className="configuration-eyebrow">Conversion complete</p>
        <h1>Your {outputType.toUpperCase()} is ready</h1>
        <p className="result-filename" title={filename}>
          {filename}
        </p>
      </div>
      <a
        className="primary-action state-primary"
        download={filename}
        href={downloadUrl}
        ref={downloadRef}
      >
        Download again
      </a>
      <button className="secondary-action" onClick={onConvertAgain} type="button">
        Convert another file
      </button>
      <div className="compact-privacy state-privacy">
        <PrivacyShieldCheckIcon />
        <span>
          Files are processed entirely on this machine.
          <br />
          Nothing is uploaded anywhere.
        </span>
      </div>
    </section>
  );
}
