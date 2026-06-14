# -*- coding: utf-8 -*-
"""pytest 共用設定：把工具目錄加進 sys.path，讓測試可直接 import 各工具。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "EBM_Analysis" / "tools", ROOT / "EBM_Search" / "scripts"):
    sys.path.insert(0, str(p))
