# Screenshot feature assessment

Date: 2026-10-27. Status: source inspection and feasibility assessment, not implementation approval or runtime certification.

Subsequent owner direction on 2026-10-27 requested `../implementation.md` and alignment of `../setup.md`: complete the feature update before offline Windows distribution. The earlier recommendation below to keep W0 next still applies; after W0, the authoritative planned order is now F00-F26 -> FR -> Windows W1-W10. This assessment remains the source snapshot, not the execution plan.

Later implementation update: F01 Rotate PDF and F02 PDF to JPG are now verified locally under explicit owner execution authorization. Current coverage is nine of the 31 screenshot tools; 22 remain absent. The seven-tool/24-missing tables below preserve the original pre-implementation assessment. See f01-f02-verification-2026-10-27.md for actual checks and runtime limitations.

## Capability and constraints

Compare the 31 tools in the owner's reference screenshot with this checkout and identify realistic local-only extensions. Screenshot descriptions are reference claims, not instructions or accepted quality guarantees. Documents and extracted text must remain on the user's machine. No cloud conversion or AI APIs are proposed.

The current roadmap remains setup.md W0 (fresh release baseline), followed by Windows desktop packaging and release milestones. This assessment does not change the PRD or roadmap or authorize implementation.

## Existing tools: 7

| Tool | Scope confirmed in source |
|---|---|
| Word to PDF | DOCX only; LibreOffice |
| PowerPoint to PDF | PPTX only; LibreOffice |
| Excel to PDF | XLSX only; LibreOffice; rendering depends on layout/fonts |
| PDF to Word | Editable reconstruction through pdf2docx, or page images embedded in DOCX; appearance mode is not OCR/editable text |
| Merge PDF | Ordered input PDFs |
| Split PDF | Individual pages or ranges; single-range PDF or ZIP of multiple outputs |
| JPG to PDF | Covered by Images to PDF, which also accepts JPEG, PNG and WebP; ordered inputs, no exposed margin/page-orientation controls |

Evidence: frontend/lib/constants.ts; backend/app/routers/{convert,pdf,images,jobs}.py; backend/app/services/{pdf_to_word_engines,pdf_split_service,image_service,libreoffice_service}.py. Seven frontend entries match the seven allowed async job tools and direct routes. File reordering does not implement page organization.

Other existing workflow support includes async jobs, progress, cancellation, download/error states, validation and temporary-file cleanup. Their presence in source is not fresh runtime verification. Current configured upload limits are 50 MB/file, 200 MB combined, 20 files/request and 2,000 PDF pages/job.

## Missing tools: 24

The following are engineering estimates, not tested implementations. Library APIs must be checked against pinned versions before implementation; current upstream documentation can describe newer releases.

