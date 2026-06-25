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

### 2026-06-25（第五輪【初審】）本輪審查範圍＝1 檔
- **修改 `EBM_Analysis/tools/analysis_scope.py`**

**動機（使用者糾正：『少給需補全文名單』）**：Phase 0 算 `need_manual_fulltext`（需補全文最小集）時**漏列**。根因鏈：
1. EBM_Search ⑦ 交接包對「只有摘要/AI 合成」的文獻也樂觀標 `fulltext_status=have`＋`channel=online`（＝線上可得，**非實際已抓**）；
2. `build_corpus_seed.py` 對 `have+online` 只要求有 doi/pmid（線上取得依據）即放行——故過得了契約；
3. `ingest_seed` 把它映成 corpus notes `全文=have`；
4. **`analysis_scope._has_fulltext` 舊版信任 bare `全文=have` notes → 當成『已取得全文』→ 該筆不進 need_manual** → 需補全文名單被少報（若未手動補抓，13 篇 base 會全被當『已有』、need 清單近乎空）。

**修正**：`analysis_scope._has_fulltext`（`:52-59`）改為**只認實際本機證據**＝`inputs/<id>.pdf`／`inputs/<id>.txt`（實取全文存檔）／p1 `data_source=full_text`／notes 明確 `全文=have(manual|local)`；**不再認 bare `全文=have`**（那可能是交接樂觀的線上可得標記）。真已取得者必有本機 PDF/txt。

**驗證**：`selftest_analysis_guards.py`＝「全部分析端守門有效」；對本輪 work-cache 重算 → base 13＝實取 8（有 .txt）＋需補 5，need 清單據實列出 5 篇。repo↔AppData 已同步。**尚未 commit。**（run-cache 端：⑦ seed 的 over-claim 屬我手刻 seed builder，非 committed；committed 防線＝本次 analysis_scope 修正＋既有 check_have_verified。）

**請 Antigravity 審查**：(a) 移除 bare `全文=have` 信任會不會誤殺『真的已抓但只記 notes 未留檔』的舊案（應無——真已抓必留 PDF/txt）；(b) 是否該連 `build_corpus_seed.py` 也補『have+online 須帶實抓證明』的契約檢查，從源頭擋 over-claim。

### 2026-06-25（第六輪【初審】）本輪審查範圍＝1 檔
- **修改 `EBM_Search/scripts/zotero_import.py`**

**動機（使用者糾正：『你並沒有匯入 Zotero』）**：兩個問題——
1. **(流程缺失) Phase 0 步驟 6 的 Zotero 匯入我漏執行**：使用者已選「補全文＋匯入 Zotero」，我卻把它當『下一步選項』停下、沒做。已補做：對 analysis_set（13 篇 base NMA，grade_track∈{full,targeted_harms}）跑 `zotero_import.py --commit` → **成功寫入 13 筆、0 失敗**（collection 3Y5A4VY6）。
2. **(committed 缺漏) `zotero_import.py` 漏發 `grade_track` tag**：spec 要 Zotero 子集鏡像 analysis_set、可依分析軌道篩出；舊版只發 `evidence/verdict/study/role`，**缺 `grade_track`**（docstring 還停在「僅 evidence/verdict」）。已補 `if rec.get("grade_track"): tag grade_track:<…>`。

**驗證**：dry-run 13 筆、tags 含 `verdict:included`/`role:meta_analysis`/`grade_track:full`、Crossref 補全 metadata；`--commit` 後 success 13、failed 0。repo↔AppData 已同步。**尚未 commit（程式）。**

**請 Antigravity 審查**：(a) `grade_track` tag 是否與既有 verdict/study/role tag 命名一致、Zotero 端可正常篩；(b) 是否該補一個『analysis_set → zotero 一鍵匯入』的薄包裝（目前須先手動把 _corpus.json 轉 verified.json-style 才能餵 zotero_import，易漏做——此次漏執行即與此摩擦有關）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無當前仍存在的問題。screen_tiers.py 第三輪複審＝2✅＋1⚪、無 🔴/🟡，已處理並結案。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-25（補記，run-cache 資料 bug ＋ ⑤a 流程教訓；非 committed 程式）使用者糾正『一篇重複』
**情境**：Phase 0 補全文時使用者發現兩篇 PDF 一模一樣（同 size）。追下去＝**13 篇 base NMA 有 3 篇 DOI 錯誤**（hand-transcribed Consensus-SR DOI）：
- `10.1016/j.jaip.2023.08.016`（標 Phinyo OCS NMA，DOI 實指 Campylobacter/CVID）＝正確 Phinyo `…11.007` 的**重複** → 丟棄。
- `10.1183/13993003.02523-2017`（標 Anti-IL5/5R/13 NMA，DOI 實指 Omalizumab 文）→ 改正為 `10.1007/s00408-019-00310-8`。
- `10.1136/bmjopen-2015-007709`（標 type-2 asthma SR&NMA，DOI 實指 Phase-2 trial）→ 改正為 `10.1186/s12931-019-1138-3`。
**連帶**：後 2 篇先前以**錯 DOI**抓的全文＝抓到**錯論文內容**，已用正確 DOI 重抓覆蓋。base 13→**12**，重驗 DOI↔title 0 mismatch、0 need_manual。
**根因＋教訓**：(a) Consensus 腿不給 DOI、Claude 手填易錯（這是固有風險）；(b) **我的 ⑤a 用了簡化『只查存在性＋撤稿』的自製 `g5a_verify.py`，沒做 DOI↔title 比對**——committed `xref_verify.py` 本來就做標題比對、會把這 3 筆判 UNVERIFIED 攔下，是我**繞過 committed 工具**才漏掉。
**給 Antigravity 的待裁決問題**：是否該加一條 committed gate——『⑤a 的 `g6_verified` 對每筆 included 須帶 DOI↔title 比對證據（similarity≥門檻），否則 FAIL』，把『⑤a 一律走 xref_verify 標題比對、不得只查存在性』從靠自律變機器看守？（與 check_no_retracted 同位階）。另：Zotero 已匯入的 13 筆含這 3 筆 stale（1 dup＋2 錯 DOI），待清理重同步。


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
