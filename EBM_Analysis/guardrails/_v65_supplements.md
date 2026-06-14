---
id: v65_supplements
title: Cochrane v6.5 補遺（對既有護欄的增補規則）
applies_to: all
trigger: 各對應情境（見每條）
handbook_ref: 見各條
---

本檔集中補足稽核發現的尾端缺口，依情境觸發；與既有護欄交叉引用。

## A. 預測區間（補 heterogeneity；Ch10 §10.10.4.3）
有實質異質性的 MA：**隨機效應摘要 CI 不描述跨研究變異分布**，應看/索取**預測區間**（呈現「未來一個研究的真實效應可能落在何處」）。使用門檻：≥5 研究、無明顯漏斗圖不對稱。紅旗：「孤立引用隨機效應摘要 CI 當充分摘要」＝常見過度詮釋（§10.10.4.2）。SoF/synthesis 有預測區間時應呈現。

## B. 連續結果可解讀再表達＋MID（補 sof_table；Ch14 §14.1.6.2、Ch15 §15.5）
連續結果（FEV1、量表分數）SoF 必做：(1) **每結果註明 MID/MCID**（§14.1.6.2、§III.3.4.5）；(2) **不精確以 CI 是否跨 MID 判定**——CI 全距落於 MID 同側＝精確（即使統計顯著也代表「精確地無/有臨床重要差異」），**不因此降不精確**（見本案 FEV1：38 mL，CI 11–65 全距 < MID 100 mL → 精確的「無臨床重要益處」）；(3) SMD 須可解讀化：熟悉量表單位/平均值之比/MID 單位/二分化（`tools/absrisk.py smd2or <SMD>`，lnOR≈1.81×SMD，§15.5.3.3）。

## C. 效應量補強（補 effect_measure；Ch6）
- **HR/time-to-event**：見 time_to_event 護欄。
- **零事件處理**（§6.4.1.2）：對照組零事件時 RR/OR 不可直接算；加 ½ 校正會引偏誤；兩組皆零應自 MA 略去（見 rare_events）。
- **estimand 標註**（§6.1.2.2）：核心結論之效應須標明係 **ITT 效應** 或 **per-protocol（遵循）效應**，勿混用。

## D. 選擇性報告補強（補 selective_reporting / registry_check；Ch7 §7.7）
- registry 比對**不只 primary，須含 secondary outcomes 與註冊歷史版本**（次要結果更常被選擇性報告，§7.2.3.3）。
- 偵測 **under-reporting（低報）**：結果「報了但僅述 P>0.05／無效應量／無法併入 MA」＝情境2 偏倚，非「未報」。
- NMA 的缺失證據偏誤用 **ROB-MEN**（非 ROB-ME）＋comparison-adjusted funnel plot（補 nma/nonreporting；Ch13 §13.3、Ch11 Box 11.5.a）。

## E. RoB2 領域4 補強（補 rob2；Ch8 §8.6）
領域4 五考量除「評估者是否設盲/受知情影響」外，明列：(1) **測量方法是否適當**（如血糖機測不到嚴重低血糖）；(2) **組間測量是否不同**（differential：實驗組更密集監測→更多偶見診斷/被動 harms）。差異性測量誤差為紅旗。

## F. COI 路徑補強（補 coi；Ch7 §7.8.3）
新增因果路徑：**招募者有 COI × 分派未隱藏 → 更易破壞分派 → 餵 RoB2 領域1（隨機化）**，非只連到選擇性報告。

## G. 資料蒐集補強（補 extraction_conventions；Ch5）
- **統計量轉換優先於封頂**（§5.6 C47）：缺 SD 時，先嘗試由 SE/CI/t/F/P 反推 SD（附公式與計算紀錄，§5.7 保留原始＋計算數字）；轉換不成才走 registry_backfill→封頂。
- **共用對照組**（§3.2.3.1、§5.3.6）：多臂試驗多個介入臂共用同一對照→meta-analysis 須按臂數拆分對照組樣本，避免 unit-of-analysis error；萃取時記 `shared_control`。
- **圖形數值**（§5.5.8）：僅見於圖之數值**可用 WebPlotDigitizer 類工具萃取**並標 `data_source: figure_digitized`＋記工具，優於一律放棄（仍禁目視臆測）。
- **連續結果陷阱**（§10.5）：SMD 下變化分數與終末值不可混；偏斜粗檢（mean/SD<2 暗示偏斜）；二分類+連續混合需 OR↔SMD 轉換。

## H. 證據體 GRADE（補 grade_assessment / phase4；Ch14 §14.2.1）
GRADE 評定對象＝「某 outcome 跨研究的證據體」，**非逐篇分數取均/取最差**。synthesis 層須逐 outcome 重評五領域（不一致性=跨研究、不精確=合併 CI vs MID/OIS、發表偏誤=跨研究漏斗/ROB-ME），輸出 `body_of_evidence`。

## I. 敏感度分析（補 phase4；Ch10 §10.14、Ch13 §13.3.4.6）
就關鍵判斷（離群、固定vs隨機、零格校正、低偏誤子集、缺失證據假設）做敏感度分析，檢視結論穩健性；缺則列為呈現缺陷（非自動降級）。缺失證據敏感度見 missing_evidence_sensitivity（假設未發表為 null 是否翻轉）。

## J. critical outcomes 不可從 SoF 消失（Ch14 §14.1.6.1；防 outcome reporting bias）
**全因死亡（all-cause mortality）＋嚴重不良事件（SAE）為任何全身性藥物之必列 critical outcomes**——即使事件極少、統計不顯著、或無法統合，仍須留在 SoF（給低/極低確定性並註明「未具檢定力」），不得因「不顯著/事件少」而刪除。刪除＝結果報告偏誤。selfcheck **C11** 硬擋（SoF 須含死亡列＋SAE 列）。事前 outcomes_prioritized 應含至少一益一害。

## K. 對照組須精準界定背景照護／add-on vs replacement（MECIR C7、Ch14 SoF 表頭）
SoF 表頭與 review_question.C **必須精準描述對照條件**：是「純安慰劑/無治療」還是「安慰劑＋背景標準照護(SOC)」。多數慢性病試驗（如支氣管擴張症：氣道清除、必要時抗生素）對照組接受 SOC → 該藥為**附加療法(add-on)**，不可寫成單純「安慰劑」（否則醫師誤以為可『取代』現行療法）。共同介入(co-interventions)同時給兩組者須註明。

## L. 借用他人 MA 合併值的一致性（防 Emara paradox）
若引擎自稱「不做自己的統計池化」（因異質性），卻在 SoF 借用他人 MA 的合併 RR/OR 推算絕對效應，**必須明示**：(a) 係『採用已發表 MA 之合併估計呈現類別效應、非本引擎自行池化』；(b) 標明該 MA 之異質性侷限；(c) 單藥療效另以最大樞紐試驗為錨點。否則為自我矛盾。selfcheck **C12** 硬擋。
