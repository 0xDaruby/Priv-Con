const BYTE_UNITS = ["B", "KB", "MB", "GB"] as const;

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "—";
  }

  if (bytes === 0) {
    return "0 B";
  }

  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    BYTE_UNITS.length - 1,
  );
  const value = bytes / 1024 ** unitIndex;
  const maximumFractionDigits = value >= 10 || Number.isInteger(value) ? 0 : 1;

  return `${new Intl.NumberFormat("en", { maximumFractionDigits }).format(value)} ${BYTE_UNITS[unitIndex]}`;
}

export function formatFileCount(count: number): string {
  return `${count} ${count === 1 ? "file" : "files"}`;
}
