#!/usr/bin/env python3
"""
test_mem0_facts.py — 单元测试（v2.0）

覆盖：
  1. 冲突检测（n-gram + 矛盾关键词）
  2. TTL 清理
  3. dynamic_importance 公式
  4. Cache 层（LRU + TTL）
  5. 分类半衰期配置
  6. feedback_adjust 闭环

运行：
  python3 test_mem0_facts.py
"""
import unittest
import tempfile
import json
import time
import math
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# ── mock FACTS_JSON 到临时文件 ──
TMPDIR = tempfile.mkdtemp()
FAKE_JSON = Path(TMPDIR) / "facts.json"

import sys
sys.path.insert(0, str(Path.home() / ".agent-memory"))

# 注入 mock 路径
import mem0_facts as mf
mf.FACTS_JSON = FAKE_JSON
mf.FACTS_MD   = Path(TMPDIR) / "facts.md"
mf._CACHE     = mf.FactCache(ttl_seconds=1)  # 1秒 TTL 用于测试


class TestDynamicImportance(unittest.TestCase):
    """测试 dynamic_importance 公式"""

    def test_formula(self):
        # importance = base × (1 + log(1 + access_count))
        cases = [
            (0.9, 0,   0.9),
            (0.9, 1,   round(0.9 * (1 + math.log(2)), 4)),
            (0.9, 9,   round(0.9 * (1 + math.log(10)), 4)),
            (0.5, 99,  round(0.5 * (1 + math.log(100)), 4)),
        ]
        for base, acc, expected in cases:
            result = mf._dynamic_importance(base, acc)
            self.assertAlmostEqual(result, expected, places=4)

    def test_bounded(self):
        # access_count 超过 MAX_ACCESS 时应封顶
        imp = mf._dynamic_importance(0.5, mf.MAX_ACCESS + 100)
        imp_max = mf._dynamic_importance(0.5, mf.MAX_ACCESS)
        self.assertEqual(imp, imp_max)


class TestConflictDetection(unittest.TestCase):
    """测试冲突检测"""

    def setUp(self):
        self.facts = [
            {"id": "a", "text": "用户Yul偏好白天工作", "importance": 0.8, "invalidated": False},
            {"id": "b", "text": "用户Yul偏好深夜编程", "importance": 0.9, "invalidated": False},
            {"id": "c", "text": "用户Yul用Python开发", "importance": 0.7, "invalidated": False},
            {"id": "d", "text": "用户Yul喜欢Rust",     "importance": 0.95, "invalidated": False},
        ]

    def test_ngram_overlap_high(self):
        # 完整重叠（相同文本）→ n-gram 完全一致，必然 ≥ 3
        new_text = "用户Yul偏好白天工作"
        conflicts = mf._detect_conflicts(new_text, self.facts)
        ids = {c["id"] for c in conflicts}
        self.assertIn("a", ids)

    def test_ngram_overlap_threshold(self):
        # 重叠 ≥ 3：两文本共享至少 3 个相同的 4-gram Chinese tokens
        # "用户Yul偏好白天工作" → Chinese: "用户偏好白天工作" → 4-grams: 用户偏, 户偏好, 偏好白, 好白天, 白天工, 天工作
        # "Yul偏好白天工作内容" → Chinese: "偏好白天工作内容" → 4-grams: 偏好白, 好白天, 白天工, 天工作内, 工作内容
        # 重叠 = "偏好白" + "好白天" + "白天工" + "天工作" = 4 个 → 触发
        old_text = "用户Yul偏好白天工作"
        new_text = "Yul偏好白天工作内容"
        facts = [{"id": "x", "text": old_text, "importance": 0.5, "invalidated": False}]
        conflicts = mf._detect_conflicts(new_text, facts)
        self.assertEqual(len(conflicts), 1)

    def test_ngram_overlap_low(self):
        # 重叠 < 3 → 不触发
        new_text = "Yul 今天天气很好"
        conflicts = mf._detect_conflicts(new_text, self.facts)
        self.assertEqual(len(conflicts), 0)

    def test_time_contradiction_day_vs_night(self):
        # 白天 vs 深夜 → 低 importance 失效
        conflicts = mf._detect_conflicts("用户Yul深夜加班", self.facts)
        ids = {c["id"] for c in conflicts}
        self.assertIn("a", ids)  # 白天工作 vs 深夜加班

    def test_lang_contradiction(self):
        # 中文 vs 英文 偏好冲突
        cn_fact = {"id": "e", "text": "用户Yul偏好英文沟通", "importance": 0.7, "invalidated": False}
        facts = [cn_fact]
        conflicts = mf._detect_conflicts("用户Yul偏好中文沟通", facts)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["id"], "e")

    def test_rust_vs_python(self):
        # 新事实引入 Rust（旧事实关于 Python，importance<0.9）→ 旧 Python 事实失效
        py_fact = {"id": "c", "text": "用户Yul用Python开发", "importance": 0.7, "invalidated": False}
        conflicts = mf._detect_conflicts("用户Yul转向Rust开发", [py_fact])
        ids = {c["id"] for c in conflicts}
        self.assertIn("c", ids)

    def test_rust_vs_python_high_imp_preserved(self):
        # 新事实引入 Rust（旧事实关于 Python，importance>=0.9）→ 保留
        py_fact = {"id": "c", "text": "用户Yul用Python开发", "importance": 0.9, "invalidated": False}
        conflicts = mf._detect_conflicts("用户Yul转向Rust开发", [py_fact])
        self.assertEqual(len(conflicts), 0)

    def test_already_invalidated_skip(self):
        # 已失效的事实不再参与检测
        conflicts = mf._detect_conflicts("Yul白天工作很专注", [{"id": "x", "text": "白天", "importance": 0.5, "invalidated": True}])
        self.assertEqual(len(conflicts), 0)


