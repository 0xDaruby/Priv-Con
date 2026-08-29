# PrivCon Phase 1 Completion Summary

**Project:** PrivCon local-first document conversion application  
**Phase:** Phase 1 — Backend Proof of Concept  
**Status:** Code-complete and automated-verification complete  
**Prepared:** 25 August 2026  
**Scope of this document:** Backend work completed during the Phase 1 implementation and security-review conversations

## 1. Executive summary

PrivCon now has a complete local FastAPI backend for all six MVP tools defined by the PRD:

1. DOCX to PDF
2. PPTX to PDF
3. XLSX to PDF
4. PDF merge
5. PDF split
6. Images to PDF

The backend processes files locally with LibreOffice, pypdf, and Pillow. It does not introduce cloud storage, third-party conversion services, accounts, persistent job history, or other features outside the Phase 1 scope.

Phase 1 Steps 1–10 are implemented. The automated test, lint, dependency, privacy, cleanup, and real LibreOffice smoke-test gates pass. The remaining acceptance activity is the owner's manual real-file testing before beginning Phase 2.

## 2. Phase 1 roadmap completion

| Step | Roadmap deliverable | Completion summary |
|---|---|---|
| 1 | Python environment and dependencies | Python virtual environment and pinned backend dependencies are present in `requirements.txt`. The final test-client dependency is `httpx2`, as recommended by the installed Starlette version. |
| 2 | FastAPI scaffold and health endpoint | FastAPI application, startup lifespan, router registration, CORS, exception handling, and `GET /api/health` are implemented. |
| 3 | LibreOffice conversion service | Headless LibreOffice conversion uses an argument list with `shell=False`, a per-job profile, an execution timeout, private output directories, output-signature checks, and cleanup on all known failure paths. |
| 4 | Office-to-PDF endpoints and structural validation | DOCX, PPTX, and XLSX routes accept exactly one matching file, validate the OOXML package before invoking LibreOffice, return a PDF download, and clean all temporary artifacts. |
| 5 | PDF merge | Ordered multipart PDFs are validated and merged in upload order. At least two files are required. The response is `merged.pdf`. |
| 6 | PDF split | `every_page` and `ranges` modes are implemented with the agreed 1-based inclusive range contract and deterministic PDF/ZIP naming. |
| 7 | Images to PDF | Ordered JPG/JPEG/PNG/WebP uploads are converted into one PDF with EXIF orientation, white transparency flattening, source dimensions, and upload order preserved. |
| 8 | Cleanup service | Immediate or delayed post-response cleanup, active-job protection, startup/periodic orphan sweeping, and cleanup-root allowlisting are implemented. |
| 9 | Validation and error hardening | Streaming and aggregate limits, corrupt/encrypted/empty input handling, archive expansion defenses, active-content checks, consistent errors, and cleanup on every failure path are implemented. |
| 10 | Privacy-safe logging | Logs contain only timestamps, tool names, internal job IDs, and started/success/failure status. User filenames and file contents are not logged. |

## 3. Final API surface

| Method | Endpoint | Input | Successful output |
|---|---|---|---|
| `GET` | `/api/health` | None | `{"status": "ok"}` |
| `POST` | `/api/convert/docx-to-pdf` | Exactly one `.docx` using multipart field `file` | PDF |
| `POST` | `/api/convert/pptx-to-pdf` | Exactly one `.pptx` using multipart field `file` | PDF |
| `POST` | `/api/convert/xlsx-to-pdf` | Exactly one `.xlsx` using multipart field `file` | PDF |
| `POST` | `/api/pdf/merge` | At least two PDFs using ordered multipart field `files` | `merged.pdf` |
| `POST` | `/api/pdf/split` | One PDF using `file`, plus `mode` and optional `ranges` form fields | PDF or ZIP |
| `POST` | `/api/images/to-pdf` | One or more ordered images using multipart field `files` | `images.pdf` |

All controlled API failures use the project contract:

```json
{
  "error": "machine_readable_code",
  "message": "Human-readable explanation."
}
```

The application also normalizes request-validation, unknown-route, unsupported-method, and unexpected server failures into this shape.

## 4. Product decisions finalized during implementation

### 4.1 PDF split contract

`POST /api/pdf/split` supports:

- `mode=every_page`
- `mode=ranges`
- 1-based inclusive ranges such as `1-3,5,8-10`

The range parser rejects:

- malformed tokens
- empty tokens
- duplicate pages
- overlapping ranges
- reversed ranges
- zero or negative pages
- pages beyond the PDF page count
- ranges supplied with `every_page`
- missing ranges when using `ranges`

One valid range returns a PDF. Multiple ranges and `every_page` return a ZIP.

Every-page ZIP entries use:

```text
<sanitized-stem>_page_001.pdf
<sanitized-stem>_page_002.pdf
```

