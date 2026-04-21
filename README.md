# 🧠 MemFree

**Open-source long-term memory for AI agents.**

Give your AI agents permanent, structured, and searchable memory. No hosted services. No API keys. Just files.

```
┌──────────────────────────────────────────────────────┐
│                    MemFree Architecture              │
├──────────┬───────────────────────────────────────────┤
│  HOT     │  System Prompt + SESSION-STATE.md (WAL)  │
├──────────┼───────────────────────────────────────────┤
│  WARM    │  facts.json — Dynamic Importance + TTL   │
│          │  + Conflict Detection + Access Tracking   │
├──────────┼───────────────────────────────────────────┤
│  COLD    │  MEMORY.md — Core Facts Archive          │
│          │  DECISIONS.md — Architecture Log          │
└──────────┴───────────────────────────────────────────┘
```

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Stars](https://img.shields.io/github/stars/yul0101/memfree)](https://github.com/yul0101/memfree/stargazers)

---

## ⚡ Quick Start

```bash
# One-line install
curl -fsSL https://raw.githubusercontent.com/yul0101/memfree/main/install.sh | bash

# Add your first fact
python3 ~/.memfree/mem0_facts.py add "I prefer concise, technical writing" --importance 0.9 --category preference

# Search your memory
python3 ~/.memfree/mem0_facts.py search "writing style"

# Start the Web UI
python3 ~/.memfree/mem0_server.py &
open http://localhost:19099
```

**30 seconds from zero to memory-powered agent.**

---

## 🎯 Why MemFree?

| Feature | Mem0 | Zep | MemFree |
|---------|------|-----|---------|
| Local-only (no cloud) | ❌ | ❌ | ✅ |
| Zero API keys required | ❌ | ❌ | ✅ |
| Category-specific TTL | ❌ | ✅ | ✅ |
| Dynamic importance scoring | ❌ | ❌ | ✅ |
| Visual Web UI | ❌ | ✅ | ✅ |
| Cross-agent memory bridge | ❌ | ❌ | ✅ |
| MIT license | ❌ | ❌ | ✅ |

---

## 📁 Architecture

```
~/.memfree/
├── mem0_facts.py       # Core CLI — add / search / list / feedback
├── mem0_server.py       # REST API + Web UI server
├── sync_to_soul.py       # Cross-agent memory bridge
├── decisions.py          # Architecture decision log
├── facts.json           # Warm layer — structured fact storage
├── memory/              # Cold layer — markdown archives
│   ├── MEMORY.md
│   └── DECISIONS.md
└── web_ui.html          # Visual memory dashboard
```

---

## 🔧 Core Commands

```bash
# Add a fact with importance (0.0–1.0) and category
python3 ~/.memfree/mem0_facts.py add "User prefers dark theme" \
  --importance 0.85 --category preference

# Semantic search across all facts
python3 ~/.memfree/mem0_facts.py search "theme preference"

# List facts by minimum importance
python3 ~/.memfree/mem0_facts.py list --min-importance 0.7

# User feedback loop — correct / wrong
python3 ~/.memfree/mem0_facts.py feedback "fact-id-here" --correct

# Auto-cleanup expired facts
python3 ~/.memfree/mem0_facts.py cleanup

# Monitor memory stats
python3 ~/.memfree/mem0_facts.py stats

# LLM-assisted fact extraction (optional — requires DeepSeek API key)
python3 ~/.memfree/mem0_facts.py extract "Fixed a memory leak in the agent"
```

---

## 🌐 Web UI

Start the server:

```bash
python3 ~/.memfree/mem0_server.py &
# → http://localhost:19099
```

Features:
- Visual fact browser with category tabs
- Dynamic importance display (base × access multiplier)
- User feedback buttons (Correct / Wrong → auto-adjusts importance)
- Search + filter by category
- Stats dashboard (total / valid / expired)
- Invalidated fact history with reason

---

## ⚙️ Dynamic Importance System

Every fact has two importance values:

```python
base_importance     # Set on creation (0.0–1.0)
dynamic_importance  # base × (1 + log(1 + access_count))
```

**Access count increments on every search hit.** Facts that are frequently retrieved grow in importance, while unused facts naturally decay.

**Category TTL (Time-To-Live):**

| Category | TTL | Example |
|----------|-----|---------|
| identity | 365 days | "I am a senior engineer" |
| preference | 90 days | "I prefer Python over Go" |
| tool | 90 days | "I use Cursor as main IDE" |
| project | 60 days | "The project uses PostgreSQL" |
| lesson | 60 days | "Don't use mutable defaults" |
| thread | 30 days | "Open thread about scaling" |
| behavior | 30 days | "User checks email every morning" |
| test | 1 day | Test/draft facts |

---

## 🤝 Cross-Agent Memory Bridge

MemFree facts sync to your agent's `SOUL.md` automatically:

```bash
# After adding facts, sync to SOUL.md
python3 ~/.memfree/sync_to_soul.py

# Dry run (preview only)
python3 ~/.memfree/sync_to_soul.py --dry-run
```

Works with: OpenClaw, Hermes Agent, WorkBuddy, or any agent that reads markdown files.

---

## 📦 Manual Install

```bash
git clone https://github.com/yul0101/memfree.git ~/.memfree
cd ~/.memfree
./install.sh
```

Or copy files manually:

```bash
mkdir -p ~/.memfree
cp src/*.py ~/.memfree/
cp web/*.html ~/.memfree/
chmod +x ~/.memfree/*.py
```

---

## 🔌 Integrations

**OpenClaw** — Add to your `openclaw.json`:

```json
{
  "memory": {
    "provider": "memfree",
    "path": "~/.memfree/facts.json"
  }
}
```

**Hermes Agent** — Reference in system prompt:

```
Your memory is stored in ~/.memfree/facts.json
Run: python3 ~/.memfree/mem0_facts.py search "<query>"
```

---

## 🗺️ Roadmap

- [ ] MCP Server — native MCP protocol support
- [ ] Docker one-click deploy
- [ ] VS Code extension
- [ ] Multi-namespace support (team memory)
- [ ] Import/export (Obsidian, Notion)
- [ ] Web UI: fact timeline view
- [ ] Web UI: importance graph over time

---

## 📄 License

MIT — free for personal and commercial use.

---

## 🙏 Credits

Built by [Yul](https://github.com/yul0101) with 🦂卡兹克.

Inspired by Mem0, Zep, and the OpenClaw ecosystem.
