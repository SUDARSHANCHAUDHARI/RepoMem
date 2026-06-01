#!/usr/bin/env bash
# RepoMem install script — one command setup
# Usage: bash install.sh
set -euo pipefail

REPOMEM_DIR="${REPOMEM_DIR:-$HOME/.repomem}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "  ${BOLD}RepoMem — Persistent memory for AI coding agents${NC}"
echo "  =================================================="
echo ""

# ── Check Python ───────────────────────────────────────────────────────────────
echo "Checking Python..."

PYTHON3=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON3="$candidate"
            PYTHON3_PATH="$(command -v $candidate)"
            PY_VERSION="$ver"
            break
        fi
    fi
done

if [ -z "$PYTHON3" ]; then
    echo -e "${RED}❌ Python 3.11+ required but not found (tried python3.13/3.12/3.11/python3)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ Python $PY_VERSION ($PYTHON3_PATH)${NC}"

# ── Create directories ─────────────────────────────────────────────────────────
echo "Creating directories..."
mkdir -p "$REPOMEM_DIR/lib" "$REPOMEM_DIR/logs" "$REPOMEM_DIR/sync" \
         "$REPOMEM_DIR/exports" "$REPOMEM_DIR/bin" "$REPOMEM_DIR/crons"
echo -e "  ${GREEN}✅ $REPOMEM_DIR${NC}"

# ── Install Python package ─────────────────────────────────────────────────────
echo "Installing RepoMem..."
cp -r "$SCRIPT_DIR/repomem" "$REPOMEM_DIR/lib/"
cp -r "$SCRIPT_DIR/server"  "$REPOMEM_DIR/lib/"
cp "$SCRIPT_DIR/crons/"*.py "$REPOMEM_DIR/crons/"
echo -e "  ${GREEN}✅ Package installed to $REPOMEM_DIR/lib/${NC}"

# ── Install wrapper script ─────────────────────────────────────────────────────
echo "Installing repomem command..."
WRAPPER="$REPOMEM_DIR/bin/repomem"
cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
REPOMEM_INSTALL="$REPOMEM_DIR/lib" PYTHONPATH="$REPOMEM_DIR/lib" \\
  "$PYTHON3_PATH" -m repomem "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER"

# Symlink to /usr/local/bin if writable, else suggest PATH addition
if [ -w "/usr/local/bin" ]; then
    ln -sf "$WRAPPER" /usr/local/bin/repomem
    echo -e "  ${GREEN}✅ repomem → /usr/local/bin/repomem${NC}"
else
    echo -e "  ${GREEN}✅ repomem wrapper at $WRAPPER${NC}"
    echo -e "  ${YELLOW}⚠️  Add to PATH: export PATH=\"\$PATH:$REPOMEM_DIR/bin\"${NC}"
fi

# ── Install Claude Code hooks ──────────────────────────────────────────────────
if [ -d "$CLAUDE_DIR/hooks" ]; then
    echo "Installing hooks..."
    cp "$SCRIPT_DIR/hooks/memory-capture.py" "$CLAUDE_DIR/hooks/"
    cp "$SCRIPT_DIR/hooks/memory-inject.py"  "$CLAUDE_DIR/hooks/"
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
    mkdir -p "$CLAUDE_DIR/skills/repomem"
    cp "$SCRIPT_DIR/skills/repomem/SKILL.md" "$CLAUDE_DIR/skills/repomem/SKILL.md"
    echo -e "  ${GREEN}✅ /repomem skill installed${NC}"
else
    echo -e "  ${YELLOW}⚠️  Claude skills dir not found — skills not installed${NC}"
fi

# ── Wire settings.json ─────────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "Wiring Claude Code integration..."
    PYTHON3_PATH_ESC="$PYTHON3_PATH"
    REPOMEM_LIB="$REPOMEM_DIR/lib"
    $PYTHON3 - "$PYTHON3_PATH_ESC" "$REPOMEM_LIB" "$SETTINGS" <<'PYTHON'
import json, sys

python3_path, repomem_lib, settings_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})

