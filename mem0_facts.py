#!/usr/bin/env python3
"""MemFree CLI — entry point (imports from src.facts)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from facts import main
if __name__ == "__main__":
    main()
