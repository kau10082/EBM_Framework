---
id: multitrack_integration
title: 多軌並行整合（RCT / NRSI / SR-MA 三軌絕不混池）
feeds: Phase 4 synthesis.tracks ＋ SoF 表 ＋ 結論
trigger: 核心證據體含 ≥2 種設計型態（RCT、NRSI、既有 SR/MA）
applies_to: 統合層（synthesis）
output_field: synthesis.tracks（rct / nrsi / srma_context）
source: 本檔即護欄正本（Cochrane Handbook Ch.10/14/25/V；機器看守 validate.py check_synthesis_tracks）
---

[多軌並行整合]——**最高鐵則：三類證據（RCT／NRSI／既有 SR/MA）絕不丟進同一統計模型合併(pooling)，也不混在同一 GRADE。** 採「多軌並行(multi-track)」分軌呈現。各軌資料寫入 `synthesis.tracks`（暫存/交付容器），每軌獨立 pool／森林圖／SoF／起始確定性。

## 第一軌：RCT（RoB 2）＝核心主力
- **合成**：放入主分析 meta-analysis、繪**專屬森林圖**。RoB 2 為 high／some concerns 者→做**敏感度分析**（剔高風險看穩健性）或依 RoB 分層；寫 `tracks.rct.sensitivity_analysis`。
- **GRADE**：專屬 SoF；起始 **high(⊕⊕⊕⊕)**；RoB 扣分則於「偏誤風險」領域降級＋腳註說明。`tracks.rct.starting_certainty=high`。

## 第二軌：NRSI（ROBINS-I）＝真實世界輔助
- **合成**：**絕不可與 RCT 合併於同一 meta-analysis**——獨立森林圖。異質性過大→放棄統計合併、改**敘事綜整(narrative)**（`synthesis_mode=narrative`）。
- **排除 critical**：ROBINS-I=critical 之結果**必從任何合成剔除**（列 `tracks.nrsi.excluded_critical_ids`，不得進 `included_paper_ids`）。
- **GRADE**：獨立 SoF（或同表內獨立區塊）；起始 low（ROBINS-I 容許 high 但因殘餘干擾常降至 **low/very low**）；大效應/劑量反應可升級。

## 第三軌：既有 SR/MA（AMSTAR 2 / ROBIS）＝討論對照基準
- **非 Overview 時**：他人 SR/MA **絕不可作數據提取來源、不得進入你的統合**（防 double-counting）。`tracks.srma_context.used_as_data_source=false`、`role=discussion_context`。
- **整合方式**：高品質 SR/MA 作為**討論章節**的對照座標：把你自跑的 RCT/NRSI 結果與其對比（一致 concordant／相左 discordant／更新翻轉 updates）。
- 若本研究即「回顧之綜覽(Overview)」→ `is_overview=true`，SR/MA 才為分析單位（另循 overview 流程＋CCA 重疊）。

## 結論分層撰寫（Authors' Conclusions）
1. **首要**（RoB 2 的 RCT，high）：「根據高確定性證據，…」
2. **次要支持**（ROBINS-I 的 NRSI，low）：「真實世界觀察性證據（低確定性）效應方向與 RCT 一致，支持外推性…」（矛盾則探討情境差異/干擾）。
3. **脈絡對照**（AMSTAR 2 的 SR）：「本回顧發現更新/強化了先前高品質 SR 的結論…」

## 機器看守（`validate.py check_synthesis_tracks`，synthesis 階段）
- **跨軌混池** → FAIL：同一 paper 不得同時在 `rct.included` 與 `nrsi.included`。
- **critical 矛盾** → FAIL：paper 不得同時在 NRSI `included` 與 `excluded_critical`。
- **SR/MA 當數據源** → FAIL：非 Overview 時 `srma_context.used_as_data_source` 必 false、`role=discussion_context`。
- **GRADE 遺失** → FAIL：某軌 `synthesis_mode=meta_analysis` 且有 included 卻無 `sof`／`certainty_summary`。
- schema(`phase4_output.json`) 另以 const 鎖 `rct.tool=rob2`、`nrsi.tool=robins_i`、`rct.starting_certainty=high`。

## PDF 輸出（多軌 SoF）
報告須**分軌呈現 SoF**：RCT-SoF、NRSI-SoF 各自獨立區塊（標題標明證據類型與起始確定性），SR/MA 僅於討論對照表/段落出現、不混入 SoF。（`build_grade_pdf.py` 偵測 `synthesis.tracks` 時逐軌渲染；整合運算規則待補後再調整最終版型。）