Range ZIP entries use:

```text
<sanitized-stem>_pages_1-3.pdf
<sanitized-stem>_pages_5-5.pdf
```

### 4.2 Images-to-PDF contract

The MVP accepts JPG, JPEG, PNG, and WebP. Validation checks both the filename extension and actual decoded image format.

For each image, PrivCon:

- applies EXIF orientation
- fully decodes the image before conversion
- flattens alpha transparency onto white
- clears image metadata from the prepared PDF page image
- preserves multipart upload order
- sizes the PDF page to the oriented source image
- does not crop or resize the source

### 4.3 Cleanup timing

`CLEANUP_MODE=immediate` remains the default. `delayed` mode is supported with the configured cleanup delay.

Successful response artifacts are not deleted when the response object is created. Cleanup is attached as a post-response background operation so the file remains present for the complete download stream. Failures clean partial uploads and outputs immediately.

## 5. Implementation details by subsystem

### 5.1 FastAPI application and routing

`app/main.py` now:

- creates the FastAPI application with the cleanup lifespan
- registers health, Office conversion, PDF, and image routers
- applies exact-origin CORS configuration
- applies request-size, origin, concurrency, and security-header middleware
- returns consistent validation, HTTP, and unexpected-error responses

Blocking filesystem, pypdf, Pillow, and LibreOffice operations are exposed through synchronous endpoint functions. FastAPI therefore runs them through its worker-thread path instead of blocking the main asynchronous event loop.

### 5.2 Office conversion

Before LibreOffice sees a DOCX, PPTX, or XLSX upload, PrivCon checks:

- expected extension
- valid ZIP container
- required OOXML package members
- correct root elements for required XML parts
- normalized, non-traversing internal paths
- duplicate package names, including case-normalized duplicates
- encrypted members
- symbolic-link entries
- allowed ZIP compression methods
- archive member count
- total expanded archive size
- individual expanded component size
- compression ratio
- CRC/readability of every archive member, including optional media
- malformed XML
- DTD and entity declarations in XML members
- macro-enabled content and VBA project parts
- ActiveX content
- embedded objects
- external resource relationships that could cause non-local resource access

Static external hyperlink relationships remain allowed so ordinary document hyperlinks do not cause a false rejection.

LibreOffice processing includes:

- executable-path resolution from configuration or `PATH`
- unique output directories and user profiles
- a short Windows-safe profile path under the controlled output root
- crash-orphan sweep coverage for profiles
- a hard conversion timeout
- `shell=False`
- removal of interfering `PYTHONHOME` and `PYTHONPATH` variables from the child environment
- PDF signature and output-size verification
- cleanup of the profile on every normal success or failure path

The short profile-path design was verified after a real Windows LibreOffice test exposed a crash caused by deeply nested profile directories.

### 5.3 PDF merge

PDF merge:

- requires at least two files
- validates every extension before processing it
- validates actual PDF structure
- rejects malformed, encrypted, and zero-page PDFs
- preserves upload and page order
- enforces aggregate upload and page-count limits
- rejects active or embedded PDF content
- validates generated output size
- cleans earlier inputs if a later upload or validation fails
- deletes inputs and the output directory only after the download finishes

### 5.4 PDF split

PDF split:

- requires exactly one PDF
- validates mode-dependent fields before saving the upload where possible
- validates the PDF before processing
- enforces page-count and generated-output bounds
- generates ranges in the user's supplied order
- returns a PDF for one range
- returns an ordered ZIP for multiple ranges or every-page mode
- stores ZIP members using sanitized flat names
- deletes intermediate PDFs after the ZIP is created
- cleans the entire job directory on failure or after response streaming

### 5.5 Images to PDF

Image processing:

- restricts Pillow decoders to the supported format allowlist
- rejects renamed/mismatched image data
- turns Pillow decompression-bomb warnings into validation failures
- enforces per-image and combined decoded-pixel limits
- performs a validation decode before conversion
- performs defense-in-depth pixel checks during conversion
- creates independent RGB images
- closes every opened and prepared image
- writes a private PDF output and verifies its PDF signature
- validates generated output size
- cleans all inputs and outputs on every error or completed download

### 5.6 Temporary-file lifecycle

Temporary storage now uses:

- random internal job IDs
- sanitized user-facing filename components
- normalization of both Windows and POSIX path separators
- bounded filename lengths
- exclusive file creation that refuses to overwrite an existing path
- owner-only `0600` file and `0700` directory modes where POSIX permissions apply
- separate upload and output roots
- active-path tracking to prevent sweeping in-flight jobs
- immediate and delayed cleanup modes
- startup and periodic stale-artifact sweeps
- checks that prevent cleanup from deleting a configured root or anything outside the two approved temp roots
- refusal of broad, nested, identical, or symlinked cleanup-root configurations

