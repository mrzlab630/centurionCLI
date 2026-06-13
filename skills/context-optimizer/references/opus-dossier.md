# Opus 4.8 Dossier Mode

Use this reference when a task is large enough to tempt loading many files into Claude Opus 4.8.

## Rule

Large context is a reserve, not a default. Build a dossier first; load raw files only when the owner needs exact text.

## Dossier Shape

```yaml
opus_dossier:
  objective: "single sentence"
  owner: "one Legionary slug"
  constraints:
    - "allowed paths"
    - "non-goals"
    - "forbidden patterns"
  evidence:
    - path: "file:line"
      why_needed: "short reason"
  changed_files: []
  proof_commands: []
  handoffs:
    - owner: "adjacent Legionary"
      trigger: "when to call"
  risks:
    - "known uncertainty"
```

## Loading Policy

- Start with paths, symbols, and summaries.
- Add exact file excerpts only when implementation or review depends on wording.
- Prefer references under `skills/*/references/` over pasting long guidance into prompts.
- At phase boundaries, compress to objective, changed files, proof, failures, and next owner.
