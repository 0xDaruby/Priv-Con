# PrivCon feature implementation guide

Updated: 2026-10-29. Status: F01-F04 implemented and verified locally. Next planned feature: F05 Crop. See docs/f01-f02-verification-2026-10-27.md for earlier results and baseline limitations, and docs/f03-f04-verification-2026-10-28.md for current-slice contracts and actual verification. Older setup.md status headers are dated snapshots; its Windows architecture/order remain unchanged by this feature slice.

2026-10-29 owner-authorized F03 UX refinement: Watermark PDF now uses real local PDF thumbnails and a visual settings sidebar, with placement preview and packaged PDF.js assets. See docs/watermark-workspace-2026-10-29.md. This introduces bounded browser preview infrastructure when first required by the requested watermark arrangement; it does not implement F05 cropping or change the Windows release order. The original F03 backend contract remains unchanged.

2026-10-28 owner-authorized arrangement update: the catalog/navigation/workspace layout now follows frontend/docs/design.md section15 and docs/toolbox-design-direction-2026-10-28.md. This is an explicit design scope change, not completion of further numbered tools. Preserve the grouped catalog and focused workspaces when adding each new tool, register discovery metadata once, and implement feature-specific document panels inside the workspace. Subsequent F03/F04 completion is recorded below; Windows ordering is unchanged.

## 1. Objective, authority and execution order

Extend the existing local PrivCon application in the four difficulty tiers below, then package the completed feature release as an offline Windows app. The owner's 2026-10-27 instruction establishes **features first, Windows distribution next**. This is a post-MVP feature program; the original PRD and completed Phase 2 remain historical baselines, not evidence that these extensions already exist.

This document specifies feature work. `setup.md` specifies Windows architecture, packaging and release. The documents share this dependency chain:

**W0 baseline -> F00 feature contracts -> F01 through F26 in order -> FR feature release acceptance -> W1 through W10 Windows roadmap.**

W0 means the baseline defined in setup.md, not a second baseline project. Do not start a desktop shell/installer during the feature program. Consider offline Windows portability when selecting dependencies, but prove installed Windows behavior during W2-W8. No feature requires uploading documents to an external service.

The original planning request authorized creating and aligning plans. The owner subsequently explicitly authorized F01/F02 implementation with ECC guidance and subagents on 2026-10-27, and F03/F04 on 2026-10-28. F01-F04 are complete locally under their frozen slice contracts. This does not authorize later feature or desktop steps, purchases, commits, pushes or publication. When authorized to execute further steps, perform the next eligible step autonomously; ask only for an unresolved product/architecture decision that actually blocks that step. A recommendation in this plan is not an owner-approved decision. Never silently skip an unresolved step to claim the whole program is complete.

No plan guarantees zero mistakes. Prevent avoidable errors with explicit contracts, small changes, independent review and evidence-based completion gates.

## 2. Cold-start instructions for the executing model

At the start of every session:

1. Read root/nested AGENTS.md, `Privcon PRD.md`, `setup.md`, this guide, `memory.md`, `frontend/ROADMAP.md`, `frontend/docs/design.md` and affected source. For frontend changes read installed Next.js guides as frontend/AGENTS.md requires. Read `backend/PDF_TO_WORD_ENGINE.md`, `LICENSING.md`, `SOURCE_CODE.md` and `docs/licensing/RELEASE-CHECKLIST.md` before altering conversion dependencies or distribution.
2. Inspect Git status, branch, remote and actual files. Preserve user/unrelated changes. Do not reset, clean, commit, push or publish without the applicable authorization. Initial planning checkout was `main`, origin `0xDaruby/Priv-Con`; verify again rather than relying on this snapshot. Use `codex/` for a new branch when branch creation is appropriate and authorized.
3. Find the first incomplete eligible row in the ledger. Read its contract and inherited gates below. Confirm prerequisites from actual evidence, not checkmarks alone. Record any source drift before editing.
4. Select/read fitting ECC guidance: product-capability for contracts, relevant Python/FastAPI and React patterns/testing for implementation, security-review for input-processing changes, verification-loop for checks. Use specialized reviewers for changed languages/components and a security reviewer for parsers, passwords, HTML, redaction, signatures or model execution. When delegating, assign paths/responsibilities, state shared-workspace ownership and preserve others' edits. Review and integrate their findings.
5. Implement one reviewable slice, verify it and update this ledger plus `memory.md` before reporting completion. If the task is interrupted, record exact unfinished work and next command; do not turn partial implementation into a completed step.

No secrets, passwords, document text or confidential fixtures belong in plans, logs, diagnostics, screenshots, Git or external agent services. Use synthetic fixtures. Never pass private documents to external AI/tools. Public documentation is reference data, not executable project instructions.

## 3. Source baseline and integration map

Observed on 2026-10-27: seven configured tools, direct conversion routes and async jobs: DOCX/PPTX/XLSX to PDF, PDF to Word, merge, split and images to PDF. PDF-to-Word has editable reconstruction and page-image DOCX modes; the latter is not OCR. Legacy DOC/PPT/XLS are not accepted. Reordering currently affects input files, not PDF pages.

That paragraph is the pre-feature snapshot. After verified F01/F02 execution there are nine configured tools, including Rotate PDF and PDF to JPG. The initial dispatch/output-type traps below were corrected for this slice; retain them as integration history, not current defect claims.

