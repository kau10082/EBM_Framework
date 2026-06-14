---
name: ebm-search
description: >-
  EBM_Framework（實證醫學大計畫）的**唯一啟動入口**：系統性回顧（SR）對齊的多源文獻檢索 ＋
  Crossref／PubMed 交叉驗證（原 consensus-verify），完成後接力進入 GRADE 評讀。
  **軟指令：當使用者說「EBM分析」「實證分析」「實證醫學分析」「做EBM分析」「幫我跑實證分析」
  「對〈某主題/某藥〉做 EBM 分析」，或要做實證檢索、要「可信引用清單」、要確認文獻是否真實存在、
  要剔除幻覺引用、要為 EBM 評讀／衛教文／報告建立經查證參考文獻時，一律啟動此 skill**——
  整個 EBM 管線都從這裡開始（先檢索＋查證，再接力 ebm-analysis 評讀；本框架不接受跳過檢索）。
  觸發情境：
  - **「EBM分析」「實證分析」「實證醫學分析」「做EBM分析／評讀」「對某主題做 EBM 分析」**（＝啟動整條管線，從檢索起）
  - 「幫我查文獻」「幫我查證這個主張」「用 Consensus 找文獻」「建立可信引用清單」「幫我整理參考文獻」
  - 「驗證這些引用是不是真的」「這篇文獻真的存在嗎」「交叉驗證 Crossref PubMed」「這條 claim 有沒有證據」
---

# EBM_Search 啟動器（框架入口）

本檔是 Claude Code 的 skill 入口。**完整規格在 [`EBM_Search/SEARCH_SPEC.md`](../../../EBM_Search/SEARCH_SPEC.md)**——載入它並逐步執行。

## 執行約定（Claude Code，工作根＝EBM_Framework）
- **工作目錄＝`EBM_Framework`**（使用者開啟的專案根）。`EBM_Search/SEARCH_SPEC.md` 內所有相對路徑（`scripts/`、`config/`、`references/`）**相對於 `EBM_Search/`**；實際執行時一律**加前綴 `EBM_Search/`**：
  - 檢索/驗證引擎：`python EBM_Search/scripts/xref_verify.py …`
  - 分位閘：`python EBM_Search/scripts/journal_quartile.py …`
  - Zotero：`python EBM_Search/scripts/zotero_import.py …`
  - OA 全文：`python EBM_Search/scripts/fulltext_fetch.py …`
  - 交接包：`python EBM_Search/scripts/build_corpus_seed.py …`
- **設定／機敏**：腳本自動解析根 `config/settings.yaml`（`default_settings_path()`：env `EBM_CONFIG` > 根 config > 子計畫本地回退）。真值集中於 `config/settings.yaml`（gitignored）。
- **分階段停頓**：依規格 ★執行規範逐關停頓、等使用者確認，不一口氣跑完。

## 收尾：接力進 EBM 評讀
依規格 Phase 1 ⑦：三表＋PDF 交付後，寫交接包 `_corpus_seed.json`（`python EBM_Search/scripts/build_corpus_seed.py …`）到全文資料夾，**停下問「是否繼續進入 EBM 分析？」**。使用者回「**繼續／是**」→ 進入 **ebm-analysis**（讀 `EBM_Analysis/ANALYSIS_SPEC.md`，用交接包預填 Phase 0）。整合契約與流程見 [`INTEGRATION.md`](../../../INTEGRATION.md)。
