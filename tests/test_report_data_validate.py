# -*- coding: utf-8 -*-
"""build_search_report_data.validate：交叉檢核欄列舉守門（外部審查指出的契約漂移）。
xref_verify 會產出 VERIFIED/UNVERIFIED/PARTIAL/UNRESOLVED/OFF_TOPIC；
報告表只該出現前四者，OFF_TOPIC/RETRACTED 混入應被 validate 攔下、不得靜默放行。
（2026-06 v0.22 重寫曾把本守門整個弄丟、測試又 import 舊模組名而 collection error——本檔釘住新實作。）"""
import build_search_report_data as brd


def _data(xref):
    return {"title": "T", "search_date": "2026-06-24", "params": {}, "search_strings": [],
            "flow": [], "included": [{"title": "標題T", "pmid": "111", "doi": "10.x/a", "verify": xref}]}


def test_validate_accepts_partial_xref():
    assert not any("交叉檢核" in f for f in brd.validate(_data("PARTIAL")))


def test_validate_accepts_verified_with_tag():
    assert not any("交叉檢核" in f for f in brd.validate(_data("VERIFIED (PubMed+Crossref)")))


def test_validate_rejects_offtopic_xref():
    fails = brd.validate(_data("OFF_TOPIC"))
    assert any("交叉檢核非法" in f and "OFF_TOPIC" in f for f in fails)


def test_validate_rejects_retracted_xref():
    assert any("交叉檢核非法" in f for f in brd.validate(_data("RETRACTED")))


def test_validate_rejects_blank_search_date():
    d = _data("PARTIAL"); d["search_date"] = ""
    assert any("search_date" in f for f in brd.validate(d))
