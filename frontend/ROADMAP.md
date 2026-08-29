# PrivCon Phase 2 Frontend Roadmap

**Project phase:** Phase 2 — Frontend MVP  
**Status:** Active  
**Current milestone:** Phase 2.2 — Persistent shell, navigation, dashboard, and empty states  
**Primary target:** All six PrivCon tools work end-to-end in a local browser with the approved visual design, accessible interactions, exact backend-contract handling, and no third-party file or asset traffic.

## 1. Authority and change control

Use the following source order when planning, implementing, or reviewing frontend work:

1. `docs/design.md` and `docs/PrivCon_MVP_Prototype_Reference.png` — visual source of truth.
2. `PrivCon_Frontend_PRD_SRS_Design.md` in the approved frontend design workspace — functional frontend behavior, component contracts, state model, and error copy.
3. `../PHASE_1_COMPLETION_SUMMARY.md` — frozen backend API, limits, output, and error contract.
4. `../Privcon PRD.md` — product requirements and MVP boundaries.
5. `../setup.md` — overall project architecture and phase boundaries.

Rules:

- A visual conflict is resolved in favor of `docs/design.md` and the approved prototype.
- A backend behavior conflict is resolved in favor of `../PHASE_1_COMPLETION_SUMMARY.md` and the implemented backend.
- Do not change the backend contract during Phase 2 unless the user explicitly approves a contract change.
- Do not edit the design contract, PRD, or roadmap merely to make an implementation deviation look compliant.
- Do not move Phase 3 work into this roadmap.

## 2. Phase 2 definition of done

Phase 2 is complete only when:

1. The dashboard and all six tool routes are usable from `http://localhost:3000`.
2. DOCX, PPTX, XLSX, PDF merge, PDF split, and images-to-PDF all succeed against the real local backend.
3. Client-side checks prevent obvious wrong-type, oversize, missing-file, and invalid-range requests.
4. Every documented backend error code maps to approved human-readable UI copy.
5. Merge and Images-to-PDF preserve the visible mouse/keyboard order in the submitted multipart request.
6. Split PDF correctly handles `every_page` and 1-based inclusive `ranges`, including PDF-versus-ZIP output.
7. Uploading, processing, success, recoverable error, and backend-unavailable states always provide a clear next action.
8. The interface meets the approved monochrome design contract and reference geometry at `1487 × 1058`.
9. Core interactions are keyboard-operable, state changes are announced, and focus states remain visible.
10. No file, filename, analytics event, font, icon, or document payload is sent to a third-party service.
11. Lint, TypeScript, production build, visual QA, privacy inspection, and real-file browser acceptance all pass.

## 3. Milestone overview

| Milestone | Target | Status |
|---|---|---|
| Phase 2.0 | Contract and scaffold baseline | Complete |
| Phase 2.1 | Frontend foundation and design tokens | Complete |
| Phase 2.2 | Persistent shell, navigation, dashboard, and empty states | Next — brand asset gate open |
| Phase 2.3 | Local file intake and client-side validation | Pending |
| Phase 2.4 | API client, health monitoring, conversion state, and downloads | Pending |
| Phase 2.5 | Word, PowerPoint, and Excel end-to-end workflows | Pending |
| Phase 2.6 | Merge PDF and Images-to-PDF ordering workflows | Pending |
| Phase 2.7 | Split PDF modes and range workflow | Pending |
| Phase 2.8 | Complete states, accessibility, and responsive refinement | Pending |
| Phase 2.9 | Full verification and owner acceptance | Pending |

## 4. Milestone details

### Phase 2.0 — Contract and scaffold baseline

**Goal:** Establish a valid Next.js frontend workspace and make all source contracts locally available.

Completed:

- Next.js 16.3.3, React 19.2.8, Tailwind CSS 4, and strict TypeScript scaffold exists.
- All seven App Router route files exist.
- Shared shell, conversion, icon, hook, and library module paths exist.
- The approved design contract, prototype reference, local Geist font, and header lockup are copied into the frontend.
- Local API configuration is represented by `.env.local.example`.
- ESLint, TypeScript, and the production build pass with the placeholder routes.

Outstanding prerequisite:

- Add a clean production `public/brand/privcon-mark.png` extracted from the approved PrivCon brand artwork. Do not approximate the mark with text or CSS.

**Exit criteria:** The scaffold builds and every expected source path exists, with no invented brand asset.

### Phase 2.1 — Frontend foundation and design tokens

**Goal:** Replace create-next-app defaults with the approved local, privacy-safe frontend foundation.

Deliverables:

