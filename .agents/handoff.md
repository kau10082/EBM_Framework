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

### 2026-06-25（追加 committed 修正）gate_guard：『皆無』桶須證明 AI 合成摘要也查過
**新增審查檔（committed）：`EBM_Search/scripts/gate_guard.py`＋`EBM_Search/scripts/selftest_guards.py`**

**使用者糾正**：規格 Tier 2＝『CT.gov 登錄欄位／**AI 合成摘要 Consensus·OE**』，內容鏈最後一關＝Consensus／OE AI 合成摘要，只有它也取不到才算『全文及摘要皆無』。但本輪 run-cache 的 `screen_tier2.py`（只做 Crossref→EuropePMC→OpenAlex）與 `screen_tier4.py`（`resolve_one`：Crossref→PMC→Unpaywall）**都沒跑 AI 合成 channel** → 183 筆『皆無』是漏一條 channel 就定案（over-claim）。鐵證：補跑 Consensus 後當場救回 2 篇。**且守門 `check_nocontent_bucket` 只要求 `fulltext_parse_attempted∧channels_exhausted∧unpaywall_checked`、不要求 AI 合成查過 → 兩洞相疊、守門照樣放行。**

**修正**：`check_nocontent_bucket` 增一條——『皆無』者須帶 `ai_synthesis_checked=true`，否則 FAIL（指出須先跑 Consensus／OE）。`selftest_guards.py` 加正向(z3/z5 補旗標)＋負向(z6 未查 AI→應 FAIL)回歸。**驗證**：`selftest_guards.py`＝「全部守門有效」；對本輪 cache 跑 `gate_guard` 正確攔出 183 筆缺 `ai_synthesis_checked`。repo↔AppData 已同步。**尚未 commit。**

**請 Antigravity 審查**：此規則與既有 unpaywall_checked 並列是否合理；AI 合成 channel 的「查過」定義（Consensus 命中即算？無命中也算查過？）是否需更嚴格界定。
**run-cache 待補**：183 筆尚需實際補跑 Consensus／OE AI 合成、重判後才能定案（範圍待使用者決定）。

### 2026-06-25（補記）③ 嚴格篩執行中的缺失 —— 皆 run-cache 腳本、非 committed 程式碼
**範圍說明**：以下發生在本輪 run-cache 的篩選腳本（`cache/<topic>/screen_tier1-4.py`、`fix_*.py`），**不在 repo committed 檔內**，故不增列 repo 審查檔；登錄於此供複查並提出一個框架硬化問題。**三項皆由既有 `gate_guard.py` 攔下、修正後全綠**，整體性檢查確認 921 進=921 出、uid 唯一、⊇②b 倖存者相等、核心比較研究 49 篇仍在切題（證據基礎未受損）。

**抓到的缺失（均 gate 攔下→修正）**：
1. **(真 bug) title-only 憑標題判切題、無內容**：Tier 3 對 6 筆無摘要無全文者，因標題同時含三軸即判切題 → `check_screen_partition`（來源證明）攔下。修：補抓內容，1→切題、5→awaiting。**這是唯一會影響判定的 bug。**
2. **(真 bug) `axis_hits` 鍵名錯**：用通用 `P/I/C`，但 `strict_screen_check` 要 g0 軸名 `P_disease/I_benralizumab/C_mepolizumab` → 報「放水」。修：重映射鍵名（現 0 筆錯）。
3. **(真 bug) 最終檔未帶內容原文**：分層腳本只存 `axis_hits`、未存摘要/全文摘錄 → 來源證明 gate 報「741 筆無內容卻有判定」。修：把摘要/全文摘錄補回每筆。
4. **(流程) 逐 Tier 核准檔未寫**：使用者口頭逐關核准（回「繼續」）但未落 `g3_tierN_checkpoint.json` → 報「跨 Tier 搶跑」。修：補寫核准檔。
5. **(顯示假象，非資料) Tier1 一度顯示 0 切題**：PowerShell 管道傳 Python 時 `切題` 字串編碼被弄壞、比對失敗；實際 g3_tier1.json 為 370 切題。改檔案式重印即正常。

**給 Antigravity 的框架硬化問題（需裁決，非立即改）**：
- 缺失 1/2/3 與 Gate① 的 urllib bug 同源——**框架對「③ 分層篩選」也沒有 committed 可重用器**，每輪由 Claude 手刻 tier 腳本，故 title-only-無內容判定、axis_hits 鍵名、內容 provenance 未隨記錄帶出 等易復發。問題：是否值得新增一支 committed `screen_tiers.py`（封裝「軸判定須有內容、axis_hits 用 g0 軸名、最終檔必帶 content 證明」），把這三項從「靠 gate 事後攔」前移到「器內先天保證」？抑或維持現狀（既有 gate 已能攔、足矣）？
- 註：本補記**不新增 committed 檔**，故第一段「本輪審查範圍＝2 檔」不變；本段為觀察與待裁決問題。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
