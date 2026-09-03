# PDF-to-Word engine

PrivCon's PDF-to-Word feature is local-only and is isolated behind the
`PdfToWordEngine` protocol in `app/services/pdf_to_word_engines.py`. API routes
and job management do not depend directly on a particular conversion library.

## Modes

- `editable` (default) uses `pdf2docx` to reconstruct text, fonts, colors,
  images, vector shapes, tables, columns, links, and positioning where the PDF
  contains enough layout information. Individual page errors are fatal; PrivCon
  never falls back to a plain-text document or returns a knowingly partial file.
- `preserve_appearance` renders every PDF page locally with PyMuPDF and places
  that page image into a size-matched Word page. It prioritizes visual fidelity;
  the page content is not directly editable and OCR is not performed.

Both modes retain the shared upload limits, PDF structure and active-content
checks, controlled temporary directories, output-size enforcement, cancellation,
and automatic cleanup.

## Distribution release gate

Development evaluation is approved, but public distribution is blocked until
the dependency licensing is reviewed and recorded:

1. PyMuPDF 1.26.7 is dual licensed under AGPL-3.0 or an Artifex commercial
   license.
2. The installed `pdf2docx` 0.5.8 wheel reports GPLv3 metadata, while the
   upstream repository announced a later MIT relicense. The exact distributable
   source and license text must be reconciled before release.
3. PrivCon must either comply with all applicable open-source obligations or use
   appropriate commercial licensing. This is a release decision, not a runtime
   network dependency; conversion remains on the local machine.

Do not remove this gate merely because automated tests pass.

## Fidelity verification

Before changing or replacing the engine, test both output modes against:

- the real two-page PrivCon CV fixture used during development;
- tables, raster images, vector shapes, and multiple columns;
- external and email hyperlinks;
- mixed fonts, font weights, colors, and page sizes;
- scanned/image-only PDFs and malformed or unsafe PDFs.

Render every generated DOCX back to pages with LibreOffice and compare every
page visually. A valid ZIP package or successful `.docx` creation alone is not
proof of conversion fidelity.
