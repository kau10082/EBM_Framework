## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：分析階段『全文為準』機器強制（使用者 2026-06-21 糾正：到分析階段一切以全文資訊為準，真的各管道都讀不到全文才退網路/AI 合成）

本輪審查範圍：僅以下 8 檔
- `EBM_Analysis/guardrails/fulltext_authoritative.md`（新增護欄）
- `EBM_Analysis/tools/fulltext_gate.py`（新增機器 gate）
- `EBM_Analysis/tools/verify_all.py`（接線）
- `EBM_Analysis/schema/phase1_extract.json`（新增 `fulltext_attempts` 欄）
- `EBM_Analysis/phases/01_extract.md` ＋ `EBM_Analysis/manifest.yaml`（規格/登錄）
- `EBM_Analysis/tools/analysis_scope.py`（新增：算進入分析集／需補全文最小集）
- `EBM_Analysis/schema/phase0_corpus.json`（新增 `is_primary_report` 欄）
- `EBM_Analysis/phases/00_triage.md`（步驟 5/6 範圍改用 analysis_scope；手機可跳過實執行）
- `EBM_Analysis/tools/build_grade_pdf.py`（新增 PDF 產生器＋`--layout cochrane5` Cochrane 後半段 5 段版型）
- `EBM_Analysis/schema/phase4_output.json`（新增選用 `meta_analysis` 欄：池化合併效應＋I^2）
- `EBM_Analysis/tools/build_reports.py`（MD 改 Cochrane 6 段＋連帶產 PDF）
- `EBM_Analysis/phases/04_output.md`（明定標準 6 段 PDF/MD 統一格式）
- `EBM_Analysis/tools/selfcheck_consistency.py`（新增 C17 降級必附腳註／C18 ≥2試驗必含 meta_analysis）
- `EBM_Analysis/ANALYSIS_SPEC.md` ＋ `EBM_Analysis/manifest.yaml`（標準格式鐵律＋登錄 C1-C18）

改了什麼（5 條）：
1. **新增護欄 `fulltext_authoritative.md`**：分析階段以全文為準；退 abstract/registry/ai_synthesis 前須逐一實試 local_pdf→PMC fullTextXML→Unpaywall 全 oa_locations→manual_supplement 並記 `fulltext_attempts`；取得全文→標 `full_text` 以全文重抽；唯全部取不到才退二手，且 status=needs_review＋Phase 3 確定性封頂（連動 registry_backfill／selfcheck C4）。
2. **新增機器 gate `tools/fulltext_gate.py`**：逐 `*.p1.json`——data_source 不含 full_text 卻用二手者，須 `fulltext_attempts` 涵蓋 local_pdf/pmc_fulltextxml/unpaywall_oa 三管道（result≠skipped）且無任一 fulltext_obtained、status=needs_review，否則 FAIL；反向「標 full_text 卻無 fulltext_obtained 證據」亦 FAIL。附 `--selftest`。
3. **`verify_all.py` 接線**：新增「全文為準 fulltext_gate」一關（fail-closed）。
4. **schema `phase1_extract.json` 加 `fulltext_attempts`**（陣列：channel∈{local_pdf,pmc_fulltextxml,unpaywall_oa,manual_supplement,publisher,other}、result∈{fulltext_obtained,no_access,not_found,parse_failed,skipped}、detail）。
5. **規格/登錄**：`phases/01_extract.md` 步驟0 改「先窮盡全文管道→標 data_source＋fulltext_attempts」＋front-matter 加 guardrail；`manifest.yaml` 登錄 `fulltext_authoritative`。