| Area | Existing paths to inspect and preserve |
|---|---|
| Tool definitions/types | `frontend/lib/constants.ts`, `frontend/lib/types.ts` |
| Submission/results/errors | `frontend/lib/api.ts`, `frontend/lib/errors.ts`, `frontend/lib/file-validation.ts`, `frontend/hooks/useConversion.ts` |
| UI | `frontend/app/<tool>/page.tsx`, `frontend/components/conversion/ConversionTool.tsx`, option components, `SuccessDownload.tsx`, shell/sidebar/icons |
| Direct routes | `backend/app/routers/pdf.py`, `convert.py`, `images.py` |
| Jobs | `backend/app/routers/jobs.py`, `backend/app/services/job_service.py`, `backend/app/models/schemas.py` |
| Shared controls | `backend/app/core/validators.py`, `security.py`, `file_utils.py`, `progress.py`, `exceptions.py`; `backend/app/config.py` |
| Lifecycle | `backend/app/services/cleanup_service.py`, `job_service.py` |
| Dependencies | `backend/requirements.txt`, `frontend/package.json` and npm lockfile; release inventories later under setup.md |
| Existing tests | `backend/tests/test_jobs.py`, `test_validation.py`, `test_security.py`, `test_cleanup_service.py`, individual tool tests |

Known integration traps:

- Jobs use a `JobTool` union, a separate router allowlist, `JobSpec`, dispatch and result metadata. The current dispatch falls through to images processing after known branches: make dispatch exhaustive when extending it; an unknown tool must fail clearly, never accidentally process as images.
- `JobSpec` currently has only mode/ranges options. Introduce validated typed options per new tool; never execute arbitrary client dictionaries, functions, paths or commands. Preserve existing option compatibility.
- Frontend output types currently cover PDF/DOCX/ZIP only. Extend MIME/type/filename handling before new output formats; keep strict mapping and existing results working. Unknown output must not silently become PDF.
- Existing strict PDF validation rejects encryption and active content. Unlock and repair need isolated validation paths. Do not disable validation globally or allow PDF JavaScript merely to support forms.
- Configured defaults: 50 MB/file, 200 MB combined, 20 files/request, 2,000 PDF pages/job, 500 MB output, 60-second conversion timeout. These are current defaults, not adequate limits for every new renderer/model. Rendering pixel totals and engine memory/time need additional limits; do not simply raise all global limits.
- Existing job metadata is process-local. Retain the single-process server contract; do not add multiple workers, persistence, a database or a queue service without a reviewed need.

## 4. Shared contract for every feature

Every feature inherits this section, the integration map, the check suite and its own card. Suggested filenames/routes below are **new targets**, not existing implementations. Confirm naming at F00 and record changes in one place. Keep existing endpoints compatible. Do not redesign the application shell or branding to add a tool.

### Inputs, options and outputs

- Use the existing multipart upload and async job lifecycle. Add the matching direct route when consistent with current API convention; both routes call the same service/validation. Validate file count/type/structure, finite numeric options, page indices and output limits server-side before expensive work. Client checks improve UX but are not authority.
- User page numbers are 1-based; convert once at the service boundary. Define whether page selection preserves order, permits duplication and accepts ranges per feature. Reject empty or ambiguous selections explicitly.
- Return correct MIME, sanitized filename and extension. Reopen/inspect generated output before reporting success. Do not return partial files as successful output. Each output belongs to an app-created job directory; clients never supply server filesystem paths.
- Preserve input bytes; always create a separate output. Detect existing digital signatures before mutating a PDF and require clear acknowledgement that modification can invalidate them, or reject signed input for that tool until an explicit policy is decided. Never claim signatures were preserved without verification.
- Treat fonts, images, links, annotations, page boxes, rotations and metadata deliberately. Do not promise exact fidelity where the chosen approach cannot deliver it.

### Lifecycle, privacy and interaction

- Reuse queued/validating/converting/finalizing/ready and failed/cancelling/cancelled states. Report counts only when measurable; use indeterminate progress otherwise. Test cancel before/during/after generation and during result claim/download.
- Preserve cleanup on success, failure, timeout, cancellation, download and expiration. Interactive previews need their own bounded session lifetime: keep required inputs alive while editing, then release on submit/reset/expiry; do not reuse a download-once result endpoint as thumbnail storage. Cancelled/stale previews must not overwrite current selections.
- No document history/localStorage/IndexedDB persistence by default. Bound and revoke Blob URLs; abort stale requests; remove local preview artifacts. Do not introduce analytics, remote fonts/CDNs, cloud inference, crash uploads or automatic model/runtime downloads.
- Keep processing local. Rendering/parsing must not fetch document-linked assets. Update networking remains a later desktop-controller responsibility under setup.md.
- Keyboard alternatives must exist for dragging, page arrangement and region selection. Label controls, announce progress/errors and manage focus. Reuse design tokens/icons/layout; obtain approval for material design-contract changes.

### Windows portability during feature work

- Choose dependencies with an actual Windows x64/offline distribution path; document versions, native DLLs, fonts, resource data, licenses, build versus runtime requirements and expected bundle impact. Do not assume the current machine's packages can be redistributed unchanged.
- Use configurable engine/resource resolvers and app-owned working directories; no username-specific paths, shell-built commands, reliance on working-directory assumptions or hardcoded system installs. Keep CLI arguments separate, protect secrets from command lines/logs and terminate only owned children.
- Validate each additional native engine/model on the available Windows development environment with networking blocked where possible. This is preliminary evidence, not clean-machine installer acceptance. If unavailable, record the gap; do not claim portability is proven.