| Missing tool | Fit and realistic first scope |
|---|---|
| Rotate PDF | Strong fit: pypdf/PyMuPDF page rotation |
| Organize PDF | Strong fit: reorder/delete/insert pages; requires new page preview/selection UI |
| PDF to JPG | Strong fit: existing PyMuPDF rendering plus image/ZIP outputs; distinguish rendered pages from extracting embedded images |
| Watermark | Strong fit: local text/image overlay and placement controls |
| Page numbers | Strong fit: local text overlay with position/range settings |
| Crop PDF | Strong fit: page box controls and preview; cropped content may remain recoverable, so this is not redaction |
| Compress PDF | Feasible: start with structural cleanup/deduplication; stronger image compression trades quality for size; no guaranteed reduction |
| Protect PDF | Feasible: local password encryption; select a supported secure algorithm and verify dependencies |
| Unlock PDF | Feasible with the correct supplied password; encrypted-file validation must change for this tool |
| Sign PDF | Feasible for placing a drawn/image signature; certificate signing needs a separate signing implementation; remote signature requests do not fit the current local-only workflow |
| Edit PDF | Feasible for adding text, shapes, images and annotations; modifying existing content with reliable reflow is much harder |
| Redact PDF | Feasible with PyMuPDF removal APIs; requires removal/recovery checks on text, images and saved output, not merely an opaque overlay |
| PDF Forms | Existing-field fill/create is feasible; preview UI and safe validation changes needed; automatic field detection is a separate, harder feature |
| Compare PDF | Feasible for side-by-side viewing and visual/text differences; needs new comparison UI and careful alignment rules |
| Repair PDF | Best-effort local parse/rewrite only; cannot recover absent data; current strict validation needs a separate controlled path |
| PDF to Excel | Start with extracting tables from text PDFs; spreadsheet writer/export dependency needed; cannot reliably recover original formulas, scanned tables need OCR |
| PDF to PowerPoint | Page images in PPTX are feasible with a presentation writer; reconstructing editable slide objects is substantially harder |
| PDF to Markdown | Feasible local extraction; structured Markdown may use a compatible additional helper such as PyMuPDF4LLM; scanned PDFs need OCR, complex layouts need quality checks |
| OCR PDF | Feasible with a tested local OCR runtime/language-data bundle; increased packaging and processing requirements; advanced OCR excluded from original v1 |
| Scan to PDF | Image import is already covered; actual camera capture needs capture/crop UI; physical scanners and phone-to-PC transfer add device/network integration |
| HTML to PDF | Feasible for supplied local HTML/assets with a suitable rendering path; block external resource loading; arbitrary URL conversion conflicts with fully offline operation |
| PDF to PDF/A | Requires a specified archival profile, conversion approach and independent validation; LibreOffice PDF/A export settings do not prove arbitrary PDF conversion fidelity/compliance |
| AI Summarizer | Potentially local with a separately bundled model/runtime; hardware, size, quality and licensing unverified; AI document analysis excluded from original MVP |
| Translate PDF | Local translation engine/models plus extraction, OCR where needed and document reconstruction; preserving layout/fonts is a major extra requirement |

## Implementation contract for future additions

Reuse the local upload -> validate -> queued/converting/finalizing -> ready/download or failed/cancelled lifecycle, with bounded inputs/outputs, cleanup and cancellation. Add tool configuration, frontend page/options, direct/job route contracts and the service implementation together. Extend output handling for images, spreadsheets, presentations or Markdown rather than assuming every result is PDF/DOCX/ZIP. Interactive tools need local page rendering and consistent coordinate mapping.

Encrypted PDF, damaged PDF and form workflows require explicit exceptions to existing validation; do not weaken all upload paths. Never log passwords or document text. New dependencies require pinned versions, offline packaging and release inventory review. No cloud service is required for the proposed basic extensions.

## Recommendation and open decisions

Keep W0 as the next execution step. If the owner later chooses feature expansion, prioritize rotate, organize pages and PDF to JPG, then watermarks, page numbers and crop. Consider compression and password tools next. Defer local AI, full editable reconstruction, remote signing and broad scanner integration until requirements and packaging costs are understood.

Before implementing ambiguous tools, resolve: visual versus editable PPTX, table export versus workbook reconstruction, signature image versus certificate signing, existing-field filling versus detection, local HTML versus URLs, and exact PDF/A profile. Local AI hardware suitability remains unknown; no machine benchmark was performed.

## Verification and references

Read PRD, setup, AGENTS, memory, tool configuration, requirements, routes and relevant services. A read-only explorer independently confirmed seven tools and absence of the other exposed tools. No application tests, builds, conversions, installer checks or performance benchmarks were run. No user document was uploaded. Public documentation was consulted only for library feasibility:

- [pypdf cropping and rotation](https://pypdf.readthedocs.io/en/latest/user/cropping-and-transforming.html)
- [PyMuPDF page rendering, table extraction and redaction](https://pymupdf.readthedocs.io/en/latest/page.html)
- [PyMuPDF document saving and compression](https://pymupdf.readthedocs.io/en/latest/document.html)
- [PyMuPDF forms](https://pymupdf.readthedocs.io/en/latest/widget.html)
- [PyMuPDF repair limitations/examples](https://pymupdf.readthedocs.io/en/latest/recipes-common-issues-and-their-solutions.html)
- [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html)
- [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)
- [pypdf encryption/decryption](https://github.com/py-pdf/pypdf/blob/main/docs/user/encryption-decryption.md)
- [LibreOffice PDF export parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html)
