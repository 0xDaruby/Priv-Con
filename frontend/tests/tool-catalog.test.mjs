import assert from "node:assert/strict";
import test from "node:test";

import { TOOLS } from "../lib/constants.ts";
import { getCatalogGroups, TOOL_CATEGORIES, TOOL_DISCOVERY } from "../lib/tool-catalog.ts";

test("catalog groups every implemented tool once without empty categories", () => {
  const groups = getCatalogGroups(TOOLS);
  assert.deepEqual(groups.map(({ id }) => id), ["toPdf", "fromPdf", "organize", "edit"]);
  assert.equal(groups.flatMap(({ tools }) => tools).length, TOOLS.length);
  assert.equal(new Set(groups.flatMap(({ tools }) => tools.map(({ id }) => id))).size, TOOLS.length);
  assert.deepEqual(groups[0].tools.map(({ id }) => id), ["word", "powerpoint", "excel", "images"]);
  assert.ok(TOOLS.every(({ id }) => TOOL_DISCOVERY[id]));
});

test("catalog search matches aliases, formats and task language locally", () => {
  const ids = (query) => getCatalogGroups(TOOLS, query).flatMap(({ tools }) => tools.map(({ id }) => id));
  assert.deepEqual(ids(" JOIN "), ["merge"]);
  assert.deepEqual(ids("presentation"), ["powerpoint"]);
  assert.deepEqual(ids("webp"), ["images"]);
  assert.deepEqual(ids("turn pages"), ["rotate"]);
  assert.deepEqual(ids("stamp"), ["watermark"]);
  assert.deepEqual(ids("pagination"), ["pageNumbers"]);
  assert.deepEqual(ids("word pdf"), ["word", "pdfToWord"]);
  assert.deepEqual(ids("unavailable imaginary tool"), []);
});

test("category and query combine without changing source order", () => {
  const groups = getCatalogGroups(TOOLS, "pdf", "organize");
  assert.deepEqual(groups.map(({ id }) => id), ["organize"]);
  assert.deepEqual(groups[0].tools.map(({ id }) => id), ["merge", "split", "rotate"]);
  assert.deepEqual(getCatalogGroups(TOOLS, "presentation", "fromPdf"), []);
  assert.equal(getCatalogGroups(TOOLS, "   ").flatMap(({ tools }) => tools).length, TOOLS.length);
});

test("catalog scales to 31 registered destinations without pagination or dropped entries", () => {
  const discovery = {};
  const tools = Array.from({ length: 31 }, (_, index) => {
    const id = `fixture-${index}`;
    discovery[id] = { category: TOOL_CATEGORIES[index % TOOL_CATEGORIES.length].id, keywords: ["synthetic"] };
    return { id, title: `Tool ${index}`, description: "Synthetic layout capacity fixture", acceptedFormatLabel: ".PDF" };
  });
  const groups = getCatalogGroups(tools, "synthetic", "all", discovery);
  assert.equal(groups.length, TOOL_CATEGORIES.length);
  assert.equal(groups.flatMap(({ tools }) => tools).length, 31);
  assert.equal(new Set(groups.flatMap(({ tools }) => tools.map(({ id }) => id))).size, 31);
  assert.ok(groups.every(({ tools }) => tools.length > 0));
});

test("unregistered inputs cannot become invented catalog destinations", () => {
  const unknown = { id: "not-implemented", title: "Unknown", description: "Unknown", acceptedFormatLabel: ".PDF" };
  assert.deepEqual(getCatalogGroups([unknown]), []);
  assert.deepEqual(getCatalogGroups([]), []);
});
