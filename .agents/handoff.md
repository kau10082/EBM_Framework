## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

**【初審】功能塊：EBM_Search 檢索管線守門強化（累積，因 2026-06 實跑時使用者連續糾正三個漏洞而立）**

**本輪審查範圍：僅以下檔案**
- `EBM_Search/scripts/gate_guard.py`
- `EBM_Search/scripts/stage1_check.py`
- `EBM_Search/scripts/selftest_guards.py`
- `EBM_Search/SEARCH_SPEC.md`
- `EBM_Search/.gitignore`

**背景／動機**：實跑 triple-vs-dual COPD 檢索時，使用者連續抓到數個「靠記性、無機器守門」的漏洞——(1) 未先報告檢索策略、未等確認就檢索；(2) 檢索時自行縮放範圍；(3) 把缺摘要的記錄逕判「兩者皆無」待評估，根本沒查 Unpaywall/PMC；(4) 有 OA 全文連結卻只記 URL、沒實際抓取就掛待評估；(5) ③嚴格篩只憑摘要把對照 C 看不出者 punt 成「待評估」，沒去抓全文核對（③候選明明都已有內容）。依 AGENTS.md「機器守門優先於記性／把使用者抓到的缺失轉成 gate」，逐一落為機器 gate。

**這輪改了什麼（累積）**
1. **防搶跑** `gate_guard.check_strategy_approved`：廣蒐產物 `g1_legs_manifest.json` 存在時，`g0_strategy.json` 必須帶 `approved_by_user:true`（使用者確認策略後才設），否則 FAIL。已 wire 進 `_all_checks`（最前）＋ Stop hook（exit 2 擋回合）＋模組 docstring。任何範圍變更須回此停頓點重新核准。
2. **防『未查全文就丟兩者皆無』** `stage1_check`（併入 gate_guard Stage A→B 邊界）：awaiting 標 `兩者皆無` 卻帶 `doi/pmid` → FAIL。`兩者皆無` 僅限完全無 ID／無路徑者；有 ID＝有路徑，須先查 Unpaywall/PMC，取不到內容則改判 `待人工補全文`(`channels_exhausted=true`)。
3. **防『有 OA 連結卻不抓就丟待評估』** `stage1_check`：原則＝能 trace 到全文/摘要者一律進下一關。awaiting 帶 `oa_url` 卻無 `oa_fetch_attempted=true` → FAIL；OA 是可抓取管道，必須實際下載並嘗試解析（PDF/HTML），取得內容→升回候選，解析失敗才掛待評估並標 `oa_fetch_attempted`。
4. **防『③ 只憑摘要 punt 成待評估』** `gate_guard.check_screen_awaiting_resolved`：③候選都已有內容，須用全文/摘要做出切題/離題二元判定；`g2c_awaiting_classification.json` 內有 doi/pmid 卻無 `fulltext_checked/oa_fetch_attempted/channels_exhausted` 證明 → FAIL（不得只憑摘要把對照 C 看不出者掛待評估，須先抓全文核對）。
5. `selftest_guards.py`：為 (1)(2)(3)(4) 各加 FAIL fixture＋正向控制，全綠。
6. `SEARCH_SPEC.md`：四條 gate 都寫進「機器守門」段落。
7. `.gitignore`：補上 `cache/`（先前漏列，14MB 可重生檢索中間檔成 untracked）。
8. **軸比對品質守則（SEARCH_SPEC，非 gate 而是 guidance）**：③ 同義詞比對須(a)正規化分隔符(slash/hyphen/en-dash/逗號/and)＋詞幹；(b)C 軸禁用「會成為三合一名稱子字串的藥對」(umeclidinium vilanterol⊂FF/UMEC/VI 等)與「two long-acting bronchodilators」(描述三合一組成)當訊號；(c)對照臂精判屬 ⑦。緣由：實跑時 ETHOS/KRONOS 因 en-dash／複數被誤判離題、FULFIL/TRILOGY 因藥對子字串被誤判切題。此屬 per-run 篩選器的同義詞品質問題（不是結構不變量），故落為 SPEC guidance 而非機器 gate；篩選器本體在 gitignored cache、不進 repo。
9. **PDF 渲染器跨平台修復（`build_search_report.py` `_font()`）**：原本只找 Windows `msjh`，缺檔時退 `STSong-Light` 卻仍以字型名 `CJK` 排版→非 Windows(Linux 遠端/CI)渲染崩潰。改為依序找 msjh→settings.cjk_font→常見 Linux/Mac CJK TTF(文泉驛/Noto/PingFang)→最後退 STSong-Light 並以 `registerFontFamily/addMapping` 別名成 `CJK`。實跑：本容器以文泉驛成功渲染 SR 報告 PDF。

