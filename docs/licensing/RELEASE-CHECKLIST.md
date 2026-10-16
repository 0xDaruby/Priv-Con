# Windows release licensing checklist

Reviewed: 2026-10-16. Applies to initial installers and every subsequent update.
Completed documentation is not a certification of an unbuilt installer.

## Decisions completed in the repository

- [x] Select the open-source AGPLv3 route for PrivCon's combined application.
- [x] Include full AGPLv3 terms and preserve the previous MIT notice.
- [x] Resolve pdf2docx 0.5.8 as GPLv3 using its actual installed license and
  version-specific PyPI metadata; do not rely on the later MIT relicense.
- [x] Record PyMuPDF 1.26.7's AGPL/commercial declaration and select AGPLv3.
- [x] Preserve installed backend and production frontend dependency notices,
  including available native and vendored notices, with file hashes.
- [x] Inspect the local Geist font's copyright/license metadata and include OFL.
- [x] Define source delivery, modification notices, recipients' rights, and
  update-release obligations in LICENSING.md and SOURCE_CODE.md.

## Required when building the first Windows installer

- [ ] Create the actual Windows artifact bill of materials: package names,
  versions, original artifact hashes, source identities, licenses, patches,
  embedded native components, runtimes, installer tools, fonts, and assets.
- [ ] Reconcile the artifact against DEPENDENCY_LICENSES.json. Include the full
  production closure and embedded compiled libraries; exclude irrelevant
  platform/build-only packages from claims about the installed product.
- [ ] Resolve missing local notice texts for @next/env 16.3.3,
  @next/swc-win32-x64-msvc 16.3.3, and client-only 0.0.1 against exact source,
  if those components are distributed. Metadata currently declares MIT; this
  does not replace required copyright notices or embedded-library checks.
- [ ] If distributing sharp's Windows native package, include its README
  licensing table, exact bundled-library versions, required full texts and
  source, and LGPL replacement/relinking compliance. The lockfile declares
  Apache-2.0 AND LGPL-3.0-or-later; a top-level Apache license alone is insufficient.
- [ ] Include source/build material for PyMuPDF and its incorporated MuPDF and
  dependencies, and the GPLv3 pdf2docx source matching the distributed artifact.
  Archive originals and any patches. Confirm correspondence, not just version labels.
- [ ] Select and record the bundled LibreOffice build and fonts. Include its
  exact notices/source and satisfy its component licenses. The local reference
  files are not automatically the final distribution's notices.
- [ ] Include the correct Python and desktop runtime notices. Reinspect any
  new Electron/Tauri/updater/packager dependencies when chosen.
- [ ] Confirm provenance and rights for brand images, custom icons, and all
  other assets; do not infer permission from their presence in the repository.
- [ ] Ship the applicable full license texts, copyright notices, source
  directions, and no-warranty information in a locally accessible form.
- [ ] Add a convenient Legal / Open-source licenses / Source entry to the
  released interface. Include copyright, rights, warranty, and license access.
  Satisfy section 13's source offer if remote interaction applies.
- [ ] Verify installer terms do not prohibit licensed modification,
  redistribution, or permitted reverse engineering/relinking.
- [ ] Document how to build/run a modified version using local keys; keep
  official signing keys private. Assess section 6 Installation Information
  obligations for any covered User Product distribution.
- [ ] Publish and verify the complete matching source beside the installer,
  including dependency source and build/installation material as required.
- [ ] Inspect source archives for secrets/private documents. Verify archive
  contents and checksums and build/run from the published source instructions.
- [ ] Record version, commit, installer/source hashes, publication addresses,
  component evidence, and review date. Only then mark this release cleared.

## Repeat for each update

- [ ] Recheck new/changed dependencies, fonts, assets, and modifications.
- [ ] Update notices and the final artifact inventory before signing.
- [ ] Publish source for that update with the same availability and clear
  directions required for the original installer; verify access for recipients.
- [ ] Preserve prior release source/binary mappings and working source links.
- [ ] Ensure application and website statements match the release's actual
  licenses and behavior. Updates do not waive source obligations.

## Ready-to-use legal notice for the released interface

> PrivCon - Copyright (c) 2026 David. PrivCon is free software distributed under
> the GNU Affero General Public License, version 3. You may modify and
> redistribute it under that license. It comes WITHOUT ANY WARRANTY to the
> extent permitted by applicable law. Third-party components retain their own
> licenses. View License, Third-party notices, and Source code for this version.

Wire the named actions to actual bundled text and matching release source.
This paragraph supplements the full licenses; it does not replace them.

## Release decision

The license-selection issue is resolved through compliance with AGPLv3/GPLv3.
The installer/source distribution gate remains open until the applicable
artifact checks above have evidence. Neither passing conversion tests nor
writing these documents clears an unassembled public binary release.
