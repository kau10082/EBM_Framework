## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-25（第四輪【初審】）本輪審查範圍＝1 檔
- **修改 `EBM_Search/scripts/build_search_report.py`**

**動機**：⑥ 產 Phase 1 PDF 時，PDF 正規產生器出現 3 個 committed bug（先前只在 run-cache 繞過、未修 committed）：
1. **(🔴 會 crash) `_out_dir` 只剝雙引號**（`build_search_report.py:82-88`）：settings.yaml 的 Windows 路徑用**單引號**（`pdf_output_dir: 'C:\…\reports'`，避免反斜線轉義），舊 regex `"?([^"\n]+)"?` 把單引號連同值一起回傳 `'C:\…'` → `makedirs` 報 WinError 123 crash、PDF 產不出。
2. **(🟡 產出無副檔名) `--name` 未補 `.pdf`**（main）：傳 `--name foo`（無副檔名）→ 寫出 `foo`（無 `.pdf`），需手動改名。
3. **(🔴 守門找不到) 渲染後未回寫 `pdf_path`**：產生器從不把 `pdf_path` 寫回 `_search_report.json` → gate_guard『Phase1 PDF 實體產出』報『無 pdf_path』，須手動登記。

**修正**：
1. regex 改 `['"]?([^'"\n#]+)['"]?`（容單/雙引號＋行內註解）→ 單引號設定可正確解析。
2. main 補 `if not name.lower().endswith(".pdf"): name += ".pdf"`。
3. `build()` 後把 `data["pdf_path"]=out_pdf` 回寫 `_search_report.json`。

**驗證**：不帶 `--out`（靠單引號 config 解析）＋ `--name` 無副檔名 → 正確輸出 `…\reports\…Phase1.pdf`、pdf_path 已登記、檔案存在 159067 bytes。repo↔AppData 已同步。

**請 Antigravity 審查**：(a) 單引號 regex 是否會誤吃路徑含 `#` 者（Windows 路徑通常無 `#`，但值得確認）；(b) `pdf_path` 回寫 `_search_report.json` 會不會與 `build_search_report_data.py` 的確定性重組衝突（下次重跑 data builder 會覆蓋掉 pdf_path，需重渲染才回填——是否可接受）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無當前仍存在的問題。screen_tiers.py 第三輪複審＝2✅＋1⚪、無 🔴/🟡，已處理並結案。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-25 第三輪複審結案（screen_tiers.py / SEARCH_SPEC.md）
- **✅(a) 跨軸長詞遮蔽不會反向誤殺**：Antigravity 核對 `judge_axes` 長詞優先＋僅遮蔽該次命中 span，合法獨立命中不受阻。作者亦自驗現檔 `screen_tiers.py:55-77`（normalized masked＋longest-first＋span mask）。
- **✅(b) finalize_check 的 fetched-proof 判準與 gate_guard 100% 一致**：Antigravity 字元級核對；作者自驗現檔 `screen_tiers.py:133-137` ＝ `gate_guard.check_screen_partition` 同條件。
- **⚪(c) 「對照軸同義詞須專屬」是否升級機器 gate → 採納 Antigravity 建議：暫不升級**。理由：長詞遮蔽已對重疊泛詞 fail-safe（寧退離題、不產假切題），且 SEARCH_SPEC 已立文字鐵律；不另寫 NLP 子字串檢查器。**若日後再現假切題，再升級為機器 gate**（留作未來觸發條件）。
- **結論**：兩個第二/三輪新發現問題（對照軸假命中、fetched fallback）逐項核對在現檔已不存在；本塊結案，screen_tiers.py 可投入下一主題 ③。

### 2026-06-25 處理第二輪審查結果（第五塊）＋ 自我複審補抓
- **✅【第五塊 (1) has_content／(2) finalize 完整性】**：自我複審在實機 921 筆發現 (2) 不完整（finalize 漏 `g3_fetched_by_uid` fallback，79 筆誤擋）→ 已修。(1) 維持。
- **✅【第五塊 (3) 🟡 retrofit】**：以 `validate_screen_tiers.py` 套 harness 到實機 → 揭露 🔴 對照軸子字串假命中（29 筆，含 CALIMA）→ 已修。本輪 ③ 結果由手刻 curated C regex 產出、未受 harness bug 影響；下一主題 ③ 起走 screen_tiers。
- 修後實機：false 切題 29→0、finalize 79→0、`screen_tiers.py --selftest` 8 案全過。

### 2026-06-25 處理第一輪審查結果（無 🔴；2✅＋1⚪＋1🟡）
- **✅【第三塊 public_legs.py】** 3 項全確認，commit `eaee976`。
- **✅【第四塊 ai_synthesis_checked】⚪** 採用 Antigravity「查過」定義，commit `8a213ac`。run-cache 183 筆已補跑 Consensus AI 合成（救回 3、餘 180 蓋旗標），③ 分割 516/225/180、gate_guard 全綠。
- **✅【🟡 screen_tiers.py】** 新增 committed harness commit `a6bde9c`，第二/三輪持續修正後 commit `5bf0c26`。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