The tracked repository excludes `.env`, runtime uploads, generated outputs, temp data, and logs.

## 6. Security, safety, and privacy hardening

The final review extended the roadmap's validation step with defense-in-depth controls appropriate for hostile or accidentally extreme local inputs.

### 6.1 Request and resource limits

| Limit | Default |
|---|---:|
| One uploaded file | 50 MB |
| Combined saved uploads per job | 200 MB |
| Whole HTTP request body | 205 MB |
| Generated output | 500 MB |
| Uploaded files per multipart request | 20 |
| Non-file multipart fields | 10 |
| One non-file multipart field | 16 KB |
| Concurrent conversion requests | 2 |
| PDF pages per job | 2,000 |
| Decoded pixels per image | 40,000,000 |
| Combined decoded image pixels | 100,000,000 |
| OOXML ZIP entries | 10,000 |
| OOXML total expanded size | 250 MB |
| OOXML compression ratio | 200:1 |
| LibreOffice conversion timeout | 60 seconds |

These defaults are configurable through the Pydantic settings fields and environment-variable naming convention.

### 6.2 PDF active-content safety

Uploaded PDFs are rejected when they contain detected:

- JavaScript
- launch actions
- remote-document actions
- form import/submit actions
- rich-media execution
- embedded files
- file-attachment annotations
- rich-media, screen, or 3D annotations

This reduces the chance that merge or split results carry an active payload into the user's PDF viewer.

### 6.3 Browser and response safeguards

The API now:

- rejects unsafe-method browser requests from origins other than the configured local frontend origin
- rejects browser requests marked `Sec-Fetch-Site: cross-site`
- still permits local tools such as curl and Postman that do not send a browser `Origin`
- validates that `CORS_ORIGIN` is one exact HTTP(S) origin rather than a wildcard
- limits simultaneous processing requests, including body parsing and response streaming
- sends `Cache-Control: no-store`
- sends `Pragma: no-cache`
- sends `X-Content-Type-Options: nosniff`
- sends `Referrer-Policy: no-referrer`
- sends `X-Frame-Options: DENY`

### 6.4 Privacy guarantees implemented in code

- No third-party conversion, upload, analytics, storage, or AI service is called by the backend.
- User data remains in configured local temporary directories during processing.
- Temporary data is removed after streaming or after the delayed-cleanup window.
- Crash orphans are removed by the periodic sweeper.
- Logs exclude filenames, document text, raw data, and user metadata.
- Error responses do not expose internal exception details or local file paths.
- Image metadata is cleared from the prepared image objects used to generate image PDFs.

## 7. Error behavior

Implemented error codes include:

- `invalid_input`
- `unsupported_file_type`
- `file_type_mismatch`
- `corrupted_file`
- `password_protected`
- `empty_pdf`
- `oversized_file`
- `oversized_request`
- `output_too_large`
- `too_many_pages`
- `unsafe_document_content`
- `invalid_split_mode`
- `invalid_page_ranges`
- `origin_not_allowed`
- `server_busy`
- `backend_unavailable`
- `conversion_timeout`
- `conversion_failed`
- `split_failed`
- `file_processing_failed`
- `not_found`
- `method_not_allowed`
- `internal_error`

Expected user/input errors return readable 4xx responses. A busy converter returns 503, an unavailable LibreOffice engine returns 503, and a timed-out Office conversion returns 504. Unexpected internal failures are converted to a generic response without leaking exception details.

## 8. Test and verification record

The final verification result was:

```text
91 passed in 17.39s
```

Coverage includes:

- health and API error behavior
- valid Office-package endpoint conversion flow
- malformed Office XML rejection before LibreOffice
- real installed LibreOffice DOCX-to-PDF conversion
- PDF merge order and successful download
- fewer than two merge inputs
- non-PDF, corrupt, encrypted, and empty PDFs
- active JavaScript and embedded PDF payload rejection
- aggregate PDF page limits
- every-page, one-range, and multi-range PDF splitting
- all malformed, duplicate, overlapping, reversed, non-positive, and out-of-bounds range cases
- exact split ZIP entry order and filenames
- JPG, JPEG, PNG, and WebP image conversion
- upload-order and source-dimension preservation
- EXIF orientation
- transparency flattening
- corrupt, mismatched, and unsupported images
- per-image and combined pixel limits
- streaming per-file upload limits
- whole-body limits with and without `Content-Length`
- multipart file-count limits before endpoint processing
- bounded concurrent jobs
- cross-site request rejection
- no-store and browser security headers
- filename traversal and length handling
- exclusive no-overwrite file creation
- generated-output size limits
- cleanup refusal outside configured roots
- immediate, delayed, active-job, and orphan cleanup
- ZIP path traversal, duplicate names, CRC damage, compression ratio, excessive entries, DTD/entities, embedded objects, and external resource relationships
- settings validation
- privacy-safe logging