**fresh-clone／實跑結果**（守門變更的有意義證據＝自含的 selftest）
- `python EBM_Search/scripts/selftest_guards.py` → 全綠，含本輪新增 fixture（防搶跑、防兩者皆無、防有 OA 不抓皆會 FAIL；正向控制通過）。
- 對真實 cache 跑 `gate_guard.py --cache <dir>` → 全部已抵達關卡通過（Gate⓪ 策略核准、Stage A→B 邊界、Gate① 取盡/策略遵從/四軸、Gate②c Unpaywall 覆蓋）。
- 反向控制：`approved_by_user` 翻 false → exit 1 指名搶跑；awaiting 兩者皆無帶 pmid → stage1_check FAIL。

**想被重點看 / 自己不確定的點**
- `approved_by_user` 是「Claude 在使用者口頭確認後自行寫入」的旗標，有「自證」疑慮（理論上可不問就設 true）。判斷：仍有價值（把確認變成顯式、可稽核、Stop hook 會擋的步驟）；若需更強證據（approval_note 附原話／時間戳）請指出。
- 「兩者皆無僅限無 ID」是否過嚴？我認為合理：有 DOI/PMID 代表文獻存在、全文必在某處（至少付費牆），honest 標籤是 `待人工補全文` 而非 `兩者皆無`。
- gate 綁 `g1_legs_manifest.json` 檔名；若未來改名需同步。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

- ✅ 已修：🔴 check_no_retracted 漏判「僅有 DOI 的撤稿」（Crossref is-retracted 多以 DOI 為憑、撤稿文獻可能無 PMID）→ 新增 `retr_dois` 集合，下游 報告/背景/Zotero/交接包 一律同時比對 pmid 與 `_norm_doi(doi)`。+selftest 回歸（DOI-only 撤稿須擋；含大小寫正規化驗證 10.1/retracted vs 10.1/RETRACTED）。
- ✅ 已修：🔴 check_waiting_fulltext 全文路徑漏 `oa_url` → 條件加 `or r.get("oa_url")`，與前關一致。+selftest 回歸。
- ✅ 已修：🟡 stage1_check「兩者皆無」再補 `pmcid`（Europe PMC 常只有 pmcid）；並同步把 `pmcid` 加進 check_screen_awaiting_resolved 的 has_path（兩 awaiting 關保持對稱）。+selftest 回歸（pmcid-only 兩者皆無 須 FAIL）。

- ✅ 已修：🔴 stage1_check「兩者皆無」漏判 oa_url-only（只有 oa_url、無 doi/pmid 會被當兩者皆無漏掉）→ 條件加 `or a.get("oa_url")`、訊息同步。+selftest 回歸（oa_url-only 兩者皆無 → FAIL）。
- ✅ 已修：🔴 gate_guard `check_screen_awaiting_resolved` 的 `has_path` 同樣漏 oa_url → 加 `or a.get("oa_url")`、docstring 同步。+selftest 回歸（oa_url-only 待評估未核對 → FAIL）。
- ✅ 已確認（暫不改）：🟡 gate 多處 hardcode 檔名（g1_legs_manifest.json/g0_strategy.json）。審查端亦認「目前架構可接受」。依「改動最小化」暫不重構成常數；若未來改檔名再集中定義。
- ✅ 已確認（無需改動）：⚪ approved_by_user 自證機制足夠（卡點價值已達成，幻覺亂填才需 approval_note）；⚪「兩者皆無僅限無 ID/路徑」限制合理。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
