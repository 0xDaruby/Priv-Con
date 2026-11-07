# PrivCon toolbox arrangement and design council

Date: 2026-10-28. User request: assess how the current design scales to all planned tools, investigate iLovePDF's arrangement, and redesign the arrangement where needed. Application implementation is limited to navigation/layout; missing tools remain planned.

## Findings and decision

The flat full-height sidebar is an MVP arrangement. Source currently exposes nine tools and gives substantial width to navigation plus a large header/progress band. The live narrow in-app browser showed a horizontally scrolling tool strip, vertical page scrolling and limited space around the uploader. The current page reported backend Not running during inspection; this is a runtime status, not proof that tools are absent.

At31 destinations, the problem is not only finding tools: future page organization, crop, annotation, forms and comparison need document space. Replacing the flat sidebar with another permanent grouped sidebar would improve classification but leave the width problem. A grouped searchable catalog followed by focused tool workspaces addresses both. Existing routes already support the multi-page structure; no routing-framework/backend rewrite or UI dependency is required.

## Council positions before synthesis

- **Architect (parent):** catalog discovery and focused workspaces, with a compact switcher. Reasons: fixed navigation takes space, future canvas tools need room, existing routes can be reused. Main risk: loss of quick switching and draft context.
- **Skeptic (fresh subagent):** remove oversized chrome, but avoid a full navigation platform. A catalog and compact switcher suffice; search can wait until demonstrated need. Strongest dissent: nine tools alone do not justify elaborate search/mega-menu infrastructure.
- **Pragmatist (fresh subagent):** one registry, categorized catalog, simple All tools disclosure; preserve existing conversion hooks/routes. Biggest practical gain comes from removing permanent sidebar/progress overhead.
- **Critic (fresh subagent):** agree on separation, but guard file/job loss, ambiguous categories, zoom/keyboard behavior and offline resource failures. A polished catalog does not establish engine readiness or document privacy.

**Synthesis:** use lightweight local filtering now as preparation for the confirmed broader toolbox, without a command palette, mega-menu library or persistence. The Skeptic's challenge removes unnecessary infrastructure; search is a native field over a small local registry, not a new service. Use one canonical destination per tool, search synonyms for overlapping tasks, and show only working implementations. Future destination visibility must not imply that every engine is available: keep runtime failures truthful.

## Reference and evidence boundary