1. Load `app/fonts/Geist-Variable.woff2` through `next/font/local`; remove Google-font imports.
2. Set PrivCon metadata, title, description, and local favicon/brand references.
3. Implement the primitive, semantic, and component CSS tokens from `docs/design.md` in `app/globals.css`.
4. Remove default dark-mode, Vercel, external-link, and generic starter styles/content.
5. Define shared types in `lib/types.ts` for tool configuration, UI phases, split options, API errors, and conversion results.
6. Define all six frozen tool configurations in `lib/constants.ts`, including routes, endpoints, multipart field names, accepted formats, multiplicity, and output kind.
7. Add pure formatting and error-mapping helpers in `lib/format.ts` and `lib/errors.ts`.
8. Keep dependencies unchanged unless a later milestone proves a new dependency is necessary and the user approves it.

Verification:

- Search built source for remote font, analytics, Vercel, and starter-template references.
- Confirm all component colors resolve through the three-layer token system.
- Run `npm run lint`, `npm run typecheck`, and `npm run build`.

**Exit criteria:** The frontend has a clean PrivCon foundation, uses only local typography/assets, exposes typed configuration for all tools, and contains no default template or external-service behavior.

Completion evidence (29 August 2026):

- Local Geist is loaded with `next/font/local` and emitted in the production build.
- PrivCon metadata and local brand references replace create-next-app defaults.
- Primitive, semantic, and component token layers match `docs/design.md`.
- All six tool configurations and the frozen backend error codes are represented by shared TypeScript contracts.
- Source and built-output scans found no Google-font, Vercel, starter-template, analytics, or telemetry references.
- `npm run lint`, `npm run typecheck`, and `npm run build` passed.

### Phase 2.2 — Persistent shell, navigation, dashboard, and empty states

**Goal:** Build the approved visual frame once and reuse it across the dashboard and all six routes.

Deliverables:

1. Build the single local icon family in `components/icons/PrivConIcons.tsx`.
2. Build `AppHeader`, `ProgressRail`, `ToolSidebar`, and `AppShell` from the measured contract.
3. Keep the exact six-tool order and wording from `docs/design.md`.
4. Implement active-route navigation with `aria-current="page"`.
5. Implement the three-stage progress rail with semantic ordered markup.
6. Build the dashboard within the same continuous utility shell; do not add marketing sections, floating cards, gradients, shadows, or colored accents.
7. Build all six route empty states from shared tool configuration.
8. Use the exact two-line privacy statement and a single dominant black upload action.

Visual verification:

- Capture the Word-to-PDF route at `1487 × 1058`.
- Compare it 1:1 against `docs/PrivCon_MVP_Prototype_Reference.png`.
- Verify header, rail, shell, sidebar, dropzone, active row, and primary CTA geometry.
- Check hover, active, focus-visible, and reduced-motion behavior.

**Exit criteria:** All routes share one stable shell, the approved empty state is visually faithful, and route changes do not alter shell geometry.

### Phase 2.3 — Local file intake and client-side validation

**Goal:** Let users select valid local files safely before any network request occurs.

Deliverables:

1. Build `UploadDropzone` with click, keyboard, and drag-and-drop file selection.
2. Keep selected `File` objects in component memory only; do not use localStorage, sessionStorage, IndexedDB, analytics, or external preview services.
3. Build `FileListPreview` with filename, formatted size, position where relevant, and remove action.
4. Implement extension and per-file size pre-checks in `lib/file-validation.ts`.
5. Enforce single versus multiple selection and minimum-file requirements from tool configuration.
6. Reject unsupported files before any API call using the approved error copy.
7. Advance the progress rail to Stage 2 only after accepted files are present.
8. Revoke every object URL when it is replaced, removed, or the component unmounts if local previews are used.

Verification:

- Test browse, drag/drop, keyboard activation, remove, replace, duplicate selection, wrong extension, oversize file, and empty selection.
- Confirm no network request occurs during file selection or client-side rejection.
- Run lint, typecheck, and build.

**Exit criteria:** Every tool accepts the correct local file set, rejects obvious invalid input without a request, and remains fully usable by keyboard.

### Phase 2.4 — API client, health monitoring, conversion state, and downloads

**Goal:** Create one typed, privacy-safe integration layer for the frozen local API.

Deliverables:

1. Implement `lib/api.ts` around `NEXT_PUBLIC_API_BASE_URL`, defaulting only through documented local configuration.
2. Build multipart bodies with the exact `file` or ordered `files` field names and split form fields.
3. Parse JSON error bodies using the frozen `{ error, message }` shape.
4. Parse response headers and blobs without logging filenames or payload data.
5. Derive safe output names from `Content-Disposition`, with deterministic tool-specific fallbacks.
6. Implement `useBackendHealth` for the quiet local-backend status.
7. Implement `useConversion` as the shared idle/files-selected/ready/converting/success/error state machine.
8. Build the shared indeterminate processing, success/download, and error/retry components.
9. Use `URL.createObjectURL` only for local result download and revoke URLs on reset/unmount.
10. Do not display fake conversion percentages when the backend provides no progress stream.

