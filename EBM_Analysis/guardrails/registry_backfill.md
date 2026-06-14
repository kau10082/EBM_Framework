---
id: registry_backfill
title: 全文不可得時的登錄庫/監管補救（固定程序）
feeds: Phase 1 抽取；Phase 3 RoB/不精確/COI
trigger: 文獻僅摘要/AI 合成摘要，或關鍵欄位（RoB 細節、各臂 N、AE、結果效應量/CI）缺漏
applies_to: 全部（尤以 abstract_only / ai_synthesis）
output_field: data_source / source_locators
source: 本檔即正本（v6.1·因實跑 ASPEN abstract-only 而定為固定補救）
---

[登錄庫/監管補救]（**固定程序，不可略**）：當只有摘要或 AI 合成摘要、或 Phase 3 所需細節（隨機化/分派隱藏/失訪/ITT、各臂 N、AE 分臂、結果 CI）缺時，**先補救再下確定性結論**。

‧ **標記資料來源 `data_source`**（陣列）：full_text／registry_results／regulatory_doc／abstract／ai_synthesis。AI 合成摘要一律另標 ai_synthesis（提醒：合成是改寫、非可回核原文）。

‧ **補救順序（cascade）**：
  1. 自摘要/合成抽出 **NCT／EudraCT／PROSPERO** 號。
  2. **ClinicalTrials.gov API v2** → `https://clinicaltrials.gov/api/v2/studies/<NCT>`：取 design（allocation/masking/誰被盲）、**各臂 N＋完成數（＝失訪率）**、eligibility、primary/secondary 結果＋CI、**AE 分臂**、sponsor/responsible party、results-posted 日期。
  3. SR/MA → **PROSPERO** 取事前 protocol（餵 protocol_completeness）。
  4. 藥廠試驗 → **FDA Drugs@FDA／EMA EPAR** 取未發表結果與安全（餵 nonreporting）。
  5. 至少取 **PubMed 真實出版摘要** ＋ 撤稿/勘誤狀態（連動 integrity_check 之 WebSearch）。

‧ **出處分列**：每個補救來源的數字，於 `source_locators` 標明出處（registry/regulator＋連結），與論文/摘要來源**分開列**，不混為一談。

‧ **跨來源一致性**：登錄庫 vs 論文/摘要數字不符 → 標 `[Conflict detected]`，不靜默採用其一。

‧ **補不到時封頂**：若 RoB 關鍵領域仍無資料 → 該領域標「無法評估（資料限制）」→ Phase 3 確定性**封頂**（通常最高到「中」，不得宣稱「高」），臨床限制寫明「偏誤風險因僅摘要級資料無法完整評估」。補齊後始可解除封頂。
