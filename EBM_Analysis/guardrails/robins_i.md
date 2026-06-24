---
id: robins_i
title: ROBINS-I 七領域評估（非隨機介入研究 NRSI）
feeds: 領域1 偏誤風險（GRADE）
trigger: 回顧性/前瞻世代、case-control、真實世界、非隨機換藥(switch) 等 NRSI 之核心結果（逐結果）
applies_to: NRSI（Track C；非 RCT）
output_field: phase2.rob_tool=robins_i ＋ phase2.robins_i.domains.*；映射 GRADE 領域1
source: 本檔即護欄正本（依 Cochrane Handbook 第 25 章；機器看守 validate.py check_p2_rob_routing ＋ phase2 schema）
---

[ROBINS-I 七領域評估]（Risk Of Bias In Non-randomized Studies - of Interventions）

## 路由鐵律（三路徑，不可拿錯工具）
- **RCT → RoB 2**（見 [rob2]）。
- **NRSI（回顧性/世代/case-control/真實世界/非隨機換藥）→ ROBINS-I（本檔）**。**嚴禁對 NRSI 用 RoB 2**：RoB 2 圍繞「隨機序列產生／分配隱蔽」，NRSI 無隨機化，最大偏誤來源是**干擾（confounding by indication）**，RoB 2 完全測不到。
- **SR/MA/NMA → AMSTAR2／ROBIS**（見 [amstar2]）。
- 三路徑各自評讀，**最後在 Phase 3/4 整合**：每個 outcome 的 GRADE 領域1 讀「該證據體所屬路徑的工具結果」，SoF/報告須分路徑呈現再綜合（直接 RCT ＋ NRSI ＋ 間接 NMA），並標各自確定性與侷限。

## 核心邏輯：模擬目標試驗 (Target Trial Emulation)
先寫下「若這是一個完美 RCT，它應長怎樣」（族群/介入/對照/結果/時間零點），再比對手上的 NRSI 在以下七領域偏離多遠。`phase2.robins_i.target_trial` 記此設想。

## 七領域（逐領域判 low / moderate / serious / critical / no_information）
1. **Confounding 干擾**（最關鍵）：是否辨識並適當調整所有重要干擾因子？有無「時間變動干擾」？**本題（benralizumab vs mepolizumab in 重度嗜酸性氣喘）須查核的干擾因子**：基線血嗜酸球值、先前生物製劑暴露與**換藥原因**（換藥研究＝confounding by indication 重災區：常因對前藥反應不佳才換）、OCS 依賴程度、發作史/嚴重度、共病 CRSwNP/鼻息肉、年齡、吸菸、依從性。`confounders_considered` 記實際查核清單。
2. **Selection 受試者選入**：選入是否與介入＋結果相關（如僅納入存活/有反應者＝selection bias）；起始追蹤時間點是否一致。
3. **Classification 介入分類**：介入定義是否明確、是否依「介入時點之前」資訊分類（避免依結果回溯分組）。
4. **Deviations 偏離既定介入**：是否有非試驗情境造成的偏離；關注「指派效應 vs 接受效應」。
5. **Missing data 缺失資料**：結果/干擾因子缺失是否取決於真實值；是否有合理處理。
6. **Measurement 結果測量**：測量是否跨組一致、評估者是否知情（病人自述/需判斷的結果風險更高）。
7. **Selection of reported result 所報告結果選擇**：是否依預先計畫；有無從多分析中挑選有利結果。

## 整體判斷（最不利領域決定）
`overall` ＝ 七領域中最不利者：任一 critical → critical；任一 serious 且無 critical → serious；以此類推。於 **result 層級**（非研究層級）。

## 殘酷現實警語（Cochrane Ch.25）
> 「任何 NRSI 被判為『低偏誤風險(Low)』是極不可能的。」——NRSI 本質無法消除殘餘干擾(residual confounding)。
- 故 ROBINS-I 結果大量落在 **serious/critical 是正常的**，不得勉強給 low。
- **機器看守**：`phase2.robins_i.overall=low` **必附 `low_justification`**（明述殘餘干擾為何可忽略），否則 `validate.py check_p2_rob_routing` FAIL；七領域過半填 `no_information` 亦 FAIL（防以「無資訊」充數規避判定）。

## 映射 GRADE（領域1）＋ 起始確定性
- NRSI 證據體 **GRADE 起始＝低(low)**（見 phases/02_triage 軌道 C）。
- ROBINS-I overall：moderate → 領域1 可不額外降或降一級（視情）；**serious → 降一級**；**critical → 降兩級或不納入綜合**。
- 例外上調（僅 NRSI）：大效應、劑量反應、可信殘餘干擾會使效應更趨保守——須在 `upgrade_domains` 明列理由才可回升。

## 透明記錄（Cochrane 嚴謹處）
每篇 NRSI 須明列「在哪些干擾因子上沒處理好」（有無調整、方法、殘餘干擾方向），不可只給總分。記於各領域 `note`。
