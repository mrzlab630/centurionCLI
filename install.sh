#!/bin/bash

# CENTURION Installation Script
# Version: COHORS PRIMA

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

# Copy scripts if they exist
if [ -d "$SCRIPT_DIR/scripts" ]; then
    echo -e "${YELLOW}→${NC} Installing scripts..."
    mkdir -p "$CLAUDE_DIR/scripts"
    cp -r "$SCRIPT_DIR/scripts/"* "$CLAUDE_DIR/scripts/" 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✓ CENTURION COHORS PRIMA installed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Add your Brave API key to ~/.claude/settings.json"
echo "  2. Run 'claude' to start"
echo ""
echo "⚔️ DISCIPLINA ET FIDES"
