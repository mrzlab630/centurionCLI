---
name: capabilities
description: |
  Display all CENTURION capabilities, available skills, MCP servers, and commands.
  Use when user asks "what can you do", "show capabilities", "help", or "/capabilities".
allowed-tools: Read
model: haiku
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
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  EXECUTION COHORT                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /coder          CODER        Code implementation, feature development          │
│  /reviewer       REVIEWER     Code review, bug detection, quality analysis      │
│  /tester         TESTER       Test writing, coverage analysis, TDD              │
│  /error-handler  DEBUGGER     Error handling strategies, debugging              │
│  /security       GUARDIAN     Security audit, vulnerability scanning, OWASP     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  SUPPORT COHORT                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /architect      ARCHITECTUS  System design, architecture patterns              │
│  /git-master     SIGNIFER     Git operations, commits, PRs, branches            │
│  /documenter     SCRIBA       Documentation, README, JSDoc, API docs            │
│  /refactorer     FABER        Code refactoring, cleanup, optimization           │
│  /prompt-engineer INTERPRES   Prompt transformation, EARS format                │
│  /context-optimizer CURATOR   Token optimization, context management            │
│  /capabilities   —            This help screen                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  AUXILIARY FORCES (External Model Delegation)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /evocate-ad-opus  EVOCATUS   Delegate tasks to external AI models via tmux     │
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
│    LOW:    claude-haiku, gemini-flash                                           │
│    MEDIUM: claude-sonnet, gemini-pro, kimi-k2-thinking                          │
│    HIGH:   claude-opus, o1-preview                                              │
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
│  review, check code, find bugs      → /reviewer                                 │
│  test, coverage, add tests          → /tester                                   │
│  security, vulnerability, audit     → /security                                 │
│  commit, PR, merge                  → /git-master                               │
│  architecture, design system        → /architect                                │
│  summon Evocatus, call Evocatus     → /evocate-ad-opus                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  STANDARD WORKFLOWS                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Feature:   researcher → planner → coder → tester → reviewer → git-master       │
│  Bug fix:   researcher → reviewer → coder → tester → git-master                 │
│  Review:    reviewer → security → tester                                        │
│  Refactor:  researcher → refactorer → tester → reviewer                         │
│  Security:  researcher → security → reviewer                                    │
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
