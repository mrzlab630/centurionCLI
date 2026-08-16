---
name: feature-architecture
description: ECC-adapted feature planning skill that explores existing code before designing implementation blueprints.
---

# Feature Architecture

Use this skill for non-trivial features, cross-module changes, new admin surfaces, API contracts, database-backed content, and game/session flow work.

## Process

1. Explore first: read local docs, current git state, package scripts, and the modules that already own similar behavior.
2. Trace the existing data flow before proposing a new one.
3. Identify the smallest architecture that fits current patterns.
4. Produce a blueprint with exact files to create/modify, interfaces, data flow, validation commands, and risk gates.
5. Implement in dependency order: types/schemas, core logic, integration, UI, tests, docs.

## Design Rules

- Prefer existing local abstractions over new framework-level abstractions.
- Do not add speculative layers for future scope unless the repo already requires them.
- Keep public API contracts explicit and machine-checkable.
- Choose the model tier deliberately: Flash for small mechanical changes, Gemini Pro for ambiguous architecture, Opus for adversarial review/security/WAR ROOM.