# Stop hook
stop_hooks = hooks.setdefault("Stop", [])
capture_cmd = f"REPOMEM_INSTALL={repomem_lib} {python3_path} ~/.claude/hooks/memory-capture.py"
if not any(capture_cmd in str(h) for entry in stop_hooks for h in entry.get("hooks", [])):
    stop_hooks.append({"hooks": [{"type": "command", "command": capture_cmd,
                                   "timeout": 30, "statusMessage": "RepoMem: saving session memory..."}]})
    print("  ✅ Stop hook wired")
else:
    print("  ⏭️  Stop hook already wired")

# SessionStart hook
start_hooks = hooks.setdefault("SessionStart", [])
inject_cmd = f"REPOMEM_INSTALL={repomem_lib} {python3_path} ~/.claude/hooks/memory-inject.py"
if not any(inject_cmd in str(h) for entry in start_hooks for h in entry.get("hooks", [])):
    start_hooks.append({"hooks": [{"type": "command", "command": inject_cmd,
                                    "timeout": 10, "statusMessage": "RepoMem: loading project memory..."}]})
    print("  ✅ SessionStart hook wired")
else:
    print("  ⏭️  SessionStart hook already wired")

# MCP server
mcp_servers = settings.setdefault("mcpServers", {})
if "repomem" not in mcp_servers:
    mcp_servers["repomem"] = {
        "command": python3_path,
        "args": [f"{repomem_lib}/server/mcp_server.py"],
        "env": {"REPOMEM_INSTALL": repomem_lib},
    }
    print("  ✅ MCP server wired")
else:
    print("  ⏭️  MCP server already wired")

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
PYTHON
else
    echo -e "  ${YELLOW}⚠️  settings.json not found — Claude Code integration skipped${NC}"
    echo "     Set CLAUDE_DIR or run inside a Claude Code project."
fi

# ── Add cron jobs ──────────────────────────────────────────────────────────────
echo "Adding cron jobs..."
CRON_REFLECT="0 2 * * * REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3_PATH $REPOMEM_DIR/crons/reflect.py >> $REPOMEM_DIR/logs/reflect.log 2>&1"
CRON_DEFRAG="0 3 * * 0 REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3_PATH $REPOMEM_DIR/crons/defrag.py >> $REPOMEM_DIR/logs/defrag.log 2>&1"

(crontab -l 2>/dev/null | grep -v "repomem"; echo "$CRON_REFLECT"; echo "$CRON_DEFRAG") | crontab -
echo -e "  ${GREEN}✅ Cron jobs: reflect (2am daily), defrag (Sunday 3am)${NC}"

# ── Initialize DB ──────────────────────────────────────────────────────────────
echo "Initializing database..."
REPOMEM_INSTALL="$REPOMEM_DIR/lib" PYTHONPATH="$REPOMEM_DIR/lib" \
  $PYTHON3 -c "
import sys; sys.path.insert(0, '$REPOMEM_DIR/lib')
from repomem.db import init_db; init_db()
print('  ✅ Database initialized')
"

# ── Health check ───────────────────────────────────────────────────────────────
echo "Running health check..."
REPOMEM_INSTALL="$REPOMEM_DIR/lib" PYTHONPATH="$REPOMEM_DIR/lib" \
  $PYTHON3 -c "
import sys; sys.path.insert(0, '$REPOMEM_DIR/lib')
from repomem.db import init_db, get_stats
init_db()
s = get_stats()
print(f'  ✅ DB healthy — {s[\"observations\"]} obs, {s[\"sessions\"]} sessions, {s[\"db_size_kb\"]} KB')
"

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}${BOLD}✅ RepoMem installed successfully!${NC}"
echo ""
echo "  Quick start:"
echo "    repomem status                    # DB stats"
echo "    repomem doctor                    # health check"
echo "    repomem search 'crash'            # search memory"
echo "    repomem server                    # web UI → http://localhost:39000"
echo "    repomem sync --export             # export for cross-machine sync"
echo "    repomem graphify                  # show god nodes for current repo"
echo "    repomem obsidian                  # export to Obsidian vault"
echo ""
echo "  Memory:  $REPOMEM_DIR/memory.db"
echo "  Logs:    $REPOMEM_DIR/logs/"
echo "  Wrapper: $WRAPPER"
echo ""
echo -e "  ${YELLOW}Restart Claude Code to activate session hooks + MCP server.${NC}"
echo ""
