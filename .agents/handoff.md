## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】

**功能塊**：新增機器守門 `check_sr_filter_decided`——把「報告檢索策略時必須主動問使用者『是否套用 Systematic Review Filter』」這條鐵律（SEARCH_SPEC §★，2026-06 使用者糾正）從靠記性變機器看守。先前只有 `sr_division_check`（驗 SR filter *若套用* 的分工），沒有任何 gate 強制「這個問題有被問過並做出決定」；本輪補上，與既有 `check_strategy_approved`（⓪→① 防搶跑）對稱。

**動到哪些檔（本輪審查範圍：僅以下檔）**：
- `EBM_Search/scripts/gate_guard.py`——新增 `check_sr_filter_decided(cache)`（在 `check_strategy_approved` 之後）＋常數 `SR_DECISION_DECIDED`；註冊進 `_all_checks`；更新檔頭 docstring 關卡清單。
- `EBM_Search/scripts/selftest_guards.py`——新增三條回歸：`sr_filter_decision="pending"` 應 FAIL、缺欄位應 FAIL、`declined`（已決定）應通過（防誤報）。
- `EBM_Search/SEARCH_SPEC.md`——在「主動詢問 SR Filter」鐵律下加註此規已落為 `check_sr_filter_decided`，並定義合法決定值與流程（先 `pending`、得答覆後改 `applied`／`declined`）。

**判定邏輯**：`g1_legs_manifest.json`（Stage A 廣蒐產物）存在時，`g0_strategy.json.sr_filter_decision` 必須 ∈ {applied, declined, not_applied, none}；停在 pending／缺漏 → FAIL。g1 未產出（尚未廣蒐）→ 回 None（此關不適用），不誤擋策略撰寫階段。

**fresh-clone / 實跑結果**：`python EBM_Search/scripts/selftest_guards.py` → 全部守門有效（新增三條 SR filter 回歸：pending FAIL ✅、缺欄位 FAIL ✅、declined 通過 ✅；既有守門無回歸）。`✅ 全部守門有效。`

**想被重點看 / 自己不確定的點**：
1. 合法「不套用」token 我收了 `declined`／`not_applied`／`none` 三種同義寫法，避免下游或我自己用詞不一致誤擋；過寬與否請評估。
2. 是否該同時要求「若 `sr_filter_decision="applied"` 則 legs 必含 `<leg>-SR`」——目前那層落地由既有 `sr_division_check` 在 `g1_union` 階段把關，本 gate 只管「有沒有決定」，刻意不重疊（避免在 g1_union 尚未產出時誤擋）。此分工是否恰當。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
