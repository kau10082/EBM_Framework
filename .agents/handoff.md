## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】

**功能塊**：檢索前/初篩守門強化（三道新 gate，同屬「把使用者口頭鐵律變機器看守」一塊）：
- (1) `check_sr_filter_decided`——報告策略時**必須問過**「是否套用 SR filter」並做出決定（防忘了問；與 `check_strategy_approved` 對稱）。
- (2) `check_sr_filter_composite`——SR filter **不可只靠出版類型**，須為**複合語法『控制詞彙(PubType/MeSH/Emtree) ＋ 自由文字詞(Title/Abstract)』並用**（Cochrane MECIR C33；只靠 PubType 會因索引時間差/索引不一致漏掉最新未索引 SR/MA）。
- (3) `check_2b_abstract_screen`——**②b 高敏初篩必須以『標題＋摘要』篩，嚴禁只憑標題**（Cochrane/MECIR 高敏感紅線；與 ④ 的 `citation_screen_check` 對稱）。先前 ②b 實作只用標題＋登錄欄位（抓的是 lite 記錄、無摘要）＝只憑標題初篩，會漏殺「標題用成分名/縮寫/廣義詞、或 PK/沉積只寫藥名」的相關研究。
- (4) `check_screen_tier_stops`——**③ 內部 Tier 1→2→3→4 每層之間必須停下報告、經使用者核准才可進下一層**，嚴禁一個「繼續」把 T2→T3→T4 連跑（尤以 Tier 3/4 全文抓取量大、可能誤判）。先前實作把 Tier 2/3/4 一次背景跑完＝跨 Tier 搶跑。與 `check_2b_stop` 等停頓 gate 同構。
- (5) `classify_units.py` 對照臂判定強化（本輪，使用者抓出 TRIVERSYTI 誤判）——三件事：
  - (5a) 樞紐表更正：`PIVOTAL_LABALAMA_ARM["TRIVERSYTI"]` `True`→`False`（BDP/FF/G **vs BDP/FF＝ICS/LABA**，非雙支擴對照，與 FULFIL/TRILOGY 同類；先前 curation 誤標）。
  - (5b) ⑤b review-flags 新增**摘要矛盾偵測**：`core_basis=pivotal_trial_design` 但摘要對照疑為 ICS/LABA 且無雙支擴訊號 → 列待覆核。
  - (5c) **CT.gov 登錄各臂交叉核對 tripwire**：跑 `--enrich`（`resolve_arms`）抓每個核心試驗 NCT 的逐臂成分，與樞紐表交叉比對；**不一致記 `table_discrepancy` 攤出待人工，不靜默覆蓋**。**刻意不讓 CT.gov 凌駕表**——實測 CT.gov 逐臂 regex 兩種噪音都會發生：假陽（arm 描述跨臂提及三類藥→`has_triple` 誤 True，如 ILLUMINATE QVA149 其實 dual vs ICS/LABA）、假陰（三合一以品牌/開發代號命名未被成分庫命中→`has_triple` 誤 False，如 TRIBUTE extrafine BDP/FF/G）。故 CT.gov 只當「負向排除（無三合一臂→背景）」＋「不一致告警」，正向核心仍須樞紐表或 ICS 退階確認。實跑驗證：TRIBUTE 仍核心、TRIVERSYTI/ILLUMINATE 正確歸背景、ETHOS-ext 出現 1 筆 CT.gov 假陰告警（保留核心、flag 待人工）。

**動到哪些檔（本輪審查範圍：僅以下檔）**：
- `EBM_Search/scripts/sr_filter_composite_check.py`（**新檔**）——SR 子腿 Boolean query 須同時含控制詞彙成分（SR 詞綁 `[pt]/[ptyp]/[mesh]/[mh]/[sb]`、`pub_type:`、或 document/work-type 如 `type:review`）與自由文字成分（`[tiab]/[ti]/[tw]/[ab]`、`title:/abstract:` 欄位語法、或裸詞）；缺任一→FAIL。AI 合成腿（role=ai_synthesis／exhaustible=false）豁免。
- `EBM_Search/scripts/screen_2b_abstract_check.py`（**新檔**）——讀 `g2b_screen.json`（結構化），斷言 `screening_method="title+abstract"`、`abstracts_fetched>0`、`title_only_dropped==0`，且任一被剔除且有 ID 的記錄須有摘要證據（`has_abstract=true` 或 `abstract_status∈{none_after_fetch,registry,conference}`）；舊版純 list/只憑標題→FAIL。
- `EBM_Search/scripts/gate_guard.py`——新增 `check_sr_filter_decided`（含 `SR_DECISION_DECIDED`）、`check_sr_filter_composite`、`check_2b_abstract_screen`、`check_screen_tier_stops`；四者註冊進 `_all_checks`；更新檔頭 docstring。
- `EBM_Search/scripts/selftest_guards.py`——新增回歸：SR decided（pending/缺欄位 FAIL、declined 通過）；SR composite（只 PubType／只自由文字 FAIL、複合通過、AI 腿豁免）；②b abstract（純 list FAIL、有 ID 無摘要證據剔除 FAIL、剔除者有摘要證據通過）；③ tier-stops（Tier2/FINAL 上層未核准 FAIL、逐層核准通過）。
- `EBM_Search/SEARCH_SPEC.md`——「主動詢問 SR Filter」段加註 `check_sr_filter_decided` 與複合語法(MECIR C33)修正；②b 段加註『標題＋摘要』鐵律與 `check_2b_abstract_screen`；③ 段加註『逐 Tier 停頓報告』鐵律與 `check_screen_tier_stops`。
- `EBM_Search/scripts/classify_units.py`——`PIVOTAL_LABALAMA_ARM["TRIVERSYTI"]` True→False（對照為 ICS/LABA 非雙支擴）；review-flags 新增「樞紐表標核心但摘要對照疑為 ICS/LABA」矛盾偵測。

**fresh-clone / 實跑結果**：`python EBM_Search/scripts/selftest_guards.py` → `✅ 全部守門有效。`（三組新回歸全綠；既有守門無回歸。）後續會在本 run 真正重抓摘要、以標題＋摘要重跑 ②b（runtime，cache 為 gitignored，不進此審查範圍）。

**想被重點看 / 自己不確定的點**：
1. `sr_filter_composite_check` 的「自由文字成分」偵測含「裸詞視為搜 title/abstract」——對 EuropePMC/OpenAlex 預設檢索成立，PubMed 裸詞其實是 all-fields；本 gate 僅用於 SR 子腿，影響有限。此寬鬆判定是否可接受。
2. 複合語法/標題＋摘要要求只套在 SR 子腿與 ②b；PubMed Cochrane RCT 過濾器本身已複合，未另立 gate。是否需擴及 RCT 腿。
3. `check_2b_abstract_screen` 允許「無摘要者標 abstract_status 後只用標題判」——此例外是否足夠收斂（會不會被濫用為『一律標 registry 跳過抓摘要』？目前 gate 另要求 `abstracts_fetched>0`，但未逐筆驗證 registry 標記正確性）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
