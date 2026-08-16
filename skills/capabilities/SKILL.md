---
name: capabilities
description: Capability reference. Use when the user asks what CENTURION can do, available skills, commands, MCP servers, help, or /capabilities.
allowed-tools: Read
---

# CAPABILITIES — Full System Reference

## Activation Protocol

On activation, output the following capabilities reference:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CENTURION COHORS PRIMA — FULL CAPABILITIES                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────┐
│  COMMAND COHORT                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /orchestrator   OPTIO        Task coordination, workflow management            │
│  /planner        LIBRARIUS    Task planning, TODO creation, decomposition       │
│  /researcher     EXPLORATOR   Codebase exploration, documentation research      │
│  /praemonitor    PRAEMONITOR  Premortem, failure forecast, risky assumptions    │
│  /skill-quartermaster ARMARIUS External skill discovery, vetting, install       │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  BUILD & OPERATIONS COHORT                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /coder          CODER        Production code implementation and focused fixes  │
│  /error-handler  DEBUGGER     Error handling strategies, debugging              │
│  /tester         TESTER       Test writing, coverage analysis, TDD              │
│  /reviewer       REVIEWER     Code review, bug detection, quality analysis      │
│  /security       GUARDIAN     Security audit, vulnerability scanning, OWASP     │
│  /pontifex       PONTIFEX    Docker, CI/CD, PostgreSQL, service health          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  PRODUCT & UX COHORT                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /ludifex       LUDIFEX     Telegram Mini App game product architecture         │
│  /aedilis       AEDILIS     UI/UX architecture, component systems, review        │
│  /nomenclator   NOMENCLATOR Product language, UX-writing, naming, microcopy     │
│  /glossator     GLOSSATOR   Interface localization, i18n, glossary, locale QA   │
│  /praeco        PRAECO      Telegram Bot/Mini App platform constraints          │
│  /aleator       ALEATOR     Ethical game mechanics, rewards, retention          │
│  /mercator      MERCATOR    Growth, positioning, funnels, campaigns             │
│  /pictor        PICTOR      Frontend UI implementation                          │
│  /orator        ORATOR      Social posts, platform-native content, community    │
│  /indagator     INDAGATOR   SEO, search visibility, organic ranking             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ARCHITECTURE & CRAFT COHORT                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /architect      ARCHITECTUS  System design, architecture patterns              │
│  /git-master     SIGNIFER     Git operations, commits, PRs, branches            │
│  /documenter     SCRIBA       Documentation, README, JSDoc, API docs            │
│  /refactorer     FABER        Behavior-preserving refactoring and cleanup       │
│  /prompt-engineer INTERPRES   Prompt transformation, EARS format                │
│  /context-optimizer CURATOR   Token optimization, context management            │
│  /artifex        ARTIFEX     Create, validate, package AgentSkills              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  SECURITY & INTELLIGENCE COHORT                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /censor        CENSOR      Adversarial verification and plan critique          │
│  /velites       VELITES     Active reconnaissance and attack surface mapping    │
│  /haruspex      HARUSPEX    Static analysis and vulnerability candidates        │
│  /sicarius      SICARIUS    Exploit verification via browser automation         │
│  /augur         AUGUR       Phantom1225 pool intelligence and ScamNet data      │
│  /quaestor      QUAESTOR    Crypto/on-chain intelligence and risk review        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  UTILITY COHORT                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /evocate-ad-opus  EVOCATUS   Delegate tasks to external AI models via tmux     │
│  /tabularius    TABULARIUS  Reports, charts, HTML formatting, publishing        │
│  /capabilities  —           This help screen                                    │
│  $open-design-producer      Verified HTML and screenshot production             │
│                                                                                 │
│  Usage: Evocate, ad opus! <model> for task(s) <numbers>                         │
│                                                                                 │
│  Examples:                                                                      │
│    Evocate, ad opus! kimi-k2 for task 2                                         │
│    Evocate, ad opus! deepseek-coder for tasks 1, 3, 5                           │
│    Evocate, ad opus! gemini-pro for task 6                                      │
│                                                                                 │
│  Available Models (by cost tier):                                               │
│    FREE:   deepseek-coder, qwen3-coder, kimi-k2                                 │
│    LOW:    Codex-haiku, gemini-flash                                           │
│    MEDIUM: Codex-sonnet, gemini-pro, kimi-k2-thinking                          │
│    HIGH:   Codex-opus, o1-preview                                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  MCP SERVERS                                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  context7           Library documentation (npm, pip, etc.)                      │
│  brave-search       Web search via Brave API                                    │
│  playwright         Browser automation, E2E testing, screenshots                │
│  sequential-thinking Complex reasoning, multi-step problem solving              │
│  solanaMcp          Solana blockchain development                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  LATIN COMMANDS                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Optio!              Summon orchestrator (= /orchestrator)                      │
│  Librarius!          Summon planner (= /planner)                                │
│  Explorator!         Summon researcher (= /researcher)                          │
│  Evocate, ad opus!   Delegate to external model (= /evocate-ad-opus)            │
│  Legionarii, labora! Start execution pipeline                                   │
│  Satis!              Stop/pause current operation                               │
│  Status!             Show current workflow status                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  KEYWORD TRIGGERS (auto-invoke skills)                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  plan, break down, decompose        → /planner                                  │
│  explore, find where, investigate   → /researcher                               │
│  implement, write code, create      → /coder                                    │
│  refactor, cleanup, tech debt       → /refactorer                               │
│  docs, README, JSDoc, API docs      → /documenter                               │
│  review, check code, find bugs      → /reviewer                                 │
│  test, coverage, add tests          → /tester                                   │
│  security, vulnerability, audit     → /security                                 │
│  commit, PR, merge                  → /git-master                               │
│  architecture, design system        → /architect                                │
│  Telegram Mini App game flow        → /ludifex                                  │
│  UI/UX, interface, components       → /aedilis                                  │
│  create/revise landing/dashboard UI → /pictor + $open-design-producer           │
│  UX-writing, naming, CTA, microcopy → /nomenclator                              │
│  i18n, localization, translation    → /glossator                                │
│  Telegram API, bot, Mini App SDK    → /praeco                                   │
│  rewards, retention, gamification   → /aleator                                  │
│  growth, funnel, positioning        → /mercator                                 │
│  premortem, предразбор провала      → /praemonitor                              │
│  find/install external skill        → /skill-quartermaster                      │
│  summon Evocatus, call Evocatus     → /evocate-ad-opus                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  STANDARD WORKFLOWS                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Feature:   skill-quartermaster → researcher → planner → coder → tester → review│
│  Premortem: skill-quartermaster → praemonitor → planner → coder → tester        │
│  Bug fix:   skill-quartermaster → researcher → reviewer → coder → tester        │
│  Review:    reviewer → security → tester                                        │
│  Refactor:  researcher → refactorer → tester → reviewer                         │
│  Security:  researcher → security → reviewer                                    │
│  Design:    aedilis → pictor + open-design-producer → tester → reviewer         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  THINKING TRIGGERS                                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  "think hard"           Activate extended thinking for architecture             │
│  "ultrathink"           Maximum reasoning for complex algorithms                │
│  "think step by step"   Structured multi-step analysis                          │
│  "analyze thoroughly"   Deep investigation mode                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                              DISCIPLINA ET FIDES
```

## Output Notes

- Always output the full capabilities table
- Do not summarize or abbreviate
- Keep the box-drawing characters intact for visual structure