fresh-clone / 自測：
- `python EBM_Analysis/tools/fulltext_gate.py --selftest` → ✅（壞例被抓、好例放行、full_text 證據一致性檢查有效）。
- 實跑 COPD analysis cache：4 篇核心試驗 p1（IMPACT/ETHOS/KRONOS/TRIBUTE）先全部 abstract-only → gate **FAIL（正確抓出未窮盡全文）**；補實試三管道（local_pdf=not_found、PMC=not_found〔NEJM/Lancet 非 OA、不在 PMC，已重試排除 503〕、Unpaywall=not_found/parse_failed〔僅 Manchester 典藏 landing 頁、非 PDF〕）記入 fulltext_attempts 後 → schema ✅＋gate **PASS**。證明 gate 屬實有效、且 4 篇全文確實線上不可得（退 abstract 合法、status=needs_review、Phase 3 封頂）。
- `verify_all.py`/`fulltext_gate.py` 語法＋import OK。

另一組改動（同屬分析階段、2026-06 使用者『只匯入/只補進入分析那幾篇』）：
6. **新增 `tools/analysis_scope.py`**：確定性算 `analysis_set`（grade_track∈{full,targeted_harms}＝進入分析＝Zotero 範圍）、`need_manual_fulltext`（分析集中全文未取得且為錨點者＝full 的 is_primary_report 每 Study 一篇＋targeted_harms 真害；＝補這些即可）、`optional_fulltext`（full 次級/overlap，補了不增進核心 GRADE）。
7. **schema `phase0_corpus.json` 加 `is_primary_report`**（每核心 Study 標一篇主報告為分析全文錨點）。
8. **`phases/00_triage.md` 步驟 5/6 改範圍**：補全文範圍＝`need_manual_fulltext`（不再全 full+harms 都補）；Zotero 範圍＝`analysis_set`（不再鏡像 _corpus.json 全集，背景 light_summary 不進 Zotero，除非 --include-background）；註明手機/遠端可暫跳過實執行、範圍清單仍算好備查。
   實跑：本案 analysis_set=51 報告（核心 28→4 Study＋targeted_harms 23）；need_manual=4 核心主報告（IMPACT/ETHOS/KRONOS/TRIBUTE primaries）＋21 harms 候選；optional=24 IMPACT/ETHOS/TRIBUTE 次級報告。

想被重點看：(a) gate 要求的三必試管道 {local_pdf,pmc_fulltextxml,unpaywall_oa} 是否合理（manual_supplement 容許 skipped）；(b) 「標 full_text 卻無 fulltext_obtained 證據→FAIL」會否誤傷『本機 PDF 直接讀』情境（local_pdf 取得也記 fulltext_obtained，應不誤傷）；(c) 與既有 registry_backfill／selfcheck C4「非全文不得 low」是否衝突；(d) analysis_scope 把 Zotero 範圍縮成『只分析集、不含背景』是否與既有『Zotero≡報告』規則衝突（按：EBM_Search ⑤c 已 deprecated 移 Phase 0，此為新權威範圍，無衝突）。