Verification:

- Test healthy, unavailable, timeout, busy, validation-error, unknown-error, PDF-response, and ZIP-response paths.
- Confirm retry retains files where the contract permits it.
- Confirm reset/repeat releases result URLs and file references.
- Inspect browser network traffic for localhost-only requests.
- Run lint, typecheck, and build.

**Exit criteria:** One shared API/state layer can represent every documented success and failure without leaking data or leaving the interface stuck.

### Phase 2.5 — Word, PowerPoint, and Excel end-to-end workflows

**Goal:** Complete the three structurally identical single-file Office conversion routes against the real backend.

Deliverables:

1. Implement `ConversionTool` as the shared route engine.
2. Wire `/word-to-pdf` to `POST /api/convert/docx-to-pdf` using `file`.
3. Wire `/ppt-to-pdf` to `POST /api/convert/pptx-to-pdf` using `file`.
4. Wire `/excel-to-pdf` to `POST /api/convert/xlsx-to-pdf` using `file`.
5. Preserve selected files after recoverable errors.
6. Support successful browser download plus an explicit download-again action.
7. Return to a clean idle state for convert-again without persistent job history.

Verification:

- Use one valid real file for each Office route.
- Test wrong extension, renamed/mismatched content, corrupt package, oversized file, backend unavailable, timeout, and successful download.
- Confirm output begins with a valid PDF signature and uses the returned filename.
- Confirm backend temp folders are empty after completed and failed requests.

**Exit criteria:** All three Office workflows work end-to-end in the browser with shared code and exact error behavior.

### Phase 2.6 — Merge PDF and Images-to-PDF ordering workflows

**Goal:** Complete both ordered multi-file tools while preserving visible order in the submitted request.

Deliverables:

1. Build one reusable `ReorderList` with pointer/mouse reordering and visible keyboard reordering using `Alt + Up/Down`.
2. Include drag handle, position, filename, size, and remove action in each row.
3. Prevent reorder controls from becoming drag-only or color-only.
4. Require at least two PDFs before enabling Merge.
5. Allow one or more JPG/JPEG/PNG/WebP files for Images-to-PDF.
6. Enforce documented per-file, aggregate-size, and file-count pre-checks where the approved frontend contract requires them.
7. Submit multipart files in the exact visible order.
8. Download deterministic `merged.pdf` and `images.pdf` outputs.

Verification:

- Reorder by pointer and keyboard, remove items, add more items, and confirm numbering updates.
- Verify backend output order matches the visible order for several real PDFs and distinguishable images.
- Test too few merge files, wrong types, corrupt files, aggregate oversize, too many files, and successful downloads.
- Run lint, typecheck, build, and browser accessibility checks.

**Exit criteria:** Both ordered tools are fully usable by mouse and keyboard, and the generated output order matches the visible list.

### Phase 2.7 — Split PDF modes and range workflow

**Goal:** Complete the specialized split interface against the frozen range contract.

Deliverables:

1. Build `SplitOptions` with `every_page` and `ranges` modes.
2. Validate 1-based inclusive syntax such as `1-3,5,8-10` before submission.
3. Reject empty tokens, malformed tokens, duplicate pages, overlaps, reversed ranges, zero, and negative pages client-side.
4. Leave page-count bounds to the backend unless a local page-count capability is explicitly approved later.
5. Submit `file`, `mode`, and conditional `ranges` fields exactly as the backend expects.
6. Explain before conversion whether the expected output is one PDF or a ZIP.
7. Render the returned PDF/ZIP filename and download action accurately.

Verification:

- Test every-page, one range, multiple ranges, user-supplied range order, malformed input, overlap, duplicate, reversed, zero/negative, out-of-bounds, encrypted, empty, and active-content PDFs.
- Confirm one range returns PDF and multiple ranges/every-page return ZIP.
- Confirm generated ZIP entry names and order match the backend contract.

**Exit criteria:** Both split modes work end-to-end, invalid syntax is blocked early, and PDF-versus-ZIP behavior is always clear.

### Phase 2.8 — Complete states, accessibility, and responsive refinement

**Goal:** Make every route polished, understandable, and robust across the approved states and viewport classes.

Deliverables:

