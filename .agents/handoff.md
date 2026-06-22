## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】

**功能塊**：依使用者定版，取消 Stage A→B 切分與 `_stage1_corpus` 交接契約；把「全文取得(②c)」融入
「嚴格篩選(③)」成單一**融合式分層升級嚴格篩選**——Tier1 摘要 → Tier2 CT.gov 登錄/AI 合成 →
Tier3 強制實取全文；**只有『切題』可早停，『離題』只在 Tier3 實取全文後定案**（登錄/AI 結構化內容
例外，tier2 終端）；單一產物 `g3_FINAL_screen.json`，桶＝**切題／離題／全文及摘要皆無**（取代待評估雙桶）。

**本輪審查範圍：僅以下檔案**
1. `EBM_Search/scripts/gate_guard.py`（重寫 ③ 守門：新增 3 個、移除 8 個舊 gate）
2. `EBM_Search/scripts/selftest_guards.py`（全面改寫 ③ 區塊）
3. `EBM_Search/scripts/fulltext_exhaust.py`（加 force 參數）
4. `EBM_Search/scripts/strict_screen_check.py`（離題訊息更新 v0.22）
5. `EBM_Search/SEARCH_SPEC.md`（★★v0.22 定版區塊＋步驟編號）
6. 刪除：`stage1_check.py`／`build_stage1_corpus.py`／`awaiting_channels_check.py`／
   `awaiting_stage_check.py`／`references/stage1_corpus_schema.json`

**動了什麼**
- gate_guard：新增 `check_screen_partition`（單一產物 g3 三桶分割閉合＋uid 反坍縮＋切題/離題須有
  abstract/全文/登錄/AI 或 fetched 證明）、`check_excl_requires_fulltext`（離題須 tier==3／
  fulltext_parse_attempted；**登錄/AI/nct 例外**＝終端結構化內容免 Tier3）、`check_nocontent_bucket`
  （全文及摘要皆無須 fulltext_parse_attempted∧channels_exhausted∧無內容）。移除舊 gate：check_stage1／
  check_screen_order／check_awaiting_channels／check_awaiting_stage／check_unpaywall_coverage／
  check_waiting_fulltext／check_screen_awaiting_resolved／check_partition_provenance(舊版)。
- fulltext_exhaust：`force=True`＝Tier3 即使已有摘要也強制實取全文；取不到更長正文且原有摘要→保留摘要當
  內容、照樣蓋 fulltext_parse_attempted（不誤降 awaiting）。
- selftest：改寫為融合式分層篩選 8+ 條回歸（反坍縮 uid 重複／切題無內容/離題未 Tier3/離題已 Tier3 正向/
  登錄AI離題 tier2 正向/全文及摘要皆無 有內容 FAIL/缺證明 FAIL/證明齊正向）；移除 Stage A/B 與待評估雙桶測試。

**fresh-clone 結果**：clone→覆蓋 5 改檔＋套用 5 刪除後 `selftest_guards.py`「✅ 全部守門有效」；
無懸掛 import 指向已刪模組。

**真實資料端（本案 triple-vs-dual COPD）**：base 816（②b 倖存）→ ③ 融合分層：
**切題 306（Tier1:191／Tier2:7／Tier3:108）／離題 435（Tier2 登錄AI:154＋Tier3:281）／
全文及摘要皆無 75（Tier3）**。`gate_guard --cache` 全綠（含新 3 gate）。
相比舊單層 ③（切題 212），分層升級多撈回 ~94 筆切題（摘要看不出、實取全文後才確認）→ 驗證高 recall 設計。

**想被重點看／自己不確定**
- (a) `check_excl_requires_fulltext` 對登錄/AI 的例外是否過寬？理由：CT.gov Condition/InterventionName、
  Consensus/OE 合成摘要＝終端結構化內容，無對應全文可再取（結果論文常不存在），以該內容判離題即定案。
- (b) 「離題只在 Tier3 後定案」導致對 ~618 筆非早停切題者全部強制實取全文（網路成本高）；本案以 12 執行緒
  約 10–15 分完成，但量更大的題可能需更久——是否可接受，或要加「明確他病(P 缺)可早停離題」的成本優化。
- (c) Tier3 判離題時，全文取不到更長正文者退回以『摘要』判離題（force+had_abstract 保留摘要）——
  即「離題定案」實際所依內容可能仍只是摘要（全文真的抓不到時）。這是誠實退路，但與「離題只在全文後」字面
  略有張力（已盡力實取、取不到才退摘要），想確認這個退路可接受。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
