# Third-party notices

Inspection date: 2026-10-16. PrivCon incorporates open-source software. Each
component retains its own copyright and license. The full collected notices
are in [LICENSES](LICENSES/README.md); exact paths and SHA-256 hashes are in
[DEPENDENCY_LICENSES.json](DEPENDENCY_LICENSES.json).

**This is a development dependency snapshot, not the final Windows installer
bill of materials or a statement that all binary/source obligations are complete.**

2026-10-28 animation dependency addendum: Motion 14.7.1, framer-motion 14.7.1,
motion-dom 14.7.1 and motion-utils 14.7.0 were added for the theme toggle.
Their installed MIT notices are preserved in `LICENSES/npm/`; exact lockfile
integrities and notice hashes are in
[the addendum](docs/licensing/motion-dependencies-2026-10-28.json).
The existing tslib 2.8.1 notice remains in the original inventory. Reconcile
both inventories against the actual artifact before Windows distribution.

## PDF engines: resolved distribution route

2026-10-29 browser preview addendum: PDF.js (`pdfjs-dist` 6.4.299) provides local
PDF page rendering. Its Apache-2.0 license and embedded CMap, font, ICC and
WASM notices are preserved under `LICENSES/npm/pdfjs-dist/`; these resources
have their own license terms, including the Liberation font GPLv2 exception.
See [the exact dependency/resource addendum](docs/licensing/pdfjs-dependencies-2026-10-29.json).
The npm package also declares optional Node canvas dependencies; they are not
required by the browser renderer. Inspect the actual distributed closure and
resolve the optional native package's missing local notice if it is shipped.
Regenerate local runtime assets with `frontend/scripts/prepare-pdfjs.mjs`;
no CDN assets are used. Existing final source/notice obligations still apply.

- PyMuPDF 1.26.7: select GNU AGPLv3 from its AGPL/commercial licensing options.
  The installed COPYING file is a one-line declaration, so the full AGPL text
  is separately supplied in LICENSE and LICENSES/AGPL-3.0-only.txt.
- pdf2docx 0.5.8: follow its included GPLv3 license and version-specific PyPI
  metadata. Full text is in LICENSES/GPL-3.0.txt and its original package notice.
  A later MIT relicense is not applied to this pinned artifact.
- The compatible combination is documented in LICENSING.md. Required source
  delivery for these engines and incorporated native libraries remains part
  of each actual binary release.

## Pinned backend environment

All 31 requirements pins matched installed versions at inspection. The labels
below are package declarations, not substitutes for their full license texts.

| Package | Version | Declared license |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.14.2 | MIT |
| click | 8.4.2 | BSD-3-Clause |
| colorama | 0.4.6 | License :: OSI Approved :: BSD License |
| fastapi | 0.141.1 | MIT |
| fire | 0.7.1 | Apache-2.0 |
| fonttools | 4.64.0 | MIT |
| h11 | 0.16.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx2 | 2.12.0 | BSD-3-Clause |
| idna | 3.19 | BSD-3-Clause |
| lxml | 6.1.2 | BSD-3-Clause |
| numpy | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| opencv-python-headless | 5.0.0.93 | Apache 2.0 |
| pdf2docx | 0.5.8 | GPL v3 |
| pillow | 12.3.0 | MIT-CMU |
| pydantic | 2.13.4 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pydantic_core | 2.46.4 | MIT |
| pytest | 9.1.1 | MIT |
| pypdf | 6.16.1 | BSD-3-Clause |
| PyMuPDF | 1.26.7 | Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License |
| python-docx | 1.2.0 | MIT |
| python-dotenv | 1.2.3 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| starlette | 1.6.0 | BSD-3-Clause |
| termcolor | 3.3.0 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| uvicorn | 0.52.4 | BSD-3-Clause |

Additional installed environment packages are inventoried separately; their
presence does not mean they should be bundled in the consumer application.

