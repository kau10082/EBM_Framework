# -*- coding: utf-8 -*-
"""
study_type_classifier.py — 研究設計（文獻類型）判定共用模組
==========================================================
精確判『文獻類型/研究設計』：讀每篇 pubtype＋摘要，逐篇判實際設計。
"""
import re

def classify_study_type(pt_list, title, abstract):
    """
    根據 pubtype 清單、標題與摘要判定實際研究設計。
    :param pt_list: pubtype 的 list (如 ["Journal Article", "Review"])
    :param title: 標題字串
    :param abstract: 摘要字串
    :return: 判定後的類型字串
    """
    pt = " ".join(pt_list or []).lower()
    blob = (title or "") + " " + (abstract or "")
    
    def has(rx): return re.search(rx, blob, re.I)
    
    # 1) 間接比較/統合先判（NMA 常被掛 Review pubtype）
    if has(r"network meta|indirect treatment|indirect compar|matching[- ]adjusted|\bMAIC\b|mixed treatment compar"): return "間接比較/NMA"
    if ("meta-analysis" in pt and "systematic review" in pt): return "系統性回顧+統合分析"
    if "meta-analysis" in pt or has(r"\bmeta[- ]?analysis\b"): return "統合分析(MA)"
    if "systematic review" in pt or has(r"systematic review"): return "系統性回顧(SR)"
    
    # 2) pubtype 權威：RCT / 綜述 / 病例報告（pubtype 比摘要字眼可靠，先擋）
    if "randomized controlled trial" in pt or "controlled clinical trial" in pt: return "隨機對照試驗(RCT)"
    if "review" in pt and "systematic" not in pt: return "綜述"   # 敘述性綜述(如 Hillas 2020；勿因摘要含 real-world 字樣誤判)
    if "case reports" in pt: return "病例報告"
    
    # 3) 設計型訊號（摘要）：藥物警戒 / 事後分析 / 回溯·前瞻（先於『摘要-RCT』回退，避免回溯研究提及 randomized 被誤判）
    if has(r"disproportionalit|pharmacovigilance|\bFAERS\b|VigiBase|adverse event reporting system|signal detection"): return "藥物警戒/不成比例分析"
    if has(r"post[- ]?hoc|pooled analysis|secondary analysis of|individual patient data"): return "事後/匯總分析"
    if has(r"case series"): return "病例系列"
    if has(r"retrospective"): return "回溯性世代/觀察研究"
    if has(r"prospective"): return "前瞻性世代/觀察研究"
    
    # 4) 摘要-RCT 回退：須有自身隨機化證據、且非回溯/真實世界用語
    if has(r"randomi[sz]ed|double[- ]blind|placebo[- ]controlled") and not has(r"retrospective|real[- ]world|real[- ]life|chart review"): return "隨機對照試驗(RCT)"
    if has(r"cross[- ]sectional"): return "橫斷面研究"
    if has(r"\bregistry\b|registry-based|register\b"): return "登錄研究(registry)"
    if has(r"real[- ]world|real[- ]life|clinical practice|observational|\bcohort\b|chart review|medical records"): return "真實世界觀察研究"
    if "review" in pt or has(r"\breview\b|narrative"): return "綜述"
    
    return "原始研究(設計未明)"
