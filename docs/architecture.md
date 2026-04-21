# Architecture

MemFree implements a **three-tier memory architecture** optimized for AI agents running on local machines.

## Core Principles

1. **Write once, read many** — Facts are written to warm layer, read frequently by agents
2. **Importance decays over time** — Unless reinforced through access
3. **Conflict resolution** — New facts auto-invalidate contradictory old ones
4. **Zero external dependencies** — Pure Python, local JSON files

## Three Layers

### HOT Layer — Session State

**Purpose:** Millisecond-level access to most-recent conversation context

**Files:**
- `SESSION-STATE.md` — WAL-style session log (append-only per session)
- System prompt injection — Current context injected into agent's system prompt

**TTL:** Session duration (cleared on new session)

### WARM Layer — Facts Store

**Purpose:** Structured, searchable, long-term facts

**File:** `facts.json`

**Schema:**
```json
{
  "id": "8-char-hash",
  "text": "The fact content",
  "importance": 0.85,
  "category": "preference",
  "source": "cli",
  "created_at": "2026-04-21T10:00:00",
  "valid_days": 90,
  "expires_at": "2026-07-20T10:00:00",
  "invalidated": false,
  "invalidated_at": null,
  "invalidated_reason": null,
  "access_count": 3
}
```

**TTL by category:** identity=365d > preference/tool=90d > work/project/lesson=60d > thread/behavior=30d > test=1d

### COLD Layer — Archive

**Purpose:** Rarely-accessed but important knowledge

**Files:**
- `MEMORY.md` — Core facts archive
- `DECISIONS.md` — Architecture decision log
- `TECH-DEBT.md` — Technical debt tracker

**TTL:** Manual (never auto-expire)

## Dynamic Importance

```
dynamic_importance = base_importance × (1 + log(1 + access_count))
```

- Each search hit increments `access_count`
- Frequently-accessed facts grow in importance (logarithmic, capped at 1.0)
- High-importance facts (≥0.8) are candidates for HOT layer promotion

## Conflict Detection

On every `add` operation:
1. Compute 4-gram character n-grams for new fact
2. Compare against all valid existing facts
3. If overlap ≥ 3 AND old fact importance < 0.9 → auto-invalidate old fact
4. Store invalidation reason for audit trail

## Cross-Agent Sync

`sync_to_soul.py` reads top-importance facts from `facts.json` and appends them to agent SOUL.md files. Enables memory sharing across heterogeneous agent systems.