1. Normalize empty, selected, ready, processing, success, recoverable error, and backend-unavailable presentation across all tools.
2. Keep one dominant black action per state and visually subordinate secondary actions.
3. Implement `aria-live` status announcements and semantic current-step text.
4. Verify all focus states, 44 × 44 px minimum targets, labels, names, and keyboard paths.
5. Ensure status is never communicated by color alone; retain strict monochrome.
6. Honor `prefers-reduced-motion` and keep motion within the approved 120/180 ms rules.
7. Refine large desktop, compact desktop/tablet, and narrow best-effort layouts without hiding tool choice or privacy status.
8. Prevent long filenames, many files, errors, and translated browser UI from breaking the shell.

Verification:

- Complete a keyboard-only pass of all six workflows.
- Check at the reference viewport, 1280 px, 1024 px, 768 px, and representative narrow viewports.
- Inspect focus, zoom, text overflow, reduced motion, contrast, and screen-reader announcements.
- Repeat visual overlay QA for representative empty, selected, processing, success, and error states.

**Exit criteria:** Every state has a clear next action, accessibility requirements pass, and responsive layouts preserve the product hierarchy.

### Phase 2.9 — Full verification and owner acceptance

**Goal:** Prove the complete frontend against the real backend before declaring Phase 2 complete.

Automated gates:

1. `npm run lint`
2. `npm run typecheck`
3. `npm run build`
4. Any approved focused frontend test suite
5. Existing backend regression suite

Real-browser acceptance matrix:

1. Valid DOCX to PDF.
2. Valid PPTX to PDF.
3. Valid XLSX to PDF.
4. Ordered PDF merge.
5. Split every page.
6. Split one range to PDF.
7. Split multiple ranges to ZIP.
8. Ordered JPG/PNG/WebP to PDF, including transparency and EXIF-oriented input.
9. Representative wrong-type, corrupt, oversized, password-protected, unsafe-content, invalid-range, timeout, busy, and backend-unavailable failures.
10. Retry, remove, reset, convert-again, and download-again behavior.

Privacy and cleanup gates:

- Browser network inspection shows only local application/backend requests.
- No analytics, telemetry, remote font, remote icon, or third-party file request exists.
- Browser console contains no file content or user filename logging.
- Backend temporary upload/output folders are empty after successful and failed workflows.
- Result object URLs and in-memory file state are released after reset/unmount.

Visual acceptance:

- Reference overlay at `1487 × 1058` has no unexplained geometry drift.
- All six tools use the approved icon family, type scale, monochrome tokens, shell, and state hierarchy.
- The user performs the final non-technical usability and visual acceptance pass.

**Exit criteria:** Every Phase 2 definition-of-done item is checked, the user accepts the browser experience, and no required work remains before Phase 3.

## 5. Decision gates

These decisions must be resolved before the named milestone. They are recorded here to prevent speculative implementation.

| Decision | Needed before | Recommended default | Status |
|---|---|---|---|
| Clean standalone `privcon-mark.png` asset | Phase 2.2 | Extract exactly from approved brand art; do not redraw | Open |
| Backend health behavior | Phase 2.4 | Check on initial load and after a failed request; avoid continuous polling | Open |
| Frontend representation of backend limits | Phase 2.3 | Mirror frozen Phase 1 limits in typed constants; no new backend config endpoint in Phase 2 | Open |
| Reorder implementation | Phase 2.6 | Native lightweight implementation with explicit keyboard controls; no dependency unless needed | Open |
| Automated frontend test stack | Phase 2.3 | Add only the smallest test setup that materially protects validation/state logic | Deferred — no dependency needed for the Phase 2.1 foundation |

## 6. Required checks after every milestone

At the end of every implementation milestone:

1. Review the diff for unrelated or user-owned changes.
2. Run focused checks for the files and behavior changed.
3. Run `npm run lint` and `npm run typecheck`.
4. Run `npm run build` before marking the milestone complete.
5. Confirm no new third-party request or file-data persistence path was introduced.
6. Compare affected screens and states against `docs/design.md`.
7. Update only the status table and evidence notes in this roadmap; do not silently change milestone requirements.

## 7. Scope boundary

Do not include the following in Phase 2:

- Authentication, accounts, collaboration, cloud sync, public SaaS behavior, payments, or persistent history.
- OCR, AI document analysis, document editing, watermarking, compression, rotation, or other post-MVP tools.
- Dockerfiles, Docker Compose, deployment hardening, OS sandboxing, or public-network security architecture.
- Backend API redesign, config endpoints, or new conversion behavior unless explicitly approved.
- Analytics, telemetry, remote fonts/icons, external upload services, or Google Stitch.

These remain Phase 3 or post-MVP work unless the user explicitly changes scope.

## 8. Immediate next action

Begin **Phase 2.2 — Persistent shell, navigation, dashboard, and empty states** after resolving the standalone `privcon-mark.png` asset gate. Phase 2.1 passed its local font, metadata, token, shared-type, tool-configuration, error-mapping, privacy-scan, lint, typecheck, and production-build checks.
