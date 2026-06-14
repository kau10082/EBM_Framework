---
id: phase00_triage
title: 第〇階段 — 回顧問題 + corpus 相關性/角色分流
input: 所有輸入文獻（標題＋摘要/全文）
output_schema: schema/phase0_corpus.json
output: cache/_corpus.json
guardrails: [overlap_indirect]
---

## 為什麼要先做這一步
GRADE 是「針對某個 review question 的某個 outcome」評定確定性。沒有問題就無法判間接性、無法選 outcome、統合沒有錨點。
而且一批文獻通常**不是同質**的——有樞紐療效 RCT、有 MA、也有機制/PK/健康受試者/綜述。**把機制或 PK 研究丟進「GRADE 療效分級」是範疇錯誤。** 故須先分流。

## 步驟
0. **（若有 EBM_Search 交接包）先匯入預填**：若本批來自 EBM_Search（指向含 `_corpus_seed.json` 的資料夾，或使用者回「繼續」接力）→ 先跑 `python tools/ingest_seed.py --seed-dir "<交接包資料夾>"`：把全文 PDF 複製進 `inputs/`、產出**預填草稿** `cache/_corpus.draft.json`（review question 雛形＋每篇 relevance/role/grade_track 建議值＋同試驗 overlap_with）。下面第 1–4 步**改為「覆核並修正草稿」**而非從零建。映射規則見 `..\INTEGRATION.md`。草稿經使用者確認後存成 `cache/_corpus.json`。**注意：EBM_Search 不以結果(O)為軸，草稿的 review_question.O 是佔位，必須在此補定。**
1. **定 review question（PICO）**：和使用者確認；不確定時依 corpus 主題提出並標「待確認」。（接力時：以草稿 review_question 為起點覆核，補定 O 軸。）
   > **★ O 軸＝先讀文獻盤點『所有實測結局』再讓使用者勾選(鐵律,v0.20.1):** **嚴禁憑記憶/常識列部分結局**。補定 O 軸前**務必先讀 full-track 研究的可讀全文**(本機 PDF／PMC fullTextXML／ai_synthesis＋登錄結果),把**每個試驗主要/次要終點＋安全性結局全部抽出來、去重彙整成完整清單**(含益與害、含特異性 AE、含次要如『延後惡化＝首次惡化時間』),逐項標「哪些試驗測、是主要還是次要、測量工具/時點」,**攤給使用者選 critical/important**。再依 GRADE/Cochrane 收斂 `outcomes_prioritized`(≤7、至少一益一害、**不放替代/中間指標如生化 biomarker、未達 MCID 的生理替代**、優先放病人重要結局與特異性治療負擔)。實測教訓:曾憑記憶漏掉 WILLOW/AIRLEAF 的『主要終點＝延後惡化』,使用者糾正;讀文獻盤點才完整。
2. **逐篇判定**：
   - `relevance`：direct（直接回答問題）／indirect（相關但間接，如不同藥物/族群）／background（機制/PK/不直接評療效）／excluded（與問題無關）。
   - `role`：pivotal_efficacy／meta_analysis／safety／supportive_secondary（樞紐試驗的次分析/子群）／mechanism_pd／pharmacokinetic／narrative_review／other。
   - `grade_track`：
     - **full**＝跑完整 Phase 1–4（樞紐療效 RCT、MA）
     - **targeted_harms**＝只評 harms（安全性子研究）
     - **light_summary**＝背景摘要、不做 GRADE（機制/PK/healthy/綜述）
     - **none**＝排除
3. **MA 記 `included_trials`**：讀出每篇 meta-analysis 納入了哪些原始試驗（供統合去重）。
4. **標 `overlap_with`**：同一試驗的次分析/子群/區域分析互相標注，避免被當獨立證據重複計入。

## 輸出
`cache/_corpus.json`（符合 schema/phase0_corpus.json）。之後 Phase 1–4 只對 `grade_track ∈ {full, targeted_harms}` 的文獻執行；light_summary 另出背景清單。（接力時：覆核確認後由 `cache/_corpus.draft.json` 定稿為 `cache/_corpus.json`。）

## 斷點
分流完成後**摘要給使用者、確認 review question 與分流正確**，才進 Phase 1。
