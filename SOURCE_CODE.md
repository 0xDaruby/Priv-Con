# Obtaining and distributing PrivCon source

PrivCon's application as a whole is distributed under AGPLv3, with individual
third-party components retaining their licenses. See LICENSE, LICENSING.md, and
THIRD_PARTY_NOTICES.md. No document upload is needed to exercise source rights.

## Current development source

The repository's configured upstream is
[0xDaruby/Priv-Con](https://github.com/0xDaruby/Priv-Con).
That is a development-source location, not a claim that a particular installer's
complete corresponding source is already available there.

No Windows installer/source release pair has been published by this licensing
work. Do not present a missing release archive as an available source download.

## Required source delivery for website downloads and updates

PrivCon uses the download-based delivery approach in AGPLv3 section 6(d), rather
than relying on a written source offer. Before enabling any installer or update:

1. Record its version, source commit, target architecture, build environment,
   dependency/artifact versions, upstream source identities, local patches,
   and binary/source archive SHA-256 hashes.
2. Assemble the source preferred for modification, including frontend, backend,
   desktop launcher, updater integration, installer definitions, lockfiles,
   dependency pins, and scripts/instructions to generate, install, run, and
   modify that release. Include non-secret configuration examples.
3. Include corresponding source for covered required dependencies and their
   incorporated libraries, including pdf2docx, PyMuPDF and MuPDF. Audit native
   wheels: a Python wrapper source archive alone may omit embedded native code.
   Include required third-party build instructions and local patches. Retain
   required notices for permissively licensed components too.
4. For independent bundled programs such as LibreOffice, satisfy their own
   source and notice obligations for the exact distribution used. Audit any
   LGPL components, including libvips if sharp is included: retain notices,
   provide required source, and permit replacement/relinking as applicable.
5. Publish the matching source archive(s) with equivalent download access at no
   extra charge. Put clear source directions beside the installer on the website
   and release page, and make them available to update recipients. Hosting on a
   different server is allowed by section 6(d) if the directions and equivalent
   access are maintained. PrivCon remains responsible for source availability.
6. Verify source downloads from a fresh session. Build and run a development
   version using only the published source material and documented prerequisites.
   Do not promise byte-for-byte reproducibility unless separately demonstrated.
7. Preserve each released version's source and clear mapping to its binary.
   Keep source available for as long as required by the applicable licenses;
   do not treat the three-year rule for a different source-offer method as a
   universal limit for website downloads. Keep links working after updates.

The source package must not contain user files, conversion fixtures containing
private information, uploads, outputs, credentials, production signing keys,
private .env files, or machine-specific secrets. Include sufficient instructions
to create local keys and build/run modified versions. Excluding secrets must
not remove source or installation information actually required by the licenses.

## Release layout

Each version's download page must identify:

- The installer, version, supported Windows/CPU target, and checksum.
- A complete corresponding-source download (or clearly listed source archives).
- Build instructions and a release record mapping source to binaries.
- LICENSE, LICENSING.md, THIRD_PARTY_NOTICES.md, and applicable LICENSES material.
- Changes and modification dates for covered upstream code where applicable.

Use actual published addresses in that version's bundled SOURCE_CODE.md and
interface. Do not ship placeholders or a source link that only points to the
latest branch. Add a prominent source-access notice if section 13 applies.

## Consumer documents

Obtaining source is optional. Users can use the packaged conversion tools
offline without downloading source. Source distribution does not grant PrivCon
any rights to users' documents or require sending their documents anywhere.
