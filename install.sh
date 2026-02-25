#!/bin/bash

# CENTURION Installation Script
# Version: COHORS SECUNDA

set -e

echo "⚔️ CENTURION Installation"
echo "========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CLAUDE_DIR="$HOME/.claude"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude Code CLI not found.${NC}"
    echo "Please install Claude Code first: https://github.com/anthropics/claude-code"
    exit 1
fi

echo -e "${GREEN}✓${NC} Claude Code CLI found"

# Create backup if .claude exists
if [ -d "$CLAUDE_DIR" ]; then
    BACKUP_DIR="${CLAUDE_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}→${NC} Backing up existing configuration to $BACKUP_DIR"
    cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
fi

# Create .claude directory if it doesn't exist
mkdir -p "$CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR/skills"

# Copy CLAUDE.md
echo -e "${YELLOW}→${NC} Installing CLAUDE.md..."
cp "$SCRIPT_DIR/CLAUDE.md" "$CLAUDE_DIR/"

# Copy skills
echo -e "${YELLOW}→${NC} Installing skills..."
cp -r "$SCRIPT_DIR/skills/"* "$CLAUDE_DIR/skills/"

# Handle settings
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    echo -e "${YELLOW}!${NC} settings.json already exists. Skipping to preserve your API keys."
    echo "   Review settings.json.example for new configuration options."
else
    echo -e "${YELLOW}→${NC} Creating settings.json from example..."
    cp "$SCRIPT_DIR/settings.json.example" "$CLAUDE_DIR/settings.json"
    echo -e "${YELLOW}!${NC} Remember to add your API keys to ~/.claude/settings.json"
fi

# Copy libs (Legion Core)
if [ -d "$SCRIPT_DIR/libs" ]; then
    echo -e "${YELLOW}→${NC} Installing Legion Core (libs)..."
    mkdir -p "$CLAUDE_DIR/libs"
    cp -r "$SCRIPT_DIR/libs/"* "$CLAUDE_DIR/libs/" 2>/dev/null || true
fi

# Copy scripts if they exist
if [ -d "$SCRIPT_DIR/scripts" ]; then
    echo -e "${YELLOW}→${NC} Installing scripts..."
    mkdir -p "$CLAUDE_DIR/scripts"
    cp -r "$SCRIPT_DIR/scripts/"* "$CLAUDE_DIR/scripts/" 2>/dev/null || true
    chmod +x "$CLAUDE_DIR/scripts/"*.sh 2>/dev/null || true
fi

# Install Python dependencies
echo -e "${YELLOW}→${NC} Checking Python dependencies..."
if command -v python3 &> /dev/null; then
    PIP_CMD="python3 -m pip"
    if $PIP_CMD --version &> /dev/null; then
        echo "  Installing playwright..."
        $PIP_CMD install --user --break-system-packages playwright 2>/dev/null \
            || $PIP_CMD install --user playwright 2>/dev/null \
            || echo -e "${YELLOW}!${NC} Could not install playwright. Install manually: pip install playwright"
        python3 -m playwright install chromium 2>/dev/null \
            || echo -e "${YELLOW}!${NC} Could not install Chromium. Run: python3 -m playwright install chromium"
    else
        echo -e "${YELLOW}!${NC} pip not found. Install pip first, then run:"
        echo "    pip install playwright && python3 -m playwright install chromium"
    fi
else
    echo -e "${YELLOW}!${NC} Python3 not found. Some skills (velites, sicarius, haruspex) require Python."
fi

# Install Node dependencies for researcher (browse.js)
RESEARCHER_SCRIPTS="$CLAUDE_DIR/skills/researcher/scripts"
if [ -d "$RESEARCHER_SCRIPTS" ] && command -v npm &> /dev/null; then
    echo -e "${YELLOW}→${NC} Installing Node dependencies for researcher..."
    cd "$RESEARCHER_SCRIPTS"
    npm init -y 2>/dev/null
    npm install playwright-core 2>/dev/null \
        || echo -e "${YELLOW}!${NC} Could not install playwright-core. Install manually in $RESEARCHER_SCRIPTS"
    cd - > /dev/null
fi

echo ""
echo -e "${GREEN}✓ CENTURION COHORS SECUNDA installed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Add your API keys to ~/.claude/settings.json"
echo "     - BRAVE_API_KEY (for brave-search MCP)"
echo "     - CONTEXT7_API_KEY (for context7 MCP)"
echo "  2. Set PERPLEXITY_API_KEY in your shell:"
echo "     export PERPLEXITY_API_KEY=\"pplx-...\""
echo "  3. Run 'claude' to start"
echo ""
echo "⚔️ DISCIPLINA ET FIDES"