class TestTTLExpiration(unittest.TestCase):
    """测试 TTL 过期清理"""

    def test_expired_fact_marked(self):
        past = (datetime.now() - timedelta(days=1)).isoformat()
        facts = [
            {"id": "expired", "text": "临时任务", "importance": 0.5, "invalidated": False,
             "expires_at": past, "valid_days": 1, "category": "preference",  # preference 不被归档
             "created_at": "2026-04-01T00:00:00"},
        ]
        FAKE_JSON.write_text(json.dumps(facts))
        result = mf.cleanup_expired()
        self.assertEqual(result["cleaned"], 1)
        self.assertEqual(result["archived"], 0)
        data = json.loads(FAKE_JSON.read_text())
        self.assertTrue(data[0]["invalidated"])
        self.assertEqual(data[0]["invalidated_reason"], "TTL过期")

    def test_valid_fact_preserved(self):
        future = (datetime.now() + timedelta(days=30)).isoformat()
        facts = [
            {"id": "valid", "text": "永久偏好", "importance": 0.9, "invalidated": False,
             "expires_at": future, "valid_days": 365, "category": "preference"},
        ]
        FAKE_JSON.write_text(json.dumps(facts))
        result = mf.cleanup_expired()
        self.assertEqual(result["cleaned"], 0)
        data = json.loads(FAKE_JSON.read_text())
        self.assertFalse(data[0]["invalidated"])


class TestCategoryTTL(unittest.TestCase):
    """测试分类半衰期配置"""

    def test_default_ttl(self):
        self.assertEqual(mf._get_default_ttl("identity"), 365)
        self.assertEqual(mf._get_default_ttl("preference"), 90)
        self.assertEqual(mf._get_default_ttl("tool"), 90)
        self.assertEqual(mf._get_default_ttl("work"), 60)
        self.assertEqual(mf._get_default_ttl("thread"), 30)
        self.assertEqual(mf._get_default_ttl("unknown_cat"), 30)  # fallback


class TestCache(unittest.TestCase):
    """测试内存缓存层"""

    def test_cache_ttl_eviction(self):
        cache = mf.FactCache(ttl_seconds=1)
        cache.set(key="test", data=[{"id": "1"}])
        self.assertIsNotNone(cache.get("test"))
        time.sleep(1.2)
        self.assertIsNone(cache.get("test"))

    def test_cache_invalidate(self):
        cache = mf.FactCache(ttl_seconds=10)
        cache.set(key="x", data=[1, 2, 3])
        cache.invalidate("x")
        self.assertIsNone(cache.get("x"))

    def test_cache_stats(self):
        cache = mf.FactCache(ttl_seconds=10)
        cache.set(key="a", data=[1])
        cache.set(key="b", data=[2])
        s = cache.stats()
        self.assertEqual(s["total_slots"], 2)


class TestFeedbackLoop(unittest.TestCase):
    """测试用户反馈闭环"""

    def test_positive_feedback(self):
        facts = [
            {"id": "fb1", "text": "测试", "importance": 0.5, "invalidated": False,
             "access_count": 5, "valid_days": 30, "expires_at": "2099-01-01T00:00:00", "category": "test"},
        ]
        FAKE_JSON.write_text(json.dumps(facts))
        mf.feedback_adjust("fb1", +0.1)
        data = json.loads(FAKE_JSON.read_text())
        self.assertAlmostEqual(data[0]["importance"], 0.6, places=4)
        self.assertEqual(data[0]["access_count"], 8)  # +3 for positive

    def test_negative_feedback(self):
        facts = [
            {"id": "fb2", "text": "测试", "importance": 0.5, "invalidated": False,
             "access_count": 5, "valid_days": 30, "expires_at": "2099-01-01T00:00:00", "category": "test"},
        ]
        FAKE_JSON.write_text(json.dumps(facts))
        mf.feedback_adjust("fb2", -0.1)
        data = json.loads(FAKE_JSON.read_text())
        self.assertAlmostEqual(data[0]["importance"], 0.4, places=4)
        self.assertEqual(data[0]["access_count"], 6)  # +1 for negative

    def test_feedback_clamp(self):
        # 不超过 1.0
        facts = [{"id": "fb3", "text": "测试", "importance": 0.95, "invalidated": False,
                  "access_count": 0, "valid_days": 30, "expires_at": "2099-01-01T00:00:00", "category": "test"}]
        FAKE_JSON.write_text(json.dumps(facts))
        mf.feedback_adjust("fb3", +0.1)
        data = json.loads(FAKE_JSON.read_text())
        self.assertEqual(data[0]["importance"], 1.0)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMPDIR, ignore_errors=True)
