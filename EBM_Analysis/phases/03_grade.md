---
id: phase03_grade
title: 第三階段 — GRADE 確定性評定（逐結果）
input: phase1 + phase2 輸出 + 原文
output_schema: schema/phase3_grade.json
framework: grade_assessment
guardrails: [grading_rules, rob2, heterogeneity, surrogate, coi, effect_measure, nonreporting, no_effect_interpretation, nma]
---

## 目標
**逐 outcome** 自起始確定性出發，跑完五下調＋三上調領域，輸出 高/中/低/極低。

## 框架
主框架見 [grade_assessment]（五下調可降一級、單領域非常嚴重降兩級、至多降三級、不低於極低；三上調主用於 NRSI 或下調後 RCT）。

## 每個 outcome 的五下調領域（各領域必須有 verdict ＋ rationale，缺欄＝驗證失敗）
- **領域1 偏誤風險** ← [rob2]（RCT）／ROBINS-I（NRSI）。映射：低→不降；some concerns→不降或降一；高→降一或降兩；critical→降三。result-level。
- **領域2 不一致性** ← [heterogeneity]。非單純 I^2 高即降；依分段＋情境＋次組嚴謹度。（NMA 脈絡改用 [nma]）
- **領域3 間接性** ← [surrogate]（O 面）＋[coi] (i) 設計面。五軸（P/I/C/直接比較/O）各問「夠直接？」
- **領域4 不精確** ← OIS／RIS ＋ CI 寬度；CI 同時與可觀益處及危害相容 → 降。**強制併 [no_effect_interpretation]**（CI 跨無效線不得稱無效／等效）。
- **領域5 發表偏誤** ← [nonreporting]。

## 三上調領域（主用於 NRSI／下調後 RCT）
大效應（RR>2 或 <0.5 升一；>5 或 <0.2 升二）／劑量反應梯度／殘餘干擾朝低估方向。

## 橫向護欄（讀效應量時全程套用）
[effect_measure]：OR≠RR、基線風險依賴、SMD 假設、分析單位假精確、NNT 不可合併、罕見事件方法。

## 輸出
每 outcome：`certainty_final` ＋ 各領域 verdict／rationale ＋ 觸發之 guardrail 結果。
