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
