# PICTOR — Project Conventions

> Project-specific frontend patterns. Updated as the codebase evolves.

## Current Projects

### Snorter Telegram Bot (telegram/base/)
- **Framework**: grammY (NOT React — this is a Telegram bot, consult PRAECO)
- **Mini App**: Not yet implemented (future: React + Tailwind via PICTOR)

### Address Info (src/commands/addressInfo/)
- **Output**: Telegram HTML messages (NOT web components)
- **Formatting**: `formatTreeBlock()` pattern — consult PRAECO/our-patterns.md

## General Rules
- Check existing stack in `package.json` before suggesting a framework
- Follow project's existing patterns (naming, folder structure, imports)
- If project uses Tailwind — use Tailwind. If CSS Modules — use CSS Modules.
- Never introduce a new framework without OPTIO approval