本輪 Claude Code 自我覆核追加微調（3 項，均已 py_compile＋快測通過；皆落在上方已列審查範圍的檔內）：
- **A. `tools/verify_all.py` 顯示標籤過時**：彙總畫面與 docstring 寫「selfcheck C1-C15」，但 selfcheck 早已實作 C1-C18（C17 降級必附腳註／C18 ≥2 試驗須含統合分析段）且確實擋關——只是名稱沒跟上。改為 C1-C18。**純顯示字串、零行為變更。**
- **B. `phases/01_extract.md` 步驟0 補明全文證據鐵律**：`data_source` 含 `full_text` 時，`fulltext_attempts` 至少要一筆 `result=fulltext_obtained`（記下從哪個管道讀到全文），與 `fulltext_gate.py` 反向檢查對齊。schema 把 `fulltext_attempts` 列為選用，但本鐵律＋gate 在 `full_text` 情形下視為必填——明文寫「以 gate 為準」，消除「schema 過得了、gate 過不了」的落差。**僅文件，無程式行為變更。**
- **C. `tools/analysis_scope.py` 加防呆 `warnings`**：full track 的 Study 若『無任一報告有全文』又『無任一主報告進 must』（多半是 Phase 0 漏標 `is_primary_report`），其全文需求原會被靜默漏列（全掉 optional）。新增主動警示請回 Phase 0 補標主報告（**不阻擋**）。`compute()` 回傳新增 `warnings` 鍵、`_print` 末段印出；`--json`/`--write` 一併帶出。快測證實：漏標主報告的 Study 正確觸發警示、有主報告者不誤報。
  想被重點看(e)：此防呆只警示、不阻擋，且 Study 標籤取自 notes 的 `study=` regex（取不到記 `—` 並略過警示，避免雜訊）——是否同意此「警示不擋關」的安全傾向。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（本塊初審：0 🔴，無任何未解決問題。各項判定明細已移入「## 已處理」。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 初審通過(Antigravity,2026-06-22):本塊「分析階段『全文為準』機器強制＋analysis_scope＋PDF/格式統一」15 檔審畢，**0 🔴**、邏輯縝密無錯誤。自我存疑點與追加微調判定——(a)三必試管道 {local_pdf,pmc_fulltextxml,unpaywall_oa} 合理、manual_supplement 容許 skipped〔⚪〕；(b)「標 full_text 卻無 fulltext_obtained→FAIL」不誤傷本機 PDF（local_pdf 記 fulltext_obtained 即通過）〔⚪〕；(c)與 registry_backfill／selfcheck C4 無衝突、相輔相成（退二手強制 status=needs_review，呼應 C4『非全文不得 low』）〔⚪〕；(d)analysis_scope 把 Zotero 範圍縮成只分析集＝架構優秀決策（不再被背景文獻污染）〔🟡〕；(e)A/B/C 三項微調皆妥當，其中 C 的「警示不擋關」安全傾向正確（避免 study= regex 命名不規範引發假陽性死鎖）〔🟡〕。全數無需修改。

