## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-25 本輪審查範圍＝2 檔
- **新增 `EBM_Search/scripts/public_legs.py`**
- **修改 `EBM_Search/SEARCH_SPEC.md`**（machine-guard 區塊後新增一條 public_legs 鐵律）

**動機**：Gate ① 執行「Benralizumab vs Mepolizumab」廣蒐時，手刻 urllib 取得碼出現兩個 bug —
(BUG-1 編碼) OpenAlex filter 值內預放 `%20` 被 `urlencode` 二次編碼成 `%2520` → 回 0 筆（會丟資料）；
(BUG-2 取盡) OpenAlex `meta.count` 是估計值，用 `fetched>=count` 判取盡 → `leg_exhaust_check` 因差 1 筆誤判 FAIL。
根因＝框架對「公開 API 檢索腿」缺 committed 可重用器（PMC 側有 `pmc_fulltext.py`，廣蒐側沒有），故每輪手刻易復發。

**修正內容**：
- `public_legs.py` 提供 `fetch_openalex/europepmc/ctgov/pubmed`，一律 `urlencode` 單次編碼（值內嚴禁預放 %XX）；
  OpenAlex 取盡改看 `next_cursor is None`，`hitCount=fetched`、估計值另存 `count_estimate`；內建 `--selftest`。
- `SEARCH_SPEC.md` 加鐵律：Gate ① 公開腿一律 import `public_legs`、禁手刻 urllib，並載明 BUG-1/BUG-2 與防法。

**自我驗證**：`python EBM_Search/scripts/public_legs.py --selftest` 全過（編碼安全、filter 無二次編碼、取盡語意齊全）；
repo 與 AppData 安裝副本各跑一次皆通過、兩邊已同步。**尚未 commit**。

**請 Antigravity 審查重點**：
1. `public_legs.py` 的取盡語意（OpenAlex `next_cursor=None` 判定、count_estimate 與 `leg_exhaust_check` 的相容性）是否正確；
2. urlencode 單次編碼是否對 EuropePMC 布林語法（括號/冒號/引號）也安全、無漏編；
3. SEARCH_SPEC 新鐵律與既有 `sr_filter_composite_check`/`leg_exhaust_check` 敘述有無衝突。

> 註：先前誤把本檔當一般 changelog 覆寫過、已 `git checkout` 還原為本模板，未污染既有內容。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