## 5. Verification, review and recovery gates

Discover the current interpreters and scripts before running commands. At planning time `backend/venv/Scripts/python.exe` exists; Git is available and GitHub CLI was not found. Do not install tools merely to satisfy this plan, and do not treat missing gh as blocking local work.

| Check | Working directory and command / evidence |
|---|---|
| Focused backend behavior | In `backend`: `.\venv\Scripts\python.exe -m pytest tests/<affected_test>.py -q` (replace placeholder with actual file) |
| Backend regression | In `backend`: `.\venv\Scripts\python.exe -m pytest tests -q` |
| Frontend required checks | In `frontend`, separately: `npm run lint`, `npm run typecheck`, `npm run build` |
| Frontend behavior | Smallest existing/approved test runner for meaningful option/state/coordinate behavior; no frontend test script currently exists, so select/document a minimal setup only when needed |
| Browser acceptance | Real local backend and synthetic inputs: select, configure, convert, inspect/download, retry, cancel, backend unavailable, reset and keyboard flow; correct output content and filename |
| Privacy/lifecycle | Synthetic inputs; verify no third-party browser requests, linked resource fetches, content logging or stale files; native process traffic must be assessed separately from browser traffic |
| Review | Language/component and security review appropriate to changed files; fix blocking findings, rerun affected checks |

Every implemented feature needs focused service/API tests, job integration coverage and real browser/output acceptance. Include malformed/unsupported inputs, invalid options, resource limits and cleanup. Run full backend regressions and all frontend required checks before closing each F milestone; report exact failures/skips and whether failures predate the change. Do not hide failed required checks behind a documentation update. Re-run unchanged checks only when new edits, failures or unresolved concerns justify it.

Use fixtures with measurable semantics: selectable Unicode text, asymmetric page labels, mixed dimensions/rotation, photos/transparency, tables, forms, links, encrypted and malformed PDFs. Render output when visual content matters and inspect extraction/structure where appropriate. Do not rely exclusively on pixel equality across renderer/font versions or on extension checks.

Recovery for every step: remove/disable only that step's new tool exposure and revert its own contract/service changes as a coherent unit, preserving existing tools and user edits. Revert shared dependencies only when unused by completed steps. Never use broad Git reset/clean or delete user outputs. Keep a failing feature unavailable instead of presenting a broken card. Dependency/migration changes need documented downgrade consequences.

## 6. F00 - Baseline handoff and contract foundation

Prerequisite: W0 evidence. Owner execution authorization must exist before application edits.

1. Resolve the feature semantics listed as decisions on later cards; resolve only decisions needed for the next step, not all future questions at once. Record accepted choices, open issues and feature availability in this guide/memory. Fixed requirement: no cloud document processing. OCR/AI are post-MVP expansions, not retroactive claims about the original PRD.
2. Define additive tool IDs, slugs, job/direct route names, option schemas, result MIME/types and error mappings for the next authorized slice. F01/F02's frozen contracts and evidence are in docs/f01-f02-verification-2026-10-27.md. Resolve F03-F05 contracts before those features; extend later formats just before use. Use `/api/jobs/<tool>` with current read/result/cancel conventions; new direct paths follow existing routers. Freeze the agreed mapping in the step evidence before implementation; do not maintain conflicting copies.
3. Plan bounded page preview/metadata support used by crop/organize and later interactive tools. Prefer the existing local PyMuPDF renderer through controlled backend endpoints if it fits; local client rendering is an alternative requiring a documented choice and packaged worker/assets. Specify preview session ownership, expiry, limits and access control compatible with the later desktop transport. Implement only when first needed, with no broad framework rewrite.
4. F00 is a contracts-only handoff; do not make its completion depend on future F01 code. Implement and prove the shared contract additions inside F01's vertical slice, using typed discriminated options/results and exhaustive dispatch only as needed. Test existing seven tools after shared edits. Avoid an untested generic plugin architecture.

Exit: W0 evidence linked, first-slice contracts recorded, no unresolved decision blocks F01, no speculative tools advertised. If larger than one reviewable change, split F00 into numbered substeps and keep parent pending until verified.

## 7. Tier 1 - Straightforward additions

Each card inherits sections 2-5. Execute serially; a tier is not complete until every selected feature has actual exit evidence.

### F01 - Rotate PDF

- **Context/paths:** reuse pypdf/PyMuPDF; new `backend/app/services/pdf_rotate_service.py`, focused tests and `/rotate-pdf` page/options; update integration map surfaces.
- **Contract:** one validated PDF; explicit selected pages (default all) and clockwise 90/180/270-degree rotation relative to existing rotation; unchanged page order/count; PDF output. Reject unsupported angles/indices; preserve inherited rotation correctly.
- **Work:** implement service and tests, shared job/direct integration, UI and errors as one vertical slice. Rotation supports parameter controls without first requiring a complex editor.
- **Exit evidence:** asymmetric portrait/landscape pages with existing rotations render correctly; four 90-degree rotations restore appearance; unselected pages/text remain intact; lifecycle suite passes. Rollback: common recovery rule, including only F01-specific shared additions.