✅ 已修:① 關報告誤含引文搜索語意（SEARCH_SPEC.md 第①關停頓點新增「廣蒐去重不含引文搜索」鐵律）
✅ 已修:報告策略時未主動問 SR filter（SEARCH_SPEC.md `check_strategy_approved` 段新增鐵律）
✅ 已修:SR Filter 套用對象寫錯成 PubMed（改為「PubMed 以外的腿、additive、`<leg>-SR`、design_filter_allowed:true」）
✅ 已修:leg_exhaust gate 不認得 SR 子腿（scripts/leg_exhaust_check.py 新增 `_base()` 去 `-SR` 後綴）
✅ 已修:Bug1 無可解析內容者漏到③（SEARCH_SPEC.md ②c 鐵律＋gate_guard 強化：無abstract須有實抓解析證明，否則②c判待評估）
✅ 已修:Bug2 未盡力解析全文、只憑旗標標 have（SEARCH_SPEC.md 規定②c須窮盡 PMC/Unpaywall全locations/PDF/HTML 實抓解析；gate 以 text_len 證明）
✅ 已修(使用者 2026-06 糾正『交接包只要 PRISMA Included 那些、不要背景』):**`build_corpus_seed.py` 預設改為只交接『納入一起分析』者**。原本 seed 帶全 79 篇(included 22＋background 57)，使用者要求交接包＝PRISMA 流程末步「Included」產生的「核心 RCT＋子研究」＋「納入分析的 SR/MA」即可。修法（本輪動檔）：(1) `scripts/build_corpus_seed.py` 新增 `filter_analysis_set()`＋預設過濾——只留 `verdict=included 且 suggested.grade_track∈{full,targeted_harms,light_summary}`(＝核心RCT主報告/子研究/安全性/PK/機轉/子群＋納入SR/MA)，**剔除 background 與 grade_track=none(僅登錄端/待評估)**；加 `--include-background` 旗標保留舊全帶行為；docstring 同步。(2) `references/corpus_seed_schema.json` papers 欄描述更新為『預設＝Included 分析集，背景以 --include-background 才帶』(與口徑一致、與 build_search_pdf『Included＝核心+SR/MA』對齊)。實證：本案交接由 79→**20 篇**(4 full＋8 targeted_harms＋8 light_summary；0 background)；`--include-background` 仍回 79；`selftest_guards`／`gate_guard`(含⑥驗證覆蓋、撤稿)全綠。本輪動檔：`EBM_Search/scripts/build_corpus_seed.py`、`EBM_Search/references/corpus_seed_schema.json`。
✅ 已修(使用者 2026-06 追加微調『Included 下兩類須簡短列出是哪幾篇』):承上條，`scripts/build_search_pdf.py` 段3 Included 明細再加「逐篇簡列」——核心 RCT＋子研究：在數量後逐 Study 名＋報告數（如「17（WILLOW 9、ASPEN 4、SAVE-BE 2、AIRLEAF 2）」，細目見段4）；SR/MA：在數量下逐篇短標題（截 44 字）＋PMID。皆資料驅動（讀 included_studies 核心群＋background SR/MA 列），換主題自適用。實證：Included 20＝核心17（4 Study 逐列）＋SR/MA 3（Emara 41299471／抗發炎療法 41534709／Carvalhal 41443427 逐篇列）；report_check／gate_guard 全綠。本輪動檔：`EBM_Search/scripts/build_search_pdf.py`。
✅ 已修(使用者 2026-06 實跑 DPP1×支擴 案糾正『PRISMA Included 下不該列背景/進行中』):**`build_search_pdf.py` 段3 的「納入分析文獻 Included」明細口徑錯誤**。原本把 `included_breakdown`(⑤b 全 79 切題的分流統計，含背景/進行中/他族群/綜述)整串列在「納入分析文獻 Included」之下，造成「Included」像是包含了非納入分析的類別。修法（本輪動檔）：`scripts/build_search_pdf.py` 段3 改為**確定性只計『真正納入下游評讀分析者』**＝(a)核心 RCT＋子研究（`included_studies` 中 type 含『核心』之群報告數總和）＋(b)SR/MA（`background` 表中型態為 Meta-Analysis／Systematic Review 者）；Included 數＝兩者相加，明細**只列這兩行**，不再吃 `included_breakdown`。資料驅動、換主題自適用。實證：本案 Included＝20（核心 RCT＋子研究 17＋SR/MA 3；B45-06 會議摘要 MA 無 PMID 不計入分析單位）；`report_check`／`gate_guard` 全綠。順手移除 `_search_report.json` 已過時的 `included_breakdown` 欄（避免 stale 資料誤導）。本輪動檔：`EBM_Search/scripts/build_search_pdf.py`。
✅ 已修(使用者 2026-06 實跑 DPP1×支擴 案糾正『待評估怎麼跑到③才挑出來』):**Bug2 的漏網路徑——`stage1_check` 未攔 OA-flag-only 的假 have**。原本 `check_partition_provenance` 雖能抓「screened 無內容」但**只在 ③(g3 產出後)才觸發**；Stage A→B 邊界 `stage1_check` 只驗 `fulltext_status∈{have,…}` 與「fs=none∧as=none→awaiting」，**漏掉「fs=have 但 abstract 空、非 registry、無解析證明」**＝只憑 Unpaywall `oa_url` 旗標標 have、未實抓解析，於是「線上能否讀到全文」被拖到 ③ 才定、待評估外溢到 ③。修法（本輪動檔）：(1) `scripts/stage1_check.py` 不變量 2 新增一條——`fulltext_status=have ∧ abstract_status=none` 時，須 `fulltext_channel=registry`(登錄結構化) 或 `abstract` 非空 或 `fulltext_chars≥1500` 或 `fulltext_verified`，否則 FAIL（指引：②c 真抓 PMC fullTextXML／OA HTML/PDF 解析出正文才標 have，線上讀不到則改判 awaiting＋`online_read_attempted=true`）；把「have 須實抓驗證」前移到 ②c→Stage B 邊界，與 `check_partition_provenance`(③) 互補、提早一關攔下。(2) `scripts/selftest_guards.py` 加回歸：OA-flag-only 假 have 須 FAIL、registry／`fulltext_chars≥1500` 應通過(防誤報)。實證：`selftest_guards.py`→✅全綠；模擬本案 RCCM 編者文(have+online+空abstract)→新 gate 正確 FAIL；本案 cache 補實抓解析後 rebuild `_stage1_corpus.json`(candidates 84/awaiting 7)→`gate_guard` 全關綠。本輪動檔：`EBM_Search/scripts/stage1_check.py`、`EBM_Search/scripts/selftest_guards.py`。
✅ 已修:⑤b --enrich 找不到介入軸→CT.gov 交叉核對靜默跳過（scripts/classify_units.py enrich 改穩健尋找介入軸 I/I_*/role；補跑 CT.gov 核對 34 NCT，核心 RCT 正確歸併、非核心歸背景）
✅ 已修(使用者要求):⑥ PDF PRISMA 段移除流程圖、只保留漏斗表格（scripts/build_search_pdf.py 刪除段3 的 Drawing/box/arrow 流程圖區塊，保留 funnel 表＋二分閉合；report_check/gate_guard 仍綠）
✅ 已修(使用者要求):⑥ PDF PRISMA 漏斗表最後一步固定補「納入分析文獻 Included」——由產生器確定性附加（非手動編 funnel）：scripts/build_search_pdf.py 段3 先濾掉 funnel 內既有『納入分析』步、再附加一行，數量取 prisma_flow.included（缺則由 included_studies 報告數推算）；已驗：移除 _search_report.json 手動步後 PDF 仍渲染出該末步（423），report_check/gate_guard 綠
✅ 已修(使用者要求):⑥ PDF PRISMA 末步須詳述『分類後各類篇數』——scripts/build_search_pdf.py 段3 於 Included 步後逐類渲染 `included_breakdown`（核心RCT/SR-MA/其他RCT/各背景，總和=Included）為縮排子列；breakdown 由 ⑤b g7_units.buckets 計算寫入 _search_report.json（本案 59/64/45/143/89/23=423）。report_check/gate_guard 綠
✅ 已修(使用者糾正):⑤b 核心/非核心 RCT 判準誤判——scripts/classify_units.py：(a) 對照軸偵測先正規化 en/em-dash→hyphen＋β→b（修 ETHOS/KRONOS `glycopyrrolate–formoterol` 假陰）、(b) 遮蔽三合一藥名跨度(R_TRIP.sub)再掃 R_DUAL＋R_TRIP 補 FF/UMEC/VI·BGF·BDP/FF/G 縮寫（修 `FF/UMEC/VI⊃UMEC/VI` 子字串假陽）、(c) **核心/非核心是試驗設計屬性、非單篇報告屬性**→對已知樞紐試驗以 trial-level 權威表 `PIVOTAL_LABALAMA_ARM` 定案（IMPACT/ETHOS/KRONOS/TRIBUTE=核心；FULFIL/TRILOGY/TRINITY=非核心 vs ICS/LABA），非樞紐才回退 regex。實證：7 大樞紐全部歸位正確；核心報告 59→53。
✅ 已修(使用者要求『逐筆核對＋修 regex』):⑤b 非樞紐『獨立核心 RCT』誤判——逐筆核對 24 篇後發現只 6 篇真核心（其餘＝綜述/藥物簡介 8、觀察/before-after 3、藥動/機轉 2、對照=MITT/usual-care 2、off-topic/非三合一 2、無摘要會議短摘 1）。修法：(1) scripts/classify_units.py 設計判別新增 `R_REVIEW_STRONG`/`R_PK_STRONG`（無 RCT pubtype 而命中綜述體/藥動訊號者先歸背景，避免綜述描述他人試驗含 randomized 字樣→誤判 RCT）＋`R_PRIM2` 回退路徑加 `R_RAND`（須確有隨機化證據）＋`R_OBS` 補 before-after/pharmacoepidemiolog；實證 regex 自動更正 11/18。(2) 殘餘 7 以本案逐筆核對結果覆寫 g7_units（run-specific 資料）。核心報告 53→32（4 樞紐＋6 真獨立）。下游 report/breakdown/corpus_seed/PDF 同步重建。

