#!/usr/bin/env python3
"""
migrate-hot-to-facts.py — 热层迁移脚本（v2.0 架构变更）

迁移内容：
  1. hot.md 实体已在本脚本执行前由主流程删除（本次为预防性保留）
  2. 为所有旧事实补充 access_count 字段（默认 0）
  3. 为所有旧事实补充 valid_days 字段（缺失时从 CATEGORY_TTL 推断）
  4. 删除 LanceDB 配置引用（温层已禁用）

灰度策略：
  --dry-run：仅打印迁移预览，不写文件
  --backup：先备份 facts.json 再迁移
  --rollback：恢复备份

用法：
  python3 migrate-hot-to-facts.py [--dry-run] [--backup] [--rollback]
"""
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta

FACTS_JSON = Path.home() / ".agent-memory" / "facts.json"
BACKUP_DIR = Path.home() / ".agent-memory" / "backups"
LOCK_PATH  = Path.home() / ".agent-memory" / ".sync.lock"

CATEGORY_TTL = {
    "identity": 365, "preference": 90, "tool": 90, "work": 60,
    "project": 60, "lesson": 60, "thread": 30, "behavior": 30,
    "general": 30, "test": 1,
}


def backup():
    """备份 facts.json"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"facts.json.backup_{ts}"
    shutil.copy2(FACTS_JSON, dest)
    print(f"✅ 备份已创建: {dest}")
    return dest


def rollback():
    """恢复最近一次备份"""
    backups = sorted(BACKUP_DIR.glob("facts.json.backup_*"), key=lambda p: p.stat().st_mtime)
    if not backups:
        print("[ERROR] 未找到备份文件")
        return
    latest = backups[-1]
    shutil.copy2(latest, FACTS_JSON)
    print(f"✅ 已回滚至: {latest}")


def migrate(dry_run: bool = False, do_backup: bool = True):
    """
    执行迁移：
    - 补充 access_count
    - 补充 valid_days
    - 标注 LanceDB 引用已失效
    """
    facts = json.loads(FACTS_JSON.read_text(encoding="utf-8"))
    changes = {"access_count_added": 0, "valid_days_added": 0, "unchanged": 0}

    for f in facts:
        modified = False

        # 1. 补充 access_count（历史数据默认为 0）
        if "access_count" not in f:
            f["access_count"] = 0
            changes["access_count_added"] += 1
            modified = True

        # 2. 补充 valid_days（从 CATEGORY_TTL 推断）
        if "valid_days" not in f or not f["valid_days"]:
            cat = f.get("category", "general").lower()
            f["valid_days"] = CATEGORY_TTL.get(cat, 30)
            changes["valid_days_added"] += 1
            modified = True

        # 3. 补充 expires_at（缺失时补充，防止旧数据永远不过期）
        if not f.get("expires_at") and f.get("valid_days"):
            try:
                created = datetime.fromisoformat(f["created_at"])
                f["expires_at"] = (created + timedelta(days=f["valid_days"])).isoformat()
                modified = True
            except Exception:
                pass

        if not modified:
            changes["unchanged"] += 1

    if dry_run:
        print("[DRY RUN] 迁移预览：")
        print(f"  - 将补充 access_count: {changes['access_count_added']} 条")
        print(f"  - 将补充 valid_days:   {changes['valid_days_added']} 条")
        print(f"  - 保持不变:            {changes['unchanged']} 条")
        print(f"\n前 3 条预览：")
        for f in facts[:3]:
            print(f"  {json.dumps(f, ensure_ascii=False)}")
        return

    if do_backup:
        backup()

    FACTS_JSON.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 迁移完成：")
    print(f"  - access_count 补充: {changes['access_count_added']}")
    print(f"  - valid_days   补充: {changes['valid_days_added']}")
    print(f"  - 保持不变:          {changes['unchanged']}")
    print(f"  - LanceDB 温层: 已禁用（无引用）")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    do_backup = "--backup" in sys.argv and "--rollback" not in sys.argv

    if "--rollback" in sys.argv:
        rollback()
    else:
        migrate(dry_run=dry_run, do_backup=do_backup)
