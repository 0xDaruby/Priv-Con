/** Validate the option-only tools before uploading; the backend checks actual pages. */
export function validatePdfPages(value: string, pageCount?: number): string | undefined {
  if (!value.trim()) return undefined;

  const intervals: { start: number; end: number }[] = [];
  for (const token of value.split(",")) {
    const match = token.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) return "Use pages like 1-3,5, or leave this blank for all pages.";
    const start = Number(match[1]);
    const end = Number(match[2] ?? match[1]);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end < start || end > 2_000) {
      return "Use ascending page ranges from 1 to 2,000. The PDF must contain each page.";
    }
    if (pageCount !== undefined && end > pageCount) {
      return `This PDF has ${pageCount} pages. Choose pages within this document.`;
    }
    if (intervals.some((interval) => start <= interval.end && end >= interval.start)) {
      return "Page selection cannot contain duplicate or overlapping pages.";
    }
    intervals.push({ start, end });
  }
  return undefined;
}

export function validateJpgOptions(dpi: string, quality: string): string | undefined {
  if (!/^\d+$/.test(dpi) || !Number.isInteger(Number(dpi)) || Number(dpi) < 72 || Number(dpi) > 300) {
    return "Resolution must be a whole number from 72 to 300 DPI.";
  }
  if (!/^\d+$/.test(quality) || !Number.isInteger(Number(quality)) || Number(quality) < 40 || Number(quality) > 95) {
    return "JPG quality must be a whole number from 40 to 95.";
  }
  return undefined;
}
