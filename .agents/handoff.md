## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【複審】程式碼自上次審查後已依 🔴🟡 修改，請重新讀取 repo 當前檔案內容（勿沿用上一輪結論）。

**本輪審查範圍：僅以下檔案**
1. `EBM_Search/scripts/fulltext_exhaust.py`
2. `EBM_Search/scripts/awaiting_channels_check.py`
3. `EBM_Search/scripts/selftest_guards.py`

**這次改了哪些檔 / 針對上一輪哪些 🔴🟡 做了什麼**
- 🔴（fulltext_exhaust L193 & L64-68，內容防呆）→ **已修**：新增 `_looks_like_content(t, min_chars)`
  （需命中 ≥2 個科學/方法學特徵：methods/results/conclusions/background/randomi/patients/placebo/
  95% CI/p<0.0/exacerbat/efficacy/outcome…），**只套在 Unpaywall OA 下載分支**（Crossref 摘要欄、
  PMC fullTextXML 為結構化來源不套）。cookie/登入/paywall 純文字湊字數者命中 0–1 → 不算取得、不升 have。
- 🟡（fulltext_exhaust PMC 成功提早 return 未補旗標）→ **已修**：把 `fulltext_parse_attempted=True`
  ＋ `oa_fetch_attempted=True` 提到 PMC 全文階段（在 PMC 嘗試前就設），任何進入全文實抓階段者皆帶證明旗標，
  不論從哪個分支成功 return。
- ⚪（awaiting_channels L63-64 oa_urls_tried key 檢查）→ 審查者確認寫法正確、無需改（見「已處理」備查）。

**自查另修一個交互 Bug（修 🟡 時連帶發現）**：PMID-only（無 DOI）的 awaiting 記錄，Unpaywall(DOI-based)
不適用，原本 `oa_fetch_attempted` 只在 `if doi` 內設 → 這類記錄會卡守門。已將 `oa_fetch_attempted=True`
設在 PMC 全文階段（不限有 DOI；對 PMID-only，PMC 即其 OA 管道），並把 `unpaywall_checked=True` 移進
`if doi`（無 DOI 不謊稱查過 Unpaywall）。

**fresh-clone 結果**（clone→覆蓋 3 檔）：
- `selftest_guards.py`「✅ 全部守門有效」，含新回歸：缺 fulltext_parse_attempted 會 FAIL、帶 doi 缺
  oa_urls_tried 會 FAIL、cookie/paywall 牆頁不算真內容、真內容(含方法學特徵)通過。
- PMID-only(no doi) awaiting：oa_fetch_attempted=True、unpaywall_checked=None（正確未設）、
  fulltext_parse_attempted=True → awaiting_channels_check **PASS**。
- 真實資料端：防呆重核把 12 篇牆頁/通訊假陽性（letters/corrections/editorials/離題）降回 awaiting；
  現 have 572／registry 160／ai_summary 5／awaiting 79（73 待人工補全文＋6 兩者皆無），
  awaiting 守門 ✅ 通過。

**想被重點看 / 仍不確定**
- (a) `_looks_like_content` 門檻＝「≥2 特徵」是否過寬/過嚴；對「真摘要但極短、無結構標題」的 OA HTML 是否會誤殺
  （目前 Crossref 摘要欄不走此分支，風險僅限 OA-HTML 下載且內容極短者）。
- (b) min_chars=250 之雙門檻分工（②c 篩選層 250 vs verify_have_fetchable 評讀層真全文）是否合理。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無未解決問題：複審確認上一輪 🔴🟡 皆已解決，本輪無新增 🔴🟡；2 條 ⚪ 釋疑見「已處理」。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已確認（⚪ 釋疑，無需改）：`_looks_like_content`「≥2 特徵」門檻安全——只攔 Unpaywall OA 下載分支，
  真 OA 全文（再短）幾乎必含 patients/methods/results/conclusion/efficacy 等詞，命中 2 即放行、誤殺率極微，
  且擋下滿版 cookie 牆頁（審查者複核確認設計合理）。
✅ 已確認（⚪ 釋疑，無需改）：min_chars 雙門檻分工合理——②c 篩選層 250 字＋科學特徵足以判 P/I/C 切題；
  評讀層 verify_have_fetchable 要 12000 字真全文供數據粹取；目的不同、各司其職（審查者複核確認）。

✅ 已修：🔴 fulltext_exhaust OA 下載牆頁假陽性（_strip_tags 濾不掉 cookie/paywall 純文字、易過 250 字）
  （本輪修改：新增 `_looks_like_content` 內容防呆，只套 OA 下載分支，需 ≥2 科學/方法學特徵；
   加 selftest 回歸 cookie 牆頁/真內容各一）。
✅ 已修：🟡 fulltext_exhaust PMC 成功路徑提早 return 未補 fulltext_parse_attempted
  （本輪修改：把 fulltext_parse_attempted＋oa_fetch_attempted 提到 PMC 全文階段，旗標一致）。
✅ 已修（自查連帶）：PMID-only 無 DOI 的 awaiting 卡 awaiting_channels gate
  （本輪修改：oa_fetch_attempted 改在全文階段設、不限 DOI；unpaywall_checked 移進 if doi）。
✅ 已確認（⚪，無需改）：awaiting_channels_check `("oa_urls_tried" not in a)` 為 key 存在性檢查，
  空清單 `[]` key 仍存在 → 不誤殺「Unpaywall 真回無 OA」的正當待評估（審查者複核確認）。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
