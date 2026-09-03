import type { SVGProps } from "react";

import type { ToolIconName } from "@/lib/types";

type IconProps = SVGProps<SVGSVGElement>;

function IconBase({ children, className, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      focusable="false"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 40 40"
      {...props}
    >
      {children}
    </svg>
  );
}

export function BackendMonitorIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 24 24" {...props}>
      <rect height="14" rx="2" width="19" x="2.5" y="3.5" />
      <path d="M8.5 21h7M12 17.5V21" />
    </IconBase>
  );
}

export function PdfFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect height="34" rx="6" width="34" x="3" y="3" />
      <path
        d="M20.2 8.2c-2.2 0-2.1 4.6.2 9.5-2.2 5.4-5.1 10.3-7.8 13.1-2.6 2.7-5.7 1.8-4.9-.7.7-2.1 4.6-3.9 10.1-4.7 4.6-.6 9.8-.3 12.7 1.4 3.5 2 2.7 4.5.6 4.7-2.9.2-7.5-3.9-10.7-10.1 2.2-5.5 3.1-10.5-.2-10.5Z"
        strokeWidth="1.8"
      />
    </IconBase>
  );
}

export function WordFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 1.5h23l10 10v27H3z" />
      <path d="M26 1.5v10h10" />
      <path d="m9 17 3 15 4-10 4 10 3-15" />
    </IconBase>
  );
}

export function PowerPointFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 1.5h23l10 10v27H3z" />
      <path d="M26 1.5v10h10" />
      <rect height="14" rx="1" width="19" x="8" y="15" />
      <path d="M17.5 29v6M12 35h11M13 19h5a3 3 0 0 1 0 6h-5z" />
    </IconBase>
  );
}

export function SpreadsheetFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect height="37" rx="2" width="34" x="3" y="1.5" />
      <rect height="24" rx="1" width="22" x="9" y="8" />
      <path d="M20 8v24M9 20h22M9 26h22" />
    </IconBase>
  );
}

export function MergeFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 1.5h22l10 10v27H5z" />
      <path d="M27 1.5v10h10" />
      <path d="M0 25h17M11 19l6 6-6 6" />
    </IconBase>
  );
}

export function SplitFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect height="37" rx="1.5" width="17" x="2" y="1.5" />
      <rect height="30" rx="1.5" width="15" x="23" y="5" />
      <path d="M2 20h17M23 20h15" />
    </IconBase>
  );
}

export function ImageFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect height="37" rx="2" width="37" x="1.5" y="1.5" />
      <circle cx="13" cy="12" r="3.5" />
      <path d="m4 34 11-11 6 6 5-5 10 10" />
    </IconBase>
  );
}

export function UploadTrayIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M20 26V4M11 13l9-9 9 9" strokeWidth="3" />
      <path d="M6 24v8a3 3 0 0 0 3 3h22a3 3 0 0 0 3-3v-8" strokeWidth="3" />
    </IconBase>
  );
}

export function PrivacyShieldCheckIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 36 40" {...props}>
      <path d="M18 2 31 7v11c0 9-5.2 15.4-13 20C10.2 33.4 5 27 5 18V7z" />
      <path d="m12 19 4 4 8-9" />
    </IconBase>
  );
}

export function RemoveFileIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 24 24" {...props}>
      <path d="M5 5l14 14M19 5 5 19" />
    </IconBase>
  );
}

export function DragHandleIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 24 24" {...props}>
      <circle cx="8" cy="6" fill="currentColor" r="1" stroke="none" />
      <circle cx="16" cy="6" fill="currentColor" r="1" stroke="none" />
      <circle cx="8" cy="12" fill="currentColor" r="1" stroke="none" />
      <circle cx="16" cy="12" fill="currentColor" r="1" stroke="none" />
      <circle cx="8" cy="18" fill="currentColor" r="1" stroke="none" />
      <circle cx="16" cy="18" fill="currentColor" r="1" stroke="none" />
    </IconBase>
  );
}

export function SuccessCheckIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 48 48" {...props}>
      <circle cx="24" cy="24" r="20" />
      <path d="m15 24 6 6 13-14" />
    </IconBase>
  );
}

export function ErrorAlertIcon(props: IconProps) {
  return (
    <IconBase viewBox="0 0 48 48" {...props}>
      <path d="M24 4 45 42H3z" />
      <path d="M24 16v12M24 35h.01" />
    </IconBase>
  );
}

export function ArchiveFileIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 3h32v8H4zM7 11h26v26H7z" />
      <path d="M16 18h8" />
    </IconBase>
  );
}

export function ToolFileIcon({
  name,
  ...props
}: IconProps & { readonly name: ToolIconName }) {
  switch (name) {
    case "pdf-file":
      return <PdfFileIcon {...props} />;
    case "word-file":
      return <WordFileIcon {...props} />;
    case "powerpoint-file":
      return <PowerPointFileIcon {...props} />;
    case "spreadsheet-file":
      return <SpreadsheetFileIcon {...props} />;
    case "merge-file":
      return <MergeFileIcon {...props} />;
    case "split-file":
      return <SplitFileIcon {...props} />;
    case "image-file":
      return <ImageFileIcon {...props} />;
  }
}
