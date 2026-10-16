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

License selection was resolved on 2026-10-16 through the open-source route:

1. Use PyMuPDF 1.26.7 under its AGPLv3 option. Its installed COPYING declaration
   is preserved, and the full AGPLv3 text is supplied at the repository root.
2. Use the pinned `pdf2docx` 0.5.8 artifact under GPLv3. Both its installed full
   LICENSE and version-specific PyPI metadata say GPLv3. The later upstream MIT
   relicense is not applied to this artifact. No runtime dependency was changed.
3. PrivCon's application as a whole follows the AGPLv3 distribution policy in
   [LICENSING.md](../LICENSING.md). GPLv3/AGPLv3 section 13 permits this
   combination while the pdf2docx portion retains GPLv3.

Public binary distribution still requires assembling and publishing matching
corresponding source, including the engines' incorporated native dependencies,
and shipping applicable notices. Follow [SOURCE_CODE.md](../SOURCE_CODE.md) and
the [release checklist](../docs/licensing/RELEASE-CHECKLIST.md). The local notice
snapshot is not proof that an unbuilt installer satisfies these obligations.

Do not remove this artifact/source gate merely because automated tests pass.
Licensing compliance does not require sending user files to a third party;
conversion remains on the local machine.

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
