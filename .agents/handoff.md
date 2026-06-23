## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】

**功能塊**：SR filter 守門強化（兩道新 gate，同一功能塊）。把使用者兩條關於 SR filter 的鐵律從靠記性變機器看守：
- (1) `check_sr_filter_decided`——報告檢索策略時**必須問過**「是否套用 SR filter」並做出決定（防忘了問；與 `check_strategy_approved` 對稱）。
- (2) `check_sr_filter_composite`（本輪新增）——SR filter **不可只靠出版類型(Publication Type)**，須為**複合語法『控制詞彙(PubType/MeSH/Emtree) ＋ 自由文字詞(Title/Abstract)』並用**（Cochrane MECIR C33；只靠 PubType 會因索引時間差/索引不一致漏掉最新未索引 SR/MA）。

**動到哪些檔（本輪審查範圍：僅以下檔）**：
- `EBM_Search/scripts/sr_filter_composite_check.py`（**新檔**）——對每條 SR 子腿（`<leg>-SR`／g0 role=SR_MA_NMA）且用 Boolean query 者，斷言 query 同時含控制詞彙成分（SR 詞綁 `[pt]/[ptyp]/[mesh]/[mh]/[sb]` 或 `pub_type:`）與自由文字成分（SR 詞綁 `[tiab]/[ti]/[tw]/[ab]`、或 `title:/abstract:` 欄位語法、或裸詞＝預設搜文字）；缺任一→FAIL。AI 合成腿（role=ai_synthesis／exhaustible=false，如 Consensus-SR 用 study_types）豁免。
- `EBM_Search/scripts/gate_guard.py`——新增 `check_sr_filter_decided`（含常數 `SR_DECISION_DECIDED`）與 `check_sr_filter_composite`；兩者註冊進 `_all_checks`；更新檔頭 docstring 關卡清單。
- `EBM_Search/scripts/selftest_guards.py`——新增回歸：(a) SR decided：pending FAIL／缺欄位 FAIL／declined 通過；(b) SR composite：只用 PubType FAIL／只用自由文字 FAIL／PubType＋tiab 複合通過／AI 合成腿豁免通過。
- `EBM_Search/SEARCH_SPEC.md`——「主動詢問 SR Filter」段：加註 `check_sr_filter_decided`（決定值與流程）；修正先前誤寫的「PubType **或** Title/Abstract」→明定**複合語法並用**，補 MECIR C33／索引時間差理由與標準 PubMed 範例，註明由 `check_sr_filter_composite` 看守。

**fresh-clone / 實跑結果**：`python EBM_Search/scripts/selftest_guards.py` → `✅ 全部守門有效。`（新增兩組 SR filter 回歸全綠：decided pending/缺欄位 FAIL✅、declined 通過✅；composite 只 PubType/只自由文字 FAIL✅、複合通過✅、AI 腿豁免✅；既有守門無回歸。）

**想被重點看 / 自己不確定的點**：
1. `sr_filter_composite_check` 的「自由文字成分」偵測含「裸詞（SR 詞後無 `[欄位]` 標籤）視為搜 title/abstract」——對 EuropePMC/OpenAlex 預設全文/標題摘要檢索成立，但對 PubMed 裸詞其實是 all-fields。本 gate 僅用於 SR 子腿（非 PubMed RCT 腿），故影響有限；此寬鬆判定是否可接受，或應收緊為「必須有明確 `[tiab]`/`title:` 欄位語法」？
2. 複合語法要求目前**只套在 SR 子腿**；PubMed 的 Cochrane RCT 過濾器本身已是複合（`randomized controlled trial[pt] OR randomized[tiab]…`），未另立 gate。是否需要對 RCT 腿也加同類複合檢查。
3. 合法「不套用」token 收了 `declined`／`not_applied`／`none`；過寬與否請評估。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
