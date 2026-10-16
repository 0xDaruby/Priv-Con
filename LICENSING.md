# PrivCon licensing

Copyright (c) 2026 David.

Effective 2026-10-16, PrivCon's application as a whole is distributed under
the GNU Affero General Public License, version 3 only (`AGPL-3.0-only`).
The complete terms are in [LICENSE](LICENSE). This records the owner's choice
to use the open-source compliance route for the current PDF conversion stack.

PrivCon is free software: you may redistribute it and modify it under those
terms. It is provided WITHOUT ANY WARRANTY, including implied warranties of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE, to the extent permitted
by applicable law. See LICENSE for the full warranty and liability provisions.

## Scope and existing permissions

This notice covers PrivCon-authored application code, supporting build and
installation scripts, and documentation unless a file has its own notice.
Third-party libraries, fonts, runtimes, and independent bundled programs retain
their respective licenses; this notice does not relicense their copyright.
Do not replace upstream copyright notices with PrivCon's notice.

The previous MIT notice is preserved verbatim in
[LICENSES/PrivCon-legacy-MIT.txt](LICENSES/PrivCon-legacy-MIT.txt).
Permissions already granted for previously distributed MIT-covered code remain
available. This release policy does not revoke them. Preserve that notice when
incorporating those portions into the AGPL-covered application. New contributions
must be supplied under terms compatible with this distribution policy; check
ownership and any separately licensed contributions before each release.

The application license does not make users' input documents or ordinary
converted output AGPL software. AGPL section 2 addresses the limited case where
output itself contains a covered work. Licensing compliance never requires
uploading user documents or enabling telemetry.

## PDF conversion decision

- **PyMuPDF 1.26.7:** use its GNU AGPLv3 option, not a commercial-license claim.
  Its installed COPYING file declares AGPL/commercial dual licensing. Preserve
  that file and provide the full AGPL text, corresponding source for PyMuPDF,
  MuPDF, and other covered incorporated components, and necessary build material.
- **pdf2docx 0.5.8:** use GPLv3, as declared by this exact pinned release and its
  included full GPLv3 LICENSE. Do not label this artifact MIT based on upstream's
  later relicense. GPLv3 section 13 and AGPLv3 section 13 permit combining the
  two works: the pdf2docx portion retains GPLv3, and the AGPL portion retains
  AGPLv3. Preserve both licenses and satisfy both sets of obligations.
- No engine replacement or dependency upgrade is required to adopt this route.
  Choosing this route resolves the license-selection ambiguity, not the physical
  assembly and publication of a compliant installer and source distribution.

## Distribution obligations

For every installer and update, provide the exact corresponding source at no
additional charge beside the binary download, with clear directions. Include
required upstream source, patches, build/installation scripts, notices, and
version information. A link to a moving default branch is not enough.

Ship LICENSE, this notice, SOURCE_CODE.md, THIRD_PARTY_NOTICES.md, and the
applicable LICENSES contents. Provide convenient legal notices in the released
interface, including copyright, warranty, redistribution rights, license text,
and source access. If a modified covered version supports remote network
interaction, satisfy the source-offer provisions of AGPL section 13 as well.

Do not impose a proprietary EULA that forbids rights the applicable licenses
grant. Users may modify and redistribute covered software, including commercially;
PrivCon's nonprofit intent does not restrict those rights. Official update
signatures may authenticate official builds; document how users build and run
their own versions without needing PrivCon's production signing keys. Assess
section 6 Installation Information obligations if distributing a covered work
with a User Product in a transaction covered by that section.

## Release procedure and status

[SOURCE_CODE.md](SOURCE_CODE.md) specifies source delivery.
[docs/licensing/RELEASE-CHECKLIST.md](docs/licensing/RELEASE-CHECKLIST.md) lists
the evidence required to clear a release.
[DEPENDENCY_LICENSES.json](DEPENDENCY_LICENSES.json) records the inspected local
dependency versions and notice hashes. It is not an installer bill of materials.

No Windows installer or release source archive has been assembled or published
as part of this licensing change. Public binary release remains gated on the
completed installer/source/notice checks, not on obtaining a paid PDF license.

## Primary references

- [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html), sections 0-6, 10, 13.
- [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html), section 13.
- [pdf2docx 0.5.8 PyPI release metadata](https://pypi.org/pypi/pdf2docx/0.5.8/json).
- [PyMuPDF 1.26.7 COPYING](https://github.com/pymupdf/PyMuPDF/blob/1.26.7/COPYING).
- [LibreOffice licensing](https://www.libreoffice.org/licenses/).
