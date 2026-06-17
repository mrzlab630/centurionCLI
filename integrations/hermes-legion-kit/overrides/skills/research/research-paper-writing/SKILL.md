---
name: research-paper-writing
title: Research Paper Writing Pipeline
description: "Write ML papers for NeurIPS/ICML/ICLR: design->submit."
version: 1.1.1
author: Orchestra Research
license: MIT
dependencies: [semanticscholar, arxiv, habanero, requests, scipy, numpy, matplotlib, SciencePlots]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Research, Paper Writing, Experiments, ML, AI, NeurIPS, ICML, ICLR, ACL, AAAI, COLM, LaTeX, Citations, Statistical Analysis]
    category: research
    related_skills: [arxiv, ml-paper-writing, subagent-driven-development, plan]
    requires_toolsets: [terminal, files]

---

# Research Paper Writing Pipeline

End-to-end coordinator for producing publication-ready ML/AI papers. This compact `SKILL.md` is the always-loaded entrypoint; detailed procedures live in `references/` and templates live in `templates/`.

## When To Use This Skill

Use this skill when:
- starting a research paper from an idea, codebase, experiment log, or draft;
- designing or running experiments to support paper claims;
- writing, revising, or converting paper sections for NeurIPS, ICML, ICLR, ACL, AAAI, COLM, workshops, or arXiv;
- verifying citations, claims, statistics, figures, limitations, reproducibility, or submission readiness;
- responding to reviews, preparing camera-ready assets, posters, talks, blog posts, or code release material.

## Operating Rules

1. Be proactive: draft concrete artifacts, flag uncertainties, and iterate.
2. Never hallucinate citations. Fetch and verify metadata programmatically; mark unresolved entries as `[CITATION NEEDED]`.
3. State the one-sentence contribution before writing the full paper.
4. Map every experiment to a specific claim. Cut experiments that do not support the story.
5. Track project state with `todo`, `memory`, git commits, experiment logs, and explicit decision records.
6. Treat the paper as an iterative loop: results change experiments; reviews change analysis; page limits change framing.
7. Keep the main context lean. Load only the reference needed for the active phase.

## Phase Map

| Phase | Goal | Primary Reference |
| --- | --- | --- |
| 0. Setup | inspect repo, define contribution, create TODOs, estimate compute | `references/checklists.md` |
| 1. Literature | find seed papers, related work, BibTeX, citation proof | `references/citation-workflow.md`, `references/sources.md` |
| 2. Design | map claims to baselines, metrics, seeds, human eval if needed | `references/experiment-patterns.md`, `references/human-evaluation.md` |
| 3. Execution | launch, monitor, recover failed runs, commit completed batches | `references/experiment-patterns.md` |
| 4. Analysis | aggregate metrics, significance, figures, negative/null results | `references/experiment-patterns.md`, `references/autoreason-methodology.md` |
| 5. Drafting | write abstract, intro, methods, results, related work, limitations | `references/writing-guide.md`, `references/checklists.md` |
| 6. Review | simulate reviewers, verify claims, prioritize revisions, rebuttal | `references/reviewer-guidelines.md` |
| 7. Submission | compile, anonymize, venue checklist, arXiv, code packaging | `references/checklists.md`, `templates/README.md` |
| 8. Impact | poster, talk, project page, blog/social summary | `references/writing-guide.md` |
| Variant papers | theory, survey, benchmark, position, short/workshop | `references/paper-types.md` |

## Startup Checklist

Run the smallest relevant subset:

```bash
pwd
ls -la
find . -maxdepth 3 -iname "*.tex" -o -iname "*.bib" -o -iname "README.md"
git status --short
git log --oneline -10
```

Then establish:
- target venue and page limit, or a stated assumption;
- one-sentence contribution;
- evidence already available and evidence still missing;
- active paper path, bibliography path, results path, and figure path;
- TODO list with phases, owners, and proof commands.

Ask the user only when the decision blocks progress: target venue, contradictory contribution framing, hard budget limit, or submission readiness.

## Core Workflows

### Literature And Citations

- Search broadly, then verify exact metadata through arXiv, Semantic Scholar, CrossRef, DOI, or venue pages.
- Never invent authors, titles, years, venues, or BibTeX keys.
- Keep `.bib` entries normalized and cite only papers actually used in the argument.
- Load `references/citation-workflow.md` for API snippets and citation manager patterns.

### Experiments

- Before running: write the claim, baseline, metric, seed count, expected cost, and stopping condition.
- During running: monitor logs, partial outputs, GPU/API cost, failed seeds, and result file integrity.
- After running: aggregate, compute uncertainty/significance when appropriate, commit raw and processed results, then update the paper story.
- Load `references/experiment-patterns.md` for scripts, monitoring, recovery, statistics, and result-log templates.

