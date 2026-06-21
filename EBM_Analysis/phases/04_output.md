---
id: phase04_output
title: 第四階段 — 嚴格輸出格式（單篇報告 ＋ 統合）
input: phase1-3 輸出（所有納入文獻）
output_schema: schema/phase4_output.json
render: outputs/{paper}.report.md（單篇）、outputs/synthesis.md（統合）
guardrails: [adversarial_review, sof_table, report_completeness, computation_check, output_selfcheck, wording_template, vote_counting, swim, overlap_indirect, nma, surrogate, harms, coi, effect_measure, no_effect_interpretation]
---

## 前置 gate — [adversarial_review]（Phase 3 之後、產報告之前）
以「懷疑者」對每篇 Phase 3 關鍵 verdict 重跑一遍以推翻它：抓離群（對照 audit_consistency）、違反 grading_rules、未驗證即當低偏誤（data_source 含 ai_synthesis/abstract）、校準確認偏誤。revise 命中→回改 p3、重跑 validate.py（算術重驗）、再產報告；屬臨床顯著性抉擇者→列『臨床限制』交使用者。複查紀錄寫 outputs/_adversarial_review.md。

## 校準邏輯（送出前）
- 內部檢索：產出前在後台定位數據之頁／章節（滿足抗幻覺）。
- [computation_check]：含 NNT／ARR 等衍生數據 → 公式自檢；MA 須由合併後 RD/OR/RR 導出，禁逐篇平均。
- **[output_selfcheck]（強制 gate）**：含 GRADE 自檢＋盲化考量自檢；任一不成立 → 改寫。

## 單篇報告結構（outputs/{paper}.report.md）
1. **[PICO]** — P/I/C/O；每個 O 標「臨床／替代」。
2. **🎯 核心結論 (Bottom Line)** — 一句話；遣詞依 [wording_template]（高=直述／中=likely／低=may／極低=非常不確定）。觸發時先過 [no_effect_interpretation]、[surrogate]、[harms]、[effect_measure]。
3. **⚖️ 證據強度儀表板** — APA 格式；方括號【僅限：GRADE 層級、起始設計、升降領域、N、方法學判定】。🚫 嚴禁提及實驗結果／效果數據／p 值／作者結論。
4. **⚠️ 臨床限制 (Caveats)**（200 字內，逐護欄若觸發）：[surrogate]／[harms]／[coi]／不精確限制／[nma] 限制／非報告偏誤限制。

## 統合報告（outputs/synthesis.md）— 跨所有來源，強制輸出
- 數據一致性：彙整高確定性文獻效應值；共識強度依「效果估計方向／量值收斂（CI 重疊、點估計接近）」，**不以結論篇數計**。
- **[vote_counting]**：三層可取性（統計顯著性／主觀規則計票＝不可接受）。
- **[swim]**（若有無 MA 的敘事綜整 SR）。
- **[overlap_indirect]**（≥2 篇 SR/MA：重疊檢查＋禁非正式間接比較）。
- **[nma]**（若含網絡統合／間接比較）。
- 證據對抗：高確定性文獻不一致 → 列衝突點，比較定義嚴謹度與研究年代。
- 終極權重裁決：依 GRADE 確定性＋RoB＋效果一致性；⚠️ 不以 N 規模／期刊名裁權。

## ★ 標準成品格式（PDF＋MD 統一，鐵律，2026-06 使用者定）
analysis 階段最終報告（`outputs/FINAL_REPORT.md` 與 `FINAL_REPORT.pdf`）**一律照 Cochrane Handbook 第 III 章後半段「6 段」版型**，PDF 與 MD **同格式、同資料源**（皆由 `cache/_synthesis.json` 渲染）：
1. **納入研究特徵摘要表**（Ch9）：設計／基準風險／介入·對照精確內容／追蹤。
2. **個別試驗偏誤風險評估 RoB 2**（Ch8）：逐篇逐領域＋對 some concerns/high 點出瑕疵來源。
3. **數據綜整／統合分析**（Ch10）：逐核心結局**池化合併效應＋I²**（`synthesis.meta_analysis`）；未池化者註明理由。
4. **GRADE 證據確定性評級**（Ch14）：逐結局五下調領域結算（`body_of_evidence`）。
5. **SoF 表＋臨床建議**（Ch14·15）：SoF **必『相對＋絕對（每 1000 人）＋NNTB/NNTH』並列、全附 95% CI**；**跨無效線/資料不足者明寫『無顯著差異／不計 NNT』，不得寫 NNT=∞**；附 **GRADE 降級腳註 a/b/c…**（`sof_footnotes`）；Authors' Conclusions 平衡利弊＋MCID，**不下強制醫囑**（Ch15）。
6. **給臨床的一句話**（Clinical Bottom Line）。
- 渲染器：MD＝`tools/build_reports.py`（會連帶呼叫 PDF）；PDF＝`tools/build_grade_pdf.py`（**預設 `--layout cochrane5`**）。NNT/絕對效應一律經 `tools/absrisk.py` 計算、`selfcheck_consistency` C5/C6/C7/C14 覆驗，禁手算。**通用、資料驅動，換任何主題（PICO）自動適用。**

> **★ SoF 數據呈現黃金守則（鐵律，Ch14·15；2026-06 使用者定，務必遵照）：**
> 1. **相對＋絕對＋NNT 三者並列**：每個二分類/時間事件結局＝相對效應(RR/OR/HR)＋**絕對效應『每 1000 人』**＋**NNTB(益)/NNTH(害)**，**全附 95% CI**（NNT CI 由相對效應 CI 代入 ACR 回推，`absrisk` 算）。連續結局給 MD＋MID、率結局給率差（此二類不套 NNT，須明寫「率/連續結果不套 NNT」）。
> 2. **跨無效線/資料不足＝不寫 NNT**：CI 跨 1 → 寫「無顯著差異、不計 NNT」（禁寫 NNT=∞）；來源未報 → 寫「資料不足/待全文、不計 NNT」。（機器：C6/C6b/C14）
> 3. **GRADE 降級腳註必備**：任一結局<高，須附腳註 a/b/c…逐條說明降在哪領域（`sof_footnotes`）。（機器：C17）
> 4. **統合分析段必備**：≥2 試驗須有 `meta_analysis`（逐核心結局池化合併效應＋I²；未池化亦列 `model:not_pooled`＋理由）。（機器：C18）

> **★ 全文不可得時的 registry_backfill ＋ RoB 封印解除（鐵律，2026-06 使用者定）：** 期刊全文線上不可得時，**務必先試 ClinicalTrials.gov 登錄結果**（`data_source:registry_results`，見 [registry_backfill]）取**真實對照組事件率**(算絕對效應/NNT)、**失訪/盲蔽**(評 RoB)、分臂死亡/SAE/特異 AE。
> - **RoB 封印**：登錄確認盲蔽佳、失訪可接受 → 偏誤風險領域**不再因『僅摘要』封頂**，該結局確定性可回升（[selfcheck C4] 對 `registry_results` 不擋 low）；TRIBUTE 類無登錄結果者仍摘要級封頂。
> - **誠實標註**：登錄之死亡/SAE＝**『治療期間(treatment-emergent)』事件、非校正完整追蹤之裁定終點**（後者須期刊全文）→ 據此降一級、腳註講明、標「待全文確認」。**嚴禁以記憶/常識填全文數字**（[fulltext_authoritative]：取得全文才標 `full_text` 並以全文重抽；登錄≠全文）。
