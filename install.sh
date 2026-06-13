#!/bin/bash

# CENTURION Installation Script
# Version: COHORS SECUNDA (v2.1)
# Installs: 37 Legionaries + MEMORIA MCP + 7 MCP Servers + Pipeline Templates

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
AGENTS_DIR="${AGENTS_HOME:-$HOME/.agents}"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMORIA_DIR="$CLAUDE_DIR/mcp-servers/memoria"
SKILLS_DIR="$AGENTS_DIR/skills"

echo ""
echo -e "${BOLD}⚔️  CENTURION — COHORS SECUNDA${NC}"
echo -e "${CYAN}   37 Legionaries | canonical ~/.agents/skills | 7 MCP Servers | MEMORIA v1.2.0${NC}"
echo "=================================================="
echo ""

# ─── PHASE 1: Prerequisites ───

echo -e "${BOLD}[1/7] Checking prerequisites...${NC}"

# Check Claude Code CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}  ✗ Claude Code CLI not found${NC}"
    echo "    Install: https://github.com/anthropics/claude-code"
    exit 1
fi
echo -e "${GREEN}  ✓${NC} Claude Code CLI"

# Check Node.js >= 20
if ! command -v node &> /dev/null; then
    echo -e "${RED}  ✗ Node.js not found${NC}"
    exit 1
fi
NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VER" -lt 20 ]; then
    echo -e "${RED}  ✗ Node.js >= 20 required (found v$NODE_VER)${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓${NC} Node.js v$(node -v | sed 's/v//')"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}  ✗ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓${NC} npm v$(npm -v)"

# Check Python3 (optional, for Ferrata)
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}  ✓${NC} Python3 $(python3 --version 2>&1 | sed 's/Python //')"
else
    echo -e "${YELLOW}  ! Python3 not found (optional, needed for Cohors Ferrata scripts)${NC}"
fi

echo ""

# ─── PHASE 2: Backup ───

echo -e "${BOLD}[2/7] Backup...${NC}"

if [ -d "$CLAUDE_DIR" ]; then
    BACKUP_DIR="${CLAUDE_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}  → Backing up $CLAUDE_DIR → $BACKUP_DIR${NC}"
    cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
    echo -e "${GREEN}  ✓${NC} Backup created"
else
    echo -e "${CYAN}  - No existing config found, fresh install${NC}"
fi

echo ""

# ─── PHASE 3: Core Config ───

echo -e "${BOLD}[3/7] Installing core configuration...${NC}"

mkdir -p "$CLAUDE_DIR"
mkdir -p "$SKILLS_DIR"
mkdir -p "$CLAUDE_DIR/scripts"
mkdir -p "$CLAUDE_DIR/pipeline"

# CLAUDE.md — global instructions
cp "$SCRIPT_DIR/CLAUDE.md" "$CLAUDE_DIR/"
echo -e "${GREEN}  ✓${NC} CLAUDE.md (global instructions)"

# FERRATA.md, PROBATIO.md — doctrine docs
[ -f "$SCRIPT_DIR/FERRATA.md" ] && cp "$SCRIPT_DIR/FERRATA.md" "$CLAUDE_DIR/"
[ -f "$SCRIPT_DIR/PROBATIO.md" ] && cp "$SCRIPT_DIR/PROBATIO.md" "$CLAUDE_DIR/"
echo -e "${GREEN}  ✓${NC} Doctrine files (FERRATA.md, PROBATIO.md)"

# Settings
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    echo -e "${YELLOW}  ! settings.json exists, skipping (review settings.json.example for updates)${NC}"
else
    cp "$SCRIPT_DIR/settings.json.example" "$CLAUDE_DIR/settings.json"
    echo -e "${GREEN}  ✓${NC} settings.json created from template"
fi

# Pipeline templates (Agmen protocol)
cp "$SCRIPT_DIR/pipeline/"* "$CLAUDE_DIR/pipeline/" 2>/dev/null || true
echo -e "${GREEN}  ✓${NC} Pipeline templates (Agmen protocol)"

# Scripts
if [ -d "$SCRIPT_DIR/scripts" ]; then
    cp -r "$SCRIPT_DIR/scripts/"* "$CLAUDE_DIR/scripts/" 2>/dev/null || true
    echo -e "${GREEN}  ✓${NC} Utility scripts"
