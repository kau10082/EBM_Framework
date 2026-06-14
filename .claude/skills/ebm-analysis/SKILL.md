---
name: ebm-analysis
description: >-
  EBM（實證醫學）GRADE 評讀引擎——**EBM_Framework 管線的下游階段，不獨立冷啟動**。由 Claude 本身算力
  直接執行（不呼叫外部 API），依結構化規格（phases／guardrails／schema）逐階段評讀、每階段設斷點。
  **入口規則：EBM 評讀一律由 EBM_Search（ebm-search）完成檢索＋交叉驗證後接力進入；本框架已取消 `/ebm`。**
  觸發情境只有兩類：
  - **從 EBM_Search 接力**：使用者在 ebm-search 收尾後回「繼續（進入 EBM 分析）」，或指向／偵測到含 `_corpus_seed.json` 的交接包資料夾。
  - **封存／歸檔既有分析**：「封存／歸檔這次（EBM）分析」「把這次分析存起來」「歸檔成 XXX」「封存後清空準備下一個主題」。
  若使用者未經 EBM_Search 檢索就要求直接評讀 PDF → 不冷啟動，導引其先用 ebm-search（見規格「入口守則」）。
---

# EBM_Analysis 啟動器（下游評讀）

本檔是 Claude Code 的 skill 入口。**完整規格在 [`EBM_Analysis/ANALYSIS_SPEC.md`](../../../EBM_Analysis/ANALYSIS_SPEC.md)**——載入它並逐步執行。

## 入口守則（單一入口：EBM_Search）
**不獨立冷啟動。** 允許進入只有兩種情況：(1) 從 EBM_Search 接力（「繼續」或有 `_corpus_seed.json`）；(2) 封存／歸檔。
若使用者沒先檢索就要直接評讀 PDF → **不要從零跑 Phase 0–4**，改提醒先用 **ebm-search** 對主題檢索＋查證，收尾回「繼續」再接力。

## 執行約定（Claude Code，工作根＝EBM_Framework）
- **工作目錄＝`EBM_Framework`**。`ANALYSIS_SPEC.md` 內所有相對路徑（`phases/`、`guardrails/`、`schema/`、`tools/`、`cache/`、`inputs/`、`outputs/`、`manifest.yaml`）**相對於 `EBM_Analysis/`**；實際執行**加前綴 `EBM_Analysis/`**：
  - 交接包匯入：`python EBM_Analysis/tools/ingest_seed.py --seed-dir "<交接包資料夾>"`
  - schema 驗證：`python EBM_Analysis/tools/validate.py pN EBM_Analysis/cache/<paper>.pN.json`
  - 報告渲染：`python EBM_Analysis/tools/build_reports.py`
  - 封存：`python EBM_Analysis/tools/archive_run.py <slug> [--clear] …`
  - 讀規格：`EBM_Analysis/phases/0N.md`、`EBM_Analysis/guardrails/*.md`、`EBM_Analysis/schema/*.json`
- **設定／機敏**：個人路徑與字型見根 `config/settings.yaml` 的 `analysis` 區。
- **斷點覆核照舊**：交接包預填的分流與 review question 皆為建議值，Phase 0 仍需使用者確認。

整合契約與端到端流程見 [`INTEGRATION.md`](../../../INTEGRATION.md)。