| Additional package | Version |
|---|---|
| boolean.py | 5.0 |
| CacheControl | 0.14.4 |
| certifi | 2026.7.22 |
| charset-normalizer | 3.5.1 |
| coverage | 7.15.4 |
| cyclonedx-python-lib | 11.12.0 |
| defusedxml | 0.7.1 |
| et_xmlfile | 2.0.0 |
| filelock | 3.32.4 |
| httpcore | 1.0.9 |
| httpcore2 | 2.12.0 |
| httptools | 0.8.0 |
| iniconfig | 2.3.0 |
| license-expression | 30.4.4 |
| markdown-it-py | 4.2.0 |
| mdurl | 0.1.2 |
| msgpack | 1.2.1 |
| openpyxl | 3.1.5 |
| packageurl-python | 0.17.6 |
| packaging | 26.3 |
| pip | 26.2.1 |
| pip-api | 0.0.34 |
| pip-requirements-parser | 32.0.1 |
| pip_audit | 2.10.1 |
| platformdirs | 4.11.4 |
| pluggy | 1.6.0 |
| py-serializable | 2.1.0 |
| Pygments | 2.21.0 |
| pyparsing | 3.3.2 |
| pytest-asyncio | 1.4.0 |
| pytest-cov | 7.1.0 |
| python-pptx | 1.0.2 |
| PyYAML | 6.0.3 |
| requests | 2.34.2 |
| rich | 15.0.0 |
| ruff | 0.16.4 |
| sortedcontainers | 2.4.0 |
| tomli | 2.4.1 |
| tomli_w | 1.2.0 |
| truststore | 0.10.4 |
| urllib3 | 2.7.0 |
| watchfiles | 1.2.0 |
| websockets | 17.0.1 |
| xlsxwriter | 3.2.9 |

## Installed frontend production-lock entries

There are 54 non-development lockfile entries; 21 are installed on this Windows
machine. Uninstalled optional platform entries remain recorded in the JSON
inventory and are not claimed as shipped components. Next.js compiled dependency
license files have also been preserved.

| Installed package path | Version | Declared license | Local notice files |
|---|---|---|---|
| @img/colour | 1.1.0 | MIT | 1 |
| @img/sharp-win32-x64 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | 3 |
| @next/env | 16.3.3 | MIT | 0 |
| @next/swc-win32-x64-msvc | 16.3.3 | MIT | 0 |
| @swc/helpers | 0.5.23 | Apache-2.0 | 1 |
| baseline-browser-mapping | 2.11.20 | Apache-2.0 | 1 |
| caniuse-lite | 1.0.30001810 | CC-BY-4.0 | 1 |
| client-only | 0.0.1 | MIT | 0 |
| detect-libc | 2.1.2 | Apache-2.0 | 1 |
| nanoid | 3.3.18 | MIT | 1 |
| next | 16.3.3 | MIT | 131 |
| next/node_modules/postcss | 8.5.23 | MIT | 1 |
| picocolors | 1.1.1 | ISC | 1 |
| react | 19.2.8 | MIT | 1 |
| react-dom | 19.2.8 | MIT | 1 |
| scheduler | 0.27.0 | MIT | 1 |
| sharp | 0.35.4 | Apache-2.0 | 1 |
| sharp/node_modules/semver | 7.8.5 | ISC | 1 |
| source-map-js | 1.2.1 | BSD-3-Clause | 1 |
| styled-jsx | 5.1.6 | MIT | 1 |
| tslib | 2.8.1 | 0BSD | 2 |

### Native libraries and missing notice evidence

- @next/env, @next/swc-win32-x64-msvc, and client-only declare MIT but include
  no local notice file in the inspected packages. Resolve attribution against
  exact upstream source if these are shipped; do not substitute an invented notice.
- sharp Windows x64 includes LGPL libraries such as libvips and other native
  components. Its preserved README licensing table and versions.json identify
  the bundled components. Include their exact license/source material and
  satisfy LGPL replacement/relinking obligations if shipped. The Apache license
  alone does not cover those obligations.
- NumPy, OpenCV, Pillow, lxml, and fonttools may bundle additional code. Their
  available notices have been copied; review final native binaries and source
  rather than relying only on a top-level package license declaration.

## Fonts

frontend/app/fonts/Geist-Variable.woff2 identifies itself as Geist version 1.800,
Copyright 2024 The Geist Project Authors, licensed under SIL OFL 1.1. The full
upstream copyright and license are in LICENSES/Geist-OFL-1.1.txt. Preserve them
when bundling the font. Fonts remain under OFL; they are not relicensed AGPL.

## LibreOffice and runtimes

The notices of the locally installed LibreOffice are preserved as reference
evidence in LICENSES/libreoffice-local-reference, with its build identifier.
They must match the LibreOffice build selected for distribution; local presence
does not establish source-delivery compliance for an installer. LibreOffice
contains components under multiple licenses, so preserve its complete notices.

The inspection interpreter license is recorded in
LICENSES/python-runtime-local-reference. The exact Python interpreter, desktop
runtime, installer/updater, additional fonts, and other components selected for
Windows packaging need matching notices and source treatment.

## Release obligations

Follow [LICENSING.md](LICENSING.md), [SOURCE_CODE.md](SOURCE_CODE.md), and the
[release checklist](docs/licensing/RELEASE-CHECKLIST.md). Include the final notices
in the installed application and source distribution. Repeat the review whenever
a release changes dependencies, packaging, native libraries, fonts, or assets.
