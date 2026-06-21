## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：EBM_Search 策略/①關報告流程改善 ＋ SR Filter 分工（使用者 2026-06-21 於 triple-vs-dual COPD 實跑中連續提出）

本輪審查範圍：僅以下 2 檔
- `EBM_Search/SEARCH_SPEC.md`
- `EBM_Search/scripts/leg_exhaust_check.py`

改了什麼：
1. **① 廣蒐不含引文搜索**（SEARCH_SPEC.md，第①關停頓點新增鐵律）：第①關只「各腿用核准 query 廣蒐 → 跨腿去重」，**不做引文追蹤/snowball**；引文追蹤＝第④關、須在 ③ 定出核心後以核心為種子才做。OpenAlex／Europe PMC 在 ① 僅作廣檢，references/citations 引文鏈留待 ④；①報告勿讓使用者誤以為已做引文搜索。
2. **報告策略時主動問 SR Filter，且 SR Filter 用在『PubMed 以外』的腿**（SEARCH_SPEC.md，`check_strategy_approved` 段新增鐵律）：報告策略時必須主動問「是否套用 Systematic Review Filter」，並明確**分工**——**PubMed 腿維持 Cochrane 高敏感 RCT 過濾器**；**SR 過濾器套在 PubMed 以外的腿（Consensus／OpenAlex／Europe PMC）**補抓既有 SR/MA/NMA（Consensus `study_types`、OpenAlex/EuropePMC `PUB_TYPE`/標題）；ClinicalTrials.gov 為登錄庫、SR 不適用。SR 過濾器**additive**（每腿額外一條 SR 子查詢、聯集進池，不取代廣檢、不損 recall）；非 PubMed 的 SR 子腿用 `<leg>-SR` 命名並設 `design_filter_allowed:true`。
   - **修正歷程（使用者兩次糾正）**：第一版誤把 SR Filter 寫成套在 PubMed 腿 → 已改為「PubMed 以外的腿」。
3. **leg_exhaust gate 認得 `<leg>-SR` 子腿**（scripts/leg_exhaust_check.py）：新增 `_base()` 去掉 `-SR`/` sr`/`_sr` 後綴，讓 SR 子腿沿用母腿的窮盡分類（`Consensus-SR`→AI 合成腿免窮盡、`OpenAlex-SR`/`EuropePMC-SR`→可窮盡須 fetched≥hitCount）。配合第 2 點 `<leg>-SR` 命名約定，否則 SR 子腿會被誤判 FAIL。

fresh-clone / 自測：
- `python EBM_Search/scripts/selftest_guards.py` → ✅ 全部守門有效（含改過的 leg_exhaust）。
- 實跑 triple-vs-dual COPD cache：`gate_guard.py` 所有已抵達關卡通過（取盡/策略遵從/四軸覆蓋/四軸展開/對照軸純度）。SR 過濾器 additive 實證：EuropePMC-SR 淨增 34、Consensus-SR 淨增 3、OpenAlex-SR 淨增 0；文獻聯集 1333→1370。
- 附帶：comparator_purity gate 實際攔下我一版 Consensus-SR query 誤含「versus dual therapy」（C 軸詞）→ 已修為 C-clean query，gate 轉綠（守門有效，非放水）。

想被重點看：兩條新增鐵律措辭是否與既有「關責不外溢」「④引文追蹤」「SR 模式 PubMed 過濾器」「對照軸純度」段一致無矛盾；`leg_exhaust_check._base()` 後綴清單是否足夠（目前 `-sr`/` sr`/`_sr`/`-systematic-review`）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修:① 關報告誤含引文搜索語意（本輪修改:SEARCH_SPEC.md 第①關停頓點新增「廣蒐去重不含引文搜索、snowball 屬④」鐵律）
✅ 已修:報告策略時未主動問 SR filter（本輪修改:SEARCH_SPEC.md `check_strategy_approved` 段新增「主動詢問 SR Filter」鐵律）
✅ 已修:SR Filter 套用對象寫錯（誤寫成 PubMed 腿）（本輪修改:SEARCH_SPEC.md 改為「SR Filter 套在 PubMed 以外的腿、additive、`<leg>-SR` 命名、design_filter_allowed:true」；PubMed 維持 RCT 過濾器）
✅ 已修:leg_exhaust gate 不認得 SR 子腿會誤判（本輪修改:scripts/leg_exhaust_check.py 新增 `_base()` 去 `-SR` 後綴，SR 子腿沿用母腿窮盡分類；selftest 仍綠）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
