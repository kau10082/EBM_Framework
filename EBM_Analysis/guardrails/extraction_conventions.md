---
id: extraction_conventions
title: 抽取慣例（跨篇一致性規則）
feeds: Phase 1 抽取
trigger: 永遠（抽取時）
applies_to: 全部
output_field: pico.O / data_gaps
source: 本檔即正本（v6.0 規格·為消除跨篇判斷不一致而新增）
---

[抽取慣例]：以下為 spec 明定規則，**所有文獻一致套用**，消除逐篇臨時判斷造成的不一致。

‧ **多臂/劑量試驗**：outcome 以「臨床終點」為單位（不按劑量爆量）；同一終點的各劑量對照寫在該 outcome 的 `effect_measure`/`ci`（如「10mg：…；25mg：…」）。不可只報有利劑量。

‧ **效應量選擇**：報「計畫書預先指定的主要分析」之效應量為 `point_estimate`；若另有預先指定敏感度分析（如負二項 IRR、Anderson–Gill）併列於 `ci` 字串。二分類結果優先相對測量（RR/OR/HR）＋（若有）絕對測量。混用未轉換者標 data_gaps。

‧ **不良事件粒度**：至少分列 (a) 機制特異性 AESI（如 DPP-1 之牙科、皮膚/角化）(b) 嚴重 AE/SAE (c) 導致停藥/退出之 AE；不可把全部 harms 併成單一「不良事件」。每筆 `nature: clinical`（harms 屬病人重要）。

‧ **效應方向標準化**：以「較不常見狀態為事件」、且全 corpus 同向（如一律「惡化發生」為事件、HR<1＝有利）；反向報告須註明並轉換。

‧ **遺漏與圖表**：只在圖/表而正文未給數值者，若文字抽取無法可靠讀出 → `point_estimate: null` ＋ `ci: "[Not Stated in Source]（僅圖示）"` ＋ 記 data_gaps；嚴禁臆測。

‧ **多重性/階層檢定**：若次要終點採階層式固定順序檢定，於 data_gaps 註明順序與「一旦某項不顯著、其後 P 僅名目」，供 Phase 3 選擇性報告/effect_measure 判讀。

‧ **補齊常見遺漏 outcome**：嚴重惡化（住院）、死亡、生活品質（達 MCID 否）、停藥率——若原文有報而易漏，務必納入。
