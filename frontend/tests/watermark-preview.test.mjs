import assert from "node:assert/strict";
import test from "node:test";
import { previewPageWindow, selectedPreviewPage, watermarkPlacement, watermarkTextSize, watermarkImageDimensions } from "../lib/watermark-preview.ts";
import { HELVETICA_ADVANCES, HELVETICA_ASCENDER, HELVETICA_DESCENDER } from "../lib/helvetica-metrics.ts";
const metrics = { advances: HELVETICA_ADVANCES, ascender: HELVETICA_ASCENDER, descender: HELVETICA_DESCENDER };

test("image dimensions are checked before decoding with bounded binary headers", () => {
  const png = new Uint8Array(24);
  png.set([137, 80, 78, 71, 13, 10, 26, 10]); png.set([73,72,68,82], 12);
  const pngView = new DataView(png.buffer); pngView.setUint32(16, 160); pngView.setUint32(20, 100);
  assert.deepEqual(watermarkImageDimensions(png), { width: 160, height: 100, mime: "image/png" });
  pngView.setUint32(16, 100000); pngView.setUint32(20, 100000);
  assert.equal(watermarkImageDimensions(png), undefined);
  const jpeg = new Uint8Array([255,216,255,224,0,4,0,0,255,192,0,8,8,0,100,0,160,3]);
  assert.deepEqual(watermarkImageDimensions(jpeg), { width: 160, height: 100, mime: "image/jpeg" });
  const webp = new Uint8Array(30); webp.set([82,73,70,70],0); webp.set([87,69,66,80,86,80,56,88],8); webp[24]=159; webp[27]=99;
  assert.deepEqual(watermarkImageDimensions(webp), { width: 160, height: 100, mime: "image/webp" });
  const lossless = webp.slice(); lossless.set([86,80,56,76],12); lossless[20]=47;
  const encoded = 159 | (99 << 14); new DataView(lossless.buffer).setUint32(21,encoded,true);
  assert.deepEqual(watermarkImageDimensions(lossless), { width: 160, height: 100, mime: "image/webp" });
  const lossy=webp.slice(); lossy.set([86,80,56,32],12); lossy.set([157,1,42],23); new DataView(lossy.buffer).setUint16(26,160,true); new DataView(lossy.buffer).setUint16(28,100,true);
  assert.deepEqual(watermarkImageDimensions(lossy), { width: 160, height: 100, mime: "image/webp" });
  for (const invalid of [new Uint8Array(), new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg"></svg>'), jpeg.slice(0,15), new Uint8Array([255,216,255,224,255,255])]) assert.equal(watermarkImageDimensions(invalid),undefined);
});

test("page windows remain bounded and clamp navigation to the document", () => {
  assert.deepEqual(previewPageWindow(31, 0), { first: 1, last: 12, pages: Array.from({ length: 12 }, (_, i) => i + 1), index: 0, windows: 3 });
  assert.deepEqual(previewPageWindow(31, 99).pages, [25, 26, 27, 28, 29, 30, 31]);
  assert.deepEqual(previewPageWindow(0, 0).pages, []);
});

test("selected scope never paints an invalid or out-of-document range", () => {
  assert.equal(selectedPreviewPage("", 4, 4), true);
  assert.equal(selectedPreviewPage("3,1", 1, 4), true);
  assert.equal(selectedPreviewPage("3,1", 2, 4), false);
  for (const invalid of ["1-3,2", "0", "5", "-1", "1e2", "x", "2-1"]) {
    assert.equal(selectedPreviewPage(invalid, 1, 4), false);
  }
});

test("text geometry uses backend Helvetica metrics and rejects unsupported content", () => {
  const size = watermarkTextSize("CAFÉ", metrics);
  assert.ok(size.width > 200);
  assert.ok(Math.abs(size.height - 137.41) < 0.01);
  assert.equal(watermarkTextSize("水", metrics), undefined);
  assert.equal(watermarkTextSize("\n", metrics), undefined);
  assert.equal(watermarkTextSize("", metrics), undefined);
});

test("placement fits rotated extents within displayed page margins for nine positions", () => {
  for (const page of [{ width: 360, height: 520 }, { width: 520, height: 360 }]) {
    for (const position of ["top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"]) {
      for (const angle of [-180, -45, 0, 35, 90, 180]) {
        const placed = watermarkPlacement({ width: 600, height: 137.41 }, page, { position, angle, scale: 0.5, margin: 18 });
        assert.ok(placed);
        assert.ok(placed.x >= 17.999 && placed.y >= 17.999);
        assert.ok(placed.x + placed.width <= page.width - 17.999);
        assert.ok(placed.y + placed.height <= page.height - 17.999);
        if (position.endsWith("left")) assert.ok(Math.abs(placed.x - 18) < 0.001);
        if (position.endsWith("right")) assert.ok(Math.abs(placed.x + placed.width - page.width + 18) < 0.001);
        if (position.startsWith("top")) assert.ok(Math.abs(placed.y - 18) < 0.001);
        if (position.startsWith("bottom")) assert.ok(Math.abs(placed.y + placed.height - page.height + 18) < 0.001);
      }
    }
  }
});

test("invalid geometry and numeric options produce no misleading placement", () => {
  const mark = { width: 200, height: 100 };
  const page = { width: 400, height: 500 };
  const defaults = { position: "center", angle: 0, scale: 0.5, margin: 18 };
  for (const options of [{ ...defaults, angle: NaN }, { ...defaults, scale: 0 }, { ...defaults, position: "elsewhere" }, { ...defaults, margin: 144 }]) {
    const smallPage = options.margin === 144 ? { width: 200, height: 100 } : page;
    assert.equal(watermarkPlacement(mark, smallPage, options), undefined);
  }
  assert.equal(watermarkPlacement({ width: 0, height: 1 }, page, defaults), undefined);
  assert.equal(watermarkPlacement(mark, { width: Infinity, height: 1 }, defaults), undefined);
});
