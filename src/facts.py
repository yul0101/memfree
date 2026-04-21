"""
MemFree Facts — Core storage and operations module.

Provides: add, search, list, invalidate, cleanup, stats, feedback, extract.
"""

import fcntl
import hashlib
import json
import math
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ─── Path configuration ────────────────────────────────────────────────────────

def get_memfree_dir() -> Path:
    env = os.environ.get("MEMFREE_DIR", "")
    if env:
        p = Path(env)
        if p.exists():
            return p
    for candidate in [Path.home() / ".memfree", Path.home() / ".agent-memory"]:
        if candidate.exists():
            return candidate
    default = Path.home() / ".memfree"
    default.mkdir(parents=True, exist_ok=True)
    return default

MEMFREE_DIR = get_memfree_dir()
FACTS_FILE = MEMFREE_DIR / "facts.json"
BACKUP_DIR = MEMFREE_DIR / "backups"

# ─── Category TTL ─────────────────────────────────────────────────────────────

CATEGORY_TTL = {
    "identity":   365,
    "project":      60,
    "lesson":       60,
    "thread":       30,
    "preference":   90,
    "tool":         90,
    "work":         60,
    "behavior":     30,
    "general":      30,
    "test":          1,
}

# ─── LRU Cache ────────────────────────────────────────────────────────────────

class FactCache:
    """Thread-safe LRU cache with TTL. No external deps. """

    def __init__(self, ttl: int = 30):
        self._cache: dict = {}
        self._lock = threading.RLock()
        self._ttl = ttl
        self._atime: dict = {}

    def get(self, key: str = "facts") -> Optional[list]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            data, ts = entry
            if time.time() - ts > self._ttl:
                del self._cache[key]
                self._atime.pop(key, None)
                return None
            self._atime[key] = time.time()
            return data

    def set(self, key: str = "facts", data: list = None):
        with self._lock:
            self._cache[key] = (data, time.time())
            self._atime[key] = time.time()

    def invalidate(self, key: str = "facts"):
        with self._lock:
            self._cache.pop(key, None)
            self._atime.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            valid = sum(
                1 for (_, ts) in self._cache.values()
                if now - ts <= self._ttl
            )
            return {
                "total_slots": len(self._cache),
                "valid_entries": valid,
                "stale_entries": len(self._cache) - valid,
            }


_cache = FactCache()
_lock = threading.RLock()

# ─── File I/O ────────────────────────────────────────────────────────────────

def _backup():
    if not FACTS_FILE.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    import shutil
    shutil.copy(FACTS_FILE, BACKUP_DIR / f"facts_{ts}.json")


