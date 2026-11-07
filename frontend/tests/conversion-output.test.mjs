import assert from "node:assert/strict";
import test from "node:test";

import { resolveOutputType, isOutputTypeAllowed, resolveResultMetadata } from "../lib/conversion-output.ts";

test("known result MIME types resolve without guessing", () => {
  assert.equal(resolveOutputType("application/pdf", "result.pdf"), "pdf");
  assert.equal(resolveOutputType("application/zip", "result.zip"), "zip");
  assert.equal(resolveOutputType("image/jpeg", "page.jpg"), "jpg");
  assert.equal(resolveOutputType("IMAGE/JPEG; charset=binary", "page.JPEG"), "jpg");
  assert.equal(resolveOutputType("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "result.docx"), "docx");
});

test("unsupported and mismatched results cannot masquerade as PDFs", () => {
  assert.equal(resolveOutputType("text/html", "result.pdf"), undefined);
  assert.equal(resolveOutputType("", "result.pdf"), undefined);
  assert.equal(resolveOutputType("application/pdf", "result.jpg"), undefined);
  assert.equal(resolveOutputType("application/octet-stream", "result.zip"), undefined);
  assert.equal(resolveOutputType("image/jpeg", "result.svg"), undefined);
  assert.equal(resolveOutputType("__proto__"), undefined);
  assert.equal(resolveOutputType("image/jpeg"), "jpg");
});

test("each tool accepts only its declared result formats", () => {
  assert.equal(isOutputTypeAllowed("jpg-or-zip", "jpg"), true);
  assert.equal(isOutputTypeAllowed("jpg-or-zip", "zip"), true);
  assert.equal(isOutputTypeAllowed("jpg-or-zip", "pdf"), false);
  assert.equal(isOutputTypeAllowed("pdf", "jpg"), false);
  assert.equal(isOutputTypeAllowed("pdf-or-zip", "pdf"), true);
  assert.equal(isOutputTypeAllowed("pdf-or-zip", "zip"), true);
  assert.equal(isOutputTypeAllowed("docx", "docx"), true);
});

test("private async result transport uses verified declared MIME and filename", () => {
  assert.deepEqual(
    resolveResultMetadata("application/x-privcon-result", "image/jpeg", "page.jpg", "jpg-or-zip"),
    { contentType: "image/jpeg", outputType: "jpg" },
  );
  assert.deepEqual(
    resolveResultMetadata("application/x-privcon-result", "application/pdf", "rotated.pdf", "pdf"),
    { contentType: "application/pdf", outputType: "pdf" },
  );
  assert.deepEqual(
    resolveResultMetadata("application/x-privcon-result", "application/zip", "pages.zip", "jpg-or-zip"),
    { contentType: "application/zip", outputType: "zip" },
  );
});

test("private result transport cannot bypass metadata or tool validation", () => {
  for (const args of [
    ["application/x-privcon-result", "", "page.jpg", "jpg-or-zip"],
    ["application/x-privcon-result", "image/jpeg", undefined, "jpg-or-zip"],
    ["application/x-privcon-result", "image/jpeg", "page.pdf", "jpg-or-zip"],
    ["application/x-privcon-result", "text/html", "page.jpg", "jpg-or-zip"],
    ["application/x-privcon-result", "application/pdf", "page.pdf", "jpg-or-zip"],
    ["application/octet-stream", "image/jpeg", "page.jpg", "jpg-or-zip"],
    ["image/jpeg", "application/pdf", "page.jpg", "jpg-or-zip"],
  ]) {
    assert.equal(resolveResultMetadata(...args), undefined);
  }
});

test("ordinary result MIME must agree with declared metadata when present", () => {
  assert.deepEqual(
    resolveResultMetadata("image/jpeg", "image/jpeg", "page.jpg", "jpg-or-zip"),
    { contentType: "image/jpeg", outputType: "jpg" },
  );
  assert.deepEqual(
    resolveResultMetadata("application/pdf", "", undefined, "pdf"),
    { contentType: "application/pdf", outputType: "pdf" },
  );
  assert.deepEqual(
    resolveResultMetadata("", "application/pdf", "page.pdf", "pdf"),
    { contentType: "application/pdf", outputType: "pdf" },
  );
});
