# F03 Watermark / F04 Page numbers: contract and verification

Owner authorized both features on 2026-10-28. Completed local implementation and acceptance on 2026-10-29. This document owns this slice's API/options mapping. It extends the existing feature program without changing PRD or Windows roadmap. All document processing remains local; this is not Windows installer acceptance.

## Frozen integration contract

| Feature | UI ID / route | Direct route | Job tool | Result |
|---|---|---|---|---|
| F03 | `watermark` / `/watermark-pdf` | `/api/pdf/watermark` | `pdf-watermark` | PDF, `<sanitized-stem>_watermarked.pdf` |
| F04 | `pageNumbers` / `/page-numbers` | `/api/pdf/page-numbers` | `pdf-page-numbers` | PDF, `<sanitized-stem>_numbered.pdf` |

Both use the existing `file` field (exactly one PDF), optional `pages` string (blank means all; existing parser; source order, no overlaps/duplicates), and `options` JSON object. Unknown keys, wrong types, non-finite numbers, oversized strings and unsupported choices fail clearly before expensive work. No filesystem paths or arbitrary font names accepted. Result is `application/pdf`; retain private async transport metadata validation.

New error codes: `invalid_overlay_options` for option/font/fit errors and `unsupported_pdf_geometry` for unsupported page coordinate conventions. Retain existing upload, page-range, signed-PDF, cancellation, timeout and output-limit errors.

F03 options: `kind` (`text` default or `image`), `text` (default `CONFIDENTIAL`, 1-120 printable supported characters when kind=text), `position` (nine-grid names `top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right`; default center), `angle` (degrees counterclockwise, -180 through180, default0), `opacity` (0.1 through1, default0.25), `scale` (fraction0.1 through1, default0.5), `margin` (PDF points,12 through144, default18). Overlay only. Scale fits the rotated text/image bounding box inside the displayed crop area minus margins, preserving aspect ratio; it is a maximum fraction of available dimensions, not a fixed font size. Text uses built-in Helvetica, English/Western Latin printable glyphs only (reject C0/C1 controls, unsupported glyphs and other scripts). No system/font downloads or arbitrary assets. Image mode requires exactly one `watermark_image` upload; supported PNG/JPG/JPEG/WEBP via existing extension/content validation, transparency preserved. Reject an image in text mode or for other tools. Image mode omits `text`. Image limit: existing upload limits and at most16 million pixels (or lower configured global limit). Images are static first-frame content; no animation claim.

F04 options: `position` (top-left/center/right or bottom-left/center/right; default bottom-center), `margin` (PDF points12 through144, default18), `font_size` (PDF points8 through48, default12), `start` (integer1 through999999, default1), `format` (`number` or `page`, default number). Labels are decimal digits or `Page n`. Numbering advances once per selected page in original document order, even for non-contiguous selections. UI explains that rule and shows the actual first label before submission. All selected labels must fit inside their page margins; fail clearly instead of clipping. Both services reject existing digital signatures and unsupported geometry, preserve input bytes/page count/order/boxes/rotation and selectable source text, and validate generated PDF before success.

## Geometry and resource decisions

Use existing PyMuPDF to create isolated vector/image overlays, and pypdf to clone the source and merge overlays. Overlay dimensions follow displayed crop size; transform back through inverse source rotation plus crop origin. Preserve original MediaBox/CropBox/Rotate; reject non-finite/empty boxes, rotation not a multiple of90 and non1 UserUnit initially. No document rasterization. Tests must include all four rotations, nonzero/negative origins, mixed sizes, transparency, selected scope and underlying text. Rendered/display coordinates and extracted unrotated coordinates must not be conflated.

Reuse owned temporary paths, bounded uploads/outputs/page counts, deadlines, cancellation checkpoints, progress and cleanup. Do not weaken existing PDF validators. No new dependency or system font required; existing engine resources remain subject to Windows packaging acceptance later. Cooperative checks do not constitute a hard OS sandbox.

Implemented additional geometry bound: displayed page dimensions from1 through14,400 PDF points, with CropBox inside MediaBox. Selected page content is preflighted stream-by-stream before cloning, with an aggregate decoded-content budget of64MiB or the configured output cap, whichever is lower. Invalid contents and pages with more than10,000 content streams are rejected. Identical watermark resource objects are reused across pages. A bounded writer checks cancellation/deadline and projected output size during serialization. Watermark image validation and generation share one service deadline; no duplicate image decode occurs in router/job runner. Individual native parser/decoder calls remain cooperative, not forcibly interruptible subprocesses. Upload persistence is governed by existing request limits, outside the service deadline.

## Actual verification

### Automated verification