### Drafting

- Draft in this order when possible: contribution -> Figure 1/story -> abstract -> intro -> method -> experiments -> related work -> limitations -> conclusion.
- Keep the introduction focused: problem, gap, contribution, evidence, impact.
- Every figure/table needs a self-contained caption and a clear claim in the surrounding text.
- Load `references/writing-guide.md` for style, structure, LaTeX patterns, figure/table design, and page-budget advice.

### Review And Revision

- Simulate reviewers with distinct concerns: technical soundness, novelty/significance, clarity/reproducibility, ethics/limitations.
- Convert feedback into prioritized fixes: blockers, high-value improvements, optional polish.
- Verify all claims after revision; do not let copy drift away from results.
- Load `references/reviewer-guidelines.md` for review criteria, scoring, rebuttal patterns, and common rejection causes.

### Submission And Release

- Compile with the venue template from `templates/`; do not copy preambles between venues.
- Check anonymization, page limits, checklists, limitations, broader impact, LLM disclosure, appendix, and supplementary material.
- For accepted work, prepare camera-ready, code release, citation block, poster/talk, arXiv update, and public summary.
- Load `references/checklists.md` and `templates/README.md` for venue-specific requirements.

## Hermes Tool Pattern

Use Hermes tools proportionally:
- `terminal`: git, LaTeX, experiment launches, log checks.
- `execute_code`: citation verification, statistics, aggregation, plotting.
- `read_file` / `write_file` / `patch`: paper, bibliography, scripts, results, docs.
- `web_search` / `web_extract`: literature discovery and source verification.
- `delegate_task`: parallel section drafts or independent citation/claim checks; include all required context because delegates are isolated.
- `todo`: active phase state and next actions.
- `memory`: compact long-lived decisions only; never store secrets.
- `cronjob`: experiment/deadline monitoring; use `[SILENT]` when nothing changed.
- `clarify`: only for blocking decisions.

## Output Standards

For paper plans:
```yaml
paper_plan:
  venue: "assumed or confirmed"
  contribution: "one sentence"
  evidence_ready: []
  evidence_missing: []
  active_phase: "0-8"
  next_steps: []
  proof_commands: []
```

For experiment reports:
```yaml
experiment_report:
  claim: "what this tests"
  status: complete|running|failed|blocked
  metrics: []
  key_finding: "one sentence"
  files: []
  next_step: "write|rerun|analyze|cut"
```

For submission readiness:
```yaml
submission_gate:
  verdict: pass|warn|blocker
  compile: pass|fail|not_run
  citations_verified: true|false
  claims_verified: true|false
  venue_checklist: pass|warn|blocker
  remaining_risks: []
```

## Verification Checklist

- [ ] Contribution stated in one sentence.
- [ ] Every major claim maps to evidence, theorem, benchmark, or argument.
- [ ] Citations are verified; uncertain citations are marked.
- [ ] Baselines, metrics, seeds, and compute budget are documented.
- [ ] Figures/tables are reproducible or their provenance is recorded.
- [ ] Limitations/ethics/broader impact are handled for the target venue.
- [ ] LaTeX compiles and output PDF exists.
- [ ] Page limit and anonymization/camera-ready mode are checked.
- [ ] Code/data release path is documented when relevant.
- [ ] TODO/memory/git state reflect the current phase.

## Reference Documents

| Document | Load When |
| --- | --- |
| `references/writing-guide.md` | drafting, style, page budget, figures, LaTeX patterns |
| `references/citation-workflow.md` | citation discovery, BibTeX, API verification |
| `references/checklists.md` | venue requirements and submission gates |
| `references/reviewer-guidelines.md` | self-review, scoring, rebuttal, revision priorities |
| `references/sources.md` | external source bibliography and official venue/API links |
| `references/experiment-patterns.md` | experiment design, monitoring, statistics, recovery |
| `references/autoreason-methodology.md` | autoreason loops, strategy selection, Borda scoring |
| `references/human-evaluation.md` | annotation design, agreement, crowdsourcing, IRB |
| `references/paper-types.md` | theory, survey, benchmark, position, workshop, short papers |
| `templates/README.md` | venue templates and compilation instructions |

## Common Pitfalls

- Generic abstract or intro that could fit any ML paper.
- Related work as a list instead of a taxonomy or argument.
- Experiments without explicit claims or fair baselines.
- Statistical claims without uncertainty, seeds, or significance notes.
- Citation drift after revisions.
- Venue conversion by copying incompatible LaTeX preambles.
- Overloading the active context with every reference instead of loading the phase-specific file.