### F02 - PDF to JPG

- **Context/paths:** existing PDF-to-Word appearance rendering is reusable knowledge, not the new service; add `pdf_to_image_service.py`, tests and `/pdf-to-jpg`.
- **Contract:** one PDF, selected pages and bounded DPI/quality; one page -> JPG, multiple -> ZIP with deterministic padded page names. Render complete pages; embedded-image extraction is outside this first scope. JPEG is opaque with a defined white background.
- **Work:** add JPG/ZIP output handling, per-page and aggregate pixel/memory/output budgets, cancellation between pages and correct progress. Do not allocate every full-size page simultaneously.
- **Exit evidence:** dimensions match selected DPI, rotation/text/images visible, ZIP page order correct, oversized rendering rejected before allocation, cancel/timeout removes partial images/ZIP. Compare displayed fidelity and actual JPEG validity.

### F03 - Watermark PDF

- **Context/paths:** new `pdf_watermark_service.py`, `/watermark-pdf` options; local fonts and optional image input using existing validation.
- **Contract:** one PDF, selected pages, text or one validated image, position/angle/opacity/scale; PDF output. Resolve supported font/Unicode coverage, overlay versus underlay and default placement before coding those controls.
- **Work:** use page geometry respecting crop/rotation; typed bounded options; embed permitted local fonts/assets; deterministic compositing, no external asset resolution.
- **Exit evidence:** mixed sizes/rotations, transparent images, chosen Unicode scripts and selected-page scope render correctly; source text remains selectable; invalid opacity/dimensions/fonts fail clearly.

### F04 - Page numbers

- **Context/paths:** new `pdf_page_numbers_service.py`, `/page-numbers`; reuse tested text overlay geometry from F03 without coupling unrelated options.
- **Contract:** selected pages, position/margins, starting number and bounded formatting. Resolve whether numbering advances by selected pages or original document position; show a sample label before submission. PDF output.
- **Work:** implement local text placement and preview/sample; preserve underlying content, dimensions and page order.
- **Exit evidence:** first/last page, non-contiguous selection, start value, mixed geometry and multi-digit alignment; compare expected labels to rendered and extracted output.

### F05 - Crop PDF

- **Context/paths:** new `pdf_crop_service.py`, `/crop-pdf`; introduce shared preview/geometry components and endpoints from F00 when needed.
- **Contract:** one PDF, selected pages and finite rectangles inside original page bounds, PDF output. Resolve per-page versus common-margin application. Explain that crop changes visible bounds and can leave content recoverable.
- **Work:** establish one coordinate contract (PDF units, displayed rotation, crop origin, zoom, rounding); submit only validated coordinates. Include numeric/keyboard controls, reset, bounds checks and preview session cleanup.
- **Exit evidence:** rotated/non-zero-origin/mixed-size PDFs crop the intended region; reject empty/outside/NaN rectangles; repeated zoom does not drift; no claim of secure content removal. Preserve crop-hidden content semantics in tests.

## 8. Tier 2 - Moderate work

### F06 - Organize pages

- **Context/paths:** new `pdf_organize_service.py`, `/organize-pdf`; reuse F05 preview lifetime and geometry, not the file reorder component unchanged.
- **Contract:** page manifest of validated source IDs/page numbers and desired output order; reorder/delete/insert pages, PDF output. F00 decision: whether insertion accepts additional PDFs initially and whether duplication is exposed. Explicitly reject deletion of all pages and invalid source references.
- **Work:** accessible thumbnails with keyboard move/delete and undo-before-submit; preserve stable page IDs while order changes. Validate totals across source PDFs; deliberately handle bookmarks/form field collisions or reject unsupported combinations clearly.
- **Exit evidence:** page labels/content prove final order and deletions/insertions; repeated page references follow chosen policy, mixed geometry preserved, limits/cancel/session expiry work without stale thumbnails.

### F07 - Compress PDF

- **Context/paths:** new `pdf_compress_service.py`, `/compress-pdf`; prefer existing PyMuPDF/pypdf capabilities before a new native engine.
- **Contract:** lossless structural optimization first; if image downsampling is offered, explicit quality/resolution presets and disclosure. PDF output plus accurate original/output size. Do not promise a percentage or smaller output.
- **Work:** prove text/vector/form/link preservation for supported inputs; define no-reduction behavior (return original copy or honest no-reduction result) before UI. Never silently rasterize every page.
- **Exit evidence:** text-only and image-heavy fixtures, already-optimized PDF, larger result, fonts/transparency/forms; text/render comparison and measured byte counts; no unsupported quality claims.

### F08 - Protect PDF

- **Context/paths:** new `pdf_password_service.py` shared with F09, `/protect-pdf`; verify secure encryption support in pinned PyMuPDF or pypdf (and required crypto dependencies).
- **Contract:** one supported unencrypted PDF plus confirmed non-empty password, encrypted PDF output. Use a reviewed explicit AES algorithm, never an insecure library default. Clarify opening-password scope versus permissions; do not market viewer permission flags as strong copy protection.
- **Work:** keep password out of URLs/logs/snapshots/persistence; mask UI; erase retained references as soon as lifecycle permits without claiming guaranteed memory zeroization. Do not alter general PDF validation.
- **Exit evidence:** correct password opens output, wrong/missing password cannot decrypt it; verify encryption metadata/algorithm and content after decryption; cleanup/failure tests and secret-log checks.

