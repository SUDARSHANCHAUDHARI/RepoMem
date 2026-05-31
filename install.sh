#!/usr/bin/env bash
# RepoMem install script
# Usage: bash install.sh
set -e

REPOMEM_DIR="${REPOMEM_DIR:-$HOME/.repomem}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "  RepoMem — Persistent memory for AI coding agents"
echo "  =================================================="
echo ""

# ── Check Python ───────────────────────────────────────────────────────────────
echo "Checking Python..."

# Find Python 3.11+ — prefer explicit versioned binaries over system python3
PYTHON3=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON3="$candidate"
            PY_VERSION="$ver"
            break
        fi
    fi
done

if [ -z "$PYTHON3" ]; then
    echo -e "${RED}❌ Python 3.11+ required but not found (tried python3.13/3.12/3.11/python3)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ Python $PY_VERSION ($PYTHON3)${NC}"

# ── Create directories ─────────────────────────────────────────────────────────
echo "Creating directories..."
mkdir -p "$REPOMEM_DIR/lib" "$REPOMEM_DIR/logs" "$REPOMEM_DIR/sync" "$REPOMEM_DIR/exports"
echo -e "  ${GREEN}✅ $REPOMEM_DIR${NC}"

# ── Install Python package ─────────────────────────────────────────────────────
echo "Installing RepoMem Python package..."
cp -r "$SCRIPT_DIR/repomem" "$REPOMEM_DIR/lib/"
cp -r "$SCRIPT_DIR/server" "$REPOMEM_DIR/lib/"
echo -e "  ${GREEN}✅ Package installed to $REPOMEM_DIR/lib/repomem${NC}"

# ── Install crons ──────────────────────────────────────────────────────────────
mkdir -p "$REPOMEM_DIR/crons"
cp "$SCRIPT_DIR/crons/"*.py "$REPOMEM_DIR/crons/"
echo -e "  ${GREEN}✅ Cron scripts installed${NC}"

# ── Install Claude Code hooks ──────────────────────────────────────────────────
if [ -d "$CLAUDE_DIR/hooks" ]; then
    echo "Installing hooks..."
    cp "$SCRIPT_DIR/hooks/memory-capture.py" "$CLAUDE_DIR/hooks/"
    cp "$SCRIPT_DIR/hooks/memory-inject.py" "$CLAUDE_DIR/hooks/"
    chmod +x "$CLAUDE_DIR/hooks/memory-capture.py"
    chmod +x "$CLAUDE_DIR/hooks/memory-inject.py"
    echo -e "  ${GREEN}✅ Hooks installed${NC}"
else
    echo -e "  ${YELLOW}⚠️  Claude hooks dir not found — hooks not installed${NC}"
    echo "     Run manually: cp hooks/*.py $CLAUDE_DIR/hooks/"
fi

# ── Install Claude Code skills ─────────────────────────────────────────────────
if [ -d "$CLAUDE_DIR/skills" ]; then
    echo "Installing skills..."
    cp -r "$SCRIPT_DIR/skills/repomem-recall" "$CLAUDE_DIR/skills/"
    cp -r "$SCRIPT_DIR/skills/repomem-add" "$CLAUDE_DIR/skills/"
    echo -e "  ${GREEN}✅ Skills installed${NC}"
else
    echo -e "  ${YELLOW}⚠️  Claude skills dir not found — skills not installed${NC}"
fi

# ── Wire settings.json hooks ───────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "Wiring hooks into settings.json..."
    $PYTHON3 - <<'PYTHON'
import json, os, sys

settings_path = os.path.expanduser("~/.claude/settings.json")
repomem_lib = os.path.expanduser("~/.repomem/lib")

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})

# Stop hook — capture
stop_hooks = hooks.setdefault("Stop", [])
capture_cmd = f"REPOMEM_INSTALL={repomem_lib} python3.11 ~/.claude/hooks/memory-capture.py"
already_wired = any(
    capture_cmd in str(h) for entry in stop_hooks for h in entry.get("hooks", [])
)
if not already_wired:
    stop_hooks.append({
        "hooks": [{
            "type": "command",
            "command": capture_cmd,
            "timeout": 30,
            "statusMessage": "RepoMem: saving session memory..."
        }]
    })
    print("  ✅ Stop hook wired")
else:
    print("  ⏭️  Stop hook already wired")

# SessionStart hook — inject
start_hooks = hooks.setdefault("SessionStart", [])
inject_cmd = f"REPOMEM_INSTALL={repomem_lib} python3.11 ~/.claude/hooks/memory-inject.py"
already_wired = any(
    inject_cmd in str(h) for entry in start_hooks for h in entry.get("hooks", [])
)
if not already_wired:
    start_hooks.append({
        "hooks": [{
            "type": "command",
            "command": inject_cmd,
            "timeout": 10,
            "statusMessage": "RepoMem: loading project memory..."
        }]
    })
    print("  ✅ SessionStart hook wired")
else:
    print("  ⏭️  SessionStart hook already wired")

# MCP server
mcp_servers = settings.setdefault("mcpServers", {})
mcp_cmd = [
    f"{sys.executable}",
    f"{repomem_lib}/server/mcp_server.py"
]
mcp_env = {"REPOMEM_INSTALL": repomem_lib}

if "repomem" not in mcp_servers:
    mcp_servers["repomem"] = {
        "command": mcp_cmd[0],
        "args": mcp_cmd[1:],
        "env": mcp_env,
    }
    print("  ✅ MCP server wired")
else:
    print("  ⏭️  MCP server already wired")

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
PYTHON
else
    echo -e "  ${YELLOW}⚠️  settings.json not found — hooks not wired automatically${NC}"
fi

# ── Add crons ──────────────────────────────────────────────────────────────────
echo "Adding cron jobs..."
CRON_REFLECT="0 2 * * * REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3 $REPOMEM_DIR/crons/reflect.py >> $REPOMEM_DIR/logs/reflect.log 2>&1"
CRON_DEFRAG="0 3 * * 0 REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3 $REPOMEM_DIR/crons/defrag.py >> $REPOMEM_DIR/logs/defrag.log 2>&1"

(crontab -l 2>/dev/null; echo "$CRON_REFLECT"; echo "$CRON_DEFRAG") | sort -u | crontab -
echo -e "  ${GREEN}✅ Cron jobs added (reflect: 2am daily, defrag: Sunday 3am)${NC}"

# ── Initialize DB ──────────────────────────────────────────────────────────────
echo "Initializing database..."
REPOMEM_INSTALL="$REPOMEM_DIR/lib" $PYTHON3 -c "
import sys; sys.path.insert(0, '$REPOMEM_DIR/lib')
from repomem.db import init_db; init_db()
print('  ✅ Database initialized: $REPOMEM_DIR/memory.db')
"

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}✅ RepoMem installed successfully!${NC}"
echo ""
echo "  Quick start:"
echo "    repomem status                    # check DB stats"
echo "    repomem search 'crash'            # search observations"
echo "    repomem pending                   # open tasks"
echo "    repomem doctor                    # health check"
echo ""
echo "  Memory location: $REPOMEM_DIR/memory.db"
echo "  Restart Claude Code to activate session hooks."
echo ""
