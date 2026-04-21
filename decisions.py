#!/Users/yul/.hermes/hermes-agent/.venv/bin/python3
"""
Decision Ledger CLI — 架构决策追加工具
用法:
  python3 decisions.py add "决策标题" "决策内容" --status Accepted --date 2026-04-20
  python3 decisions.py list --status Open
  python3 decisions.py search "关键词"
"""
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime

DECISIONS_FILE = Path.home() / ".agent-memory" / "DECISIONS.md"

def parse_args():
    p = argparse.ArgumentParser(description="Decision Ledger CLI")
    sub = p.add_subparsers(dest="cmd")

    add = sub.add_parser("add", help="Add a new decision")
    add.add_argument("title", help="Decision title")
    add.add_argument("content", help="Decision content")
    add.add_argument("--status", default="Accepted", choices=["Accepted", "Rejected", "Superseded", "Open"])
    add.add_argument("--date", default=None)
    add.add_argument("--author", default="Yul")

    lst = sub.add_parser("list", help="List decisions")
    lst.add_argument("--status", default=None)

    sch = sub.add_parser("search", help="Search decisions")
    sch.add_argument("keyword", help="Search keyword")

    return p.parse_args()

def add_decision(title: str, content: str, status: str, date: str, author: str):
    DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    if not DECISIONS_FILE.exists():
        DECISIONS_FILE.write_text(
            "# DECISIONS — 架构决策日志（冷层）\n"
            "# 格式: ## DATE | Decision Title | Status: Accepted/Superseded/Rejected\n\n---\n"
        )

    lines = DECISIONS_FILE.read_text().splitlines()

    entry = [
        "---",
        f"## {date} | {title}",
        "",
        f"**状态**: {status}",
        f"**决策者**: {author}",
        "",
        content,
        ""
    ]

    lines.extend(entry)
    DECISIONS_FILE.write_text("\n".join(lines) + "\n")
    print(f"Added decision: {title}")

def list_decisions(status: str = None):
    if not DECISIONS_FILE.exists():
        print("No decisions file found.")
        return
    for line in DECISIONS_FILE.read_text().splitlines():
        if status and status not in line:
            continue
        if line.startswith("## "):
            print(line)

def search_decisions(keyword: str):
    if not DECISIONS_FILE.exists():
        print("No decisions file found.")
        return
    printing = False
    for line in DECISIONS_FILE.read_text().splitlines():
        if line.startswith("## ") and keyword.lower() in line.lower():
            printing = True
        elif line.startswith("## ") and printing:
            printing = False
        if printing or (line.startswith("## ") and keyword.lower() in line.lower()):
            print(line)

if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "add":
        add_decision(args.title, args.content, args.status, args.date, args.author)
    elif args.cmd == "list":
        list_decisions(args.status)
    elif args.cmd == "search":
        search_decisions(args.keyword)
    else:
        print("Unknown command. Use: add, list, or search")