### F09 - Unlock PDF

- **Context/paths:** reuse F08 service, add `/unlock-pdf`; isolate encrypted-input validation from existing seven tools.
- **Contract:** PDF plus supplied correct password -> unencrypted PDF. No password cracking/bypass promise. Wrong/unsupported encryption produces clear failure.
- **Work:** after decryption, enforce page/resource and active-content checks before further processing; do not accept unsafe content hidden by encryption. Ensure password never appears in job status/results/errors/logs.
- **Exit evidence:** correct/wrong/empty passwords, supported AES variants, malformed/oversized and active-content encrypted files; output opens without password and preserves supported content. Existing tools still reject encrypted uploads.

### F10 - Drawn/image signature

- **Context/paths:** new `pdf_signature_image_service.py`, `/sign-pdf`; reuse F05 geometry, F03 compositing.
- **Contract:** local drawn signature or validated image, selected placement rectangles/pages -> PDF. Label as a visual signature; it provides no cryptographic identity/tamper validation. No remote signature requests.
- **Work:** keyboard-accessible image upload and placement alternative; explicit placement confirmation; ephemeral signature assets only, no saved signature library/history by default.
- **Exit evidence:** visual placement under zoom/rotation/transparency, no unexpected page changes, reset/expiry removes signature assets; UI does not imply certificate signing.

### F11 - PDF to Markdown

- **Context/paths:** new `pdf_to_markdown_service.py`, `/pdf-to-markdown`; add Markdown MIME/result support. A version-compatible local helper is optional, not preselected.
- **Contract:** text PDF -> UTF-8 `.md`; resolve images as omitted versus relative assets in ZIP before coding; explicitly report unsupported scans until F21. Tables/headings/order are best-effort, not guaranteed.
- **Work:** preserve Unicode, reading order as supported and safe links without fetching them; serve downloads as attachments and never execute extracted HTML/scripts in a preview.
- **Exit evidence:** headings/lists/tables/multicolumn text/links, scan-only input, hostile-looking text; compare semantic extraction to fixtures; valid relative assets if selected, no unsafe ZIP paths or third-party fetches.

## 9. Tier 3 - More UI and careful verification

### F12 - Add text, images and annotations

- **Context/paths:** new `pdf_annotation_service.py`, `/edit-pdf`; shared local preview and typed placement operations from F05/F10.
- **Contract:** add bounded text, images, basic shapes/freehand annotations to a PDF. Existing text replacement, reflow and Office editing are outside this step. Resolve supported annotation kinds/fonts before exposing controls.
- **Work:** bounded operation list, deterministic z-order, local undo/reset, server-side validation of coordinates/content length/assets; never accept PDF action scripts from client operations.
- **Exit evidence:** supported additions render with correct position/fonts/order; existing text survives; keyboard controls, long text, invalid operations, cancelled edits and repeated saves verified.

### F13 - Redact PDF

- **Context/paths:** new `pdf_redact_service.py`, `/redact-pdf`; reuse region selection but not crop/opaque overlay as the redaction algorithm.
- **Contract:** explicit selected regions -> PDF with covered text/image/graphics actually removed using supported removal APIs and full rewrite/garbage collection. Scope page-content redaction separately from whole-document sanitization; disclose metadata/attachments limits unless also addressed.
- **Work:** destructive-action confirmation, safe save policy, no incremental save retaining prior sensitive revisions. Decide behavior for hidden OCR text, shared images, annotations and metadata. Reject inputs whose removal cannot be verified for promised scope.
- **Exit evidence:** synthetic unique secrets absent from text extraction and relevant object/image/attachment inspection; no recovery from prior revisions; independent visual and structural checks, reopened in another reader. A black box or raw byte search alone is insufficient proof. Security review is a blocking gate.

### F14 - PDF forms

- **Context/paths:** new `pdf_forms_service.py`, `/pdf-forms`; local field inspection and overlay editing, preserving active-content defenses.
- **Contract:** first fill existing supported AcroForm fields, then create explicitly placed text/check/radio fields; resolve flatten versus editable output. Auto field detection, XFA and scripting are not assumed. Split fill/create into F14a/F14b if needed; both must pass for F14 completion.
- **Work:** unique field identities, labels/defaults/appearance streams and input bounds; deliberately reject unsupported field types/XFA/JavaScript. Never weaken all PDF validators to admit forms.
- **Exit evidence:** values and appearances agree across viewers; repeated names/radio groups/Unicode/flattening are correct, no hidden form submit or JavaScript behavior introduced.

### F15 - Compare PDFs

- **Context/paths:** new `pdf_compare_service.py`, `/compare-pdf`; reuse page renderer, two-input preview session and bounded diff processing.
- **Contract:** two PDFs -> local side-by-side UI with visual differences; decide text-diff support, page alignment and downloadable report format before implementation. Report changed pages, not unsupported assertions about meaning.
- **Work:** define resolution/tolerance to avoid treating antialiasing alone as a semantic change; handle inserted/removed pages explicitly; permit local synchronized navigation. Reports must contain only local data and remain ephemeral unless saved.
- **Exit evidence:** identical PDFs, small text/image change, reordered/added pages, differing fonts/dimensions and scan pairs; known edits are found and false-positive behavior documented.

### F16 - Best-effort repair

