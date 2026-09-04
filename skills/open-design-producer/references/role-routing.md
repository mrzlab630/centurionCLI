# Open Design Role Routing

Open Design is a production tool shared by existing owners. It does not create a
new Legionary or replace the one-owner rule.

| Work | Primary owner | Open Design use |
| --- | --- | --- |
| UX architecture, information hierarchy, flows, design systems, visual acceptance | AEDILIS | Write the design brief, constrain the run, inspect the screenshot, request revisions |
| Landing page, dashboard, prototype, responsive HTML/UI implementation or revision | PICTOR | Execute create/revise requests, inspect HTML and responsive output, fix implementation issues |
| Reference discovery, source verification, license and attribution facts | EXPLORATOR | Search the curated reference adapters, verify source URLs, and hand the selected manifest to AEDILIS/PICTOR |
| Game screens and product loop | LUDIFEX | Supply game rules and screen requirements to AEDILIS/PICTOR |
| Telegram Bot or Mini App constraints | PRAECO | Supply platform limits and interaction constraints |
| Naming, CTA, labels, microcopy | NOMENCLATOR | Supply approved interface copy |
| Localization, RTL, text expansion | GLOSSATOR | Supply locale constraints and review translated fit |
| Positioning and conversion intent | MERCATOR | Supply audience, offer, and funnel constraints |
| Search visibility | INDAGATOR | Supply semantic HTML, metadata, and structured-data constraints |
| Functional and visual proof | TESTER | Verify acceptance criteria, viewports, interactions, and screenshot coverage |
| Regression and completion review | REVIEWER | Challenge acceptance claims and inspect the final artifact |
| External assets, dependencies, permissions, network access | GUARDIAN | Gate supply-chain, secret, capability, and network risks |

For mixed requests, keep one primary owner. A request to "design the UX" starts
with AEDILIS; a request to "create or revise the landing page/dashboard/HTML"
starts with PICTOR. Either owner may invoke `$open-design-producer`.

Hermes, Claude, and Codex are orchestrator clients, not owners. Preserve the one
owner rule in `orchestrator.owner`, and continue the same OD project by passing
the prior result JSON through `project.previousResultPath`.
