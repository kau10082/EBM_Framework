# -*- coding: utf-8 -*-
"""prisma_audit 純邏輯測試：27 項齊全→無 FAIL；缺維度→對應項 FAIL；MANUAL/ATTEST/PENDING 行為。"""
import prisma_audit as pa


def _full_search():
    return {
        "title": "DPP-1 抑制劑於支氣管擴張症之系統性回顧",
        "topic": "bronchiectasis DPP-1",
        "search_date": "2026-06-14",
        "conjunction_axes": "(DPP-1 抑制劑) AND (支氣管擴張症)",
        "axes": ["藥物軸：brensocatib OR DPP-1 ...", "疾病軸：bronchiectasis OR ..."],
        "method_notes": ["六腿：PubMed、Crossref、Consensus、ClinicalTrials.gov、Europe PMC、OpenAlex"],
        "narrative": [["廣蒐", "四軸展開六腿檢索"]],
        "background": [["背景 MA", "10.x", "MA", "有全文"]],
        "funnel": [
            {"step": "撈得", "change": "n=320", "remain": "320"},
            {"step": "去重", "change": "-80", "remain": "240"},
            {"step": "初篩排除", "change": "-200（理由：離題）", "remain": "40"},
            {"step": "納入", "change": "", "remain": "4"},
        ],
        "funnel_closure": "排除 200 篇，理由：核心軸離題。",
    }


def _full_synth():
    return {
        "report_title": "系統性回顧",
        "bottom_line": ["要點一", "要點二"],
        "clinical_one_liner": "臨床一句話。",
        "consistency": "效應估計收斂。",
        "vote_counting_check": "三層可取性檢核。",
        "weight_adjudication": "依 GRADE/RoB 裁量。",
        "conflict_analysis": "無重大衝突。",
        "study_characteristics": [{"trial": "T1", "drug": "d", "phase": "3", "n": "100",
                                   "dose": "x", "duration": "y", "comparator": "安慰劑", "primary_outcome": "惡化率"}],
        "rob_summary": [{"trial": "T1", "randomization": "low", "deviations": "low", "missing_data": "low",
                         "measurement": "low", "selective_reporting": "low", "overall": "low"}],
        "publication_bias": "研究數<10 不畫漏斗圖，改以註冊比對。",
        "missing_evidence_sensitivity": "假設未發表為 null 不翻轉。",
        "subgroup_implications": "依嚴重度分層；未來試驗應事前指定族群。",
        "limitations": ["樣本量有限；缺頭對頭比較（缺口：不同族群與比較）。"],
        "body_of_evidence": [{"outcome": "惡化率", "certainty": "moderate", "basis": "跨研究"}],
        "sof": [
            {"outcome": "年化惡化率", "assumed_control_risk": "1.5/年", "corresponding_risk": "0.9/年",
             "absolute_effect": "率差 -0.6/人年", "relative_effect": "RR 0.6 (95% CI 0.5–0.7)",
             "n_participants_studies": "400 (2)", "certainty": "moderate"},
            {"outcome": "全因死亡", "assumed_control_risk": "1%", "corresponding_risk": "1%",
             "absolute_effect": "風險差 0 個百分點", "relative_effect": "RR 1.0 (95% CI 0.5–2.0)",
             "n_participants_studies": "400 (2)", "certainty": "low"},
            {"outcome": "嚴重不良事件 SAE", "assumed_control_risk": "5%", "corresponding_risk": "5%",
             "absolute_effect": "風險差 0 個百分點", "relative_effect": "RR 1.0 (95% CI 0.6–1.6)",
             "n_participants_studies": "400 (2)", "certainty": "low"},
        ],
    }


def _by_id(rows):
    return {r["id"]: r for r in rows}


def test_full_artifacts_no_fail():
    rows = pa.audit(_full_search(), _full_synth(), per_paper=[{"paper_id": "p1"}], artifacts_present=True)
    assert len(rows) == 27
    assert pa.fails_of(rows) == []


def test_manual_items_present_but_not_blocking():
    rows = pa.audit(_full_search(), _full_synth(), per_paper=[{"paper_id": "p1"}], artifacts_present=True)
    d = _by_id(rows)
    # 24/25/26 無聲明→MANUAL；不進預設 fails
    assert d["24"]["status"] == "MANUAL" and d["25"]["status"] == "MANUAL" and d["26"]["status"] == "MANUAL"
    assert pa.fails_of(rows) == []
    # strict 下→計失敗
    assert any("項24" in f for f in pa.fails_of(rows, strict=True))


def test_attestation_flips_manual_to_attest():
    syn = _full_synth()
    syn["prisma_attest"] = {"9": "單一評讀者（Claude）抽取、逐篇二次重讀",
                            "24": "未事前於 PROSPERO 註冊；PICO 見檢索報告",
                            "25": "無外部經費", "26": "評讀者無利益衝突",
                            "27": "結構化 cache JSON＋checklist 可得"}
    rows = pa.audit(_full_search(), syn, per_paper=[{"p": 1}], artifacts_present=True)
    d = _by_id(rows)
    assert d["24"]["status"] == "ATTEST" and d["25"]["status"] == "ATTEST" and d["26"]["status"] == "ATTEST"
    assert pa.fails_of(rows, strict=True) == []


def test_missing_search_strategy_fails_item7():
    s = _full_search(); s["axes"] = []
    rows = pa.audit(s, _full_synth())
    assert _by_id(rows)["7"]["status"] == "FAIL"
    assert any("項7" in f for f in pa.fails_of(rows))


def test_missing_sof_fails_effect_and_certainty():
    syn = _full_synth(); syn["sof"] = []; syn["body_of_evidence"] = []
    rows = pa.audit(_full_search(), syn)
    d = _by_id(rows)
    assert d["12"]["status"] == "FAIL"   # 效應量測度
    assert d["22"]["status"] == "FAIL"   # 確定性結果


def test_vague_implications_fail_item23():
    syn = _full_synth()
    syn["limitations"] = ["需要更多研究。"]
    syn["subgroup_implications"] = None
    rows = pa.audit(_full_search(), syn, per_paper=[{"p": 1}])
    assert _by_id(rows)["23"]["status"] == "FAIL"


def test_synth_absent_yields_pending_not_fail():
    rows = pa.audit(_full_search(), {})   # 只跑完檢索
    d = _by_id(rows)
    assert d["11"]["status"] == "PENDING" and d["20"]["status"] == "PENDING"
    # 檢索側自動項仍可 PASS、且不因評讀未做而 FAIL
    assert d["7"]["status"] == "PASS"
    assert pa.fails_of(rows) == []


def test_item27_availability_by_artifacts():
    rows_no = pa.audit(_full_search(), _full_synth(), artifacts_present=False)
    rows_yes = pa.audit(_full_search(), _full_synth(), artifacts_present=True)
    assert _by_id(rows_no)["27"]["status"] == "MANUAL"
    assert _by_id(rows_yes)["27"]["status"] == "PASS"