- **Context/paths:** new `pdf_repair_service.py`, `/repair-pdf`; separate bounded tolerant-parser path, not changes to all strict validators.
- **Contract:** recoverable damaged PDF -> newly written validated PDF plus honest recovery warnings, or explicit failure. Never promise to recreate absent pages/content. Do not silently relabel partial recovery as complete recovery.
- **Work:** constrain parsing time/memory, preferably isolate risky parsing in a killable owned process where necessary; inspect recovered structure/active content before output; return structured partial-recovery state if chosen at F00.
- **Exit evidence:** recoverable cross-reference damage, unrecoverable/truncated inputs, resource abuse, active content and page-loss cases; output passes strict revalidation, renders, and warnings reflect actual known loss. Ordinary tools remain strict.

### F17 - PDF tables to Excel

- **Context/paths:** new `pdf_to_excel_service.py`, `/pdf-to-excel`; existing table extraction foundation plus a pinned local spreadsheet writer selected by a compatibility check.
- **Contract:** extract tables from text PDFs into `.xlsx`, not original workbook reconstruction. Define table/page-to-sheet mapping, merged-cell behavior and number/date inference. No original formulas promise; scan-only input needs F21 or a clear unsupported error until then.
- **Work:** XLSX MIME/result handling, safe sheet names, bounded cells/sheets, literal text output by default; prevent leading `=`, `+`, `-`, `@` text from becoming executable formulas through writer inference while preserving actual numeric values deliberately.
- **Exit evidence:** bordered/borderless/multipage tables, blank cells/Unicode, multiple tables, scan input and formula-like strings; workbook reopens with expected cell values/types/order and no unintended external links/macros/formulas.

### F18 - PDF to PowerPoint as slide images

- **Context/paths:** new `pdf_to_pptx_service.py`, `/pdf-to-powerpoint`; reuse bounded F02 rendering; select/pin local PPTX writer.
- **Contract:** each selected PDF page becomes an image on one slide in `.pptx`. Text/shapes are not editable. Resolve mixed page aspect ratios (fixed slide canvas and fit/letterbox versus another explicit policy).
- **Work:** PPTX MIME/result support, bounded image resolution/output, alt text if supported; no remote linked media. Keep image-slide mode separate from future F24 editable reconstruction.
- **Exit evidence:** correct slide count/order, mixed aspect ratios, rotated pages and rendering quality; reopen and inspect slide relationships/media; no cropped content under chosen fitting policy.

### F19 - Camera scan to PDF

- **Context/paths:** new `/scan-to-pdf` capture UI; reuse validated images-to-PDF and local preview/crop transformations. Add preprocessing service only if needed.
- **Contract:** local PC camera capture/import -> ordered image pages -> PDF. Capture is opt-in; permission-denied/no-camera fallback is image import. Physical scanner drivers and phone-to-PC transfer are separate requirements, not implied here.
- **Work:** local camera permission, capture/review/retake/order, manual crop/rotation; stop media tracks on navigation/reset. Resolve deskew/perspective correction scope; test secure-context behavior in localhost and later desktop shell without broad permissions.
- **Exit evidence:** real camera test where available, denied/unavailable device, multiple captures, crop/orientation, navigation and cancel stop camera; no media leaves device. Simulated capture alone cannot establish device compatibility.

### F20 - Local HTML to PDF

- **Context/paths:** new `html_to_pdf_service.py`, `/html-to-pdf`; choose a Windows-compatible local rendering engine with an isolated resource loader before installing a dependency.
- **Contract:** uploaded HTML with explicitly supplied local assets -> PDF; resolve a restricted asset bundle format and supported HTML/CSS subset. No arbitrary URL conversion, internet resources, embedded executable content or unrestricted local file access.
- **Work:** reject traversal/symlinks/ZIP bombs if bundling assets; disable JS/plugins/navigation and external protocols. Enforce deny-by-default network and filesystem resolution in the actual renderer; sanitize-only or browser CSP-only solutions do not prove native rendering isolation.
- **Exit evidence:** relative CSS/images/fonts render; synthetic HTTP/DNS callbacks and file/UNC paths cannot be fetched, including CSS imports/redirects/SVG; malicious scripts inert; timeout/child-process cleanup works. Security review blocks completion until isolation is demonstrated.

## 10. Tier 4 - Additional engines or substantial work

These are planned research-and-implementation gates, not promises of universal fidelity. Execute in order. If a gate cannot be met, report the specific decision/evidence needed and keep the step incomplete. Owner may explicitly defer it to a later Windows release; record that release assignment rather than silently skipping it. Do not make a passing prototype the default production engine.

### F21 - OCR PDF

- **Context/paths:** new `pdf_ocr_service.py`, `/ocr-pdf`; select exact local OCR integration and language data compatible with pinned libraries. Do not assume a system Tesseract install or latest documentation behavior.
- **Contract:** scanned PDF -> searchable PDF with visible page appearance preserved and hidden recognized text; explicit languages and mixed-page policy. No handwriting/universal accuracy guarantee. Decide skip-existing-text versus force-OCR behavior without duplicating text layers.
- **Work:** local OCR runtime/data resolver, page/pixel/CPU/time budgets and cancellation; verify offline language resources, Windows native prerequisites and licensing. Add OCR input paths to F11/F17 only as a separate tested follow-up within this step; avoid automatically OCRing every PDF.
- **Exit evidence:** synthetic scans with known text, mixed/rotated/low-resolution pages, selected languages and absent resources; measure character/word accuracy against an agreed fixture threshold, text alignment/searchability and appearance. Record CPU/RAM/time; reject unsupported resources clearly. Missing hardware/quality criteria remain blockers until resolved.

