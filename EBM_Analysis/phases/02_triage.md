---
id: phase02_triage
title: 第二階段 — 多軌分級與 GRADE 起始確定性
input: phase1 輸出 + 原文
output_schema: schema/phase2_triage.json
guardrails: [integrity_check, selective_reporting, protocol_completeness]
---

## 目標
定該文獻的設計軌道與 GRADE 起始確定性（第三階段升降的起點）。

## 步驟
1. **前置 gate — [integrity_check]**：查撤稿／造假／勘誤／EoC。
   - 命中撤稿 → 排除於分級與統合之外（或標重大保留），**不只是降級**。
   - 命中勘誤／EoC → 標記，評估是否影響核心結論。
2. **設計分流 → 起始確定性**（⚠️ 軌道僅為「設計分流訊號」，不以樣本量／多中心／期刊名判定確定性；精確度交第三階段領域4）：
   - 軌道 A（SR/MA of RCTs）→ 起始「高」。註明：檢索資料庫？PRISMA／納入標準？(MA) I^2／Forest Plot？
   - 軌道 B（RCT）→ 起始「高」。⚠️ 不以 N>1000／多中心／High Impact 期刊作門檻或升級；小樣本／單中心 RCT 仍起始「高」，再由領域4 降。
   - 軌道 C（NRSI／觀察性）→ 起始「低」。若用 ROBINS-I 可起始「高」但一般因干擾／選擇偏誤降兩級；大效應且無偏誤解釋可經上調領域回升。
   - 低權重（case report／專家意見／動物細胞）→ 起始「極低」。
3. **若軌道 A → 套用 [protocol_completeness]**（10 項逐查，缺項列降級候選並於臨床限制標註）。

## 輸出
`track`、`grade_start`、`integrity_check` 結果、（SR/MA）`protocol_completeness[]`。
