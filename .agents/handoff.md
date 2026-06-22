## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：修正「SR filter 啟用時，非 PubMed DB 腿的『無過濾主檢』全文噪音被灌進篩選語料庫」的流程 bug，並落為機器守門避免復發。

**本輪審查範圍：僅以下檔案**
- `EBM_Search/scripts/sr_division_check.py`（新增：SR 分工硬 gate）
- `EBM_Search/scripts/gate_guard.py`（接線：新增 `check_sr_division`＋列入 `_all_checks`；另：③ 關名重命名）
- `EBM_Search/scripts/selftest_guards.py`（新增 3 條 SR 分工回歸 fixture；另：③ 關名重命名）
- `EBM_Search/SEARCH_SPEC.md`（第 93 行 SR 過濾器段：由「additive 聯集進池」改為「DB 腿只以 -SR 結果進語料庫」定版；另：③ 關名重命名）
- `EBM_Search/scripts/fulltext_exhaust.py`（③ 關名重命名）
- `EBM_Search/scripts/strict_screen_check.py`（③ 關名重命名）

**附帶變更（第③關重命名，使用者指示）**：把第③關名稱「融合式分層升級嚴格篩」統一改為「**全文/摘要搜尋及嚴格離題篩選**」（語意/流程不變，純命名）。涵蓋 SEARCH_SPEC.md（管線步驟編號＋v0.22 定版段，line 24 保留「舊名」對照供追溯）、gate_guard.py／selftest_guards.py／fulltext_exhaust.py／strict_screen_check.py 各 docstring/註解。selftest 重跑「✅ 全部守門有效」。

**附帶變更2（②b→③ 停頓點機器化，使用者指示）**：使用者糾正「②b 高敏初篩完成後應先停下報告、點頭後才進 ③」（spec line 40 早有此停頓點，但本輪 agent 把 ②b→fetch→③ 一口氣跑完）。新增機器 gate `check_2b_stop`（併入 `gate_guard`，與 `check_strategy_approved`「⓪→① 防搶跑」對稱）：②b 產物 `g2b_survivors.json` 完成後，須於 `g2b_checkpoint.json` 設 `approved_by_user:true` 才可進 ③；`g3_FINAL_screen.json` 已產出但 ②b 未核准＝FAIL。SEARCH_SPEC.md line 40 加註此 gate。selftest 加 3 條回歸（搶跑會 FAIL、停在 ②b 不誤擋、②b 核准後通過）。本次 run 已據此把過早產出的 ③ 產物改名為 `g3_FINAL_screen.premature.json` 暫存、cache 回到 ②b 停頓點（gate_guard 全過）。涉及檔：`gate_guard.py`、`selftest_guards.py`、`SEARCH_SPEC.md`（皆已在本輪範圍內）。

**背景（bug 怎麼來的）**：triple vs dual COPD 案，使用者選擇套用 SR filter。原本把 EuropePMC『無過濾主檢』（EuropePMC REST 預設全文檢索）的 3816 筆全文泛提及噪音直接 dedup 進 `g1_union`（語料庫），使用者糾正：「當我決定用 SR filter 時，DB 腿應只給我 SR 搜尋結果」。

**修法**：
- 規則（SEARCH_SPEC §SR filter）：SR filter 啟用時，有 SR 變體的非 PubMed DB 腿（EuropePMC/Consensus/OpenAlex）**只以 `<leg>-SR` 結果進語料庫**；原始 RCT 走 PubMed 腿、SR/MA 走 -SR 腿、登錄試驗走 CT.gov；無過濾主檢只留作 manifest 取盡/稽核紀錄，不進語料庫。
- 機器 gate `sr_division_check`：由 g0 判 SR filter 是否啟用（`sr_filter_decision=="applied"` 或 legs 含 `-SR`）；啟用時若 `g1_union` 任一筆 provenance 含「有 SR 變體之非 PubMed DB 腿的主檢（同 base、非 -SR）」即 FAIL。PubMed/CT.gov 天然不在受限集合。