The [iLovePDF homepage](https://www.ilovepdf.com/) was read on 2026-10-28. It exposes category filters and grouped navigation, with separate tool destinations. This supports catalog-plus-tool-pages as a familiar discovery pattern; it does not prove superior usability for PrivCon, permit copying assets, or justify cloud uploads/accounts/upsells. Its feature claims are not PrivCon requirements or quality guarantees.

Mobbin UI Decisions informed the distinctions: destination tiles are links; category filters are buttons with pressed state; catalog search filters a collection rather than choosing a form value; tool switching is navigation; page editing uses a contextual action toolbar; measured conversion progress remains separate from workflow stages. The selected skill is a local synthesis, not an official Mobbin design certification. ECC Council and Frontend Design Direction supplied disagreement and visual constraints. No external design service receives project documents; Google Stitch remains excluded by the project design contract.

## Full toolbox mapping

This table is a future information architecture, not an implementation checklist or live availability claim. Multiple numbered implementation steps can be modes of the same destination (image/certificate signatures; image-slide/editable PowerPoint).

| Group | Destinations when implemented |
|---|---|
| Convert to PDF | Word, PowerPoint, Excel, Images, local HTML, Camera scan |
| Convert from PDF | Word, PowerPoint, Excel, JPG, PDF/A, Markdown |
| Organize pages | Merge, Split, Rotate, Organize, Crop |
| Edit & annotate | Edit/add content, Watermark, Page numbers, Forms |
| Optimize & OCR | Compress, Repair, OCR |
| Protect & sign | Protect, Unlock, Sign, Redact |
| Read & review | Compare, Summarize, Translate |

Current nine implementations occupy only the first three groups: four to-PDF, two from-PDF and three organize tools. Empty categories and unavailable future tools do not become live navigation. Certificate signing and editable presentation modes belong inside their existing destinations when implemented, avoiding duplicate catalog entries.

## Component and interaction contracts

- Catalog at `/`: local search by title, description, accepted format and task synonyms. Category choice narrows results immediately without uploading data. Empty/clear and result-count feedback are explicit. No artificial pagination for31 destinations; a searchable grouped grid is small enough to scan, while filters reduce clutter. Search/category UI state stays local and does not store files or document history.
- Tool workspace: existing route, current title, compact All tools disclosure and small stage indicator. Escape closes the disclosure and returns focus; outside click/Tab-away dismisses it. Navigation links retain browser/new-tab behavior. No desktop-menu arrow-key model is implied.
- Selected-input navigation: keep-working versus explicit discard. While a job is running, finish or use the existing Cancel control before switching tools; the navigation dialog offers return-to-work rather than promising atomic stop-and-leave across upload/job-creation races. No confirmation for an empty workspace. This guards app links and native unload; SPA browser Back/Forward is not intercepted and remains a limitation. No speculative cross-tool file reuse or workflow chains.
- Catalog and tool page are separate page types. Upload/configuration/results remain stages of one tool route, not additional browser pages that break the existing lifecycle.
- Windows later uses the same local pages. No remote fonts, analytics, model downloads, cloud catalogs, account screens or new OS integration. Installed update controls remain a separate later roadmap surface.

## Visual direction

Private desktop utility: existing monochrome identity, strong typography, quieter chrome and a broad continuous work surface. Reuse official logo, Geist font and tokens. Flat outlined destination grids aid scanning without decorative elevation. Make the current task and one primary action clear. Use normal responsive sizing instead of shrinking the entire body to80%.

Catalog desktop: compact header, title/privacy, search, wrapping categories, three-column sections. Medium: two-column grid. Narrow/zoomed: one column with stacked controls. Workspace: header/current-tool/switcher plus full-width uploader/configuration; later document tools may add their own thumbnail/option panels inside the task area. Do not duplicate the global navigation as an editor toolbar.

## Implementation and verification record

Implemented locally:

- Shared discovery registry in `frontend/lib/tool-catalog.ts`, searchable/filterable `ToolCatalog`, new catalog page and scoped styles. Current nine destinations appear once; empty future categories remain absent. Desktop filter buttons become a native labeled select on narrow screens. Clearing search/filters returns focus to search.
- Compact `AppHeader`/`ToolSwitcher`, separate catalog/workspace `AppShell` variants, focused full-width canvas and reduced stage indicator. Removed hardcoded body80% scaling. Existing upload/options/result/error components, APIs and conversion hooks are preserved.
- `WorkspaceNavigationGuard` and a tested navigation-policy helper protect same-tab app-link navigation with selected inputs. A running conversion must finish or be cancelled using its existing control before switching. Native unload warning applies while work is at risk. This does not intercept SPA browser Back/Forward; automatic file transfer and cross-tool draft persistence were not added.
- The approved arrangement addendum was written to `frontend/docs/design.md` before source implementation. It supersedes historical fixed-sidebar geometry/category prohibitions, without changing the original PRD or numbered feature order.

Actual verification on 2026-10-28:

| Check | Result |
|---|---|
| Frontend behavior tests | 17 passed: existing9 helper tests plus5 catalog and3 navigation-policy tests |
| Catalog growth | 31 injected test destinations grouped without drops/duplicates; this is registry capacity, not usability or working conversions for31 tools |
| Helper coverage | Catalog helper100% line/branch/function coverage in its focused test run; not whole-UI coverage |
| Lint / types | ESLint passed; canonical TypeScript passed; final production build also passed TypeScript |
| Production build | Unchanged Next/Turbopack passed with bundled Node24.22.1;12 static pages including all9 existing tool routes |
| Independent review | Fresh council voices before implementation; catalog worker; React, TypeScript and code/security-focused review. Clear-control focus restoration fixed and re-reviewed; running-job navigation policy narrowed to avoid an unsupported atomic-stop promise |
| Real browser | Local production frontend and existing FastAPI through in-app browser; no external conversion service; synthetic PDF only |
| Discovery | Searchalias join -> Merge; clear restores9 and search focus; no-match/clear recovery; category from-PDF returns2; ordinary switcher links, Escape close and summary focus return |
| Draft safety | Switching after choosing page2 opens native dialog; Keep working preserves page2 and restores focus; Escape preserves input; explicit leave reaches catalog |
| Existing tool journeys | Single-page JPG conversion/download and selected-page PDF rotation/download succeeded in the rearranged workspaces |
| Reflow | Desktop default viewport;768x600 two-column catalog;375x812 one-column catalog/native category selector;375x700 focused workspace. No horizontal overflow observed; body zoom is1. This is not an actual browser200% zoom or screen-reader certification |
| Browser diagnostics | No browser error entries returned in the checked preview tab. No full native-network capture was performed |

Preview screenshots: ignored local artifacts under `temp/ui-arrangement-20261028/` (`catalog-desktop.jpg`, `catalog-mobile.jpg`, `workspace-desktop.jpg`). Runtime checks used disposable synthetic data; a JPG and PDF download were created by the browser. No project document was sent to iLovePDF or a design service.

No backend implementation/dependency change, commit, push, deployment or Windows installer work occurred in this arrangement task. Earlier F01/F02 changes remain preserved. The earlier live DOCX timeout finding is not resolved by this UI work and was not retested. All31 future destinations still need their own feature implementation and installed Windows acceptance. Actual browser zoom, screen-reader/device testing and broader document workflows remain future verification gaps.
