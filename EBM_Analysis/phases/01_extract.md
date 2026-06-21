---
id: phase01_extract
title: 第一階段 — 結構化數據提取 (PICO & N)
input: 單篇文獻全文（PDF 抽取之純文字）
output_schema: schema/phase1_extract.json
guardrails: [fulltext_authoritative, data_honesty, outcome_nature, extraction_conventions, registry_backfill]
---

## 目標
從單篇文獻的《Methods》與《Results》抽取結構化錨點，作為後續分級依據。**只抽取、不評斷。**

> **★ 分析階段一切以『全文』為準（鐵律,2026-06 使用者糾正；機器強制 `tools/fulltext_gate.py`）：** 到了評讀階段，**抽取一律以全文資訊為準**；摘要、登錄庫數字、AI 合成摘要都是二手/不完整來源，**只有在『各種管道都真的無法閱讀全文』時才退用**。抽取前**必先逐一實試全文管道並把結果記進 `fulltext_attempts`**：①本機 `inputs/` PDF（`local_pdf`）→ ②PMC `fullTextXML`（`pmc_fulltextxml`）→ ③Unpaywall 全部 `oa_locations`（`unpaywall_oa`）→ ④人工補全文資料夾（`manual_supplement`）。**取得可解析全文 → `data_source` 標 `full_text` 並以全文重抽**；唯有 ①–③ 全部試過皆非 `fulltext_obtained` 才可把 `data_source` 設 `abstract/registry_results/ai_synthesis`，此時 `extraction_validation.status` 必為 `needs_review`、並連動 [registry_backfill] 補欄＋Phase 3 確定性封頂（[selfcheck C4「非全文不得 low」]）。詳見 [fulltext_authoritative] 護欄。

## 步驟
0. **窮盡全文管道 → 標 `data_source` ＋ `fulltext_attempts`**：先依上鐵律逐管道實試全文（local_pdf→PMC→Unpaywall 全 locations→manual_supplement），把每管道 `{channel,result}` 記入 `fulltext_attempts`。取得全文＝`data_source` 含 `full_text`、以全文抽取；真的全部取不到才退 `abstract/registry_results/ai_synthesis`。退用時或缺 RoB/各臂N/AE/CI → **再套用 [registry_backfill] 補救**（查 ClinicalTrials.gov API、PROSPERO、FDA/EMA），補來源於 source_locators 分列。
   - **★ 全文也必留證據（`fulltext_gate` 反向檢查，否則 FAIL）**：只要 `data_source` 含 `full_text`，`fulltext_attempts` 就**至少要有一筆 `result=fulltext_obtained`**（記下是從哪個管道讀到全文，如 `{channel:local_pdf, result:fulltext_obtained}` 或 `{channel:pmc_fulltextxml, result:fulltext_obtained}`）。標了 `full_text` 卻沒有任何 `fulltext_obtained` 證據＝『全文標記無依據』，機器 gate 會擋下。（schema 把 `fulltext_attempts` 列為選用、但本鐵律與 `tools/fulltext_gate.py` 把它在 `full_text` 情形下變必填——以 gate 為準。）
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
