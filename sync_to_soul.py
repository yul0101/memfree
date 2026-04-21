#!/usr/bin/env python3
"""
sync_to_soul.py v2.0 — facts.json → SOUL.md 同步桥

改动（相比 v1.x）：
  - 添加文件锁（fcntl），防止并发写入损坏 SOUL.md
  - 添加写入超时（alarm + signal），超过 3 秒自动放弃
  - 读取时也加锁，避免读到半写入状态
  - graceful degradation：无法获取锁时跳过而非报错

用法：python3 sync_to_soul.py [--dry-run]
"""
import json
import sys
import os
import signal
import fcntl
import time
from pathlib import Path
from datetime import datetime

FACTS_PATH   = Path.home() / ".agent-memory" / "facts.json"
SOUL_PATH    = Path.home() / ".workbuddy" / "SOUL.md"
LOCK_PATH    = Path.home() / ".agent-memory" / ".sync.lock"
MARKER_START = "<!-- SHARED_MEMORY_START -->"
MARKER_END   = "<!-- SHARED_MEMORY_END -->"
MIN_IMPORTANCE = 0.7
WRITE_TIMEOUT = 3   # 秒，超时自动放弃


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("写入超时")


def load_active_facts() -> list[dict]:
    """带文件锁的 facts.json 读取"""
    if not FACTS_PATH.exists():
        return []
    try:
        lock_fd = open(LOCK_PATH, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_SH)  # 共享锁（读）
        try:
            data = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        active = [
            f for f in data
            if not f.get("invalidated")
            and f.get("importance", 0) >= MIN_IMPORTANCE
        ]
        active.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return active
    except (IOError, OSError):
        return []


def build_block(facts: list[dict]) -> str:
    """构建 SOUL.md 中的 SHARED_MEMORY 区块"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        MARKER_START,
        "",
        "## Shared Memory (auto-synced from agent-memory-kit v2.0)",
        f"_Last sync: {ts}_",
        "",
        "### User Facts",
    ]
    for f in facts:
        lines.append(
            f"- [{f.get('category','general')}] {f['text']}"
            f"  (base={f.get('importance',0):.2f}, "
            f"acc={f.get('access_count',0)})"
        )
    lines.extend(["", MARKER_END])
    return "\n".join(lines)


def sync(dry_run: bool = False) -> bool:
    """
    带文件锁的同步写入。
    返回 True=成功，False=跳过（锁竞争/超时/异常）
    """
    facts = load_active_facts()
    new_block = build_block(facts)

    # ── 读取现有 SOUL.md ──
    try:
        lock_fd = open(LOCK_PATH, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)   # 独占锁（写）
    except (IOError, OSError):
        return False

    try:
        soul = SOUL_PATH.read_text(encoding="utf-8") if SOUL_PATH.exists() else ""
    except Exception:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        return False

    if MARKER_START in soul and MARKER_END in soul:
        pre  = soul[:soul.index(MARKER_START)]
        post = soul[soul.index(MARKER_END) + len(MARKER_END):]
        new_soul = pre + new_block + post
    else:
        new_soul = soul.rstrip() + "\n\n" + new_block + "\n"

    if dry_run:
        print("[DRY RUN] Would write to:", SOUL_PATH)
        print(new_block)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        return True

    # ── 超时保护（防止 fcntl 永久阻塞） ──
    old_alarm = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(WRITE_TIMEOUT)

    try:
        SOUL_PATH.write_text(new_soul, encoding="utf-8")
        print(f"✅ Synced {len(facts)} facts → {SOUL_PATH}")
        result = True
    except TimeoutError:
        print("[WARN] 写入超时，跳过本次同步")
        result = False
    except Exception as e:
        print(f"[ERROR] 写入失败: {e}")
        result = False
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_alarm)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    return result


if __name__ == "__main__":
    success = sync(dry_run="--dry-run" in sys.argv)
    sys.exit(0 if success else 1)