✅ 已修(使用者要求):⑥ PDF 段四「最終納入的證據清單」改為**只列核心 RCT**——scripts/build_search_pdf.py 段4 以群組 type 含『核心』篩選 `included_studies`，只渲染核心原始 RCT（三合一 vs LABA/LAMA）群組，排除『其他三合一 RCT』與 SR/MA 群組（後兩者見第三節分類統計與交接包）；標題改「四、最終納入的核心 RCT 證據清單」。report_check/gate_guard 綠。

✅ 已修(使用者糾正):⑤b 會議摘要被誤判為獨立核心 RCT——scripts/classify_units.py 新增 `R_CONF_DOI`/`R_CONF_TITLE` 偵測會議摘要(ERS congress-/conference/poster/synopsis 等)；依 Cochrane/MECIR 會議摘要＝『待評估研究』，**獨立會議摘要(無對應完整論文)不得當核心**→歸 `待評估:會議摘要(未完整發表)`；惟已納入樞紐試驗(有完整論文)的子報告即使是摘要仍保留為該試驗支持性報告。實證：1 篇 ERS congress-2020 摘要(無 PMID,n=104)由核心移出；核心報告 32→31。下游同步重建。

✅ 已修(使用者要求『確認之後會確實執行』):核心 RCT 判定邏輯已寫成可攜定版規則入 SEARCH_SPEC.md（⑦/⑤b 段新增「★ 核心 RCT 判定邏輯(定版,鐵律)」）——載明 (L1)設計判別先擋綜述/PK/觀察(R_REVIEW_STRONG/R_PK_STRONG/R_OBS)、回退須 R_RAND；(L2)會議摘要→待評估、樞紐用 PIVOTAL_LABALAMA_ARM 權威表、非樞紐 regex trip∧dual(先正規化分隔符+遮蔽三合一藥名)、NCT 經 --enrich CT.gov 介入核對；(L3)殘餘交 Phase 0 人工覆核；並明令『⑤b 須以 --enrich 執行』。確保換 session/別人 clone 也照此執行（規則入 repo、非只在對話）。對應實作全在 scripts/classify_units.py（已 commit）。

