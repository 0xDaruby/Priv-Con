import type { ToolId } from "./types";

export const TOOL_CATEGORIES = [
  { id: "toPdf", label: "Convert to PDF", description: "Bring documents and images into PDF." },
  { id: "fromPdf", label: "Convert from PDF", description: "Use PDF content in another format." },
  { id: "organize", label: "Organize pages", description: "Combine, separate and arrange your documents." },
  { id: "edit", label: "Edit & annotate", description: "Add content and complete documents." },
  { id: "optimize", label: "Optimize & OCR", description: "Prepare files for sharing and searching." },
  { id: "security", label: "Protect & sign", description: "Control access, sign and remove sensitive content." },
  { id: "read", label: "Read & review", description: "Understand and review your documents." },
] as const;

export type ToolCategoryId = typeof TOOL_CATEGORIES[number]["id"];
export type ToolCategoryFilter = ToolCategoryId | "all";

export interface ToolDiscovery {
  readonly category: ToolCategoryId;
  readonly keywords: readonly string[];
}

/** Discovery metadata describes available tools; it never creates routes. */
export const TOOL_DISCOVERY = {
  word: { category: "toPdf", keywords: ["document", "docx", "microsoft word"] },
  powerpoint: { category: "toPdf", keywords: ["presentation", "slides", "ppt", "pptx"] },
  excel: { category: "toPdf", keywords: ["spreadsheet", "workbook", "xlsx", "report"] },
  images: { category: "toPdf", keywords: ["photo", "picture", "jpg", "jpeg", "png", "webp"] },
  pdfToWord: { category: "fromPdf", keywords: ["editable document", "docx", "microsoft word"] },
  pdfToJpg: { category: "fromPdf", keywords: ["photo", "picture", "jpeg", "image", "export pages"] },
  merge: { category: "organize", keywords: ["join", "combine", "append"] },
  split: { category: "organize", keywords: ["separate", "extract pages", "page range"] },
  rotate: { category: "organize", keywords: ["turn pages", "orientation", "clockwise"] },
  watermark: { category: "edit", keywords: ["stamp", "logo", "confidential", "text overlay"] },
  pageNumbers: { category: "edit", keywords: ["pagination", "numbering", "footer", "header", "page labels"] },
} as const satisfies Readonly<Record<ToolId, ToolDiscovery>>;

export interface CatalogSearchItem {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly acceptedFormatLabel: string;
}

export interface CatalogGroup<T> {
  readonly id: ToolCategoryId;
  readonly label: string;
  readonly description: string;
  readonly tools: readonly T[];
}

/** Match all typed words, keeping category and original tool order stable. */
export function getCatalogGroups<T extends CatalogSearchItem>(
  tools: readonly T[],
  query = "",
  category: ToolCategoryFilter = "all",
  discovery: Readonly<Record<string, ToolDiscovery>> = TOOL_DISCOVERY,
): readonly CatalogGroup<T>[] {
  const words = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return TOOL_CATEGORIES.flatMap((group) => {
    if (category !== "all" && group.id !== category) return [];
    const matches = tools.filter((tool) => {
      const metadata = Object.hasOwn(discovery, tool.id) ? discovery[tool.id] : undefined;
      if (!metadata || metadata.category !== group.id) return false;
      const searchable = [tool.title, tool.description, tool.acceptedFormatLabel, ...metadata.keywords].join(" ").toLowerCase();
      return words.every((word) => searchable.includes(word));
    });
    return matches.length ? [{ ...group, tools: matches }] : [];
  });
}
