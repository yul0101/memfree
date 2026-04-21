# MemFree vs Alternatives

## Feature Comparison

| Feature | MemFree | Mem0 | Zep | Vector DB Only |
|---------|---------|------|-----|----------------|
| **Storage** | Local JSON | Cloud + Local | Cloud | External |
| **API Key** | None | Required | Required | Varies |
| **Category TTL** | ✅ Per-category | ❌ | ✅ | ❌ |
| **Dynamic importance** | ✅ Access-based | ❌ | ❌ | ❌ |
| **Conflict detection** | ✅ 4-gram | ❌ | ❌ | ❌ |
| **Web UI** | ✅ Built-in | ❌ | ✅ | ❌ |
| **Cross-agent bridge** | ✅ SOUL.md sync | ❌ | ❌ | ❌ |
| **MIT License** | ✅ | ❌ | ❌ | N/A |
| **Self-hosted** | ✅ Zero deps | Partial | ❌ | ✅ |
| **Embedding model** | None (keyword) | ✅ | ✅ | ✅ |

## When to Use MemFree

**Use MemFree when:**
- You run agents locally (OpenClaw, Hermes, Cursor, etc.)
- You want zero external dependencies
- You prefer human-readable JSON over opaque vector stores
- You need a simple, auditable memory system
- You're building on WorkBuddy or OpenClaw

**Consider Mem0 when:**
- You need semantic/embedding-based search
- You want hosted memory with managed infrastructure
- You're building a consumer app with millions of users

**Consider Zep when:**
- You need managed cloud memory with analytics
- You want built-in memory analytics dashboards

## Philosophy

MemFree is **local-first, simple, and auditable**. If you want to understand exactly how your agent's memory works, MemFree's JSON files are fully readable and editable.

No magic. No cloud lock-in. Just memory.
