---
id: sof_table
title: Summary of Findings 表 ＋ 絕對效應（Cochrane 招牌輸出）
feeds: 統合輸出（Phase 4 synthesis）
trigger: 產出統合報告時（≥1 個可量化結果）
applies_to: 統合層
output_field: synthesis.sof
source: 本檔即正本（v6.3·Cochrane Ch14 §14.1）
---

[SoF 表 ＋ 絕對效應]（Cochrane Ch14 §14.1.3/§14.1.5 強制建議）：統合報告須提供結構化 Summary of Findings 表，**最多 7 個對病患最重要的結果（含益處與傷害）**。

‧ **每列七欄**：① 結果（含測量時框）② 對照組假設風險（assumed/baseline risk）③ 介入組對應風險（corresponding risk）④ 絕對效應（風險差 RD／NNT 或率差）⑤ 相對效應（RR/OR/HR＋95% CI）⑥ 參與者數（研究數）⑦ GRADE 確定性（高/中/低/極低＋⊕）＋評論（如替代終點侷限）。

‧ **相對＋絕對並列（鐵則）**：二分類結果**必須同時給相對與絕對**（Ch14 §14.1.5）。同樣 RR，在不同基線風險下「實際減少人數」差異極大。
  - 對應風險：RR → corresponding = RR × ACR；OR → (OR×ACR)/(1−ACR+OR×ACR)。
  - 絕對風險差 RD = corresponding − ACR；**NNT = 1/|RD|**，以 NNTB（益）／NNTH（害）標方向。
  - 工具：`python tools/absrisk.py rr <RR> <baseline>`（或 `or`）自動算 corresponding/RD/NNT，避免手算錯。

‧ **率（rate，count/人年）結果**：不可套二分類 NNT；改報**率差**＝ACR_rate ×(RR−1)（如每人年少 X 次惡化）。

‧ **連續結果（如 FEV1）**：呈現平均差（MD）＋CI；不適用 NNT；於評論標替代終點侷限。

‧ **基線風險來源**：取對照組實際風險（試驗/CT.gov），或代表性研究/預後資料；於評論註明來源。多基線風險時可列高/中/低風險族群之絕對效應。

‧ **確定性即逐 outcome 之 GRADE**（取統合層；單藥 vs 類別若不同須分列或註明）。

‧ **表頭 PICO 宣告（Ch14 §14.1.6.1）**：SoF 表上方須宣告 Patients/population（含關注族群與基線風險層級）、Setting（場域）、Intervention、Comparison，讓讀者知道此表適用對象。

‧ **NNT 一律用 NNTB/NNTH（Ch15 §15.4.2，呼應 effect_measure 護欄）**：避免易誤讀的「NNH」。NNTB＝多 1 個有益結果所需治療人數；NNTH＝多 1 個有害結果所需治療人數。SoF 與報告一律標 NNTB／NNTH，不寫裸 NNT。

‧ **二分類 harms 即使不顯著也給自然頻率（Ch14 §14.1.6.3）**：以「每 1000 人發生 X 例」呈現各組絕對風險，並填 RR＋95% CI（即使無統計顯著差異），讓決策者看見基線風險高低。逐臂數缺時誠實標資料缺口、不以「各組相近」一語帶過。

‧ **並列多藥/多試驗時加防呆警語（呼應 overlap_indirect 禁非正式間接比較）**：若報告把多個藥物/試驗並列，須於表下加註「各試驗之基線、劑量與測量指標不盡相同，不應直接比較各藥相對效應大小（不可做非正式間接比較）」，防止讀者自行推論藥物優劣。
