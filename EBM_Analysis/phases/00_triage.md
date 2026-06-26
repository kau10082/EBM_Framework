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

　**★ 範圍由 `tools/analysis_scope.py` 確定性算出（鐵律,2026-06 使用者糾正『只匯入/只補進入分析的那幾篇』）：** 分流定稿後跑 `python tools/analysis_scope.py`，得三份清單：**`analysis_set`**＝實際進入分析者（`grade_track ∈ {full, targeted_harms}`）；**`need_manual_fulltext`**＝分析集中『全文尚未取得』且為**分析錨點**者（full 的 `is_primary_report` 每 Study 一篇 ＋ targeted_harms 真害結果研究）；**`optional_fulltext`**＝同 Study 的次級/overlap 報告（congress/cost/子分析，補了不增進核心 GRADE）。**前提**：Phase 0 須對每個核心 Study 標一篇 `is_primary_report:true`（主要療效報告＝分析全文錨點）。

5. **人工補全文（authoritative pass，本階段才做；範圍＝`need_manual_fulltext`）**：對 `need_manual_fulltext` 逐篇確認『我(Claude)線上讀得到全文』——順序 本機 `inputs/` PDF → PMC `fullTextXML` → `tools/unpaywall.py`（Unpaywall 全部 `oa_locations`）。仍取不到者，**實際建立**本機補全文資料夾（由 `analysis_scope._supplement_dir` 解析：優先 `run_state.paths.fulltext_dir`〔交接包所在 per-topic 夾〕→ 次 `config/settings.yaml` 的 **`report.fulltext_dir`**`/<slug>` → 留空回退 `<work>/inputs/_fulltext_supplement/`）並寫出實體 `需補全文清單.txt`（逐筆：標題／DOI／PMID／建議檔名＝DOI 去斜線或 PMID／為何需要），請使用者把缺的 PDF 放進去；完成後重新掃描、更新 `fulltext_status`（人工補入＝`have(manual)`）。**只補 `need_manual_fulltext`（每 Study 主報告＋真 harms）即可增進分析；`optional_fulltext` 次級報告不強求補**（分析以主報告全文為錨點，其餘當 overlap）。**為何移到此**：最終評讀哪幾篇要到 Phase 0 分流定稿才確定（如 SUNSET/WISDOM 退階試驗最後只當背景就不必補），故補全文以此處 `grade_track`＋`is_primary_report` 為準，避免白補。
   > **★ 補/掃全文後、進 Phase 1 抽取前，必跑 `python tools/fulltext_title_audit.py`（鐵律,2026-06 使用者糾正而立）：** 稽核**每篇 base 的本機全文實際內容是否就是該 paper_id 那篇**（讀首頁標題與 corpus title 比對；別篇標題佔據開頭＝內容放錯 paper_id → 🔴 mismatch）。這是 EBM_Search ⑤a `doi_title_audit`（DOI↔title）在**分析端的對稱守門（內容↔title）**——實測 base「updated NMA」的 inputs 全文其實是另一篇 Edris「SR & NMA」的誤存、會靜默進抽取。**有 🔴 mismatch 者嚴禁進 Phase 1**，須換成正確全文或修正 paper_id；🟡 unverifiable（多為 .txt 被截掉封面、標題缺如）至少人工抽查一次。`selftest_analysis_guards.py` 已含此守門回歸。
6. **匯入 Zotero（authoritative pass，本階段才做；範圍＝`analysis_set`）**：分流（含補全文）定稿後，**問使用者「是否把進入分析的文獻匯入 Zotero？」**（未明確同意不匯；同意先 dry-run 顯示 payload 再 `--commit`）。**匯入範圍＝`analysis_scope.analysis_set`（＝`grade_track ∈ {full, targeted_harms}`，即實際進入分析者），不匯背景 light_summary**（背景留在 `_corpus.json`／報告／交接包；使用者另要求時 `--include-background` 才併入）。每篇標 `grade_track:<full/targeted_harms>`、`role:<…>`、同試驗共用 `study:<試驗名>`、主報告另標 `primary`，使 Zotero 子集與分析一致。**為何移到此＋為何只匯分析集**：Zotero 是「實際分析清單」的鏡像，須以 Phase 0 定稿分流為準；只匯進入分析者可免把數百篇背景灌進 Zotero（使用者 2026-06 指定）。

## 輸出
`cache/_corpus.json`（符合 schema/phase0_corpus.json；每核心 Study 標一篇 `is_primary_report`）。之後 Phase 1–4 只對 `grade_track ∈ {full, targeted_harms}` 的文獻執行；light_summary 另出背景清單。（接力時：覆核確認後由 `cache/_corpus.draft.json` 定稿為 `cache/_corpus.json`。）補全文（步驟 5，範圍＝`need_manual_fulltext`）與 Zotero 匯入（步驟 6，範圍＝`analysis_set`）皆由 `tools/analysis_scope.py` 確定性算範圍。

## 斷點
分流完成後**摘要給使用者、確認 review question 與分流正確**，才進補全文（步驟 5）與 Zotero 匯入（步驟 6）；三者都確認後才進 Phase 1。**手機/遠端可暫時跳過步驟 5、6 的實際執行**（補全文需放 PDF、Zotero 需確認匯入），但範圍清單仍由 `analysis_scope.py` 算好備查，回桌機再執行。