fi

# Libs
if [ -d "$SCRIPT_DIR/libs" ]; then
    mkdir -p "$CLAUDE_DIR/libs"
    cp -r "$SCRIPT_DIR/libs/"* "$CLAUDE_DIR/libs/" 2>/dev/null || true
    echo -e "${GREEN}  ✓${NC} Shared libraries (legion_core.py)"
fi

echo ""

# ─── PHASE 4: Skills (37 Legionaries) ───

echo -e "${BOLD}[4/7] Deploying 37 Legionaries to canonical skill root...${NC}"

SKILL_COUNT=0
for skill_dir in "$SCRIPT_DIR/skills/"*/; do
    skill_name=$(basename "$skill_dir")
    # Copy everything except memory/ directories (project-specific)
    mkdir -p "$SKILLS_DIR/$skill_name"

    # Copy SKILL.md
    [ -f "$skill_dir/SKILL.md" ] && cp "$skill_dir/SKILL.md" "$SKILLS_DIR/$skill_name/"
    [ -f "$skill_dir/REFERENCE.md" ] && cp "$skill_dir/REFERENCE.md" "$SKILLS_DIR/$skill_name/"
    [ -f "$skill_dir/package.json" ] && cp "$skill_dir/package.json" "$SKILLS_DIR/$skill_name/"
    [ -f "$skill_dir/package-lock.json" ] && cp "$skill_dir/package-lock.json" "$SKILLS_DIR/$skill_name/"

    # Copy references/ (institutional knowledge)
    if [ -d "$skill_dir/references" ]; then
        rm -rf "$SKILLS_DIR/$skill_name/references"
        cp -r "$skill_dir/references" "$SKILLS_DIR/$skill_name/"
    fi

    # Copy agents/ (UI metadata)
    if [ -d "$skill_dir/agents" ]; then
        rm -rf "$SKILLS_DIR/$skill_name/agents"
        cp -r "$skill_dir/agents" "$SKILLS_DIR/$skill_name/"
    fi

    # Copy scripts/ (tools)
    if [ -d "$skill_dir/scripts" ]; then
        rm -rf "$SKILLS_DIR/$skill_name/scripts"
        cp -r "$skill_dir/scripts" "$SKILLS_DIR/$skill_name/"
    fi

    # Copy knowledge/ (e.g. augur)
    if [ -d "$skill_dir/knowledge" ]; then
        rm -rf "$SKILLS_DIR/$skill_name/knowledge"
        cp -r "$skill_dir/knowledge" "$SKILLS_DIR/$skill_name/"
    fi

    SKILL_COUNT=$((SKILL_COUNT + 1))
done

echo -e "${GREEN}  ✓${NC} $SKILL_COUNT legionaries deployed"
echo -e "${CYAN}    Core 8:    OPTIO CODER DEBUGGER EXPLORATOR PONTIFEX TESTER GUARDIAN LIBRARIUS${NC}"
echo -e "${CYAN}    Command:   CAPABILITIES SKILL-QUARTERMASTER PRAEMONITOR${NC}"
echo -e "${CYAN}    Build 6:   ARTIFEX ARCHITECT DOCUMENTER PICTOR PRAECO REFACTORER${NC}"
echo -e "${CYAN}    Product 4: LUDIFEX AEDILIS NOMENCLATOR GLOSSATOR${NC}"
echo -e "${CYAN}    Quality 2: CENSOR REVIEWER${NC}"
echo -e "${CYAN}    Intel 3:   AUGUR QUAESTOR TABULARIUS${NC}"
echo -e "${CYAN}    Growth 4:  MERCATOR ORATOR INDAGATOR ALEATOR${NC}"
echo -e "${CYAN}    Ops 2:     EVOCATUS SIGNIFER${NC}"
echo -e "${CYAN}    Ferrata 3: VELITES HARUSPEX SICARIUS${NC}"
echo -e "${CYAN}    Prompt 1:  INTERPRES${NC}"

if [ -d "$CODEX_DIR/skills" ]; then
    echo -e "${CYAN}    Codex system skills remain in: $CODEX_DIR/skills/.system${NC}"
    echo -e "${CYAN}    Legion duplicates are not installed into $CODEX_DIR/skills${NC}"
