## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：EBM_Search 檢索流程多項改善（使用者 2026-06-21 於 triple-vs-dual COPD 實跑中連續糾正）

本輪審查範圍：僅以下 4 檔
- `EBM_Search/SEARCH_SPEC.md`
- `EBM_Search/scripts/leg_exhaust_check.py`
- `EBM_Search/scripts/gate_guard.py`
- `EBM_Search/scripts/classify_units.py`

改了什麼（6 條）：
1. **① 廣蒐不含引文搜索**（SEARCH_SPEC.md，第①關停頓點）：① 只「廣蒐＋去重」，引文追蹤/snowball＝④，須在 ③ 定核心後做；OpenAlex/EuropePMC 在 ① 僅廣檢。
2. **報告策略時主動問 SR Filter**（SEARCH_SPEC.md，`check_strategy_approved` 段）：報告策略時必須主動問是否套 Systematic Review Filter。
3. **SR Filter 用在『PubMed 以外』的腿**（SEARCH_SPEC.md）：PubMed 維持 Cochrane RCT 過濾器；SR 過濾器套 Consensus/OpenAlex/EuropePMC（additive、`<leg>-SR` 命名、design_filter_allowed:true）；CT.gov 不適用。
4. **leg_exhaust 認得 `<leg>-SR` 子腿**（scripts/leg_exhaust_check.py）：新增 `_base()` 去 `-SR` 後綴，SR 子腿沿用母腿窮盡分類。
5. **②c 必『實抓+解析』全文、無可解析內容者在②c就判待評估**（SEARCH_SPEC.md ＋ scripts/gate_guard.py）：
   - Bug1（使用者）：所有管道都無摘要/無可解析全文者，應在「②c 全文搜索」這一關就歸「待評估」，不該漏到 ③ 才發現。
   - Bug2（使用者）：未盡力解析全文（只憑 OA/PMC 旗標標 have），導致後關才「突然」多出可解析全文。
   - 修法：SEARCH_SPEC 新增鐵律——②c 對無摘要者須**窮盡管道實抓+解析**（PMC fullTextXML／Unpaywall 全部 oa_locations／OA PDF(pdftotext)・HTML 去標籤），取得可解析正文才算 have；三管道抓+解析後仍無內容（含外文無法以英文軸詞比對）→ ②c 判 `待人工補全文`，不得漏進 ③。
   - 機器看守：`gate_guard.check_partition_provenance` 強化——screened 且無 abstract 者，其 uid 須在 `g3_fetched_by_uid.json` 且帶實抓解析證明（`text_len`≥1500 或 `verified`，登錄試驗 `channel:registry` 例外）；只掛旗標無正文＝FAIL。等於把「have 須實抓驗證」前移到 ②c。
6. **⑤b classify_units 的 `--enrich` 找不到介入軸→CT.gov 交叉核對靜默跳過**（scripts/classify_units.py，使用者糾正）：
   - Bug：`enrich()` 寫死 `axes.get("I")` 找介入軸，但 g0 介入軸鍵名為 `I_triple` → isyn 取到空 → 所有 NCT 介入判「不在範圍」→ 真三合一 RCT 會被誤丟背景；且因實跑時我整步跳過 `--enrich`，CT.gov 的 NCT→試驗名／介入交叉核對根本沒跑，留下大量「未辨識 RCT／格式異常 NCT」需人工覆核。
   - 修法：`enrich()` 改為**穩健尋找介入軸**——`axes.get("I")` 無效時，掃 axes 找鍵名 `I`／`I_` 開頭或 role 含 "intervention" 的軸。實跑（補 g0.four_axis_expansion 三合一成分後）`--enrich` 生效：CT.gov 核對 34 NCT→13 三合一／21 雙合一·他藥，核心 82→59 報告、25 筆非核心 RCT 正確歸背景。
   - 殘留「未辨識 39」經查證實＝**有摘要的獨立小型 RCT（無 NCT）**、「title-only 19」＝**勘誤/讀者來函/社論/會議短摘**（本無摘要）——非流程缺失。

fresh-clone / 自測：
- `python EBM_Search/scripts/selftest_guards.py` → ✅ 全部守門有效（含改過的 leg_exhaust、gate_guard）。
- 實跑 COPD cache：`gate_guard.py` 全關通過。第 5 條修正後實跑效果：原 96 筆「無摘要卻靠旗標/標題進 ③」者重抓，58 可解析、其中 27 可靠重篩（14 切題/13 離題）、69 無可解析內容→退回②c待評估；切題 349→354、待評估 63→132。證明 Bug 屬實且修正生效。

想被重點看：第 5 條 `check_partition_provenance` 的 `text_len≥1500` 門檻與 `channel:registry` 例外是否合理；②c 鐵律措辭是否與既有「待評估三管道」「有 OA 卻不抓」「have 須實抓驗證(verify_have_fetchable)」段一致無重複矛盾。

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

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
