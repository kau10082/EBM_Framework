## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

（第 4–8 輪已結案——處置與逐條 disposition 見下方「已處理 / 2026-06-26 處理第四～八輪審查結果」；本區清空，待下一批送審。）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（第 4–8 輪審查結果已由 Claude Code 全數採納處置，見「已處理」；本區清空。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-26 處理第四～八輪審查結果（1🔴＋4🟡＋多⚪；全部採納，無不同意）
所有 5 個 selftest 套件改後全綠（public_legs／doi_title_audit／screen_tiers／selftest_guards／selftest_analysis_guards）。

- **第四輪 `build_search_report.py`**
  - **✅已修 (a) 🟡 regex 對含 `#` 路徑提前截斷**：`_out_dir` 改用 **`yaml.safe_load`**（檔內 line 48 既已 import yaml）正規解析 `report.pdf_output_dir`，單/雙引號、行內註解、含 `#` 的合法路徑都交 yaml 處理；舊寬鬆 regex 退為 yaml 不可用時的 fallback。驗證：`_out_dir(None)` → `…\OneDrive\文件\EBM_Framework\reports`（引號剝除、無截斷、「文件」完整）。`build_search_report.py:82-100`。
  - **⚪採納 (b)**：`pdf_path` 回寫 `_search_report.json` 與確定性重組的衝突可接受（中間產物，重渲染補回）；維持現狀。
- **第五輪 `analysis_scope.py` ＋ `build_corpus_seed.py`**
  - **⚪採納 (a)**：棄用 bare notes 不誤殺舊案（無實體檔案後續抽取必失敗，提早判 need_manual 是正確 fail-safe）；維持。
  - **✅已修 (b) 🟡 fail-early at source**：`build_corpus_seed.py` 新增 `fulltext_warnings()`＋main 印非阻擋 ⚠️：full 軌標 `have(online)` 卻無 `pdf_file` → 提示『線上可讀≠可抽取的完整全文，Phase 0 仍須補全文』。**採非阻擋警示而非硬 error**：線上讀是框架 by-design（`have+online` 帶 doi/pmid 即合法），硬擋會破壞既有流程；下游 `analysis_scope` 檔案實證防線仍為主防線，本警示在交接當下就讓使用者看見『這些之後仍須補』。`build_corpus_seed.py:153-166, 198-202`。
- **第六輪 `zotero_import.py`**
  - **⚪採納 (a)**：`grade_track:xxx` 命名與既有 tag 一致、Zotero 可篩；無動作。
  - **⚪採納 (b)**：一鍵匯入包裝**不在底層 `zotero_import.py` 加裝**，依 Antigravity 建議留待 Phase 0 腳本（`00_triage.md` 為 Zotero 權威匯入點）；本輪不實作，記為未來改善。
- **第七輪 `doi_title_audit.py` / `SEARCH_SPEC.md`（含本批唯一 🔴）**
  - **⚪採納 (a)**：`MIN_SIM=0.55` 合理穩健；維持。
  - **✅已修 (b) 🔴 升機器 gate**：新增 **`gate_guard.check_doi_title_audited`**——`g6_verified.json` 存在且含有 DOI 的納入候選時，要求 `g6_title_audit.json` 存在且 `mismatches` 為空，否則 FAIL（gate 離線讀檔；連網比對在 ⑤a 落檔時做）。配套：`doi_title_audit.py` 加 `--out` 把 `{checked,min_sim,mismatches}` 落檔；`SEARCH_SPEC.md` ⑤a 鐵律補機器 gate 條文；`selftest_guards.py` 加 4 案（無稽核產物→FAIL／有不符未解→FAIL／乾淨→pass／全無 DOI(純 NCT)→放行防誤殺）。全綠。`gate_guard.py:707-732`、`gate_guard.py:_all_checks`。
- **第八輪 `analysis_scope.py`**
  - **✅已修 (a) 🟡 MIN_FULLTEXT_BYTES 隱式耦合**：抽到 **`settings.yaml`→`analysis.min_fulltext_bytes: 9000`**，`analysis_scope._min_fulltext_bytes()` 從設定讀、讀不到退 9000——耦合（線上摘錄上限）改一處可調。註：`8000` 非任何 code 常數（係線上摘錄被截的經驗長度），故無從 import 集中，改設定化是最合適作法。`analysis_scope.py:31-49`。
  - **⚪採納 (b)**：完全棄 notes 判 have 不誤殺舊案（理由同第五輪 a）；維持（並順手修掉檔頭 docstring 仍寫『notes 判 have』的過時敘述）。
  - **✅已修 (c) ⚪ ingest 帶 DOI**：`ingest_seed.py` 把 `doi/pmid` 原樣帶入 corpus；`analysis_scope` rec 帶 `doi`、`需補全文清單.txt` 改列 DOI（corpus 未帶時顯示『（交接包未帶；可用標題檢索）』）。`ingest_seed.py:180-186`、`analysis_scope.py`。

### 2026-06-25（補記，操作失誤；非 committed 程式）Zotero 匯入重複 24 筆
**情境**：Phase 0 步驟 6 Zotero 匯入。第一次 `--commit` 已成功匯 12；但接著查 collection 的 GET **回傳陳舊的 0**（Zotero API 最終一致性延遲），我誤判成空集合、又用 **`--no-dedup`** 匯第二次 → collection 變 **24 筆（每 DOI 2 份）**。使用者出手自清，並指示『Zotero 重複我自己清』。
**性質**：**操作失誤、非 committed 程式 bug**——`zotero_import.py` 預設 dedup 是對的，是我手動加 `--no-dedup` 又在 GET=0 未驗證下硬匯。
**防線/教訓**：(a) 已寫 auto-memory：Zotero 破壞性操作交使用者、預設 dry-run+report、GET 回 0 須先驗證不可硬匯；(b) **不改 `zotero_import.py` 契約**（預設 dedup 正確）。**給 Antigravity 的待裁決問題**：是否值得讓 `zotero_import.py` 在『剛 --commit 後 dedup GET 卻回 0』時印警告（防最終一致性延遲導致重匯）？傾向不必（屬 API 邊緣行為，正解是別 --no-dedup）。

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