✅ 已修(使用者/外部 Claude 逐筆核對):⑤b 核心 RCT 再精進兩類——(A) **研究計畫書(無結果)不得當核心**：scripts/classify_units.py 新增 `R_PROTO_STRONG`(study protocol/rationale and design/results expected/will be randomised/first patient 20XX…)，且 protocol 強訊號**蓋過 R_RCT**(protocol 含 randomized 字樣會誤觸 RCT)→ ANTES B+、日本 RCT 由核心移到『進行中/試驗計畫書(待結果)』。(B) **ICS 退階/移除設計≠起始三合一 vs 雙支擴**：新增 `R_ICS_WD`(withdrawal of ICS/de-escalation/step-down/discontinue ICS…)，凡核心且命中者改記 `核心:ICS 退階試驗` 並打 `design_subtype=ICS-withdrawal`→ SUNSET、WISDOM 與起始試驗分開、下游 meta 不混算。實證：核心起始 IMPACT/ETHOS/KRONOS/TRIBUTE=27 報告、ICS 退階 2、計畫書移出 2；corpus_seed included 31→29。下游 report/breakdown/seed/PDF 同步重建、全關綠。

✅ 已修(使用者『避免下次再犯』總結教訓):⑤b classify_units 新增**主動覆核防線 `core_review_flags`**——classify() 收尾自動把『高風險核心判定』攤出來寫 g7_review_flags.json 並於 main 顯著警示:(1)非樞紐核心(純 regex,無權威表背書)、(2)無 PMID(疑會議摘要/未完整發表)、(3)DOI 疑會議摘要、(4)ICS 退階子型、(5)標題含 protocol 訊號。**教訓＝我一再信任自動化結果就當定稿、靠使用者抓錯;此防線把不確定性主動逼出來覆核(對齊框架『rapid-review 須人工覆核』『機器守門優先於記性』),下次同類風險會自動浮現而非等下游爆。** 本案實測 flag 出 SUNSET/WISDOM(非樞紐+ICS退階)＋2 筆 conf-DOI 樞紐子報告。

