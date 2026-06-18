## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【本輪性質】**【初審】** — 新增機器守門，根治「擅自偏離核准檢索策略（私自加未核准過濾器）無人攔」的 bug。

**本輪審查範圍：僅以下檔（版控內）：**
- `EBM_Search/scripts/strategy_adherence_check.py`（**新增**）
- `EBM_Search/scripts/gate_guard.py`（接線：新增 `check_strategy_adherence`，併入 `_all_checks` 的 Gate ① 群）
- `EBM_Search/scripts/selftest_guards.py`（補一個會 FAIL 的 fixture）

**這塊在解什麼（bug）：**
- Stage A ① 廣蒐時，核准策略（「PubMed 套 Cochrane RCT 過濾器；**其餘腿不設計型限制以求 recall**」）只存在於對話／記性，**無任何機器關卡比對「實際送出的 query」vs「核准策略」**，導致我擅自在 OpenAlex／Europe PMC 加設計過濾、把 PubMed 過濾器擴大，無人攔下（已即時 revert）。

**修法（已實作）：**
- `strategy_adherence_check.check(manifest, strategy)`：讀 `g1_legs_manifest.json`（每腿須含實際 `query`）＋ `g0_strategy.json`（逐腿 `design_filter_allowed`）。被核准為 `design_filter_allowed=false` 的腿，其 query 若出現設計／品質過濾特徵（`[pt]`/`[ptyp]`、`systematic[sb]`、`PUB_TYPE:`、`randomi*`、`placebo[tiab]`、`meta-analysis`、`systematic review`、`controlled clinical trial`、`sjr`/`quartile`）→ FAIL；缺記 query、或腿不在 g0 → 亦 FAIL。
- 併入 `gate_guard`（Stop hook 自動跑）：只在 cache 有哨兵旗標時生效。
- `g0_strategy.json` 與每腿 `query` 由 ⓪ 核准／Stage A 廣蒐寫出（run-local `_fetch_legs.py` 已備妥，不在版控）。

**想被重點看 / 我不確定的點：**
1. `DESIGN_FILTER_PATTERNS` 是否漏列某種「設計／品質過濾」寫法（如其他登錄庫/平台的過濾語法），或是否可能**誤觸**正當的疾病/介入詞（目前測試：disease∧triple 分子名不誤觸）。
2. 「腿不在 g0_strategy.json 即 FAIL」是否過嚴（會擋掉 g0 未涵蓋的新腿——刻意如此，逼策略先落地；請確認此嚴格度可接受）。
3. gate_guard 對「manifest 在、g0 不在」會 FAIL：是否應放行為「尚未到此關」？（目前刻意 FAIL，逼 ⓪ 必寫 g0。）

**自測：**
- `python EBM_Search/scripts/selftest_guards.py` → 全部守門（含新守門）皆「會 FAIL（守門有效）」、總結「全部守門有效」。
- 正向測試：核准策略相容的 manifest（PubMed 帶 RCT 過濾＝allowed、其餘腿無過濾）→ 無誤報。
- fresh-clone 實跑結果見對話回報。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
