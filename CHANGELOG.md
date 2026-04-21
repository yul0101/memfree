# Changelog

All notable changes to MemFree will be documented in this file.

## [0.1.0] — 2026-04-21

### Added
- **MemFree core**: Three-tier memory architecture (HOT / WARM / COLD)
- **mem0_facts.py**: CLI for adding, searching, listing, and managing facts
- **mem0_server.py**: REST API server with built-in Web UI
- **Dynamic importance**: `base × (1 + log(1 + access_count))` scoring
- **Category-specific TTL**: identity=365d, preference/tool=90d, project/lesson=60d, thread/behavior=30d, test=1d
- **Conflict detection**: 4-gram overlap detection auto-invalidates conflicting facts
- **User feedback loop**: Correct/Wrong buttons auto-adjust importance
- **sync_to_soul.py**: Cross-agent memory bridge to SOUL.md
- **Web UI**: Dark-themed visual dashboard for fact management
- **GitHub Actions CI**: Python 3.10–3.12 test matrix
- **MIT License**: Zero-cost commercial use

### Architecture
- HOT: System prompt + SESSION-STATE.md (WAL)
- WARM: facts.json (importance + access tracking + TTL)
- COLD: MEMORY.md / DECISIONS.md / TECH-DEBT.md archives
