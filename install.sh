#!/usr/bin/env bash
# RepoMem install script — one command setup
# Usage: bash install.sh
set -euo pipefail

REPOMEM_DIR="${REPOMEM_DIR:-$HOME/.repomem}"
CLAUDE_DIR="${CLAUDE_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
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
echo "Installing skills..."
if [ ! -d "$CLAUDE_DIR/skills" ]; then
    mkdir -p "$CLAUDE_DIR/skills"
    echo -e "  ${GREEN}✅ Created $CLAUDE_DIR/skills/${NC}"
fi
# Remove old sub-skills if present
for old_skill in repomem-add repomem-recall; do
    if [ -d "$CLAUDE_DIR/skills/$old_skill" ]; then
        rm -f "$CLAUDE_DIR/skills/$old_skill/SKILL.md"
        rmdir "$CLAUDE_DIR/skills/$old_skill" 2>/dev/null || true
        echo -e "  ${GREEN}✅ Removed old skill: $old_skill${NC}"
    fi
done
mkdir -p "$CLAUDE_DIR/skills/repomem"
cp "$SCRIPT_DIR/skills/repomem/SKILL.md" "$CLAUDE_DIR/skills/repomem/SKILL.md"
echo -e "  ${GREEN}✅ /repomem skill installed${NC}"

# ── Wire settings.json ─────────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "Wiring Claude Code integration..."
    PYTHON3_PATH_ESC="$PYTHON3_PATH"
    REPOMEM_LIB="$REPOMEM_DIR/lib"
    $PYTHON3 - "$PYTHON3_PATH_ESC" "$REPOMEM_LIB" "$SETTINGS" "$CLAUDE_DIR/hooks" <<'PYTHON'
import json, os, shlex, shutil, sys, tempfile

python3_path, repomem_lib, settings_path, hooks_dir = sys.argv[1:5]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})


def wire(event, script, timeout, status, label):
    """Add the hook, or repoint an earlier RepoMem entry for the same script (no duplicates)."""
    cmd = (f"REPOMEM_INSTALL={shlex.quote(repomem_lib)} {shlex.quote(python3_path)} "
           f"{shlex.quote(os.path.join(hooks_dir, script))}")
    entries = hooks.setdefault(event, [])
    # Only entries in this installer's own format, so hand-made hooks are left alone
    existing = [h for entry in entries for h in entry.get("hooks", [])
                if str(h.get("command", "")).startswith("REPOMEM_INSTALL=")
                and str(h.get("command", "")).rstrip("'\" ").endswith("/hooks/" + script)]
    if any(h.get("command") == cmd for h in existing):
        print(f"  ⏭️  {label} hook already wired")
    elif existing:
        for h in existing:
            h["command"] = cmd
        print(f"  ✅ {label} hook updated")
    else:
        entries.append({"hooks": [{"type": "command", "command": cmd,
                                   "timeout": timeout, "statusMessage": status}]})
        print(f"  ✅ {label} hook wired")


wire("Stop", "memory-capture.py", 30, "RepoMem: saving session memory...", "Stop")
wire("SessionStart", "memory-inject.py", 10, "RepoMem: loading project memory...", "SessionStart")

# Back up, then write atomically: temp file in the same dir + rename.
# realpath keeps a symlinked settings.json pointing at its real target.
target = os.path.realpath(settings_path)
shutil.copy2(target, target + ".bak")
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".settings.", suffix=".tmp")
try:
    with os.fdopen(fd, "w") as f:
        json.dump(settings, f, indent=2)
    shutil.copymode(target, tmp)
    os.replace(tmp, target)
except BaseException:
    os.unlink(tmp)
    raise
print(f"  ✅ settings.json updated (backup: {target}.bak)")
PYTHON
else
    echo -e "  ${YELLOW}⚠️  settings.json not found — Claude Code integration skipped${NC}"
    echo "     Set CLAUDE_DIR or run inside a Claude Code project."
fi

# ── Wire MCP server ────────────────────────────────────────────────────────────
# Claude Code reads user MCP servers from its own config (managed by `claude mcp`), not settings.json.
MCP_ADD=(claude mcp add --scope user repomem -e "REPOMEM_INSTALL=$REPOMEM_DIR/lib" -- "$PYTHON3_PATH" "$REPOMEM_DIR/lib/server/mcp_server.py")
if command -v claude &>/dev/null && "${MCP_ADD[@]}"; then
    echo -e "  ${GREEN}✅ MCP server wired (user scope)${NC}"
else
    echo -e "  ${YELLOW}⚠️  MCP server not wired (claude CLI missing, or repomem already added)${NC}"
    echo "     Run: $(printf '%q ' "${MCP_ADD[@]}")"
fi

# ── Add cron jobs ──────────────────────────────────────────────────────────────
echo "Adding cron jobs..."
CRON_REFLECT="0 2 * * * REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3_PATH $REPOMEM_DIR/crons/reflect.py >> $REPOMEM_DIR/logs/reflect.log 2>&1"
CRON_DEFRAG="0 3 * * 0 REPOMEM_INSTALL=$REPOMEM_DIR/lib $PYTHON3_PATH $REPOMEM_DIR/crons/defrag.py >> $REPOMEM_DIR/logs/defrag.log 2>&1"

# Managed sentinel block only — see scripts/repomem-crontab.sh. A plain
# `grep -v "repomem"` here used to delete every crontab line containing that
# word, including jobs this installer never created.
export CRON_REFLECT CRON_DEFRAG
if bash "$SCRIPT_DIR/scripts/repomem-crontab.sh"; then
    echo -e "  ${GREEN}✅ Cron jobs: reflect (2am daily), defrag (Sunday 3am)${NC}"
else
    echo -e "  ${YELLOW}⚠️  Cron jobs skipped — your crontab was left unchanged (see above)${NC}"
fi

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
" || echo -e "  ${YELLOW}⚠️  Health check failed — run 'repomem doctor' after install to diagnose${NC}"

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
