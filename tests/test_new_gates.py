# -*- coding: utf-8 -*-
"""新增四道反飄移/反幻覺 gate 的純邏輯測試：funnel 算式、selfcheck C15、render V6 parity、fulltext_audit。"""
import funnel_check, selfcheck_consistency as sc, render_smoketest as rs


# ── funnel_check：流程圖數字逐關閉合 ──
def _funnel(*changes):
    return {"funnel": [{"step": f"s{i}", "change": c, "remain": ""} for i, c in enumerate(changes)],
            "funnel_closure": ""}


def test_funnel_ok():
    d = _funnel("【357 − 172 = 185】", "【129+45+11=185】", "【30+5+80=115】")
    assert funnel_check.check(d) == []


def test_funnel_bad_arithmetic():
    d = _funnel("【357 − 172 = 185】", "【129+45+11=186】", "【30+5+80=115】")  # 186 錯
    fails = funnel_check.check(d)
    assert any("不成立" in f and "186" in f for f in fails)


def test_funnel_too_few_exprs():
    d = _funnel("初篩剔 172，尚餘 185")  # 裸數字、無算式
    fails = funnel_check.check(d)
    assert any("算式不足" in f for f in fails)


def test_funnel_fullwidth_minus():
    d = _funnel("【357－172＝185】", "【129＋45＋11＝185】", "【30＋5＋80＝115】")  # 全形運算子
    assert funnel_check.check(d) == []


# ── selfcheck C15：SoF 受試者數一致性 ──
def _syn(sof):
    return {"sof": sof, "rob_summary": [], "publication_bias": "廠商資助 發表偏誤"}


def test_c15_consistent_n_passes():
    sof = [{"outcome": "年化惡化率", "n_participants_studies": "2,525（4 RCT，隨機）",
            "relative_effect": "率比 0.79", "absolute_effect": "率差", "certainty": "moderate",
            "assumed_control_risk": "1.29/人年", "corresponding_risk": "1.02/人年"},
           {"outcome": "全因死亡", "n_participants_studies": "2,525（4 RCT，隨機）",
            "relative_effect": "x", "absolute_effect": "y", "certainty": "low",
            "assumed_control_risk": "1.2%", "corresponding_risk": "0.6%"}]
    assert not any(f.startswith("C15") for f in sc.check(_syn(sof)))


def test_c15_inconsistent_n_fails():
    sof = [{"outcome": "年化惡化率", "n_participants_studies": "2,523（4 RCT）",
            "relative_effect": "率比 0.79", "absolute_effect": "x", "certainty": "moderate",
            "assumed_control_risk": "a", "corresponding_risk": "b"},
           {"outcome": "全因死亡", "n_participants_studies": "2,525（4 RCT）",
            "relative_effect": "x", "absolute_effect": "y", "certainty": "low",
            "assumed_control_risk": "a", "corresponding_risk": "b"}]
    assert any(f.startswith("C15") for f in sc.check(_syn(sof)))


def test_c15_subcomparison_exempt():
    # 子比較列(含『＋』兩臂和)不算跨-RCT 合併，不應觸發 C15
    sof = [{"outcome": "年化惡化率", "n_participants_studies": "2,525（4 RCT，隨機）",
            "relative_effect": "率比 0.79", "absolute_effect": "x", "certainty": "moderate",
            "assumed_control_risk": "a", "corresponding_risk": "b"},
           {"outcome": "過度角化", "n_participants_studies": "1,138（ASPEN 25mg 575＋安慰劑 563）",
            "relative_effect": "RR 4.25", "absolute_effect": "NNTH 44（95% CI 12 到 325）", "certainty": "moderate",
            "assumed_control_risk": "0.7%", "corresponding_risk": "3.0%"}]
    assert not any(f.startswith("C15") for f in sc.check(_syn(sof)))


# ── render_smoketest V6：渲染器一致性（資料有、PDF 漏渲） ──
def _gdata():
    return {"sof": [{"outcome": "全因死亡"}, {"outcome": "嚴重不良事件 SAE"}],
            "clinical_one_liner": "DPP-1 抑制劑作為附加療法以中等確定性降低肺惡化、不增死亡"}


GOOD_TXT = "1. 一節\n2. 二節\n全因死亡 嚴重不良事件 SAE 給臨床的一句話 DPP-1抑制劑作為附加療法以中等確定性降低肺惡化、不增死亡"


def test_v6_one_liner_present_ok():
    assert not any("V6" in f for f in rs.checks_on(GOOD_TXT, _gdata()))


def test_v6_one_liner_missing_detected():
    txt = "1. 一節\n2. 二節\n全因死亡 嚴重不良事件 SAE"  # 漏渲 clinical_one_liner
    fails = rs.checks_on(txt, _gdata())
    assert any("V6" in f and "clinical_one_liner" in f for f in fails)


# ── selfcheck.warnings：plain_summary 缺漏 soft warn（非阻擋） ──
def test_warn_missing_plain_summary():
    assert any("plain_summary" in w for w in sc.warnings({"sof": [{"outcome": "死亡"}]}))


def test_no_warn_when_plain_summary_present():
    assert sc.warnings({"sof": [{"outcome": "死亡"}], "plain_summary": "白話總結"}) == []


# ── fulltext_audit：純邏輯（不連網時退化為載入失敗或無 DOI 跳過） ──
def test_fulltext_audit_skips_have():
    import fulltext_audit
    # 已判有全文者不檢查；無 DOI 者跳過 → 不應因這兩類產生 fails（除非 unpaywall 模組缺）
    papers = [{"fulltext_channel": "local", "doi": "10.x/a"},
              {"fulltext_channel": "ai_synthesis", "doi": None}]
    fails, missed = fulltext_audit.audit(papers)
    assert missed == []


def _rob(overall, note, **dom):
    base = {"trial": "T", "randomization": "low", "deviations": "low", "missing_data": "low",
            "measurement": "low", "selective_reporting": "low", "overall": overall, "note": note}
    base.update(dom)
    return base


def test_c16_rob_concern_needs_note():
    fails = sc.check({"rob_summary": [_rob("some concerns", "", missing_data="some concerns")]})
    assert any(f.startswith("C16") for f in fails)
    ok = sc.check({"rob_summary": [_rob("low", "")]})
    assert not any(f.startswith("C16") for f in ok)
