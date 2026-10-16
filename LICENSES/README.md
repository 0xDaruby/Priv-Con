# License texts and preserved notices

Collected on 2026-10-16. These are license documents, not executable dependencies.
Upstream text is copied without editing. Preserve it when distributing covered
components. The index is [../DEPENDENCY_LICENSES.json](../DEPENDENCY_LICENSES.json).

| Location | Provenance and scope |
|---|---|
| AGPL-3.0-only.txt | Full AGPLv3 text from the SPDX license-list-data project; also copied to the root LICENSE. |
| PrivCon-legacy-MIT.txt | Exact previous repository LICENSE, retained for previously MIT-covered portions. |
| GPL-3.0.txt | Full GPLv3 text copied from the installed pdf2docx 0.5.8 distribution. |
| Geist-OFL-1.1.txt | Geist upstream OFL/copyright text. Local font name-table inspection confirms Geist version 1.800, the same 2024 copyright, and OFL 1.1. |
| python/ | Notice files copied from the exact installed Python distributions pinned in backend/requirements.txt, including native-package third-party notices. |
| npm/ | Notice files copied from installed non-development frontend lockfile entries, including licenses found inside Next.js's compiled dependencies. |
| libreoffice-local-reference/ | license.txt, NOTICE, and version.ini from the locally installed LibreOffice. Reference evidence only: the eventual Windows package must use notices/source matching its own LibreOffice build. |
| python-runtime-local-reference/ | License of the interpreter used for inspection. Reference evidence only; replace/verify for the interpreter actually bundled. |

The npm inventory also lists optional platform packages that are not installed
on this machine. They have no copied local notices and must not be interpreted
as shipped Windows dependencies. Conversely, a package present in the lockfile
is not proof it survives production bundling.

The inventory records missing local notice files and metadata verbatim instead
of inventing copyright attributions. For final packaging, resolve missing notices
against exact upstream source and add a final artifact bill of materials.
Do not infer that all native licensing is complete because a package has a
top-level LICENSE: embedded components can have additional terms.

An installer must expose applicable notices locally without an internet
connection. This folder is not yet wired into an installer or application menu.

## Downloaded license provenance

- AGPL: https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-only.txt
- Geist: https://raw.githubusercontent.com/vercel/geist-font/main/OFL.txt

The font was inspected without modifying it or installing a dependency. Its
name table identifies the same upstream copyright and license recorded above.