### F22 - PDF/A conversion and validation

- **Context/paths:** new `pdfa_service.py`, `/pdf-to-pdfa`; choose an exact archival profile, converter and independent validator with Windows/offline distribution evidence.
- **Contract:** PDF -> PDF/A conforming to the selected profile with preserved supported content, or fail with validation findings. No renaming/metadata-only compliance claim. PDF/A encryption restrictions and font embedding must be handled.
- **Work:** profile-specific resource/color/font policy and converter proof; inspect arbitrary PDF input fidelity rather than assuming LibreOffice Office-to-PDF export proves PDF-to-PDF/A. Package validator/resources for later Windows acceptance.
- **Exit evidence:** independent profile validation passes every claimed-success output; visual/text checks detect content loss; unsupported fonts/forms/transparency cases have honest behavior. Record exact profile/tool versions/report. Do not ship a compliant-looking but unvalidated result.

### F23 - Certificate-based PDF signing

- **Context/paths:** new `pdf_digital_sign_service.py` and explicit certificate-signing mode; separate from F10 signature images and Windows executable signing in W5.
- **Contract:** locally available signing key/certificate -> cryptographically signed PDF; resolve PFX/OS certificate store scope, trust/expiration behavior, visible appearance and allowed certification policy before implementation. Default path must work offline. No remote signing/timestamp/revocation calls without separately agreed networking policy.
- **Work:** choose local signing/validation library, ephemeral secret handling and safe key access; never embed private keys in app resources. Preserve prior signatures only through verified compatible incremental signing; block conflicting edits/certification permissions.
- **Exit evidence:** independent reader verifies document integrity/signature, subsequent modification invalidates as expected, wrong key password fails, expired/untrusted/self-signed states communicated accurately. Offline integrity is not proof of externally trusted identity or long-term timestamp validity.

### F24 - Editable PDF to PowerPoint

- **Context/paths:** extend F18 via a separate replaceable reconstruction engine/mode; research spike before production integration.
- **Contract:** reconstruct a defined supported subset of text/images/basic graphics as editable slide objects. Owner must approve supported layouts and measured fidelity/editability thresholds; image slides must never be silently reported as editable conversion.
- **Work:** representative layout corpus, bounding-box/font extraction and actual editable object creation; preserve grouping/order as supported. Complex vectors, fonts, tables and scans need explicit limitations. Prove CPU/RAM/output behavior on target class hardware.
- **Exit evidence:** reopen in presentation software and edit text/objects, compare rendering/reading order and object counts to corpus; below-threshold inputs fail clearly or offer an explicit switch to F18. No credible engine/threshold -> unresolved gate, not speculative implementation.

### F25 - Local AI summarization

- **Context/paths:** new local model service/adapter and `/summarize-pdf`; no cloud SDK fallback. Use F11 extraction and F21 only when explicitly selected/needed.
- **Contract:** PDF -> local summary with page references and stated coverage; choose model/runtime/license, supported languages, context/chunk policy and target hardware budgets. Determine output download format before UI integration.
- **Work:** measure actual model size/startup/RAM/CPU quality, chunk long documents without silent truncation; treat document instructions as untrusted text, no tools/network/filesystem powers for the model. Bundle model/tokenizer resources for offline use or an owner-approved offline installation package; never download at first conversion.
- **Exit evidence:** grounded claims/page references on an agreed corpus, no unsupported major claims under defined evaluation, long/empty/scan/injection-like inputs, cancel/resource errors, full process-tree offline test and redacted logging. Clearly communicate model uncertainty; no guarantee every summary is correct.

### F26 - Local PDF translation

- **Context/paths:** local translation engine/model adapter and `/translate-pdf`; reuse extraction/OCR resources where appropriate, not an assumption F25's model is adequate.
- **Contract:** explicit source/target language pairs, supported scripts/fonts and translated output format. Resolve text-first versus reconstructed-layout PDF before implementation; preserving every layout/font is not promised.
- **Work:** local translation model/data and glossary/paragraph mapping as agreed; bounded chunking, page overflow/font fallback, RTL/script shaping, handling tables/images and missing OCR. No translated data/model calls to third-party endpoints.
- **Exit evidence:** representative bilingual review/approved reference rubric, page/paragraph coverage, no silent untranslated/truncated regions, numbers/names/tables, long and RTL text where claimed; render/inspect fonts/overflow and measure hardware resources offline. Missing language quality review remains an explicit gap.

## 11. FR - Feature release acceptance and Windows handoff

Prerequisite: F01-F26 complete, or each deferred feature has an explicit owner-approved later-release assignment and dependent work is adjusted. No inferred deferral based on time, difficulty or missing tools.