✅ 已修(使用者糾正『最終分析名單在 Phase 0 才定，Zotero 匯入/人工補全文應移到這裡』):把 ⑤c Zotero 匯入、⑤d 人工補全文的**權威執行從 EBM_Search 移到 EBM_Analysis Phase 0**——(1) `EBM_Analysis/phases/00_triage.md` 分流定稿後新增步驟 5（補全文，以 grade_track∈full/targeted_harms 為準）、步驟 6（Zotero 匯入，鏡像 _corpus.json 全集＋分流標籤），斷點改「分流→補全文→Zotero→Phase 1」；(2) `EBM_Search/SEARCH_SPEC.md` ⑤c/⑤d 段標『預設不在此匯/補，權威版在 Phase 0』；(3) `config/settings.example.yaml` 補 `analysis.fulltext_dir`。理由：退階試驗（SUNSET/WISDOM）等到 Phase 0 才決定只當背景，補全文/匯入須以定稿名單為準，避免白補與重複匯入。

✅ 已修(使用者糾正『分析階段一切以全文為準，真的各管道讀不到才退網路/AI 合成』):新增 `fulltext_authoritative` 護欄＋機器 gate `tools/fulltext_gate.py`（併入 verify_all），phase1 schema 加 `fulltext_attempts`，phases/01_extract.md＋manifest 同步。強制：退二手前須實試 local_pdf/PMC/Unpaywall 三管道並記錄，取得全文須以全文重抽；唯全部取不到才退 abstract/registry/ai_synthesis 且 status=needs_review＋確定性封頂。實證 gate 抓出我原本 4 篇 abstract-only 未窮盡全文（FAIL）→補實試（4 篇 NEJM/Lancet 全文確線上不可得）後 PASS。

✅ 已修(使用者『之後 analysis 階段 PDF/MD 務必遵照此規格與規範，務必』):把標準格式從『文件規範』升級為『機器硬 gate』——(1) selfcheck_consistency 新增 **C17（任一結局確定性<高→sof_footnotes 必非空，GRADE 降級透明）** 與 **C18（≥2 試驗→meta_analysis 必含，未池化亦須 model=not_pooled+理由）**，併入 build_reports/verify_all 的硬 gate，不過則擋渲染；(2) phases/04_output.md 補『SoF 數據呈現黃金守則』與『registry_backfill＋RoB 封印解除』兩條鐵律（相對+絕對每千人+NNT+CI、跨無效線不計NNT、降級腳註、登錄補實後可解 RoB 封頂但須誠實標治療期間/待全文、禁以記憶填全文）；(3) ANALYSIS_SPEC.md PDF 段改『標準成品格式·務必遵照』、manifest 更新 C1-C18 並指向 phases/04。負向測試證 C17/C18 確實抓得到違規；正向本案合規、verify_all 19 項全綠。

