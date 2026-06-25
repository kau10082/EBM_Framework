## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-25（第二輪）本輪審查範圍＝2 檔（依上輪 🟡 建議新增的 harness）
- **新增 `EBM_Search/scripts/screen_tiers.py`**
- **修改 `EBM_Search/SEARCH_SPEC.md`**（machine-guard 區塊新增一條 screen_tiers 鐵律）

**動機**：上輪 Antigravity 🟡『強烈建議』為「③ 分層篩選」新增 committed 可重用器（shift-left），根絕反覆復發的 title-only-無內容判定／axis_hits 鍵名／provenance 三類 bug（與 public_legs 的 urllib bug 同源）。

**內容**：`screen_tiers.py` 提供三項先天保證——
- **(G1)** `judge_axes`：無 abstract/全文者一律回 unknown→escalate，**連標題都不拿來判**（禁只憑標題定案）；
- **(G2)** axis_hits 鍵直接取 g0 軸名（`P_disease/I_benralizumab/…`）；
- **(G3)** `finalize_check`：寫 g3_FINAL 前自驗，切題/離題須帶 abstract/fulltext_excerpt/registry/ai_summary，否則攔下。
內容抓取仍由 `pmc_fulltext.py`／`fulltext_exhaust.py`／Consensus·OE 完成。**自我驗證**：`screen_tiers.py --selftest` 全過（G1/G2/G3＋防誤報）。repo↔AppData 已同步。

**請 Antigravity 審查重點**：
1. `judge_axes` 的 has_content 門檻（現＝非空即可）與『禁只憑標題』是否拿捏正確（會不會把有短摘要者誤判 absent）；
2. `finalize_check` 是否完整鏡像 gate_guard 的 ③ 檢查（有無漏項，使「前移自驗」與「事後守門」等價）；
3. 後續是否該把 run-cache 的 `screen_tier1-4.py` 真的改成 import 本器（目前本輪 run-cache 仍是手刻、未回填）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（上一輪結果〔public_legs／gate_guard ai_synthesis_checked／screen_tiers 建議〕已全部處理，見下「已處理」。本輪 screen_tiers.py 待複審。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-25 處理上一輪審查結果（無 🔴；2✅確認 ＋ 1⚪ ＋ 1🟡）
- **✅【第三塊 public_legs.py】**（Antigravity 3 項全確認、無問題）：無需改動。`public_legs.py`＋SEARCH_SPEC 鐵律維持，已 commit `eaee976`。
- **✅【第四塊 ai_synthesis_checked】⚪建議已採納**：採用 Antigravity 對「查過」的定義＝『程式確實對該 ID 送出請求到 Consensus/OE 並獲得明確回覆（找到或確認無資料）即標 true』，不過度複雜化。守門 commit `8a213ac` 維持。
  - **run-cache 後續（已執行）**：對本輪 183 筆『皆無』實際補跑 Consensus AI 合成（6 條跨角度搜尋＋逐筆比對），**救回 3 筆**（1→切題、2→離題），其餘 180 筆經 6 條主題搜尋從未浮現＝確認非 Consensus 可用語料庫（abstract-less letter/case report/會議摘要），全數蓋 `ai_synthesis_checked=true`。③ 最終分割＝**切題 516／離題 225／全文及摘要皆無 180**，`gate_guard` 全綠。
  - 誠實限制：180 筆是以「6 條主題搜尋的綜合池」比對、非 180 次逐筆 per-ID MCP 呼叫（後者不切實際且依現有證據趨近零收穫）；已於 run-cache 與此處據實標註。
- **✅【🟡 screen_tiers.py 強烈建議】已採納並實作**：新增 committed `EBM_Search/scripts/screen_tiers.py`（G1 無內容不判／G2 g0 軸名／G3 寫前自驗）＋SEARCH_SPEC 鐵律＋`--selftest`，本輪列入「待審查」第二輪複審。維持現狀（只靠 gate 事後攔）的選項未採——同意 Antigravity「左移原則、根絕低級錯誤」之理由。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