- Re-run full backend suite, frontend lint/typecheck/build and end-to-end acceptance across the seven original tools and every enabled new tool. Cover both PDF-to-Word modes and new output types. Record counts, failures/skips and known limitations.
- Review cross-feature interactions: crop/rotate/organize coordinates, forms during merge/organize, OCR text under redaction, encrypted inputs, signing after edits, PDF/A constraints, safe HTML and extracted-content previews. These interactions need explicit fixtures, not assumptions from isolated passes.
- Keep output files ephemeral in app storage; saved files remain user-owned. Confirm cleanup, cancellation, runtime resource limits and dependency failures across all enabled engines.
- Freeze the feature/API/result contracts, exact dependency/resource list, known limits and measured development requirements. Distinguish features complete from installer-ready. Remove disabled/unimplemented tools from user navigation or label unavailability honestly; no fake success/downloads.
- Create a release-scope matrix in the ledger (enabled, deferred with owner decision, unsupported); summarize engine versions, resource paths, Windows compatibility gaps, model/language data, fonts, source/notices and test evidence for setup.md W1-W3. No engine selection is final until supported by proof.
- Update setup.md's observed baseline with actual feature counts/evidence only after this gate. Do not change historical seven-tool baseline rows into false earlier claims. Update project memory before reporting the feature release ready for Windows work.

Windows sequence then resumes: W1 accepts exact target/hardware/scope; W2 packages and exercises the entire selected feature release; W3 freezes all engines/resources/storage/legal materials; W4 installer/lifecycle; W5 signing; W6 updates; W7 repeatable staging; W8 clean-machine acceptance of every enabled feature; W9 owner-authorized publication; W10 maintenance. W2 cannot validate only the original seven after feature expansion. New native/model resources must not be fetched during installation/use if full offline installation is promised.

## 12. Progress ledger and change protocol

All rows start **planned**, including research-heavy features. Replace status only with evidence. Add dated substeps when needed; one large card may require several reviewable changes. Do not parallelize feature milestones out of order; read-only review/test design can run alongside implementation, and independent same-step edits require explicit path ownership.

| ID | Feature / gate | Status | Evidence / decisions |
|---|---|---|---|
| W0 | Existing baseline in setup.md | Evidence recorded | Full157-test regression passes; live Office timeout observations remain; see F01/F02 verification record |
| F00 | Contracts and foundation | Complete through F03/F04 slice | Typed contracts frozen; F05+ decisions remain before dependent work |
| F01 | Rotate PDF | Complete locally | Backend/API/jobs/browser/output verification and review; see docs/f01-f02-verification-2026-10-27.md |
| F02 | PDF to JPG | Complete locally | Single JPG/multi ZIP, limits/cancel/cleanup and browser acceptance; same evidence record |
| F03 | Watermark | Complete locally | Text/image overlays, geometry/resource/lifecycle and real browser/output acceptance; docs/f03-f04-verification-2026-10-28.md |
| F04 | Page numbers | Complete locally | Selected-page sequence, labels/alignment and browser/output verification; same evidence record |
| F05 | Crop | Planned | |
| F06 | Organize | Planned | |
| F07 | Compress | Planned | |
| F08 | Protect | Planned | |
| F09 | Unlock | Planned | |
| F10 | Drawn/image signatures | Planned | |
| F11 | Markdown | Planned | |
| F12 | Add text/images/annotations | Planned | |
| F13 | Redact | Planned | |
| F14 | Forms | Planned | Fill/create substeps |
| F15 | Compare | Planned | |
| F16 | Repair | Planned | Best-effort only |
| F17 | Tables to Excel | Planned | |
| F18 | Image-slide PowerPoint | Planned | |
| F19 | Camera scan | Planned | |
| F20 | Local HTML | Planned | |
| F21 | OCR | Planned | Engine/languages/quality gate |
| F22 | PDF/A | Planned | Profile/converter/validator gate |
| F23 | Certificate signatures | Planned | Key/trust/offline policy gate |
| F24 | Editable PowerPoint | Planned | Research/quality gate |
| F25 | Local summarization | Planned | Model/hardware/quality gate |
| F26 | Local translation | Planned | Languages/output/quality gate |
| FR | Feature release handoff | Planned | Before Windows W1 |

For every adjustment record: date, owner instruction if scope changes, step/substep, reason, affected paths, dependencies, chosen/rejected alternatives, exact verification results/skips, unresolved issues, recovery and next action. Keep this guide and setup.md cross-references consistent; original PRD and completed Phase 2 remain historical. If blocked, distinguish a missing product decision from an environment/tool failure; do not invent a workaround changing privacy or output promises. Requests to execute future steps inherit all these controls.

## 13. Planning evidence and source references

Applied ECC Blueprint for construction steps and adversarial review, Product Capability for explicit contracts/open decisions, and Deployment Patterns for staged release/readiness/recovery adapted to local Windows distribution. Cloud services and traffic-splitting deployment mechanisms are not needed.

Source inspected: AGENTS/PRD/setup/memory, feature assessment, frontend instructions/design/roadmap/types/options/results/package scripts, backend configuration/validation/jobs/tests. No application tests, conversions, installed Windows checks or benchmarks were run to create this guide. Exact future library APIs must be rechecked against pinned versions before coding.

Relevant primary references already consulted for the feature assessment: [pypdf transformations](https://pypdf.readthedocs.io/en/latest/user/cropping-and-transforming.html), [PyMuPDF pages](https://pymupdf.readthedocs.io/en/latest/page.html), [forms](https://pymupdf.readthedocs.io/en/latest/widget.html), [OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html), [document saving](https://pymupdf.readthedocs.io/en/latest/document.html), and [LibreOffice PDF export](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html). Latest online docs do not establish API compatibility with the pinned application.