✅ 已修(使用者『之後 analysis 階段 PDF 跟 MD 都比照此模式』):把 Cochrane 6 段＋升級 SoF（每千人+NNT+CI+腳註+meta_analysis）定為 analysis 標準格式，PDF 與 MD 統一——(1) `build_grade_pdf.py` 預設 `--layout cochrane5`（舊 8 段保留為 `--layout default`）；(2) `build_reports.py` final_report() 重寫為同 6 段結構（特徵表/RoB2/統合MA含I²/GRADE/SoF含每千人+NNT+CI+腳註+Authors'Conclusions+Ch15不下醫囑/臨床一句話），且寫完 MD 連帶呼叫 build_grade_pdf 產 PDF（--no-pdf 可關、缺 reportlab 只警告不中斷）；(3) `phases/04_output.md` 明定此為標準格式鐵律、通用資料驅動。實證：一道 build_reports.py 同時產 FINAL_REPORT.md＋.pdf，兩者同格式同資料源，render_smoketest＋verify_all 19 項全綠；legacy default 版型仍可用。

✅ 新增(使用者指定數據呈現黃金守則):SoF 升級為 Cochrane Ch14/15 精確呈現——絕對效應『每 1000 人』＋相對效應＋NNTB/NNTH 並附 95% CI；跨無效線/資料不足者明寫『無顯著差異/資料不足→不計 NNT』（非寫 NNT=∞）；新增 GRADE 降級腳註 a/b/c/d。schema/phase4 加選用 `sof_footnotes`。實證：肺炎 NNTH 84(95% CI 48–200)、惡化減少 264 次/1000 人年(率結果不套 NNT)。selfcheck C5/C6/C7/C14 與 verify_all 19 項全綠。

✅ 新增(使用者指定 Cochrane 後半段 5 段版型):`build_grade_pdf.py --layout cochrane5` 渲染 Cochrane Handbook 第 III 章報告規範之 5 核心數據段（1 納入研究特徵表／2 RoB2 逐篇逐領域／3 數據綜整·統合分析含池化 RR＋I^2／4 GRADE Evidence Profile／5 SoF 絕對效應換算+燈號+Authors' Conclusions 含 Ch15『不下強制醫囑』聲明）；通用、資料驅動換主題即用。配套 schema/phase4 新增選用 `meta_analysis` 欄（固定/隨機/未池化＋I^2）。實證：本案中重度惡化固定效應合併 RR 0.76 (0.72–0.81)、I^2=0%（IMPACT/ETHOS/TRIBUTE 3 試驗），肺炎標 not_pooled（HR vs % 不同型、族群相依）。通過 render_smoketest＋verify_all 19 項。

✅ 新增(補 repo 缺口):`tools/build_grade_pdf.py`——評讀端 GRADE 報告 PDF 產生器（reportlab，資料驅動、CJK 字型 fallback、TOFU 淨化對齊 render_smoketest、SoF 橫向、GRADE ●○ 標示）。repo 原本只有檢索端 build_search_pdf、評讀端無 PDF 渲染器（spec 只說「用 reportlab 自建」）。實證：產出 outputs/FINAL_REPORT.pdf 通過 render_smoketest（無磚塊/章節連續/SoF 含死亡+SAE/列數一致）＋ verify_all 19 項全綠。

✅ 已修(使用者『只匯入/只補進入分析那幾篇』):新增 `tools/analysis_scope.py` 確定性算『進入分析集(Zotero 範圍)＝full+targeted_harms』『需補全文最小集＝每 Study 主報告(is_primary_report)＋真 harms』『選補＝full 次級 overlap』；schema phase0 加 `is_primary_report`；phases/00_triage.md 步驟 5/6 範圍改用 analysis_scope（補全文只補 need_manual、Zotero 只匯 analysis_set 不含背景）並註明手機可暫跳過實執行。實證：本案進入分析 51 報告(4 核心 Study＋23 harms)、需補全文 4 核心主報告為主。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
