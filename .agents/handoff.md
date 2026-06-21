## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：EBM_Search 檢索流程多項改善（使用者 2026-06-21 於 triple-vs-dual COPD 實跑中連續糾正）

本輪審查範圍：僅以下 3 檔
- `EBM_Search/SEARCH_SPEC.md`
- `EBM_Search/scripts/leg_exhaust_check.py`
- `EBM_Search/scripts/gate_guard.py`

改了什麼（5 條）：
1. **① 廣蒐不含引文搜索**（SEARCH_SPEC.md，第①關停頓點）：① 只「廣蒐＋去重」，引文追蹤/snowball＝④，須在 ③ 定核心後做；OpenAlex/EuropePMC 在 ① 僅廣檢。
2. **報告策略時主動問 SR Filter**（SEARCH_SPEC.md，`check_strategy_approved` 段）：報告策略時必須主動問是否套 Systematic Review Filter。
3. **SR Filter 用在『PubMed 以外』的腿**（SEARCH_SPEC.md）：PubMed 維持 Cochrane RCT 過濾器；SR 過濾器套 Consensus/OpenAlex/EuropePMC（additive、`<leg>-SR` 命名、design_filter_allowed:true）；CT.gov 不適用。
4. **leg_exhaust 認得 `<leg>-SR` 子腿**（scripts/leg_exhaust_check.py）：新增 `_base()` 去 `-SR` 後綴，SR 子腿沿用母腿窮盡分類。
5. **②c 必『實抓+解析』全文、無可解析內容者在②c就判待評估**（SEARCH_SPEC.md ＋ scripts/gate_guard.py）：
   - Bug1（使用者）：所有管道都無摘要/無可解析全文者，應在「②c 全文搜索」這一關就歸「待評估」，不該漏到 ③ 才發現。
   - Bug2（使用者）：未盡力解析全文（只憑 OA/PMC 旗標標 have），導致後關才「突然」多出可解析全文。
   - 修法：SEARCH_SPEC 新增鐵律——②c 對無摘要者須**窮盡管道實抓+解析**（PMC fullTextXML／Unpaywall 全部 oa_locations／OA PDF(pdftotext)・HTML 去標籤），取得可解析正文才算 have；三管道抓+解析後仍無內容（含外文無法以英文軸詞比對）→ ②c 判 `待人工補全文`，不得漏進 ③。
   - 機器看守：`gate_guard.check_partition_provenance` 強化——screened 且無 abstract 者，其 uid 須在 `g3_fetched_by_uid.json` 且帶實抓解析證明（`text_len`≥1500 或 `verified`，登錄試驗 `channel:registry` 例外）；只掛旗標無正文＝FAIL。等於把「have 須實抓驗證」前移到 ②c。

fresh-clone / 自測：
- `python EBM_Search/scripts/selftest_guards.py` → ✅ 全部守門有效（含改過的 leg_exhaust、gate_guard）。
- 實跑 COPD cache：`gate_guard.py` 全關通過。第 5 條修正後實跑效果：原 96 筆「無摘要卻靠旗標/標題進 ③」者重抓，58 可解析、其中 27 可靠重篩（14 切題/13 離題）、69 無可解析內容→退回②c待評估；切題 349→354、待評估 63→132。證明 Bug 屬實且修正生效。

想被重點看：第 5 條 `check_partition_provenance` 的 `text_len≥1500` 門檻與 `channel:registry` 例外是否合理；②c 鐵律措辭是否與既有「待評估三管道」「有 OA 卻不抓」「have 須實抓驗證(verify_have_fetchable)」段一致無重複矛盾。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修:① 關報告誤含引文搜索語意（SEARCH_SPEC.md 第①關停頓點新增「廣蒐去重不含引文搜索」鐵律）
✅ 已修:報告策略時未主動問 SR filter（SEARCH_SPEC.md `check_strategy_approved` 段新增鐵律）
✅ 已修:SR Filter 套用對象寫錯成 PubMed（改為「PubMed 以外的腿、additive、`<leg>-SR`、design_filter_allowed:true」）
✅ 已修:leg_exhaust gate 不認得 SR 子腿（scripts/leg_exhaust_check.py 新增 `_base()` 去 `-SR` 後綴）
✅ 已修:Bug1 無可解析內容者漏到③（SEARCH_SPEC.md ②c 鐵律＋gate_guard 強化：無abstract須有實抓解析證明，否則②c判待評估）
✅ 已修:Bug2 未盡力解析全文、只憑旗標標 have（SEARCH_SPEC.md 規定②c須窮盡 PMC/Unpaywall全locations/PDF/HTML 實抓解析；gate 以 text_len 證明）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
