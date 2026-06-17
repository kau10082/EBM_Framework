# -*- coding: utf-8 -*-
"""build_report_data.validate：交叉檢核欄列舉守門（外部審查指出的契約漂移）。
xref_verify 會產出 VERIFIED/UNVERIFIED/PARTIAL/UNRESOLVED/OFF_TOPIC；
報告表只該出現前四者，OFF_TOPIC/RETRACTED 混入應被 validate 攔下、不得靜默放行。"""
import build_report_data as brd


def _core(xref):
    return {"studies": [{"study": "S", "reports": [["標題T", "111", "10.x/a", "線上", xref]]}],
            "background": [], "ongoing_trials": [["NCT1", "內容", "RECRUITING"]]}


def test_validate_accepts_partial_xref():
    assert not any("交叉檢核" in f for f in brd.validate(_core("PARTIAL")))


def test_validate_rejects_offtopic_xref():
    fails = brd.validate(_core("OFF_TOPIC"))
    assert any("交叉檢核非法" in f and "OFF_TOPIC" in f for f in fails)


def test_validate_rejects_bg_bad_xref():
    data = {"studies": [], "ongoing_trials": [["NCT1", "x", "RECRUITING"]],
            "background": [["標題", "222", "10.x/b", "Meta-Analysis", "線上", "TYPO_VERDICT"]]}
    assert any("背景檢核非法" in f for f in brd.validate(data))