**fresh-clone/實跑結果**：
- `selftest_guards.py` → 「✅ 全部守門有效」；新 3 條 SR fixture：FAIL 案有觸發、2 條防誤報（只 -SR/PubMed/CT.gov 進池；未啟用 SR filter）皆通過。
- 本案 cache 實跑：`sr_division_check` standalone PASS、`gate_guard --cache` 全部已抵達關卡通過（含新關「Gate① SR分工」✅）。

**想被重點看 / 不確定點**：
- (1) 我把 SEARCH_SPEC 既有「additive、不損 recall」定版**改成**「DB 腿主檢不進語料庫」。取捨：真實世界觀察性研究（非 RCT、非 SR）較不易進池——這是依使用者明確決策做的，已在對話告知並提供「要的話把 Consensus 主檢觀察性加回背景池」。請確認此 spec 改寫無自相矛盾、且與 leg_exhaust（主檢仍須取盡）不衝突。
- (2) gate 啟用條件用「union 是否存在」區分『SR 已啟用但語料庫未組（暫不適用）』vs『已組須稽核』，請看這個 None/[] 邏輯是否會漏擋。

**附帶變更3（『全文及摘要皆無』必須真查過 Unpaywall，使用者糾正）**：使用者問「全文及摘要皆無的部分，是否有查過 unpaywall？」——查核發現本輪 Tier3 是手刻、只試了 EuropePMC PMC fullTextXML，**沒跑 Crossref 摘要／Unpaywall** 就把 23 筆標 `channels_exhausted=true`。用 repo 既有 `fulltext_exhaust.py`（PMC→Crossref 摘要→Unpaywall 全部 oa_locations）實跑後，**13/23 其實取得到內容**（多為 Crossref 摘要、部分 PMC 全文）→ 該桶誤判。修正：(1) 強化機器 gate `check_nocontent_bucket`——『全文及摘要皆無』且有 DOI 者，須帶 `unpaywall_checked=true`，否則 FAIL（不可只試 PMC 就宣稱三層皆失敗）；(2) SEARCH_SPEC.md line 31 加註此要求＋指明用 `fulltext_exhaust.py` 跑完整管道；(3) selftest 加 2 條回歸（有 DOI 無 unpaywall_checked→FAIL；查過→通過）。涉及檔：`gate_guard.py`、`selftest_guards.py`、`SEARCH_SPEC.md`（皆已在本輪範圍內）。run-local 的 ③ Tier3（待 ②b 核准後重跑）會改用 `fulltext_exhaust` 完整管道。

**附帶變更4（把 Unpaywall 拆成獨立 Tier 4，使用者定版）**：使用者要求把「Tier 3 後仍『摘要及全文皆無』者」明確升級到**獨立 Tier 4＝用 Unpaywall 查 OA 全文並判離題**，避免 Unpaywall 被埋在 Tier 3 內部而被略過（正是附帶變更3 的 bug 成因）。修正：(1) SEARCH_SPEC.md v0.22 分層升級段由 3 層改 4 層——Tier 3＝Crossref 摘要＋PMC fullTextXML；**Tier 4＝Unpaywall 全部 oa_locations 探查**；『全文及摘要皆無』只能在 Tier 4 也失敗後定案（標 unpaywall_checked=true、tier=4）；『離題』可在 Tier 3／Tier 4 定案。(2) `check_nocontent_bucket` docstring/訊息改述為「Tier 4 未跑＝FAIL」（機器訊號仍是 DOI 者須 unpaywall_checked=true，與附帶變更3 同一檢查，語意對齊 Tier 4）。(3) run-local tier3.py 對走過 Unpaywall 的記錄標 tier=4。selftest 仍「✅ 全部守門有效」。涉及檔：`SEARCH_SPEC.md`、`gate_guard.py`（皆已在本輪範圍內）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