fi

echo ""

# ─── PHASE 5: MEMORIA MCP Server ───

echo -e "${BOLD}[5/7] Building MEMORIA MCP Server v1.2.0...${NC}"

if [ -d "$SCRIPT_DIR/mcp-servers/memoria" ]; then
    mkdir -p "$MEMORIA_DIR"

    # Copy source
    cp "$SCRIPT_DIR/mcp-servers/memoria/package.json" "$MEMORIA_DIR/"
    cp "$SCRIPT_DIR/mcp-servers/memoria/tsconfig.json" "$MEMORIA_DIR/"
    cp -r "$SCRIPT_DIR/mcp-servers/memoria/src" "$MEMORIA_DIR/"

    # Create data directory
    mkdir -p "$MEMORIA_DIR/data"

    # Install dependencies
    echo -e "${YELLOW}  → npm install (this may take a minute)...${NC}"
    cd "$MEMORIA_DIR"
    npm install --silent 2>/dev/null
    echo -e "${GREEN}  ✓${NC} Dependencies installed"

    # Build
    echo -e "${YELLOW}  → Building TypeScript...${NC}"
    npm run build --silent 2>/dev/null
    echo -e "${GREEN}  ✓${NC} MEMORIA built successfully"

    cd "$SCRIPT_DIR"
else
    echo -e "${YELLOW}  ! mcp-servers/memoria not found, skipping${NC}"
fi

echo ""

# ─── PHASE 6: MCP Server Registration ───

echo -e "${BOLD}[6/8] Registering MCP servers...${NC}"

# MEMORIA (local)
if [ -f "$MEMORIA_DIR/dist/index.js" ]; then
    claude mcp add -s user memoria -- node "$MEMORIA_DIR/dist/index.js" 2>/dev/null && \
        echo -e "${GREEN}  ✓${NC} memoria (local, semantic memory)" || \
        echo -e "${YELLOW}  ! memoria already registered or error${NC}"
fi

# Context7 (cloud, no keys needed)
claude mcp add -s user context7 -- npx -y @upstash/context7-mcp 2>/dev/null && \
    echo -e "${GREEN}  ✓${NC} context7 (documentation retrieval)" || \
    echo -e "${YELLOW}  ! context7 already registered or error${NC}"

# Playwright (local, no keys needed)
claude mcp add -s user playwright -- npx -y @playwright/mcp 2>/dev/null && \
    echo -e "${GREEN}  ✓${NC} playwright (browser automation)" || \
    echo -e "${YELLOW}  ! playwright already registered or error${NC}"

# Sequential Thinking (local, no keys needed)
claude mcp add -s user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking 2>/dev/null && \
    echo -e "${GREEN}  ✓${NC} sequential-thinking (chain of thought)" || \
    echo -e "${YELLOW}  ! sequential-thinking already registered or error${NC}"

# Solana MCP (remote, no keys needed)
claude mcp add -s user solanaMcp -- npx mcp-remote https://mcp.solana.com/mcp 2>/dev/null && \
    echo -e "${GREEN}  ✓${NC} solanaMcp (Solana SDK)" || \
    echo -e "${YELLOW}  ! solanaMcp already registered or error${NC}"

# Brave Search (needs API key)
if [ -n "$BRAVE_API_KEY" ]; then
    claude mcp add -s user -e BRAVE_API_KEY="$BRAVE_API_KEY" brave-search -- npx -y @brave/brave-search-mcp-server 2>/dev/null && \
        echo -e "${GREEN}  ✓${NC} brave-search (web search)" || \
        echo -e "${YELLOW}  ! brave-search already registered or error${NC}"
else
    echo -e "${YELLOW}  ! brave-search skipped (set BRAVE_API_KEY in env first)${NC}"
fi

