import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_WATERMARK_OPTIONS, DEFAULT_PAGE_NUMBER_OPTIONS,
  validateWatermarkOptions as validateWatermark, validatePageNumberOptions, pageNumberSample,
  buildWatermarkFields, buildPageNumberFields,
} from "../lib/pdf-overlay-options.ts";
import { BACKEND_LIMITS } from "../lib/constants.ts";

const validateWatermarkOptions = (options, image) => validateWatermark(options, image, BACKEND_LIMITS.maxFileBytes);

test("watermark defaults and supported Western Latin text serialize as bounded options", () => {
  assert.equal(validateWatermarkOptions(DEFAULT_WATERMARK_OPTIONS), undefined);
  assert.equal(validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, text: "Révision café £ ©" }), undefined);
  assert.equal(validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, text: "non\u00a0breaking soft\u00adhyphen" }), undefined);
  const fields = buildWatermarkFields({ ...DEFAULT_WATERMARK_OPTIONS, angle: "-45" }, "1,3");
  assert.equal(fields.pages, "1,3");
  assert.deepEqual(JSON.parse(fields.options), { kind: "text", text: "CONFIDENTIAL", position: "center", angle: -45, opacity: 0.25, scale: 0.5, margin: 18 });
});

test("watermark rejects unsupported glyphs, controls, blank and oversized text", () => {
  for (const text of ["", "   ", "中", "😀", "line\nbreak", "control\u0085", "a".repeat(121)]) {
    assert.equal(typeof validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, text }), "string", text);
  }
});

test("watermark numeric boundaries and choices reject ambiguous non-finite input", () => {
  assert.equal(typeof validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, kind: "unknown" }), "string");
  for (const [key, values] of Object.entries({ angle: ["", "NaN", "Infinity", "181", "-181", "1e2"], opacity: ["0", "0.09", "1.1"], scale: ["0", "1.01"], margin: ["11", "145"], position: ["outside"] })) {
    for (const value of values) assert.equal(typeof validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, [key]: value }), "string", `${key}=${value}`);
  }
  assert.equal(validateWatermarkOptions({ ...DEFAULT_WATERMARK_OPTIONS, angle: "180", opacity: "1", scale: "0.1", margin: "144" }), undefined);
});

test("image watermark requires a bounded supported local image and omits hidden text", () => {
  const state = { ...DEFAULT_WATERMARK_OPTIONS, kind: "image", text: "unsupported 中" };
  assert.equal(typeof validateWatermarkOptions(state), "string");
  assert.equal(typeof validateWatermarkOptions(state, { name: "logo.svg", size: 20 }), "string");
  assert.equal(typeof validateWatermarkOptions(state, { name: "logo.png", size: 0 }), "string");
  assert.equal(typeof validateWatermarkOptions(state, { name: "logo.png", size: BACKEND_LIMITS.maxFileBytes + 1 }), "string");
  const image = new File(["synthetic"], "logo.PNG", { type: "image/png" });
  assert.equal(validateWatermarkOptions(state, image), undefined);
  const fields = buildWatermarkFields(state, "", image);
  assert.equal(fields.watermark_image, image);
  assert.equal(Object.hasOwn(JSON.parse(fields.options), "text"), false);
  assert.equal(Object.hasOwn(buildWatermarkFields(DEFAULT_WATERMARK_OPTIONS, "", image), "watermark_image"), false);
});

test("page numbering sample and fields match sequential selected-page semantics", () => {
  assert.equal(validatePageNumberOptions(DEFAULT_PAGE_NUMBER_OPTIONS), undefined);
  const state = { ...DEFAULT_PAGE_NUMBER_OPTIONS, start: "12", format: "page", position: "top-right" };
  assert.equal(pageNumberSample(state), "Page 12");
  assert.deepEqual(JSON.parse(buildPageNumberFields(state, "5,1-2").options), { position: "top-right", margin: 18, font_size: 12, start: 12, format: "page" });
  assert.equal(buildPageNumberFields(state, "5,1-2").pages, "5,1-2");
  assert.equal(pageNumberSample(DEFAULT_PAGE_NUMBER_OPTIONS), "1");
});

test("page numbering rejects unsafe starting values, out-of-bounds sizing and choices", () => {
  for (const [key, values] of Object.entries({ start: ["", "0", "1.5", "1e2", "1000000"], margin: ["11", "145", "NaN"], font_size: ["7", "49", "Infinity"], position: ["center"], format: ["roman", "{n}"] })) {
    for (const value of values) assert.equal(typeof validatePageNumberOptions({ ...DEFAULT_PAGE_NUMBER_OPTIONS, [key]: value }), "string", `${key}=${value}`);
  }
  assert.equal(validatePageNumberOptions({ ...DEFAULT_PAGE_NUMBER_OPTIONS, start: "999999", font_size: "48", margin: "144" }), undefined);
  assert.equal(pageNumberSample({ ...DEFAULT_PAGE_NUMBER_OPTIONS, start: "" }), undefined);
});
