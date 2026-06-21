---
id: fulltext_authoritative
title: 分析階段『全文為準』— 退網路/AI 合成前須窮盡全文管道（固定程序，機器強制）
feeds: Phase 1 抽取（並連動 registry_backfill / data_honesty / 確定性封頂）
trigger: 進入評讀（Phase 1 起）每一篇要抽取的文獻
applies_to: 全部 grade_track ∈ {full, targeted_harms} 的文獻
output_field: data_source / fulltext_attempts / extraction_validation
source: 本檔即正本（因 2026-06 使用者糾正「到分析階段一切以全文資訊為準」而立）
---

[全文為準]（**固定程序，不可略；機器強制 `tools/fulltext_gate.py`**）：

**到了分析（評讀）階段，一切以『全文資訊』為準。** 摘要、登錄庫數字、AI 合成摘要都是**二手或不完整**來源，**只有在真的『各種管道都無法閱讀全文』時才退用**，且退用後確定性須封頂（連動 registry_backfill）。

‧ **抽取前必先窮盡全文管道（cascade，逐一實試、逐一記錄結果於 `fulltext_attempts`）**：
  1. **本機 `inputs/` PDF**（含人工補全文資料夾匯入者）→ `local_pdf`
  2. **PMC `fullTextXML`**（efetch db=pmc 或 EuropePMC fullTextXML）→ `pmc_fulltextxml`
  3. **Unpaywall 全部 `oa_locations`**（非只 best；逐一抓 OA PDF/HTML 解析）→ `unpaywall_oa`
  4. **人工補全文資料夾**（`analysis.fulltext_dir`，Phase 0 步驟 5 產出）→ `manual_supplement`
  （出版商付費牆 `publisher` 視為 no_access；非英文無法以英文軸詞比對亦記下。）

‧ **`fulltext_attempts` 逐管道記錄**：每筆 `{channel, result}`；`result ∈ {fulltext_obtained, no_access, not_found, parse_failed, skipped}`。**取得可解析全文 → `data_source` 必含 `full_text`，並以全文重抽**（不得只標旗標卻仍抽摘要）。

‧ **何時才可退二手**：**唯有上述 1–4 全部試過、皆非 `fulltext_obtained`（即真的取不到全文）**，才可把 `data_source` 設為 `registry_results`／`abstract`／`ai_synthesis`。此時：
  - `extraction_validation.status` 一律 `needs_review`（非全文不得宣稱 ok 定稿）。
  - 連動 **registry_backfill**：缺的 RoB/各臂 N/AE/CI 先查 ClinicalTrials.gov/PROSPERO/FDA/EMA 補。
  - 連動 **selfcheck C4「非全文不得 low」**：Phase 3 確定性**封頂**（通常最高到「中」），臨床限制寫明「因僅摘要/登錄級資料、全文不可得」。

‧ **機器強制**：`tools/fulltext_gate.py`（併入 `verify_all.py`）逐 `*.p1.json` 檢查：凡 `data_source` 不含 `full_text` 卻用了 `abstract/ai_synthesis/registry_results`，**必須**附 `fulltext_attempts` 且涵蓋 `local_pdf／pmc_fulltextxml／unpaywall_oa` 三管道皆已實試（result≠skipped）、且無任一 `fulltext_obtained`；否則 FAIL（＝沒窮盡全文就退二手）。`full_text` 卻沒附 `fulltext_attempts`／結果不一致亦 FAIL。
