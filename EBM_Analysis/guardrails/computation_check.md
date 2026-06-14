---
id: computation_check
title: 運算驗證機制
feeds: Phase 4 輸出前
trigger: 輸出含 NNT／ARR 等衍生數據
applies_to: 全部
output_field: derived_value_checks
source: 本檔即護欄正本（v6.0 規格）
---

[運算驗證機制]：若輸出包含 NNT 或 ARR 等衍生數據，請在內部執行 自檢邏輯：
檢核公式：NNT = 1 / (Control Group Event Rate - Treatment Group Event Rate)。
嚴禁輸出未經算式確認的概約數字。若無法取得原始事件率，僅能描述「相對風險降低度（RRR）」而非 NNT。
※ 合併情境：若資料來自 meta-analysis，NNT／ARR 須由「合併後」之 RD／OR／RR 導出，嚴禁逐篇 NNT 直接平均、亦嚴禁由跨試驗彙整總數計算（見 [效應測量詮釋與分析單位護欄] (f)）。