def load_facts() -> list[dict]:
    cached = _cache.get()
    if cached is not None:
        return cached
    if not FACTS_FILE.exists():
        _cache.set([])
        return []
    with _lock:
        try:
            data = json.loads(FACTS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = []
    _cache.set(data)
    return data


def save_facts(facts: list[dict]):
    _cache.set(facts)
    with _lock:
        FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        FACTS_FILE.write_text(
            json.dumps(facts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ─── Core operations ─────────────────────────────────────────────────────────

def compute_dynamic(fact: dict) -> float:
    base = fact.get("importance", 0.5)
    acc = fact.get("access_count", 0)
    dyn = base * (1 + (0 if acc == 0 else math.log(1 + acc)))
    return round(min(dyn, 1.0), 4)


def ngrams(text: str, n: int = 4) -> set[str]:
    """Character n-grams (space-agnostic for Chinese support)."""
    t = text.replace(" ", "")
    return set(t[i:i+n] for i in range(max(0, len(t) - n + 1)))


def add_fact(
    text: str,
    importance: float = 0.5,
    category: str = "general",
    source: str = "cli",
) -> dict:
    """Add a fact with auto-conflict detection."""
    facts = load_facts()
    conflicts = []

    # Conflict detection
    for f in facts:
        if f.get("invalidated"):
            continue
        ng_new = ngrams(text)
        ng_old = ngrams(f["text"])
        overlap = len(ng_new & ng_old)
        if overlap >= 3:
            if f.get("importance", 0) < 0.9:
                f["invalidated"] = True
                f["invalidated_at"] = datetime.now().isoformat()
                f["invalidated_reason"] = f"Replaced by new fact (4-gram overlap: {overlap})"
            conflicts.append(f["id"])

    fid = hashlib.md5(text.encode()).hexdigest()[:8]
    valid_days = CATEGORY_TTL.get(category, 30)

    new_fact = {
        "id": fid,
        "text": text,
        "importance": max(0.0, min(1.0, importance)),
        "category": category,
        "source": source,
        "created_at": datetime.now().isoformat(),
        "valid_days": valid_days,
        "expires_at": (datetime.now() + timedelta(days=valid_days)).isoformat(),
        "invalidated": False,
        "invalidated_at": None,
        "invalidated_reason": None,
        "access_count": 0,
    }

    facts = [f for f in facts if f["id"] not in conflicts] + [new_fact]
    save_facts(facts)
    return new_fact


def search_facts(query: str, include_invalidated: bool = False) -> list[dict]:
    """Keyword search across all facts."""
    facts = load_facts()
    q = query.lower()
    results = []

    for f in facts:
        if not include_invalidated and f.get("invalidated"):
            continue
        if q in f["text"].lower():
            f["access_count"] = f.get("access_count", 0) + 1
            results.append(f)

    save_facts(facts)
    return sorted(results, key=lambda x: compute_dynamic(x), reverse=True)


def list_facts(
    min_importance: float = 0.0,
    category: Optional[str] = None,
) -> list[dict]:
    """List valid facts sorted by dynamic importance."""
    facts = load_facts()
    valid = [f for f in facts if not f.get("invalidated")]

    if category:
        valid = [f for f in valid if f.get("category") == category]

    return sorted(valid, key=lambda x: compute_dynamic(x), reverse=True)


def invalidate_fact(fact_id: str, reason: str = "") -> bool:
    """Manually invalidate a fact."""
    facts = load_facts()
    for f in facts:
        if f["id"] == fact_id:
            f["invalidated"] = True
            f["invalidated_at"] = datetime.now().isoformat()
            f["invalidated_reason"] = reason or "Manually invalidated"
            save_facts(facts)
            return True
    return False


def cleanup_facts() -> dict:
    """Remove expired facts and orphaned invalidated ones."""
    facts = load_facts()
    now = datetime.now()
    removed = 0

    # TTL-based expiration
    for f in facts:
        if f.get("expires_at") and not f.get("invalidated"):
            try:
                exp = datetime.fromisoformat(f["expires_at"])
                if exp < now and f.get("category") in ("behavior", "test", "general"):
                    f["invalidated"] = True
                    f["invalidated_at"] = now.isoformat()
                    f["invalidated_reason"] = "TTL expired"
                    removed += 1
            except ValueError:
                pass

    # Remove truly expired (TTL-cleared categories)
    before = len(facts)
    facts = [f for f in facts if not (
        f.get("invalidated") and
        f.get("category") in ("behavior", "test", "general") and
        f.get("invalidated_reason") == "TTL expired"
    )]
    removed += before - len(facts)

    save_facts(facts)
    return {"removed": removed, "remaining": len(facts)}


def feedback_fact(fact_id: str, delta: float) -> Optional[dict]:
    """Apply importance delta and increment access count."""
    facts = load_facts()
    for f in facts:
        if f["id"] == fact_id:
            f["importance"] = max(0.0, min(1.0, f.get("importance", 0.5) + delta))
            acc = f.get("access_count", 0) + (3 if delta > 0 else 1)
            f["access_count"] = min(acc, 1000)
            save_facts(facts)
            return f
    return None


def get_stats() -> dict:
    """Return memory statistics."""
    facts = load_facts()
    now = datetime.now()
    cats: dict = {}
    expired = 0
    invalidated = 0

    for f in facts:
        c = f.get("category", "general")
        cats[c] = cats.get(c, 0) + 1
        if f.get("invalidated"):
            invalidated += 1
        elif f.get("expires_at"):
            try:
                if datetime.fromisoformat(f["expires_at"]) < now:
                    expired += 1
            except ValueError:
                pass

    size_kb = FACTS_FILE.stat().st_size / 1024 if FACTS_FILE.exists() else 0
    cache_stats = _cache.stats()

    return {
        "total": len(facts),
        "valid": len(facts) - invalidated,
        "expired": expired,
        "invalidated": invalidated,
        "by_category": cats,
        "file_size_kb": round(size_kb, 1),
        "cache": cache_stats,
    }


def extract_facts_with_llm(text: str, api_key: Optional[str] = None) -> list[dict]:
    """
    Extract structured facts from natural language using LLM.
    Falls back to rule-based extraction if no API key.
    """
    import subprocess

    script = MEMFREE_DIR / "mem0_facts.py"
    if script.exists():
        result = subprocess.run(
            [sys.executable, str(script), "extract", text],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return [{"text": line.strip(), "source": "llm-extract"}
                    for line in result.stdout.splitlines() if line.strip()]

    # Rule-based fallback
    facts = []
    patterns = [
        (r"(使用?|用|靠|喜欢|prefer|use|like).{0,20}", "preference"),
        (r"(修复|修|解决|bug|fix|resolve).{0,20}", "lesson"),
        (r"(正在做|项目|project|building|开发).{0,20}", "project"),
    ]
    for pat, cat in patterns:
        if re.search(pat, text):
            facts.append({"text": text.strip(), "category": cat, "source": "rule-extract"})
    return facts


# ─── CLI entry point ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog="memfree",
        description="MemFree — Agent Long-term Memory CLI",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Add a new fact")
    p_add.add_argument("text", help="Fact text")
    p_add.add_argument("--importance", "-i", type=float, default=0.7)
    p_add.add_argument("--category", "-c", default="general")
    p_add.add_argument("--mem0", action="store_true", help="LLM-assisted extraction")

    p_search = sub.add_parser("search", help="Search facts")
    p_search.add_argument("query")
    p_search.add_argument("--all", action="store_true")

    p_list = sub.add_parser("list", help="List facts")
    p_list.add_argument("--min-importance", type=float, default=0.0)
    p_list.add_argument("--category")

    p_inv = sub.add_parser("invalidate", help="Invalidate a fact")
    p_inv.add_argument("--id", required=True)
    p_inv.add_argument("--reason", default="")

    sub.add_parser("cleanup", help="Clean up expired facts")
    sub.add_parser("stats", help="Show memory statistics")

    p_fbk = sub.add_parser("feedback", help="Give feedback on a fact")
    p_fbk.add_argument("id")
    p_fbk.add_argument("--correct", action="store_true")
    p_fbk.add_argument("--wrong", action="store_true")

    p_ext = sub.add_parser("extract", help="Extract facts from text")
    p_ext.add_argument("text", help="Text to extract from")

    args = parser.parse_args()

    if args.cmd == "add":
        fact = add_fact(args.text, args.importance, args.category)
        print(f"Added: {fact['id']} ({fact['category']}, imp={fact['importance']})")
        if args.mem0:
            extracted = extract_facts_with_llm(args.text)
            for e in extracted:
                add_fact(e["text"], 0.6, e.get("category", "general"), source="llm-extract")
                print(f"  + LLM extracted: {e['text'][:60]}")

    elif args.cmd == "search":
        results = search_facts(args.query, args.all)
        if not results:
            print("No results.")
        for f in results:
            dyn = compute_dynamic(f)
            print(f"[{f['id']}] [{f['category']}] imp={f['importance']:.2f} dyn={dyn:.3f}")
            print(f"  {f['text']}")
            print()

    elif args.cmd == "list":
        facts = list_facts(args.min_importance, args.category)
        for f in facts:
            print(f"[{f['id']}] [{f['category']}] imp={f['importance']:.2f}")
            print(f"  {f['text']}")
            print()

    elif args.cmd == "invalidate":
        ok = invalidate_fact(args.id, args.reason)
        print("Done." if ok else "Fact not found.")

    elif args.cmd == "cleanup":
        result = cleanup_facts()
        print(f"Removed {result['removed']} facts. Remaining: {result['remaining']}")

    elif args.cmd == "stats":
        stats = get_stats()
        print(f"Total:      {stats['total']}")
        print(f"Valid:      {stats['valid']}")
        print(f"Expired:    {stats['expired']}")
        print(f"Invalidated:{stats['invalidated']}")
        print(f"File size:  {stats['file_size_kb']} KB")
        print("By category:", stats["by_category"])

    elif args.cmd == "feedback":
        delta = 0.1 if args.correct else (-0.1 if args.wrong else 0)
        result = feedback_fact(args.id, delta)
        if result:
            print(f"Updated: imp={result['importance']:.2f}, access={result['access_count']}")
        else:
            print("Fact not found.")

    elif args.cmd == "extract":
        facts = extract_facts_with_llm(args.text)
        for f in facts:
            print(f["text"])

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
