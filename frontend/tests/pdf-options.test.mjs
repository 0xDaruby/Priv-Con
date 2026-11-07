import assert from "node:assert/strict";
import test from "node:test";

test("known PDF page count rejects selections outside the loaded document", () => {
  assert.ok(validatePdfPages("5", 4));
  assert.ok(validatePdfPages("1-5", 4));
  assert.equal(validatePdfPages("1,3-4", 4), undefined);
  assert.equal(validatePdfPages("", 4), undefined);
});

import { validatePdfPages, validateJpgOptions } from "../lib/pdf-options.ts";

test("page selection permits all pages, spaces and non-contiguous ranges", () => {
  for (const value of ["", "   ", "1", "1-3,5", "5, 1 - 3"]) {
    assert.equal(validatePdfPages(value), undefined);
  }
});

test("page selection rejects ambiguous or unsafe ranges", () => {
  for (const value of ["0", "3-1", "1,1", "1-3,3-5", "1,,2", "1.5", "1e2", "2001", "9007199254740992"]) {
    assert.equal(typeof validatePdfPages(value), "string", value);
  }
});

test("JPG options require whole numbers within rendering bounds", () => {
  assert.equal(validateJpgOptions("144", "85"), undefined);
  assert.equal(validateJpgOptions("72", "40"), undefined);
  assert.equal(validateJpgOptions("300", "95"), undefined);
  for (const [dpi, quality] of [["", "85"], ["71", "85"], ["301", "85"], ["144.5", "85"], ["1e2", "85"], ["144", "39"], ["144", "96"], ["144", ""]]) {
    assert.equal(typeof validateJpgOptions(dpi, quality), "string");
  }
});
