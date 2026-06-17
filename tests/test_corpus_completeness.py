# -*- coding: utf-8 -*-
"""Phase 0 納入完整性 gate：防樞紐試驗主報告被靜默漏掉（實測 ETHOS 32579807 案）。"""
import validate


def _corpus(papers):
    return {"review_question": {"statement": "", "P": "", "I": "", "C": "", "O": ["x"]}, "papers": papers}


def test_complete_study_passes():
    # 一個 Study：主報告(full)＋2 子報告(targeted)，互相 overlap_with → 應通過
    papers = [
        {"paper_id": "MAIN", "relevance": "direct", "role": "pivotal_efficacy",
         "grade_track": "full", "overlap_with": ["SUB1", "SUB2"]},
        {"paper_id": "SUB1", "relevance": "direct", "role": "supportive_secondary",
         "grade_track": "targeted_harms", "overlap_with": ["MAIN"]},
        {"paper_id": "SUB2", "relevance": "direct", "role": "safety",
         "grade_track": "targeted_harms", "overlap_with": ["MAIN"]},
    ]
    assert validate.check_p0_completeness(_corpus(papers)) == []


def test_missing_main_report_fails():
    # 重現 ETHOS bug：只有子報告群（互 overlap）、無 full 主報告 → 必 FAIL
    papers = [
        {"paper_id": "SUB1", "relevance": "direct", "role": "supportive_secondary",
         "grade_track": "targeted_harms", "overlap_with": ["SUB2", "SUB3"]},
        {"paper_id": "SUB2", "relevance": "direct", "role": "safety",
         "grade_track": "targeted_harms", "overlap_with": ["SUB1", "SUB3"]},
        {"paper_id": "SUB3", "relevance": "direct", "role": "supportive_secondary",
         "grade_track": "targeted_harms", "overlap_with": ["SUB1", "SUB2"]},
    ]
    fails = validate.check_p0_completeness(_corpus(papers))
    assert fails and "無 full-track 主報告" in fails[0]


def test_background_only_cluster_not_flagged():
    # 純背景群（無 direct）不該被誤擋
    papers = [
        {"paper_id": "BG1", "relevance": "background", "role": "meta_analysis",
         "grade_track": "light_summary", "overlap_with": ["BG2"]},
        {"paper_id": "BG2", "relevance": "background", "role": "meta_analysis",
         "grade_track": "light_summary", "overlap_with": ["BG1"]},
    ]
    assert validate.check_p0_completeness(_corpus(papers)) == []
