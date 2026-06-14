---
id: phase01_extract
title: 第一階段 — 結構化數據提取 (PICO & N)
input: 單篇文獻全文（PDF 抽取之純文字）
output_schema: schema/phase1_extract.json
guardrails: [data_honesty, outcome_nature, extraction_conventions, registry_backfill]
---

## 目標
從單篇文獻的《Methods》與《Results》抽取結構化錨點，作為後續分級依據。**只抽取、不評斷。**

## 步驟
0. **標 `data_source`**（full_text／registry_results／regulatory_doc／abstract／ai_synthesis）。若來源僅摘要/AI 合成、或缺 RoB/各臂N/AE/CI → **先套用 [registry_backfill] 補救**（查 ClinicalTrials.gov API、PROSPERO、FDA/EMA），補來源於 source_locators 分列。
1. 套用 [data_honesty]：未明確標註的數值（I^2、ITT、N…）一律標 `[Not Stated in Source]`，嚴禁推估。PICO 任一核心要素缺漏 → 該項標 ⚠️ 資料缺漏。
2. 判定研究設計：SR-MA / RCT / NRSI / case-report / other；RCT/原始研究確認是否「多中心」。
3. 抽取 PICO 錨點：
   - P：研究對象與收納條件
   - I：介入藥物／處置（名稱、劑量、頻率、療程）
   - C：對照（Placebo／Standard of Care）
   - O：主要與次要終點 → 對每個 outcome 套用 [outcome_nature]，標記「臨床／病人重要」或「替代／中間 (surrogate)」
4. 抽取 N（總樣本）。
5. 若有 Forest Plot → 優先抽取其總結效應值與 I^2。
6. 套用 [extraction_conventions]：多臂/劑量、效應量選擇、AE 粒度、方向標準化、階層檢定註記、補齊常漏 outcome——全 corpus 一致。

## 後置 — 抽取驗證（**真做、不可自填 ok**）
逐筆把抽出的關鍵數字（N、主要效應量與 CI）**回原文找到逐字片段**，填入 `source_locators[].quote`（schema 強制 ≥1 筆且每筆含 quote）。`extraction_validation.method` 須寫明「如何驗證」、status=ok/needs_review；對不上即 `needs_review`，不靜默納入。
- 完整模式：`python tools/validate.py p1 cache/{paper}.p1.json` 確認結構齊全。
- ⚠️ 純文字抽取會打散表格/圖；只在圖表、文字讀不出者一律 `[Not Stated in Source]`，不得臆測。
