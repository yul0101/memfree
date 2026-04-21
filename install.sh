#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# MemFree — One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/yul0101/memfree/main/install.sh | bash
#        bash <(curl -fsSL https://raw.githubusercontent.com/yul0101/memfree/main/install.sh)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; CYA='\033[0;36m'
BLD='\033[1m'; RST='\033[0m'

log()  { echo -e "${GRN}[+]${RST} $1"; }
warn() { echo -e "${YEL}[!]${RST} $1"; }
err()  { echo -e "${RED}[✗]${RST} $1" >&2; }

# ─── Config ───────────────────────────────────────────────────────────────────
MEMFREE_DIR="${MEMFREE_DIR:-$HOME/.memfree}"
REPO_URL="https://github.com/yul0101/memfree.git"

echo ""
echo -e "${BLD}Cyan🧠${RST} ${BLD}MemFree${RST} — Agent Long-term Memory"
echo -e "        ${BLD}Open-source · Zero deps · MIT License${RST}"
echo ""

# ─── Python check ─────────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    err "Python 3 not found. Install from https://python.org"
    exit 1
fi
PY_VERSION=$($PYTHON --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
log "Python: $PY_VERSION ✓"

# ─── Create dir ───────────────────────────────────────────────────────────────
if [ ! -d "$MEMFREE_DIR" ]; then
    mkdir -p "$MEMFREE_DIR"
    log "Created $MEMFREE_DIR"
fi

# ─── Clone if no git ───────────────────────────────────────────────────────────
if [ ! -d "$MEMFREE_DIR/.git" ]; then
    if command -v git &>/dev/null; then
        log "Cloning MemFree..."
        git clone --depth=1 "$REPO_URL" "$MEMFREE_DIR.tmp" 2>/dev/null || {
            err "Failed to clone repo. Installing from inline files."
        }
        if [ -d "$MEMFREE_DIR.tmp" ]; then
            cp -r "$MEMFREE_DIR.tmp/"* "$MEMFREE_DIR/" 2>/dev/null || true
            rm -rf "$MEMFREE_DIR.tmp"
        fi
    fi
fi

# ─── Copy source files ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python source
for f in src/*.py; do
    [ -f "$f" ] && cp "$f" "$MEMFREE_DIR/" 2>/dev/null || true
done

# Root scripts (if any at root level)
for f in mem0_*.py sync_to_soul.py decisions.py; do
    [ -f "$f" ] && cp "$f" "$MEMFREE_DIR/" 2>/dev/null || true
done

# Web UI
for f in web/*.html web/*.js 2>/dev/null; do
    [ -f "$f" ] && cp "$f" "$MEMFREE_DIR/" 2>/dev/null || true
done
# Fallback: web_ui.html at root
[ -f "web_ui.html" ] && cp "web_ui.html" "$MEMFREE_DIR/" 2>/dev/null || true

# ─── Init data dir ────────────────────────────────────────────────────────────
mkdir -p "$MEMFREE_DIR/memory"
if [ ! -f "$MEMFREE_DIR/facts.json" ]; then
    echo '[]' > "$MEMFREE_DIR/facts.json"
    log "Created facts.json"
fi

# ─── Make executable ───────────────────────────────────────────────────────────
chmod +x "$MEMFREE_DIR"/*.py 2>/dev/null || true

# ─── Add to PATH ──────────────────────────────────────────────────────────────
PROFILE_FILE=""
for f in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    [ -f "$f" ] && PROFILE_FILE="$f" && break
done

if [ -n "$PROFILE_FILE" ]; then
    PATH_LINE="export PATH=\"\$HOME/.memfree:\$PATH\"  # MemFree"
    if ! grep -q "MemFree" "$PROFILE_FILE" 2>/dev/null; then
        echo "" >> "$PROFILE_FILE"
        echo "# MemFree — Agent Memory" >> "$PROFILE_FILE"
        echo "$PATH_LINE" >> "$PROFILE_FILE"
        log "Added to $PROFILE_FILE"
        warn "Run: source $PROFILE_FILE"
    fi
fi

# ─── Verify ───────────────────────────────────────────────────────────────────
FACTS_EXISTS=$([ -f "$MEMFREE_DIR/facts.json" ] && echo "yes" || echo "no")
SERVER_EXISTS=$([ -f "$MEMFREE_DIR/server.py" ] && echo "yes" || echo "no")

echo ""
echo "─────────────────────────────────────"
echo -e " ${GRN}✅ Installation complete!${RST}"
echo "─────────────────────────────────────"
echo "  Install dir: $MEMFREE_DIR"
echo "  facts.json: $FACTS_EXISTS"
echo "  Web server: $SERVER_EXISTS"
echo ""
echo -e " ${CYA}Quick Start:${RST}"
echo "  python3 $MEMFREE_DIR/facts.py add \"Hello, I am an AI agent\" -i 0.9 -c identity"
echo "  python3 $MEMFREE_DIR/facts.py search \"AI agent\""
echo "  python3 $MEMFREE_DIR/server.py &"
echo "  # → open http://localhost:19099/web_ui.html"
echo ""
