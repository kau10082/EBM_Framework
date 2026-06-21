## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：把「Zotero 匯入」與「人工補全文」從 EBM_Search 移到 EBM_Analysis Phase 0（使用者 2026-06-21 糾正：最終分析哪幾篇要到 Phase 0 分流定稿才確定，故這兩步權威版該在 Phase 0 做）

本輪審查範圍：僅以下 3 檔
- `EBM_Analysis/phases/00_triage.md`
- `EBM_Search/SEARCH_SPEC.md`
- `config/settings.example.yaml`

改了什麼（3 條）：
1. **Phase 0 新增步驟 5（人工補全文）、步驟 6（Zotero 匯入）**（`EBM_Analysis/phases/00_triage.md`）：分流定稿後才做——補全文以 `grade_track∈{full,targeted_harms}`（真正要評讀者）為準（取全文順序 PMC fullTextXML→Unpaywall 全 oa_locations→本機 PDF，仍缺則實際建補全文資料夾＋寫 `需補全文清單.txt`）；Zotero 匯入鏡像 `_corpus.json` 全集、以 `relevance:`／`role:`／`grade_track:`／`study:` 標籤對齊分流。理由寫進文件：退階試驗（如 SUNSET/WISDOM）最後只當背景 light_summary 就不必補全文，故必須以 Phase 0 定稿名單為準，避免在 EBM_Search 對未定稿名單白補/重複匯入。斷點同步更新（分流→補全文→Zotero→Phase 1）。
2. **SEARCH_SPEC ⑤c/⑤d 標『權威版移到 Phase 0』**（`EBM_Search/SEARCH_SPEC.md`）：⑤c/⑤d 段首新增鐵律——⑤c 預設不匯 Zotero、⑤d 至多做 handoff 前初步可得性盤點（標 `fulltext_status` 帶下游），權威執行改在 Phase 0；原 (a)(b) 細節保留為「使用者在 EBM_Search 階段明確要求即時做」時用，預設略過。
3. **settings 範本補 `analysis.fulltext_dir`**（`config/settings.example.yaml`）：給 Phase 0 補全文資料夾用，留空回退 `EBM_Analysis/inputs/_fulltext_supplement/`。

fresh-clone / 自測：
- 本輪純文件/設定範本改動（無程式邏輯變更）。`python EBM_Search/scripts/selftest_guards.py` 仍 ✅（守門腳本未動）；COPD cache `gate_guard.py` 仍全關綠。
- 不影響既有流程：EBM_Search 不再預設在 ⑤c/⑤d 動 Zotero/補全文，與下游 Phase 0 不重工。

想被重點看：Phase 0 步驟 5/6 的措辭是否與 ANALYSIS_SPEC、ingest_seed 交接邏輯一致；SEARCH_SPEC ⑤c/⑤d 的「預設略過、改 Phase 0」與其他段（⑦交接包、Zotero≡報告表二三）是否仍自洽無矛盾（交接包仍含 verdict 供 Phase 0 預填，不受影響）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修:① 關報告誤含引文搜索語意（SEARCH_SPEC.md 第①關停頓點新增「廣蒐去重不含引文搜索」鐵律）
✅ 已修:報告策略時未主動問 SR filter（SEARCH_SPEC.md `check_strategy_approved` 段新增鐵律）
✅ 已修:SR Filter 套用對象寫錯成 PubMed（改為「PubMed 以外的腿、additive、`<leg>-SR`、design_filter_allowed:true」）
✅ 已修:leg_exhaust gate 不認得 SR 子腿（scripts/leg_exhaust_check.py 新增 `_base()` 去 `-SR` 後綴）
✅ 已修:Bug1 無可解析內容者漏到③（SEARCH_SPEC.md ②c 鐵律＋gate_guard 強化：無abstract須有實抓解析證明，否則②c判待評估）
✅ 已修:Bug2 未盡力解析全文、只憑旗標標 have（SEARCH_SPEC.md 規定②c須窮盡 PMC/Unpaywall全locations/PDF/HTML 實抓解析；gate 以 text_len 證明）
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

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