Additional completion gates:

| Gate | Result |
|---|---|
| Ruff lint | Passed |
| Ruff formatting | 31 files formatted; check passed |
| `pip check` | No broken requirements |
| `pip-audit -r requirements.txt` | No known vulnerabilities at audit time |
| `git diff --check` | Passed |
| Tracked secret/temp scan | No tracked `.env`, uploads, outputs, temp files, or logs |
| Runtime temp inspection | Upload and output directories contained no files after tests |
| LibreOffice availability | LibreOffice 26.2.5.2 detected and real conversion passed |

## 9. Important source files

| File | Responsibility |
|---|---|
| `app/main.py` | Application creation, middleware, exception handling, and router registration |
| `app/config.py` | Validated environment-backed configuration and safety limits |
| `app/core/security.py` | Request size, multipart, origin, concurrency, and response-header controls |
| `app/core/validators.py` | Office, PDF, image, archive, and active-content validation |
| `app/core/file_utils.py` | Job IDs, filename sanitization, private file creation, and size checks |
| `app/core/logging_config.py` | Privacy-safe job lifecycle logging |
| `app/routers/convert.py` | DOCX/PPTX/XLSX endpoints |
| `app/routers/pdf.py` | PDF merge and split endpoints |
| `app/routers/images.py` | Images-to-PDF endpoint |
| `app/services/libreoffice_service.py` | Headless Office conversion |
| `app/services/pdf_merge_service.py` | Ordered PDF merge |
| `app/services/pdf_split_service.py` | Page/range output and ZIP creation |
| `app/services/image_service.py` | EXIF-aware image preparation and PDF generation |
| `app/services/cleanup_service.py` | Post-response cleanup and orphan sweeping |
| `tests/test_security.py` | Cross-cutting adversarial security tests |
| `tests/test_libreoffice_integration.py` | Real LibreOffice integration smoke test |

## 10. Scope deliberately not pulled forward

The implementation did not add:

- authentication or accounts
- cloud storage or synchronization
- third-party conversion services
- public SaaS deployment behavior
- persistent file or job history
- OCR or AI processing
- document editing
- payments
- Docker packaging
- frontend UI work

The cleanup service was consolidated in Step 8 as planned. Step 6 and Step 7 used only the local cleanup integration needed by those features before that consolidation.

## 11. Residual risks and Phase 3 boundaries

The backend has strong application-level validation, but it is not an operating-system security sandbox or antivirus/content-disarm engine.

Before exposing PrivCon to the public internet or broadly untrusted users, later hardening should include:

- process and network isolation for LibreOffice and other parsers
- OS/container CPU, memory, process, and disk quotas
- reverse-proxy body and connection limits
- authentication and authorization
- per-user or per-origin rate limiting
- container image and LibreOffice package vulnerability monitoring
- deliberate crash/kill stress testing under Docker

These belong to Phase 3 packaging and hardening. They are not required for the PRD's personal/local trusted-environment MVP.

Office conversion fidelity remains dependent on LibreOffice, installed fonts, source print settings, and the host operating system. Complex Word, PowerPoint, and Excel documents therefore still require representative manual testing.

## 12. Phase 1 acceptance status and next action

### Completed

- All six backend MVP tools are implemented.
- All routers are registered.
- Error responses use the agreed shape.
- Invalid and hostile inputs are handled without leaving temporary files.
- Successful downloads retain their outputs until streaming completes.
- The automated suite and real LibreOffice smoke conversion pass.
- Static, dependency, vulnerability, privacy, and repository hygiene checks pass.

### Owner acceptance still to perform

Use representative real files to manually verify:

1. DOCX, PPTX, and XLSX rendering fidelity, including fonts, tables, images, slide layouts, sheet print areas, and multiple worksheets.
2. Merge ordering with several real PDFs.
3. Every-page and range splitting with a multi-page real PDF.
4. JPG, PNG transparency, WebP, and phone-photo EXIF orientation.
5. Browser download names and error messages.
6. Empty `temp/uploads` and `temp/outputs` directories after each completed or failed workflow.
7. Expected behavior at configured size, page, pixel, output, and concurrency limits.

Once this manual backend acceptance passes, the roadmap should move to **Phase 2 — Frontend MVP**, beginning with the Next.js/Tailwind scaffold and dashboard/tool-grid implementation.

## 13. Suggested commit

Suggested title for the consolidated Phase 1 completion work:

```text
feat: complete and harden Phase 1 conversion backend
```

Suggested body:

```text
- implement all Office, PDF, and image MVP endpoints
- add deterministic split and image conversion behavior
- centralize temp cleanup and orphan sweeping
- harden request, archive, PDF, image, and output validation
- add privacy-safe logging and consistent errors
- add adversarial and real LibreOffice integration coverage
```