# GitHub MCP (needs PAT + binary)
if [ -n "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    # Try to find github-mcp-server binary
    GH_MCP_BIN=$(which github-mcp-server 2>/dev/null || echo "$HOME/.local/bin/github-mcp-server")
    if [ -x "$GH_MCP_BIN" ]; then
        claude mcp add -s user \
            -e GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
            -e GITHUB_TOOLSETS="repos,issues,pull_requests,actions,users" \
            github -- "$GH_MCP_BIN" stdio 2>/dev/null && \
            echo -e "${GREEN}  ✓${NC} github (GitHub integration)" || \
            echo -e "${YELLOW}  ! github already registered or error${NC}"
    else
        echo -e "${YELLOW}  ! github skipped (github-mcp-server binary not found)${NC}"
        echo -e "${YELLOW}    Install: https://github.com/github/github-mcp-server${NC}"
    fi
else
    echo -e "${YELLOW}  ! github skipped (set GITHUB_PERSONAL_ACCESS_TOKEN in env first)${NC}"
fi

echo ""

# ─── PHASE 7: Claude Code Plugin Integration ───

echo -e "${BOLD}[7/8] Installing Claude Legion plugin...${NC}"

CLAUDE_LEGION_KIT="$SCRIPT_DIR/integrations/claude-legion-kit"
if [ -f "$CLAUDE_LEGION_KIT/installer/install.mjs" ]; then
    node "$CLAUDE_LEGION_KIT/installer/install.mjs" --claude-home "$CLAUDE_DIR" >/dev/null && \
        echo -e "${GREEN}  ✓${NC} Claude Legion plugin installed and canonical skills synced" || \
        echo -e "${YELLOW}  ! Claude Legion plugin install failed; inspect $CLAUDE_LEGION_KIT${NC}"
else
    echo -e "${YELLOW}  ! Claude Legion kit not found, skipping${NC}"
fi

echo ""

# ─── PHASE 8: Verification ───

echo -e "${BOLD}[8/8] Verification...${NC}"

# Count installed skills
INSTALLED=$(ls -d "$SKILLS_DIR/"*/ 2>/dev/null | wc -l)
echo -e "${GREEN}  ✓${NC} Skills installed: $INSTALLED"

if [ -f "$SKILLS_DIR/tester/scripts/legion-skill-eval.mjs" ]; then
    CENTURION_SKILLS_ROOT="$SKILLS_DIR" node "$SKILLS_DIR/tester/scripts/legion-skill-eval.mjs" >/dev/null && \
        echo -e "${GREEN}  ✓${NC} Legion skill eval: pass" || \
        echo -e "${YELLOW}  ! Legion skill eval failed; inspect $SKILLS_DIR/tester/scripts/legion-skill-eval.mjs${NC}"
fi

# Check MEMORIA build
if [ -f "$MEMORIA_DIR/dist/index.js" ]; then
    echo -e "${GREEN}  ✓${NC} MEMORIA: built and ready"
else
    echo -e "${RED}  ✗${NC} MEMORIA: build failed"
fi

# Check CLAUDE.md
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
    echo -e "${GREEN}  ✓${NC} CLAUDE.md: installed"
fi

# Check pipeline
if [ -f "$CLAUDE_DIR/pipeline/TEMPLATE-handoff.md" ]; then
    echo -e "${GREEN}  ✓${NC} Pipeline templates: installed"
fi

if [ -f "$CLAUDE_DIR/skills/centurion-legion/.claude-plugin/plugin.json" ]; then
    claude plugin validate "$CLAUDE_DIR/skills/centurion-legion" --strict >/dev/null && \
        echo -e "${GREEN}  ✓${NC} Claude Legion plugin: valid" || \
        echo -e "${YELLOW}  ! Claude Legion plugin validation failed${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}${BOLD}⚔️  CENTURION COHORS SECUNDA — DEPLOYED${NC}"
echo "=================================================="
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Set API keys in your shell profile (~/.bashrc):"
echo "     - BRAVE_API_KEY (for web search)"
echo "     - GITHUB_PERSONAL_ACCESS_TOKEN (for GitHub MCP)"
echo "     - PERPLEXITY_API_KEY (for deep search)"
echo "  2. Re-run this script after setting keys to register"
echo "     brave-search and github MCP servers"
echo "  3. Start Claude Code: claude"
echo "  4. MEMORIA will auto-index memory files on first run"
echo "  5. Legion skills are canonical in: $SKILLS_DIR"
echo ""
echo -e "  See ${CYAN}.env.example${NC} for all required environment variables"
echo ""
echo -e "${BOLD}⚔️  DISCIPLINA ET FIDES${NC}"
