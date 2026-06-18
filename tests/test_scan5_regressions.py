# -*- coding: utf-8 -*-
"""第五輪自掃修正的回歸測試（機器守門優先於記性）：
  - fulltext_audit.audit   Unpaywall 查詢失敗不可靜默放行（要記成 fail）
  - selfcheck_consistency  SoF outcome 為 None 時不可 crash（否則真違規被偽裝成環境錯誤）
  - funnel_check._safe_eval 前導零數字（007）不可因 eval SyntaxError 被靜默跳過
"""
import sys
import types
import funnel_check as fc
import selfcheck_consistency as sc


# ── fulltext_audit：Unpaywall 查不成 → gate 記 fail（不可當「非 OA」放行）──
def _audit_with_fake_lookup(lookup_fn, papers):
    sys.modules["unpaywall"] = types.SimpleNamespace(lookup=lookup_fn)
    import importlib
    fa = importlib.import_module("fulltext_audit")
    return fa.audit(papers, sleep=0)


def test_audit_unverifiable_when_lookup_fails():
    fails, _ = _audit_with_fake_lookup(lambda doi: {}, [{"fulltext_channel": "none", "doi": "10.x/a"}])
    assert any("未成功" in f for f in fails)            # 查失敗 → 記 fail，不放行


def test_audit_no_false_fail_when_genuinely_not_oa():
    fails, _ = _audit_with_fake_lookup(lambda doi: {"is_oa": False}, [{"fulltext_channel": "none", "doi": "10.x/b"}])
    assert fails == []                                   # 查成功-非OA → 不誤報


# ── selfcheck：outcome 為 None（present-but-None）不可 crash ──
def test_selfcheck_outcome_none_does_not_crash():
    cases = [
        {"sof": [{"outcome": None, "relative_effect": "合併 RR 0.70"}], "rob_summary": [], "publication_bias": "廠商 發表偏誤"},
        {"sof": [{"outcome": None, "relative_effect": "RR 0.7", "absolute_effect": "NNTB 20"}]},
        {"sof": [{"outcome": None}], "body_of_evidence": [{"outcome": None, "certainty": "low"}]},
    ]
    for c in cases:
        sc.check(c)   # 不可拋例外


def test_selfcheck_c3_still_flags_with_none_outcome():
    f = sc.check({"sof": [{"outcome": None, "relative_effect": "合併 RR 0.70"}],
                  "rob_summary": [], "publication_bias": "廠商 發表偏誤"})
    assert any(x.startswith("C3") for x in f)            # outcome=None 不影響 C3 真違規仍被抓


# ── funnel_check：前導零不可靜默跳過 ──
def test_funnel_leading_zero_evaluated():
    assert fc._safe_eval("007") == 7
    assert fc._safe_eval("120+007") == 127
    assert fc.check({"funnel": [{"change": "【007=7】"}]}, min_exprs=1) == []   # 正確算式不報錯、有被核
