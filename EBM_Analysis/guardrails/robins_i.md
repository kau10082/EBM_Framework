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
ROBINS-I 捨棄傳統品質評分量表，改採概念對標：先建構一個「**目標試驗**」——完美、無執行瑕疵、針對相同族群回答相同問題的假設性務實 RCT（不論實務上是否合倫理/可行）。**偏誤＝這篇 NRSI 的結果與該完美目標試驗結果之間的系統性差異**。`phase2.robins_i.target_trial` 記此設想。

## 評估前兩大前置作業（填表前必備；機器看守）
1. **預先指定干擾領域與共同介入**：列出可能同時影響「接受哪種治療」與「結果」的重要干擾因子（疾病嚴重度、社經、先前用藥…）＝`confounders_considered`（**須非空**）；以及可能伴隨的共同介入＝`cointerventions`。
2. **指定關注效應性質**：`effect_of_interest`＝`assignment`（分派效應，ITT-like）或 `adherence`（遵循效應，PP-like）——**這會決定領域4「偏離既定介入」如何判**（機器強制必填）。

## 信號問題（Signalling questions）
每領域以一系列信號問題作答：**Y 是／PY 可能是／PN 可能否／N 否／NI 無資訊**，再經演算法導出該領域判斷（可記於 `domains.<d>.signalling[]`）。

## 七領域（依時間軸三階段；逐領域判 low / moderate / serious / critical / no_information）
**【介入前 Pre-intervention】**（NRSI 最致命缺陷區）
1. **Confounding 干擾**（最關鍵）：是否因預後因子同時影響「接受哪種治療」與「結果」而生偏誤？有無時間變動干擾？**本題（benralizumab vs mepolizumab in 重度嗜酸性氣喘）須查核的干擾因子**：基線血嗜酸球值、先前生物製劑暴露與**換藥原因**（換藥研究＝confounding by indication 重災區：常因對前藥反應不佳才換）、OCS 依賴程度、發作史/嚴重度、共病 CRSwNP/鼻息肉、年齡、吸菸、依從性。`confounders_considered` 記實際查核清單。
2. **Selection 受試者選入**：合格者或追蹤時間是否被不當排除？如納入「盛行使用者(prevalent users，已在用藥的老病患)」造成**前導時間偏誤(lead-time bias)**；起始追蹤時間點是否一致。

**【介入時 At-intervention】**
3. **Classification 介入分類（資訊偏誤）**：介入狀態是否被錯誤分類（回憶偏誤等），尤其**與結果相關的差異性誤分類**；是否依「介入時點之前」資訊分類（避免依結果回溯分組）。

**【介入後 Post-intervention】**（類似 RoB 2 的評估面向）
4. **Deviations 偏離既定介入**：實驗/對照在實際照護上有無系統性差異；判定取決於 `effect_of_interest`（assignment ITT-like / adherence PP-like）。
5. **Missing data 缺失資料**：失訪或重要變數（含干擾因子）缺失是否取決於真實值；是否有合理處理。
6. **Measurement 結果測量（偵測偏誤）**：測量是否跨組一致、評估者是否因知情而主觀影響（病人自述/需判斷的結果風險更高）。
7. **Selection of reported result 所報告結果選擇**：是否依「取得未盲資料前預先指定的計畫」分析；有無依顯著性/P 值從多結果或多分析中挑選有利者。

## 四個風險層級（不同於 RoB 2）
- **Low（低）**：等同執行極佳的隨機試驗。⚠️ 因殘餘/未測量干擾難排除，**任何 NRSI 整體判 Low 極不可能(very unlikely)**。
- **Moderate（中）**：在 NRSI 中算健全，但仍不能與 RCT 相提並論。
- **Serious（嚴重）**：該領域有重要問題。
- **Critical（關鍵）**：問題太大，該研究**無法提供有用的介入效果證據**。

## 整體判定（木桶原則／最弱環節；result 層級）
`overall` ＝ 不得優於最不利領域：**任一領域 serious → 整體至少 serious；任一領域 critical → 整體 critical**（多個 moderate 也可累積成 serious）。
- **機器看守**：`overall` 若優於最不利領域 → `validate.py check_p2_rob_routing` **FAIL**（違反木桶原則）。
- **Critical → 直接排除於統合**：被評 critical 之結果應從 meta-analysis 排除（Cochrane Ch.25）→ 須設 `meta_analysis_action=exclude`，否則 **FAIL**。

## 殘酷現實警語（Cochrane Ch.25）
> 「任何 NRSI 被判為『低偏誤風險(Low)』是非常極不可能的(very unlikely)。」——NRSI 本質無法消除殘餘干擾(residual confounding)。
- 故 ROBINS-I 結果大量落在 **serious/critical 是正常的**，不得勉強給 low。
- **機器看守**：`overall=low` **必附 `low_justification`**；七領域過半填 `no_information` ＝充數規避 → FAIL；前置作業 `effect_of_interest` 與 `confounders_considered` 缺 → FAIL。

## 映射 GRADE（領域1）＋ 起始確定性
- NRSI 證據體 **GRADE 起始＝低(low)**（見 phases/02_triage 軌道 C）。
- ROBINS-I overall：moderate → 領域1 可不額外降或降一級（視情）；**serious → 降一級**；**critical → 降兩級或不納入綜合**。
- 例外上調（僅 NRSI）：大效應、劑量反應、可信殘餘干擾會使效應更趨保守——須在 `upgrade_domains` 明列理由才可回升。

## 透明記錄（Cochrane 嚴謹處）
每篇 NRSI 須明列「在哪些干擾因子上沒處理好」（有無調整、方法、殘餘干擾方向），不可只給總分。記於各領域 `note`。
