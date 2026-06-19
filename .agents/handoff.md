## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

**【初審】功能塊：EBM_Search 防『搶跑』機器 gate ＋ cache gitignore 修正**

**本輪審查範圍：僅以下檔案**
- `EBM_Search/scripts/gate_guard.py`
- `EBM_Search/scripts/selftest_guards.py`
- `EBM_Search/SEARCH_SPEC.md`
- `EBM_Search/.gitignore`

**背景／動機**：實跑 triple-vs-dual COPD 檢索時，發生兩件使用者糾正的事：(1) 未先報告檢索策略、未等使用者確認就執行檢索；(2) 檢索時自行縮放範圍（私自把 OpenAlex/EuropePMC 收窄成標題）。既有守門只管檢索品質（取盡／四軸／策略遵從），**無任何機器檢查管「先報策略→等確認→才檢索」**。依 AGENTS.md「機器守門優先於記性／把使用者抓到的缺失轉成 gate」，將其落為機器 gate。

**這輪改了什麼**
1. `gate_guard.py`：新增 `check_strategy_approved`——當廣蒐產物 `g1_legs_manifest.json` 存在時，`g0_strategy.json` 必須帶 `approved_by_user:true`（使用者確認策略後才設），否則 FAIL。已 wire 進 `_all_checks`（排在最前）＋ Stop hook（FAIL→exit 2 擋回合）＋更新模組 docstring 的 gate 對照。
2. `selftest_guards.py`：新增一條 FAIL fixture（g1 已產出但未核准）＋一條正向控制（已核准→通過），維持全綠。
3. `SEARCH_SPEC.md`：在「機器守門」段落白紙黑字寫進此 gate，並聲明任何範圍變更須回到此停頓點重新報告＋重新核准。
4. `.gitignore`：補上 `cache/`（與 `EBM_Analysis/cache` 慣例一致；先前漏列，導致 14MB 可重生檢索中間檔成為 untracked）。

**fresh-clone／實跑結果**（守門變更的有意義證據＝自含的 selftest，非整條管線）
- `python EBM_Search/scripts/selftest_guards.py` → 全綠，含兩條新 Gate⓪ fixture（FAIL fixture 會 FAIL、正向控制通過）。
- 對真實 cache 跑 `gate_guard.py --cache <dir>` → 新 gate「Gate⓪ 策略經使用者核准才可檢索」**通過**（該 run 的 g0 已標 approved_by_user:true）。
- 反向控制：把 `approved_by_user` 暫時翻成 false → `gate_guard` exit 1、指名 Gate⓪ 搶跑；還原後恢復通過。

**想被重點看 / 自己不確定的點**
- `approved_by_user` 是「Claude 在使用者口頭確認後自行寫入」的旗標，存在「自證」疑慮（理論上 Claude 可不問就自設 true）。我的判斷：它仍有價值——把「是否真的問過使用者」變成一個顯式、可稽核、Stop hook 會擋的步驟，比純靠記性強；但若審查端認為需要更強的不可偽造證據（例如要求 approval_note 附使用者原話／時間戳），請指出。
- gate 觸發條件綁定 `g1_legs_manifest.json` 存在；若未來把廣蒐產物改名，需同步更新——是否要改綁更穩定的哨兵？
- 放在 `_all_checks` 最前、訊息語氣是否恰當。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
