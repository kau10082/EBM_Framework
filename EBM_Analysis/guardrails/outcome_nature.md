---
id: outcome_nature
title: 結果性質標記
feeds: Phase 1 抽取；領域3 間接性、替代結果護欄
trigger: 抽取每個 outcome 時
applies_to: 全部
output_field: outcomes[].nature
source: 本檔即護欄正本（v6.0 規格）
---

[結果性質標記]（提取 O 時逐一標記）：將每個結果標記為「臨床／病人重要結果」或「替代／中間結果 (surrogate)」。替代結果＝實驗室數值、影像、生理指標（如 FEV1、HbA1c、CD4、腫瘤標記、影像縮小、骨密度）。替代結果未必能轉譯為臨床重要獲益（許多介入改善替代指標卻對臨床結果無效甚至有害），故核心結論若建立在替代結果上，須於第四階段『臨床限制』降級處理（見 [替代結果護欄]）。