- TDD: backend missing-endpoint404 and frontend missing-helper failures were observed before implementing the slice. A later deadline regression proved image-validation time was excluded (RED), then passed after sharing the service deadline.
- Focused backend:70 tests passed. Includes four rotations, mixed page sizes/crops, negative origins, selected Latin text, transparency multiplied by opacity, number alignment across six positions, non-contiguous numbering, malformed/duplicate/deep JSON and huge numeric values, unsupported geometry/signatures/glyphs, invalid image choices/types/pixels, single-use async download cleanup, cancel before/during/finalization, timeout/output budgets, and aggregate content rejection before writer clone.
- Full backend:227 tests passed, zero skips, in98.78seconds. Ran with the existing virtual environment outside the sandbox using workspace-owned test roots. This includes existing conversion integration tests; it does not independently resolve the earlier real-server DOCX timeout observation.
- New backend module coverage:94% aggregate (geometry94%, options96%, watermark92%, numbers100%). Command: `python -m coverage run --data-file=../temp/f03-f04-coverage-20261029 --source=app.services.pdf_overlay_options,app.services.pdf_overlay_geometry,app.services.pdf_watermark_service,app.services.pdf_page_numbers_service -m pytest tests -q --basetemp ../temp/f03-f04-regression-20261029`, followed by coverage report.
- Frontend:26 tests passed; the six overlay-helper tests measured100% lines/branches/functions. This is helper coverage, not full React/application coverage. ESLint and final TypeScript passed. Unchanged Next/Turbopack production build passed with bundled Node24.22.1, including both new routes. The generated cache was preserved under ignored temp before the build because of the previously documented CSS-worker cache failure. An overlapping reviewer typecheck initially lacked generated LayoutProps while the cache was moved; final build/typecheck passed afterward.
- Ruff passed for all affected Python source/tests; diff whitespace check passed. No dependency added for these features.

### Review and resolved findings

Used ECC TDD Workflow, React Patterns/Testing, Security Review and Verification Loop; backend/frontend workers had separate ownership. A read-only architect verified inverse rotation/crop transforms and installed Helvetica glyph coverage. Independent React, TypeScript, Python, general code and security reviewers examined the slice. Fixed: Python `isprintable` mismatch with permitted Latin-1 spacing/hyphen; oversized JSON numeric overflow; image pixel checks before decode; repeated image resource duplication; cumulative source-content decompression before merging; early forbidden-image multipart response failing to close spooled handles; image validation outside the deadline; keyboard focus after removing the image. Python and security re-review approved; general/React/TS review had no remaining source blocker. Some worker/reviewer continuations hit service limits; parent completed the remaining fixes/checks, and Python/security re-review subsequently completed.

### Real browser and downloaded output acceptance

Production frontend and local backend, synthetic fixtures only:

- Watermark text: unsupported script blocked with clear guidance; selected pages1,3 received `CAFÉ TEST` at35degrees; others retained source content. Image mode accepted a transparent PNG and opacity0.5 on the four rotated/cropped pages. Removal restored focus to the image input and the same file could be selected again. Reset restored default options.
- Page numbers: pages1,3-4 starting98 with `Page n` showed the exact first-label sample; downloaded output contained Page98/Page99/Page100 on the expected pages. Out-of-document range99 failed clearly, retained the PDF/options, and editing to page1 then activating by Enter succeeded.
- A600-page watermark job was cancelled from the browser; UI returned to its selected-file configuration. Actual backend temp upload/output directories were empty after the journeys. Service tests separately cover cancellation during work and finalization.
- Both new panels reflowed at375CSS pixels without horizontal overflow. Number controls also checked in light mode; dark mode remained functional. Normal desktop layout and tool switching were checked; catalog exposes11 actual tools, with the two additions under Edit & annotate. No browser error entries returned during acceptance. Temporary viewport reset.
- Downloaded browser PDFs independently reopened with pypdf/PyMuPDF: page count/order/boxes/rotations and source text retained; selected text and numbering verified; output render contact sheet visually inspected. One shared image XObject across four pages was independently verified. Synthetic input's initially cropped-away source line remains cropped away; fixtures in automated geometry tests also include visible source text.

Ignored evidence artifacts: `temp/f03-f04-qa-20261028/{new-tools-catalog.jpg,page-numbers-options.jpg,browser-output-review.png,browser-text.pdf,browser-image.pdf,browser-numbers.pdf}`. These are local test artifacts, not repository fixtures or user documents.

### Limits and next action

Fixed Helvetica English/Western Latin support, overlay only, first image frame, supported geometry limits and sequential selected-page numbering are intentional first-slice boundaries. No arbitrary fonts, underlay, AI/OCR or full document preview/editor is implied. No full accessibility certification, complete native network-isolation capture, fresh-machine/installed Windows test, or live Office acceptance rerun was performed. Existing local-only architecture preserved; no document upload to third parties, dependency install, commit, push or publication in this slice. Prior F01/F02/catalog/theme changes remain intact.

F03/F04 are complete locally. F05 Crop is the next planned feature and requires its execution scope; Windows W1-W10 still follow feature acceptance FR. Earlier live DOCX timeout and Windows packaging gates remain open; a regression pass is not a shipped desktop release.
