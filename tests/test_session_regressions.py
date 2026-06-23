# -*- coding: utf-8 -*-
"""本 session 多輪修正的『純函式回歸測試』——把當時用隔離腳本驗過的行為釘成永久測試，
防未來改動靜默回歸（機器守門優先於記性）。涵蓋：
  - absrisk._opt        CLI 參數長度守門（--ci 只給 1 值不可解包 crash）
  - build_report_data._doctype 背景表型態程式化回推（不依賴手填 doctype）

註：原 build_stage1_corpus._pid 去重鍵測試已於 2026-06 移除——該模組（含 _pid）在
EBM_Search v0.22（commit 40cf93c：取消 Stage A/B 切分、_stage1_corpus 交接契約）整支刪除，
無對應後繼函式可改測；保留死 import 會使整個 pytest 套件 collection error。
"""
import absrisk
import build_report_data as brd


# ── absrisk._opt：不足 n 個視為未提供（回 None），避免 lo,hi=sorted(...) ValueError ──
def test_opt_returns_none_when_fewer_than_n():
    assert absrisk._opt(["--ci", "0.6"], "--ci", 2) is None          # 只 1 值 → None
    assert absrisk._opt(["a", "--ci"], "--ci", 2) is None            # flag 當末參數 → None
    assert absrisk._opt(["a"], "--ci", 2) is None                    # 無 flag → None


def test_opt_returns_values_when_exactly_n():
    assert absrisk._opt(["--ci", "0.6", "0.9"], "--ci", 2) == ["0.6", "0.9"]
    assert absrisk._opt(["--dir", "harm"], "--dir", 1) == ["harm"]


# ── build_report_data._doctype：缺手填 doctype 時從 pubtypes/標題程式化回推 ──
def test_doctype_explicit_wins():
    assert brd._doctype({"doctype": "Guideline", "title": "whatever"}) == "Guideline"


def test_doctype_from_pubtypes():
    assert brd._doctype({"sources": {"pubmed": {"pubtypes": ["Meta-Analysis"]}}}) == "Meta-Analysis"


def test_doctype_from_title():
    assert brd._doctype({"title": "A Systematic Review of X"}) == "Systematic Review"
    assert brd._doctype({"input": {"title": "GOLD 2024 Guideline"}}) == "Guideline"


def test_doctype_plain_rct_not_misclassified():
    assert brd._doctype({"title": "A randomized controlled trial of X vs Y"}) is None
