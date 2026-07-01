# -*- coding: utf-8 -*-
"""跨 session 修正的『純函式回歸測試』——把當時驗過的行為釘成永久測試，
防未來改動靜默回歸（機器守門優先於記性）。涵蓋：
  - absrisk._opt                     CLI 參數長度守門（--ci 只給 1 值不可解包 crash）
  - build_search_report_data.doctype_of  文獻類型由 design 桶回推（override 優先）

註：原 build_report_data._doctype 測試已隨該模組在 v0.22（commit 4254add）重寫為
build_search_report_data.doctype_of 而改寫；原 build_stage1_corpus._pid 測試已於
2026-06 隨 Stage A/B 廢除移除。保留死 import 會使整個 pytest 套件 collection error。
"""
import absrisk
import build_search_report_data as brd


# ── absrisk._opt：不足 n 個視為未提供（回 None），避免 lo,hi=sorted(...) ValueError ──
def test_opt_returns_none_when_fewer_than_n():
    assert absrisk._opt(["--ci", "0.6"], "--ci", 2) is None          # 只 1 值 → None
    assert absrisk._opt(["a", "--ci"], "--ci", 2) is None            # flag 當末參數 → None
    assert absrisk._opt(["a"], "--ci", 2) is None                    # 無 flag → None


def test_opt_returns_values_when_exactly_n():
    assert absrisk._opt(["--ci", "0.6", "0.9"], "--ci", 2) == ["0.6", "0.9"]
    assert absrisk._opt(["--dir", "harm"], "--dir", 1) == ["harm"]


# ── build_search_report_data.doctype_of：design 桶 → 文獻類型標籤；override（手填 doctype）優先 ──
def test_doctype_override_wins():
    assert brd.doctype_of("SR/MA/NMA/ITC", "Guideline") == "Guideline"


def test_doctype_from_design():
    assert brd.doctype_of("SR/MA/NMA/ITC") == "NMA/MA"
    assert brd.doctype_of("背景:會議摘要(待評估)") == "會議摘要"
    assert brd.doctype_of("指引") == "指引"


def test_doctype_unknown_falls_back():
    assert brd.doctype_of("") == "研究"
    assert brd.doctype_of(None) == "研究"
