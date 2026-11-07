# F01 and F02 implementation evidence

Date: 2026-10-27. Scope: local application features, not Windows installer work. Owner explicitly authorized implementing F01/F02 using ECC guidance and subagents.

## Implemented contracts

| Tool | Frontend | Direct route | Async submission | Options / output |
|---|---|---|---|---|
| Rotate PDF | `/rotate-pdf`, id `rotate` | POST `/api/pdf/rotate` | POST `/api/jobs/pdf-rotate` | `file`; `pages` blank=all or 1-based ranges; `angle` 90/180/270 default90; PDF |
| PDF to JPG | `/pdf-to-jpg`, id `pdfToJpg` | POST `/api/pdf/to-jpg` | POST `/api/jobs/pdf-to-jpg` | `file`; same `pages`; integer `dpi`72-300 default144, `quality`40-95 default85; single selected page JPG, multiple ZIP |

Selections reject duplicates, overlaps, invalid/out-of-document pages and excessive numeric inputs; output follows source-page order even if selection order differs. Rotation adds to existing page orientation, preserves count/content and rejects filled digital signatures/certification. JPEG renders full pages on an opaque white RGB background; it does not extract embedded images. Padded names retain source page numbers.

No dependencies were added. Reused pypdf/PyMuPDF/Pillow. Added typed option objects and exhaustive job dispatch. JPEG native rendering runs in an owned hidden subprocess with default 40-million-pixel per-page and 100-million aggregate budgets, output-byte limits, deadline/cancellation and cleanup. Bounded metadata is delivered via a private job file, not a potentially blocking stdin write. Generated JPG/ZIP and rotated PDF are reopened/inspected before success.

The frontend preserves the established async `application/x-privcon-result` transport. Actual MIME/filename/tool-result agreement is validated before restoring the Blob type; arbitrary unknown result types cannot silently become PDFs. Existing seven tools remain configured; the new tools append to navigation. Sidebar scrolling makes added rows reachable without changing the shell dimensions.

## Actual verification

| Check | Actual result |
|---|---|
| New backend service/API/job tests | 42 passed, including malformed/oversized/signed/encrypted inputs, rotation semantics, single/multiple output, budgets, worker failure/timeout/cancel and cleanup |
| New backend module coverage | 89.59% aggregate (rotation87%, JPEG coordinator94%, renderer81%, options98%); covers these modules, not the whole application |
| Full backend regression | 157 passed, zero skips, including the installed LibreOffice round-trip integration test; 86.02 seconds |
| Final narrow timeout test after test-lint adjustment | 1 passed, 41 deselected |
| Python lint | Ruff passed for all changed backend app files and new test file |
| Frontend tests | 9 passed; 100% line/branch/function coverage for the two pure option/result helpers only |
| Frontend lint / types | Passed; final production build also performs TypeScript verification |
| Production build | Passed unchanged Next/Turbopack with bundled Node24.22.1 outside sandbox; all12 static pages generated including both new routes |
| Browser | Real production frontend + real local FastAPI, headless installed Edge156 through bundled Playwright; synthetic files only |
| Browser journeys | Rotate selected page; invalid duplicate selection; reset to defaults; JPG DPI bound; single JPG; ZIP for selection3,1; out-of-document recoverable error; real server job cancellation; simulated backend connection failure/retry; sidebar navigation |
| Download inspection | Rotations0/270/180 for fixture rotated on page2 by180; selected JPEG500x1000 at144DPI; ZIP pages001/003 in source order; archive integrity passes |
| Responsive / browser privacy observations | No horizontal overflow at375/768/1487CSS pixels; no page exceptions; no external HTTP(S) requests observed during these journeys. This is not a screen-reader audit or full native-process network isolation proof |

Reproduction commands from `backend`: `.\venv\Scripts\python.exe -m pytest tests -q --basetemp <new-workspace-test-directory>` and `.\venv\Scripts\python.exe -m pytest tests/test_pdf_tools.py -q` with an available writable temp directory. For coverage include `--cov=app.services.pdf_tool_options --cov=app.services.pdf_rotate_service --cov=app.services.pdf_to_image_service --cov=app.services.pdf_to_image_worker --cov-fail-under=80` when pytest-cov is available.

From `frontend`: `npm test`, `npm run lint`, `npm run typecheck`. The successful production build command was `& 'C:\Users\David\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' node_modules/next/dist/bin/next build`. This is the verified local runtime path, not a path to hardcode in distributed source.

## Review and corrected findings

Used ECC TDD Workflow, Verification Loop, React Patterns/Testing and local browser QA guidance. Backend/frontend workers had distinct file ownership. Independent Python, React, TypeScript and integration/security-focused code reviews were performed. Build resolver diagnosed the runtime-specific failure without changing application configuration.

Tests were written before behavior. Parent integration review caught the private async MIME regression and added failing transport tests before the fix. Python review caught blocking large-spec stdin delivery and oversized integer tokens; five new regressions failed before fixes and passed afterward. Python re-review approved both fixes. No known actionable F01/F02 review finding remains.

## Evidence limits and follow-up

- Sandbox pytest temporary-directory/native-worker restrictions caused unusable initial runs. Verification was rerun outside that sandbox with workspace-local test directories. The first all-suite run collected newly written RED tests while importing pre-change routes; its expected404 failures were not final regressions.
- System Node24.19.0 failed Turbopack CSS worker startup even outside the sandbox. Bundled Node24.22.1 completed the unchanged build twice, including final corrected source. No bundler/config/dependency workaround was introduced; document the tested runtime for later Windows build pinning.
- The original LibreOffice integration test timed out on an early baseline attempt, then passed in the final full suite. Separate live-server baseline acceptance initially timed out on DOCX and PPTX; XLSX, merge, split, images and both PDF-to-Word modes succeeded with real outputs. These Office timing observations are tracked separately from F01/F02 and must not be represented as a clean all-seven live acceptance result.
- A targeted follow-up on the same running backend converted PPTX successfully (HTTP200,22224-byte PDF), while the synthetic DOCX fixture again timed out (HTTP504). The live DOCX finding remains unresolved. No LibreOffice conversion implementation was changed for this task.
- No Windows shell, installer, updater, signing or clean-machine offline acceptance was implemented/tested. The source JPEG worker currently uses `sys.executable -m app.services.pdf_to_image_worker <private-spec-path>`; W2 must provide and verify an equivalent frozen worker entry point. Current source success is not PyInstaller readiness.
- No commit, push or publication. No private document was used. Generated synthetic inputs/downloads are in ignored local test storage and are not release artifacts.

Next planned feature is F03 Watermark, requiring its own execution authorization/scope. Windows W1-W10 remains after feature release acceptance under implementation.md/setup.md; this work does not start the desktop phase.
