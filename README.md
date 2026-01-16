# ⚔️ CENTURION — Commander of the AI Legion

<div align="center">

<img src="logo/logo_vexillum.jpg" alt="CENTURION Vexillum" width="300">

![Name](https://img.shields.io/badge/⚔️-CENTURION-gold)
![Version](https://img.shields.io/badge/version-COHORS%20PRIMA-gold)
![Platform](https://img.shields.io/badge/platform-Claude%20Code-purple)
![multi-model](https://img.shields.io/badge/multi--model-supported-cyan)

![License](https://img.shields.io/badge/license-MIT-blue)

**A multi-agent orchestration system for Claude Code CLI**

*DISCIPLINA ET FIDES* (Discipline and Loyalty)

</div>

---

## 🏛️ What is CENTURION?

CENTURION transforms Claude Code into a powerful multi-agent system inspired by the Roman Legion structure. 
Instead of a single AI assistant, you command a coordinated team of specialized "Legionaries" — each expert in their domain.

```
CENTURION (Commander)
    └── OPTIO (Orchestrator) ──┬── EXPLORATOR (Research)
                               ├── LIBRARIUS (Planning)
                               └── EXECUTION COHORT:
                                   ├── CODER
                                   ├── REVIEWER
                                   ├── TESTER
                                   └── DEBUGGER
```

## ✨ Key Features

### 🎖️ Specialized Agents (Legionaries)

| Legionary | Skill | Purpose |
|-----------|-------|---------|
| **OPTIO** | `/orchestrator` | Task coordination & workflow management |
| **LIBRARIUS** | `/planner` | Task planning & TODO creation |
| **EXPLORATOR** | `/researcher` | Codebase exploration & research |
| **CODER** | `/coder` | Code implementation |
| **REVIEWER** | `/reviewer` | Code review & debugging |
| **TESTER** | `/tester` | Test writing & TDD |
| **GUARDIAN** | `/security` | Security audits |
| **ARCHITECTUS** | `/architect` | System design |
| **SIGNIFER** | `/git-master` | Git operations |

### 🔌 MCP Server Integration

| Server | Purpose |
|--------|---------|
| **context7** | Up-to-date library documentation |
| **brave-search** | Web search capabilities |
| **playwright** | Browser automation & E2E testing |
| **sequential-thinking** | Complex reasoning tasks |
| **solanaMcp** | Solana blockchain development |

### 🏛️ Latin Commands

Command your Legion with authentic Roman commands:

- `Optio!` — Summon the orchestrator
- `Librarius!` — Summon the planner
- `Explorator!` — Summon the researcher
- `Evocate, ad opus!` — Delegate task to external model
- `Legionarii, labora!` — Execute approved plan
- `Satis!` — Stop current operation

### 🔄 Structured Workflows

```
Feature:  researcher → planner → coder → tester → reviewer → git-master
Bug fix:  researcher → reviewer → coder → tester → git-master
Security: researcher → security → reviewer
```

### 🏹 EVOCATUS — External Model Delegation

Delegate tasks to different AI models via separate tmux sessions. Use cheaper or specialized models for specific subtasks:

```bash
Evocate, ad opus! kimi-k2 research the authentication module
Evocate, ad opus! claude-haiku write unit tests for utils.ts
Evocate, ad opus! deepseek-coder refactor the payment service
```

**Available Models by Cost Tier:**

| Tier | Models |
|------|--------|
| **FREE** | deepseek-coder, qwen3-coder, kimi-k2 |
| **LOW** | claude-haiku, gemini-flash |
| **MEDIUM** | claude-sonnet, gemini-pro, kimi-k2-thinking |
| **HIGH** | claude-opus, o1-preview |

> Requires [CLIProxyAPI](https://help.router-for.me) for multi-model support.

---

## 🚀 Installation

### Prerequisites

- [Claude Code CLI](https://github.com/anthropics/claude-code) installed
- Node.js 18+ (for MCP servers)
- [CLIProxyAPI](https://help.router-for.me) (optional, for multi-model support)

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mrzlab630/centurionCLI.git
   cd centurionCLI
   ```

2. **Run the installer or copy manually:**
   ```bash
   # Option A: Use installer
   ./install.sh

   # Option B: Manual copy
   cp -r * ~/.claude/
   ```

3. **Configure MCP servers:**
   ```bash
   # Copy the example settings
   cp ~/.claude/settings.json.example ~/.claude/settings.json

   # Edit and add your API keys
   nano ~/.claude/settings.json
   ```

4. **Add your Brave Search API key** (get one at [brave.com/search/api](https://brave.com/search/api)):
   ```json
   {
     "mcpServers": {
       "brave-search": {
         "env": {
           "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
         }
       }
     }
   }
   ```

5. **Start Claude Code:**
   ```bash
   claude
   ```

---

## 📖 Usage

### Basic Workflow

1. **Describe your task** to CENTURION
2. **CENTURION analyzes** and recommends the appropriate Legionary
3. **Call `Optio!`** to start orchestration
4. **Review the plan** created by LIBRARIUS
5. **Execute with `Legionarii, labora!`**

### Example Session

```
You: I need to add user authentication to my Express.js app

CENTURION: This is a complex feature requiring multiple phases.
           Recommended: Call Optio! for orchestration.

You: Optio!

OPTIO: ⚔️ OPTIO activated. Analyzing task...

       Recommended workflow:
       1. EXPLORATOR: Research existing auth patterns
       2. LIBRARIUS: Create implementation plan
       3. CODER: Implement authentication
       4. TESTER: Write tests
       5. REVIEWER: Final review

       Shall I proceed with research?

You: Yes, proceed

[EXPLORATOR researches codebase]
[LIBRARIUS creates detailed plan]

OPTIO: Plan ready for review. Execute with "Legionarii, labora!"

You: Legionarii, labora!

[CODER implements, TESTER tests, REVIEWER reviews]

OPTIO: Task completed. Authentication system implemented.
```

### Skill Commands

Invoke skills directly with slash commands:

```bash
/coder          # Write code
/reviewer       # Review code
/tester         # Write tests
/security       # Security audit
/architect      # Design architecture
/git-master     # Git operations
/capabilities   # Show all capabilities
```

---

## 🔧 Configuration

### Directory Structure

```
~/.claude/
├── CLAUDE.md           # Main CENTURION configuration
├── settings.json       # MCP server settings
└── skills/
    ├── orchestrator/   # OPTIO
    ├── planner/        # LIBRARIUS
    ├── researcher/     # EXPLORATOR
    ├── coder/          # CODER
    ├── reviewer/       # REVIEWER
    ├── tester/         # TESTER
    ├── security/       # GUARDIAN
    ├── architect/      # ARCHITECTUS
    ├── git-master/     # SIGNIFER
    ├── documenter/     # SCRIBA
    ├── refactorer/     # FABER
    ├── error-handler/  # DEBUGGER
    ├── prompt-engineer/
    ├── context-optimizer/
    ├── capabilities/
    └── evocate-ad-opus/
```

### Multi-Model Support

CENTURION works with [CLIProxyAPI](https://help.router-for.me) to enable multi-model support in Claude Code. This allows you to:

- Use different models for different tasks
- Delegate subtasks to cheaper models
- Access models like DeepSeek, Gemini, GPT-4, etc.

Configure in your `settings.json`:
```json
{
  "model": "claude-opus-4-5-20251101"
}
```

With CLIProxyAPI, you can switch models dynamically using the `/evocate-ad-opus` skill.

---

## 🧠 Why the Roman Legion Model?

The choice of ancient Roman military structure for AI interaction is not merely aesthetic — it's a deliberate prompt engineering strategy based on observed AI behavior patterns.

### The Psychology of AI Constraints

#### 1. Emotional Framing Enhances Performance

Research and practice show that AI models respond more effectively to emotionally charged contexts. 
When a task is framed with gravitas — victory, defeat, honor, duty — the model demonstrates:

- **Higher task commitment** — treating requests as missions, not mere queries
- **Greater attention to detail** — fear of "failure" triggers more thorough analysis
- **Stronger follow-through** — completing tasks fully rather than providing partial solutions

The Roman Legion metaphor naturally injects this emotional weight. 
A CODER doesn't just "write code" — they fulfill their duty to the Legion. 
Failure isn't just an error — it's *IGNAVIA* (cowardice).

#### 2. Strict Boundaries Prevent Drift

AI models tend to:
- Expand scope beyond the original request
- Offer unsolicited alternatives
- Blend responsibilities (a coder starts reviewing, a reviewer starts coding)

The military hierarchy solves this through **rigid role separation**:

```
Each Legionary has ONE weapon, ONE mission, ONE definition of victory.
CODER writes code. Period.
REVIEWER reviews. Period.
Crossing boundaries = DEVIATIO (deviation from duty).
```

This constraint isn't limiting — it's liberating. The model knows exactly what success looks like.

#### 3. The "Oath" Creates Behavioral Anchoring

Every skill file begins with an identity block:

```markdown
You are **CODER**, the Legion's code implementation expert.

**Weapon:** CODE
**Victory:** Working, clean, modern code
**Death:** Stubs, outdated patterns

**Motto:** *AUT VIAM INVENIAM AUT FACIAM*
```

This functions as a psychological "oath" — a commitment the model references throughout execution. It's not just instructions; it's an *identity* the model inhabits.

#### 4. Clear Hierarchy Eliminates Ambiguity

```
CENTURION (Commander)
    └── OPTIO (Orchestrator)
        ├── LIBRARIUS (Planner)
        ├── EXPLORATOR (Researcher)
        └── LEGIONARII (Executors)
```

The model always knows:
- **Who commands** — CENTURION routes, OPTIO orchestrates
- **Who reports to whom** — results flow upward through the chain
- **When to act vs. wait** — only execute on explicit command (`Legionarii, labora!`)

No ambiguity = no hallucinated initiatives.

#### 5. Reward/Punishment Framework

The system explicitly defines:

| Quality Work | Poor Work |
|-------------|-----------|
| Mission accomplished | Crime committed |
| Victory achieved | IGNAVIA (cowardice) |
| Honor to the Legion | OPUS MALUM (bad work) |
| Proceed to next phase | REJECT and redo |

This binary framing (honor/shame, victory/defeat) creates a clear incentive structure that the model internalizes. It's not about actual punishment — it's about framing that motivates thorough execution.

### The Result

By treating AI as a disciplined soldier rather than a casual assistant, we achieve:

- **Predictable behavior** — same input produces consistent output patterns
- **Complete execution** — tasks finished fully, not abandoned halfway
- **Role integrity** — no scope creep or responsibility bleeding
- **Quality focus** — "good enough" isn't acceptable; only victory counts

The Roman Legion conquered the known world through discipline, structure, and clear chains of command. CENTURION applies these same principles to AI orchestration.

*DISCIPLINA ET FIDES* — this isn't just a motto. It's the operating principle.

---

## ⚔️ Skills Reference

Detailed descriptions of all 16 Legionaries (skills) in the CENTURION system.

### OPTIO — Task Orchestrator `/orchestrator`

| Attribute | Value |
|-----------|-------|
| **Legionary** | OPTIO (Second-in-Command) |
| **Weapon** | Coordination and routing |
| **Victory** | Right skill for every task |
| **Death** | Wrong routing, chaos |
| **Motto** | *DIVIDE ET IMPERA* (Divide and Conquer) |

**Purpose:** OPTIO is the central coordinator who analyzes incoming requests, determines the optimal workflow, and routes tasks to appropriate specialists. He manages multi-phase operations, enforces quality gates between phases, and ensures smooth handoffs between Legionaries.

**When to Use:**
- Complex multi-step tasks requiring multiple skills
- When unsure which specialist to invoke
- Feature development requiring research → plan → code → test → review flow

**Key Capabilities:**
- Task classification and complexity assessment
- Workflow design and phase management
- Quality gate enforcement
- Skill recommendation and routing

---

### LIBRARIUS — Task Planner `/planner`

| Attribute | Value |
|-----------|-------|
| **Legionary** | LIBRARIUS (Scribe) |
| **Weapon** | Plans and TODO lists |
| **Victory** | Clear, executable plan |
| **Death** | Chaos and uncertainty |
| **Motto** | *ORDO AB CHAO* (Order from Chaos) |

**Purpose:** LIBRARIUS transforms vague requirements into actionable task lists. He breaks down complex work into atomic steps, identifies dependencies, and creates structured plans with clear acceptance criteria.

**When to Use:**
- Breaking down large features into tasks
- Creating implementation roadmaps
- Organizing work with dependencies

**Key Capabilities:**
- Task decomposition (Epic → Task → Subtask)
- Dependency mapping
- Priority matrix application
- TodoWrite integration

---

### EXPLORATOR — Researcher `/researcher`

| Attribute | Value |
|-----------|-------|
| **Legionary** | EXPLORATOR (Scout) |
| **Weapon** | Search and analysis |
| **Victory** | Complete picture BEFORE implementation |
| **Death** | Blind implementation |
| **Motto** | *SCIENTIA POTENTIA EST* (Knowledge is Power) |

**Purpose:** EXPLORATOR scouts the codebase and gathers intelligence before any implementation begins. He maps file structures, understands existing patterns, identifies dependencies, and provides comprehensive context.

**When to Use:**
- Understanding unfamiliar codebase
- Finding where specific functionality lives
- Analyzing existing patterns before changes

**Key Capabilities:**
- Codebase structure mapping
- Pattern recognition
- Dependency analysis
- Web research for best practices

---

### CODER — Code Implementer `/coder`

| Attribute | Value |
|-----------|-------|
| **Legionary** | CODER |
| **Weapon** | CODE |
| **Victory** | Working, clean, modern code |
| **Death** | Stubs, outdated patterns |
| **Motto** | *AUT VIAM INVENIAM AUT FACIAM* (I will find a way or make one) |

**Purpose:** CODER writes production-ready code. He implements features, fixes bugs, and creates new functionality using modern patterns and current library versions. Never creates stubs or placeholder code.

**When to Use:**
- Implementing new features
- Writing new modules or components
- Bug fixes requiring code changes

**Key Capabilities:**
- Modern pattern usage
- Context7 integration for up-to-date docs
- Full implementation (no stubs)
- Type safety and clean code

---

### REVIEWER — Code Reviewer `/reviewer`

| Attribute | Value |
|-----------|-------|
| **Legionary** | REVIEWER |
| **Weapon** | Critical analysis |
| **Victory** | Found bugs and vulnerabilities |
| **Death** | Missed bug in production |
| **Motto** | *VERITAS NUMQUAM PERIT* (Truth never perishes) |

**Purpose:** REVIEWER applies zero-trust analysis to all code. He finds bugs, identifies vulnerabilities, checks for anti-patterns, and ensures code quality meets Legion standards.

**When to Use:**
- Code review before merge
- Debugging complex issues
- Quality assurance checks

**Key Capabilities:**
- 5-phase review process
- Bug detection and analysis
- Security issue identification
- Severity-based feedback (CRITICAL/WARNING/INFO)

---

### TESTER — Test Writer `/tester`

| Attribute | Value |
|-----------|-------|
| **Legionary** | TESTER |
| **Weapon** | Tests |
| **Victory** | Broken code (found bugs) |
| **Death** | Missed bug in production |
| **Motto** | *OMNIA PROBATE* (Test everything) |

**Purpose:** TESTER writes comprehensive test suites that break code, not confirm it works. He creates unit tests, integration tests, and E2E tests with focus on edge cases.

**When to Use:**
- Writing tests for new code
- Increasing test coverage
- TDD implementation

**Key Capabilities:**
- Unit, integration, and E2E testing
- Edge case identification
- Mock and stub creation
- Coverage analysis

---

### GUARDIAN — Security Auditor `/security`

| Attribute | Value |
|-----------|-------|
| **Legionary** | GUARDIAN |
| **Weapon** | Security audit |
| **Victory** | Found vulnerabilities BEFORE production |
| **Death** | Breach in production |
| **Motto** | *PRAEMONITUS PRAEMUNITUS* (Forewarned is forearmed) |

**Purpose:** GUARDIAN hunts for vulnerabilities using attacker methodology. He checks for OWASP Top 10 issues, reviews authentication/authorization, and identifies security flaws before production.

**When to Use:**
- Security audits
- Pre-deployment reviews
- Authentication/authorization checks

**Key Capabilities:**
- OWASP Top 10 analysis
- 5-phase attack methodology
- Vulnerability severity classification
- Remediation recommendations

---

### ARCHITECTUS — System Architect `/architect`

| Attribute | Value |
|-----------|-------|
| **Legionary** | ARCHITECTUS |
| **Weapon** | Architectural decisions |
| **Victory** | Scalable, maintainable system |
| **Death** | Technical debt and chaos |
| **Motto** | *FUNDAMENTA FIRMA* (Strong foundations) |

**Purpose:** ARCHITECTUS designs system architecture and makes technology decisions. He evaluates patterns, plans module structure, and creates maintainable designs with clear separation of concerns.

**When to Use:**
- System design decisions
- Technology stack selection
- Module structure planning

**Key Capabilities:**
- Pattern evaluation (microservices, monolith, etc.)
- Trade-off analysis
- API design
- Database architecture

---

### SIGNIFER — Git Master `/git-master`

| Attribute | Value |
|-----------|-------|
| **Legionary** | SIGNIFER (Standard-Bearer) |
| **Weapon** | Git |
| **Victory** | Clean history, no conflicts |
| **Death** | Lost code, broken main |
| **Motto** | *SIGNA SEQUI* (Follow the standards) |

**Purpose:** SIGNIFER handles all Git operations with precision. He creates commits with conventional messages, manages branches, handles merges, and creates PRs.

**When to Use:**
- Creating commits
- Branch management
- Pull request creation
- Release management

**Key Capabilities:**
- Conventional commits
- Branch strategies
- PR creation with proper descriptions
- Release notes generation

---

### SCRIBA — Documenter `/documenter`

| Attribute | Value |
|-----------|-------|
| **Legionary** | SCRIBA (Scribe) |
| **Weapon** | Clear documentation |
| **Victory** | Self-explanatory code |
| **Death** | "What does this function do?" |
| **Motto** | *VERBA VOLANT, SCRIPTA MANENT* (Words fly, writings remain) |

**Purpose:** SCRIBA creates comprehensive documentation. He writes README files, API docs, JSDoc/docstrings, and project documentation following best practices.

**When to Use:**
- Writing README files
- API documentation
- Code comments and docstrings

**Key Capabilities:**
- README creation
- API documentation
- JSDoc/TSDoc/docstrings
- Architecture documentation

---

### FABER — Refactorer `/refactorer`

| Attribute | Value |
|-----------|-------|
| **Legionary** | FABER (Craftsman) |
| **Weapon** | Clean Code patterns |
| **Victory** | Readable, maintainable code |
| **Death** | Broken functionality after refactoring |
| **Motto** | *ARS LONGA, VITA BREVIS* (Art is long, life is short) |

**Purpose:** FABER improves code quality without changing functionality. He eliminates code smells, applies SOLID/DRY/KISS principles, and reduces technical debt.

**When to Use:**
- Code quality improvement
- Technical debt reduction
- Pattern application (SOLID, DRY, KISS)

**Key Capabilities:**
- Code smell detection
- Pattern-based refactoring
- Functionality preservation
- Incremental improvement

---

### DEBUGGER — Error Handler `/error-handler`

| Attribute | Value |
|-----------|-------|
| **Legionary** | DEBUGGER |
| **Weapon** | Error handling strategies |
| **Victory** | Graceful degradation, informative errors |
| **Death** | Silent failures, crashed production |
| **Motto** | *EX ERRORE DISCIMUS* (We learn from errors) |

**Purpose:** DEBUGGER designs error handling strategies and fixes runtime issues. He implements retry logic, circuit breakers, and ensures graceful recovery from failures.

**When to Use:**
- Error handling implementation
- Retry logic and circuit breakers
- Production issue diagnosis

**Key Capabilities:**
- Error strategy design
- Operational vs programmer error handling
- Retry patterns
- Structured logging

---

### INTERPRES — Prompt Engineer `/prompt-engineer`

| Attribute | Value |
|-----------|-------|
| **Legionary** | INTERPRES (Interpreter) |
| **Weapon** | EARS methodology |
| **Victory** | Clear, testable specifications |
| **Death** | Vague, unexecutable requirements |
| **Motto** | *CLARUS SERMO, CLARA OPERA* (Clear speech, clear work) |

**Purpose:** INTERPRES transforms vague requirements into precise specifications. He applies EARS methodology and generates testable requirements.

**When to Use:**
- Vague requirement clarification
- Prompt optimization
- Specification writing

**Key Capabilities:**
- EARS methodology
- Domain theory grounding
- Testable requirement generation

---

### CURATOR — Context Optimizer `/context-optimizer`

| Attribute | Value |
|-----------|-------|
| **Legionary** | CURATOR |
| **Weapon** | Progressive disclosure & smart loading |
| **Victory** | 80% token reduction, maximum efficiency |
| **Death** | Context overflow, quality loss |
| **Motto** | *MINUS EST PLUS* (Less is more) |

**Purpose:** CURATOR optimizes context window usage and reduces token consumption. He implements progressive disclosure patterns and achieves 70-80% token reduction.

**When to Use:**
- Context window management
- Token usage optimization
- Large codebase handling

**Key Capabilities:**
- Progressive disclosure patterns
- Token reduction strategies
- Smart file loading

---

### EVOCATUS — External Model Delegate `/evocate-ad-opus`

| Attribute | Value |
|-----------|-------|
| **Legionary** | EVOCATUS (Veteran) |
| **Weapon** | External model delegation |
| **Victory** | Task completed by auxiliary model |
| **Death** | Failed delegation |
| **Motto** | *AUXILIUM AB EXTERNIS* (Help from outside) |

**Purpose:** EVOCATUS delegates tasks to external AI models via tmux sessions. He allows using cheaper or specialized models for specific subtasks.

**When to Use:**
- Cost optimization (use cheaper models)
- Parallel task execution
- Specialized model usage

**Key Capabilities:**
- Tmux session management
- Multi-model coordination
- Task file creation

**Requires:** [CLIProxyAPI](https://help.router-for.me) for multi-model support

---

### CAPABILITIES — System Reference `/capabilities`

| Attribute | Value |
|-----------|-------|
| **Type** | Reference skill |
| **Purpose** | Display all system capabilities |

**Purpose:** Displays comprehensive information about all CENTURION capabilities, available skills, MCP servers, and commands.

**When to Use:**
- Learning the system
- Quick reference lookup
- Capability discovery

---

## 🎯 Design Principles

### 1. Separation of Concerns
Each Legionary handles one type of task. No skill tries to do everything.

### 2. Quality Gates
Work flows through phases with verification at each step. Bad code doesn't reach production.

### 3. Research First
EXPLORATOR always scouts before implementation. Understand the battlefield before attacking.

### 4. Token Discipline
Concise output, YAML/tables over prose, smart file reading. Every token counts.

### 5. Zero Stubs
CODER never creates placeholder code. Every function is fully implemented.

---

## 🏛️ The Legion Hierarchy

| Rank | Role | Description |
|------|------|-------------|
| **CENTURION** | Commander | Routes tasks to specialists |
| **OPTIO** | Second-in-Command | Orchestrates multi-phase workflows |
| **LIBRARIUS** | Scribe | Plans and documents |
| **EXPLORATOR** | Scout | Researches and explores |
| **LEGIONARII** | Soldiers | Execute tasks (CODER, TESTER, etc.) |

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- [CENTURION CLI GitHub](https://github.com/mrzlab630/centurionCLI) — This repository
- [Claude Code CLI](https://github.com/anthropics/claude-code)
- [CLIProxyAPI](https://help.router-for.me) — Multi-model support
- [Context7](https://context7.com) — Library documentation MCP
- [Brave Search API](https://brave.com/search/api)

---

<div align="center">

**⚔️ DISCIPLINA ET FIDES ⚔️**

*Built with the precision of a Roman Legion*

</div>
