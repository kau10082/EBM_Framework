# -*- coding: utf-8 -*-
"""本 session 多輪修正的『純函式回歸測試』——把當時用隔離腳本驗過的行為釘成永久測試，
防未來改動靜默回歸（機器守門優先於記性）。涵蓋：
  - absrisk._opt        CLI 參數長度守門（--ci 只給 1 值不可解包 crash）
  - build_stage1_corpus._pid   去重 key 去坍縮＋跨檔穩定
  - build_report_data._doctype 背景表型態程式化回推（不依賴手填 doctype）
"""
import absrisk
import build_stage1_corpus as bsc
import build_report_data as brd


# ── absrisk._opt：不足 n 個視為未提供（回 None），避免 lo,hi=sorted(...) ValueError ──
def test_opt_returns_none_when_fewer_than_n():
    assert absrisk._opt(["--ci", "0.6"], "--ci", 2) is None          # 只 1 值 → None
    assert absrisk._opt(["a", "--ci"], "--ci", 2) is None            # flag 當末參數 → None
    assert absrisk._opt(["a"], "--ci", 2) is None                    # 無 flag → None


def test_opt_returns_values_when_exactly_n():
    assert absrisk._opt(["--ci", "0.6", "0.9"], "--ci", 2) == ["0.6", "0.9"]
    assert absrisk._opt(["--dir", "harm"], "--dir", 1) == ["harm"]


# ── build_stage1_corpus._pid：穩定唯一鍵，無 ID 不得坍縮、跨檔須一致 ──
def test_pid_priority_pmid_doi_uid():
    assert bsc._pid({"pmid": "123"}) == "PMID123"
    assert bsc._pid({"doi": "10.1/AB cd"}).startswith("DOI10.1_AB")   # 非 \w.- 轉底線
    assert bsc._pid({"uid": "u9"}) == "UIDu9"


def test_pid_no_id_does_not_collapse():
    a = bsc._pid({"title": "Trial A of X vs Y"})
    b = bsc._pid({"title": "Trial B of P vs Q"})
    assert a != b and a.startswith("H") and b.startswith("H")        # 不同標題 → 不同鍵、不坍縮


def test_pid_no_id_cross_file_stable():
    # 同一篇在不同 cache 檔可能帶不同狀態欄位（class/verdict），雜湊須只看標題、跨檔一致
    content_side = {"title": "A Trial of X vs Y", "class": "有全文", "verdict": "candidate"}
    awaiting_side = {"title": "A Trial of X vs Y", "verdict": "待人工補全文", "channels_exhausted": True}
    assert bsc._pid(content_side) == bsc._pid(awaiting_side)


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
