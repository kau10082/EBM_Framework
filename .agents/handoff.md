## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

（檢索 run 進行中，尚未送審；本檔目前累積使用者於 run 中提出的流程糾正紀錄。）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

### 2026-06-22 triple-vs-dual COPD 檢索 run — 使用者即時糾正（累積紀錄）

✅ 已修：**OpenAlex 腿又把『引文追蹤』混進 ① 廣蒐階段**（本輪糾正）。
   - 問題：① 報告把 OpenAlex 腿描述成「廣檢＋④引文追蹤」，又在覆蓋限制寫「OpenAlex 原本擔任 ④ 引文追蹤」。引文追蹤（滾雪球）＝**第 ④ 關**，須等 ③ 嚴格篩定出核心後以核心為種子才做，**不屬 ① 廣蒐**。關責不外溢。
   - 本輪修改：g0_strategy.json 移除 OpenAlex 腿一切「引文追蹤/citation tracking」字眼；① 報告不再把引文追蹤掛在任何 ① 腿上；④ 的引文追蹤來源（OpenAlex 或 Europe PMC references/citations）留待 ④ 關再談。

✅ 已修：**SR filter 開啟時，SR 腿『完全取代』原搜尋腿——主檢腿不該出現、不該花力氣取盡**（本輪糾正）。
   - 問題：先前把非 PubMed DB 腿（Consensus／OpenAlex／EuropePMC）的『無過濾主檢』也跑出來（甚至把 EuropePMC main 取盡 4132 筆）只當 audit。使用者定版：**SR filter ON → 該腿只剩 -SR 變體，主檢腿整個不存在、不執行、不報告、不浪費力氣**。
   - 與舊 spec 文字的張力：SEARCH_SPEC §99「DB 腿的無過濾主檢若有實跑，只作為廣蒐取盡/稽核紀錄寫進 manifest」→ 使用者澄清語意為「**根本不要跑主檢**」（取代 audit-retain 寫法）。建議下次正式審查時一併更新 SEARCH_SPEC 措辭與 leg_exhaust_check 的 ≥4 計數假設（≥4 應以實際可跑之 SR/RCT/登錄腿為準，不靠主檢墊數）。
   - 本輪修改：g0_strategy.json 與 g1_legs_manifest.json **移除 Consensus-main、EuropePMC-main、OpenAlex-main**；不再 fetch/exhaust EP-main；語料庫腿＝PubMed(RCT)＋Consensus-SR＋OpenAlex-SR＋EuropePMC-SR＋ClinicalTrials.gov。

✅ 已修：**③ 分層篩升級『鐵律』——只有切題可早停，其餘一律逐層往下推，不得偷懶**（本輪糾正）。
   - 使用者定版鐵律：**Tier1 只要不是切題 → 全部進 Tier2；Tier2 只要不是切題 → 全部進 Tier3；Tier3 只要找不到全文 → 全部進 Tier4**。離題／皆無只能在記錄實際抵達的最底層定案。
   - 問題（舊碼）：(1) 登錄(CT)/AI(Consensus) 記錄在 **Tier2 就逕判離題**、沒被推進 Tier3/Tier4；(2) 只有「帶摘要的 PM/EP」被升 Tier3，純標題等其他非切題未一律逐層推進。＝偷懶早停。
   - 本輪修改（screen_3_run.py 重寫）：每筆非切題一律 Tier1→2→3→4 逐層累積內容、逐層判（命中切題才停）；登錄/AI 非切題也必須過 Tier3（全文嘗試）＋Tier4（Unpaywall）才可判離題；Tier3 找不到全文者**全部**進 Tier4 跑 Unpaywall。`tier` 欄記錄該筆實際抵達的最底層。
   - 註：gate `check_excl_requires_fulltext` 對登錄/AI 有「免 Tier3」例外（因無全文可取）；本鐵律比 gate 更嚴（仍逐層推進），故 gate 必過、且更誠實。

✅ 已修：**用語沿用舊編號『②c 關 / ③ 關』分開講，但 v0.22 已整合**（本輪糾正）。
   - 問題：對話說明（如 ②b 收尾「③ 嚴格篩需先 ②c 抓摘要/全文，再進 ③」）仍把 ②c 與 ③ 當兩關講。**v0.22 定版已取消獨立 ②c**：舊「②c 搜尋全文/取得性」整個併入 **③「全文/摘要搜尋及嚴格離題篩選」**——③ 內含 Tier1 既有摘要、Tier2 登錄/AI、Tier3 實取全文、Tier4 Unpaywall，全文取得＝③ 的 Tier3/Tier4，不是前置的 ②c。
   - 本輪修改：後續說明一律稱「③（含 Tier1–4）」，不再出現「②c」字眼；「待評估」桶亦已取消（③ 三桶＝切題/離題/全文及摘要皆無）。管線編號＝① 廣蒐去重 → ② 篩選策略 → ②b 高敏初篩 → ③ 全文/摘要搜尋及嚴格離題篩選（Tier1–4） → ④ 引文追蹤 → ⑤ 收斂後處理 → ⑥ 三表+PDF → ⑦ 交接包。

✅ 已修：**⑤b classify_units `--enrich` 的 nct_triple 過嚴，把核心試驗誤丟背景**（本輪發現並繞過）。
   - 問題：`--enrich` 以 g0 I 軸同義詞比對 CT.gov `InterventionName` 判試驗是否三合一，但 CT.gov 多把介入列為**成分藥分項**（Budesonide／Glycopyrronium／Formoterol 各一筆，或「BGF MDI」），無單一字串含完整三合一名 → 57 NCT 僅 6 判 in-scope、50 判 non-triple。classify 內 `if key in nontriple: 歸背景 continue` 在 **PIVOTAL 權威表之前**，導致 KRONOS／TRIBUTE／BGF 藥名報告（30232048/29429593/32152869…）被誤丟「背景:非核心RCT」。
   - 本輪處置：停用該 run 的 `nct_triple.json`（改名 .enrich_disabled），改靠 curated `PIVOTAL_LABALAMA_ARM` ＋ trip∧dual regex 判核心。重跑後核心 IMPACT 23／KRONOS 9／ETHOS 9(+ext1)／TRIBUTE 1＋BGF 藥名報告皆正確歸核心；對帳 57+105+415+18=595 平。
   - 建議下次正式審查時修 `classify_units.enrich`：I 軸比對 CT.gov 介入時應**逐成分**判（ICS∧LABA∧LAMA 三類各命中即三合一），而非要求單一字串含完整三合一名；或把 nontriple override 移到 PIVOTAL 表之後。

✅ 已修（深修）：**⑤b 不應出現『試驗未辨識／待人工確認介入』——應妥善用 CT.gov 解析**（使用者本輪糾正；已改 `classify_units.py`）。
   - 改了什麼：(1) 新增 `resolve_arms()`（取代舊 enrich）：摘要無 NCT 的 RCT **以標題搜 CT.gov 補回 NCT**（`uid_resolved.json`）；對每個 NCT 抓臂/介入**逐成分**判 `has_triple`／`has_dual_ll`（`nct_arms.json`）。(2) classify 取消舊 `nontriple` override 與 `RCT(待人工確認介入)` 桶；(3) 設計分類器收緊：群體藥動(population PK)、基因/生物標記關聯、composite-tool 方法學、real-life 即使帶 RCT pubtype 也歸背景，不進 RCT 路徑（修掉把 PK/基因/他病/裝置研究誤升核心）。
   - **關鍵發現＋安全裁決**：CT.gov 逐成分 `has_triple=True` **不可靠**——安慰劑/比較組 intervention 的 description 常列「他臂藥」造成跨臂污染假陽（實測 ILLUMINATE＝QVA149 vs ICS/LABA 無三合一臂，卻 has_triple=True；POWER 亦假陽）。**故核心一律只由 curated `PIVOTAL_LABALAMA_ARM` 背書**；CT.gov 臂只用於『可靠方向』＝`has_triple=False` 確認背景對照側、補 NCT/試驗名。已加 ETHOS-ext/FULFIL-ext 進樞紐表。
   - 結果：核心未辨識 0、待人工 0；核心 43 報告全 pivotal 背書（IMPACT22/ETHOS9/KRONOS9/ETHOS-ext2/TRIBUTE1），CT.gov 確認 41 筆「對照側RCT(無三合一臂)」歸背景；對帳 595 平。
   - 建議正式審查：若要讓 CT.gov 也能正向判核心，`_ct_arms` 需 (a) 逐 armGroup 對應其 interventionNames、(b) 排除 placebo/比較組描述、(c) 只認 intervention 自身名稱+自述成分，避免跨臂污染。

✅ 已修：**⑥ build_report_data 背景表對『無 PMID 的 SR/MA preprint』留空→validate FAIL**（本輪發現並修）。
   - 問題：兩篇 SR/MA preprint（Preprints.org 10.20944、Research Square 10.21203，標題含 "Systematic Review and Meta-analysis"）無 PMID（不在 PubMed），背景列 PMID 欄留空→`validate` 缺格 FAIL。違反 spec『PMID 無→不留空，以登錄號/DOI＋理由』。
   - 本輪修改 `build_report_data.py`：背景迴圈對無 PMID 者改以 `DOI:<doi>` 當識別欄（標 preprint）、全文狀態記『需補』、檢核沿用 verdict，不再留空。
   - 結果：三表產出（核心 43／背景 SR-MA+指引 118／進行中 5），report_check 5 段全過、Phase1 PDF 產出且登記 pdf_path、gate_guard 全綠。

✅ 已修：**PRISMA 最後一步『納入分析文獻 Included』須與交接包 corpus_seed 內容/細項一致**（使用者本輪糾正；已改 `build_search_pdf.py`）。
   - 問題：build_search_pdf 自行以『核心 RCT＋srma_in_analysis』即時重算 Included，與 corpus_seed(verdict=included) 兩套來源各算各的 → 會漂移。本案實測：`srma_in_analysis=[]` 使 PDF Included＝43(核心)＋0，但 corpus_seed included＝168（43 pivotal＋105 SR/MA＋20 支持性）→ 不一致。
   - 本輪修改 `build_search_pdf.py`：Included 步驟優先採用報告的 `included_for_analysis`（total＋breakdown），**該欄由產生 corpus_seed 的同一 ⑤b verdict=included 分類確定性計算**（同源→不可能漂移）；未提供才回退舊即時重算（向後相容）。
   - 落地：`_search_report.json` 新增 `included_for_analysis`（total 168／核心RCT43[IMPACT22/ETHOS9/KRONOS9/ETHOS-ext2/TRIBUTE1]／SR/MA 105／支持性RCT 20），prisma_flow.included＝168，與 `_corpus_seed.json` verdict=included(168) 完全一致；report_check／gate_guard 全綠。
   - 建議正式審查：可在 report_check 增一條硬 gate『_search_report.included_for_analysis.total == _corpus_seed verdict=included 數』把此一致性釘成機器檢查（本輪以同源計算＋斷言保證，尚未落為常駐 gate）。

✅ 已修：**交接包只放『實際納入分析』者，背景不進交接包、也不進 PRISMA 末步『納入分析的文獻』**（使用者本輪定版）。
   - 問題：我產 corpus_seed 時用了 `--include-background`，把 427 篇背景（觀察/經濟/綜述/指引/對照側 dual-only RCT/三合一 vs ICS-LABA/進行中）也塞進交接包（595 篇）。使用者定版：**沒有要進分析的（如背景）就不該出現在交接包，也不該出現在 PRISMA 末步**。
   - 處置：移除 `--include-background`（回到 build_corpus_seed 正確預設＝只交接 verdict=included 且 grade_track∈{full,targeted_harms,light_summary}）。corpus_seed 由 595→**168**（核心RCT 43＋SR/MA 105＋候選三合一RCT 20），verdict=background 0；與報告 `included_for_analysis.total=168`／PRISMA 末步一致（已斷言）。
   - 「實際納入分析」定版＝168：①4 樞紐 RCT(43 報告，RoB+outcome) ②105 SR/MA/NMA(主要綜合證據，GRADE pooled) ③20 候選三合一 RCT(待 Phase 0 全文確認對照臂)。背景 427 留在 g7_units／報告分流統計供追溯，不交接、不計入「納入分析」。
   - 建議正式審查：可加一條機器 gate『_corpus_seed.json 不得含 verdict=background』＋『included_for_analysis.total == corpus_seed 篇數』把「交接包＝納入分析集、且與 PRISMA 末步一致」釘死（本輪以正確預設＋斷言保證）。

✅ 已修：**⑤b 不得有『候選/待確認』灰色地帶——每筆三合一 RCT 一律確定核心或背景**（使用者本輪糾正；已改 `classify_units.py`）。
   - 問題：上一版把對照臂未能確認者丟『背景:三合一RCT(非樞紐,待Phase0覆核)』灰色桶＝灰色地帶。使用者定版：不應有此類東西。
   - 本輪修改 `classify_units.py`（核心判定改為『正向確認制』，無灰色、無未辨識）：
     * **核心『只』由三條正向來源背書**：①curated `PIVOTAL_LABALAMA_ARM`（IMPACT/ETHOS/KRONOS/TRIBUTE+ETHOS-ext）②ICS 退階設計（嚴格 `ICS_WD_STRICT`：撤除/退階須與 ICS 鄰近共現，修掉泛 step-down 管理策略誤判，如 30147307 退背景；保 WISDOM/SUNSET）。
     * **移除 `ctgov_dual_arm` 自動判核心**：實測 CT.gov `has_triple`／`trip` 皆有假陽（安慰劑/比較組 description 列他臂藥→跨臂污染：ILLUMINATE、POWER；`has_dual_ll` 又會誤收純雙支擴試驗 27028749 dual-vs-dual）→ 不可靠，不用於『指派』核心；CT.gov 只用於可靠的『負向』方向（`has_triple=False`→背景對照側）＋補 NCT/命名。
     * **其餘三合一 RCT 一律確定歸背景**：『背景:三合一RCT(對照非雙支擴或未確認,本題非核心)』，不留待覆核。
     * **消除『(未辨識)』**：核心未連到試驗名者改以 NCT 或 `研究-PMID<pmid>` 穩定識別。
   - 結果：核心 46（43 樞紐＋3 ICS 退階：WISDOM×2、SUNSET）｜灰色待覆核 0｜未辨識 0；corpus_seed=151（46 核心＋105 SR/MA，全 included/full），background 444 不交接；PRISMA included 151＝corpus_seed 151（斷言通過）；gate_guard 全綠。
   - 後果說明（安全傾向）：核心改『正向確認制』後，極少數『非樞紐、CT.gov 無法可靠確認對照臂』的真三合一-vs-雙支擴 RCT（如 BGF 影像子研究 34210340）會落背景而非核心；最壞後果＝下游少一兩篇支持性子研究，pivotal 主證據(IMPACT/ETHOS/KRONOS/TRIBUTE)＋105 SR/MA 不受影響。寧可如此，也不要灰色地帶或假陽核心。

✅ 已修：**SR/MA 不可全納入分析（避免 double-counting）；依 Cochrane 方法學分模式處理**（使用者本輪定版方法學）。
   - 鐵律（Cochrane Handbook Ch.4／Ch.V）：撈到的 SR/MA **絕不全進最終數據池**。
     * 標準 SR（分析單位＝原始 RCT）：SR/MA 只當『引文追蹤種子』＋『討論區對照』，不進森林圖/GRADE 池。
     * Overview/Rapid Overview（分析單位＝SR/MA）：仍須以 §V.3.2.1 四步挑選：①PICO 契合 ②檢索新鮮度 ③方法學品質(AMSTAR2/ROBIS) ④原始研究重疊率(CCA/證據矩陣)；只取最新+最佳+不重疊的 1～幾篇為基底。
   - 本案使用者選 **Rapid Overview**。處置（改 run 層 build_seed.py，非框架碼）：
     * **基底 SR/MA 候選 shortlist（6 篇，grade_track=full）**＝可從 metadata 判的條件挑出（檢索新鮮度≥2024、NMA/全族群、PICO 直接 triple-vs-dual、來源）：42237170/41998645(2026 NMA 綜合)、41425996/40139054(2025 NMA 死亡率/CV)、39649253/38877687(2024 NMA/比較效益)。**最終非重疊基底由 Phase 0 以 AMSTAR2/ROBIS＋CCA＋檢索日定稿**（本層只給候選）。
     * **非基底 SR/MA（99 篇）→ 不進池**（verdict=background, grade_track=none）：用途＝引文追蹤(已於④做)＋討論對照。
     * **核心 RCT（46）→ 佐證**（grade_track=light_summary, role=pivotal_efficacy）：驗證基底 SR/MA 數據＋關鍵試驗 RoB，不自行池化。
     * 方法學示例：唯一 Cochrane review 40178181 為『dual vs 單方』＝PICO 不符，**故依步驟①排除**（不因是 Cochrane 就收）。
   - 結果：corpus_seed＝**52**（6 基底 SR/MA＋46 佐證 RCT），background 0；PRISMA「納入分析」52＝corpus_seed 52（斷言通過）；report_check／gate_guard 全綠。
   - 修正先前錯誤：上一版把 105 SR/MA 全標 grade_track=full 進池＝double-counting 偏誤，已改為 shortlist 制。
   - **已持久化（committed，不隨 container 消失）**：方法學鐵律寫入 `EBM_Search/SEARCH_SPEC.md`（★★ SR/MA 處置鐵律：模式 A 標準 SR／模式 B Overview 四步挑選；檢索只給候選 shortlist、AMSTAR2/CCA 定稿留 Phase 0）。run 層 shortlist 邏輯在 cache/build_seed.py（run-specific，gitignored，屬本題 run 資料）。

✅ 已修：**PDF PRISMA 漏斗表『納入分析』明細欄過長、與下方文獻清單重疊**（使用者本輪糾正；已改 `build_search_pdf.py`）。
   - 問題：funnel 表 `fr` 各格用『純字串』餵 reportlab Table→長字串（納入分析的基底 SR/MA＋RCT 明細）不換行、溢出與下一段（段4 最終納入清單）重疊。
   - 本輪修改 `build_search_pdf.py`：funnel 表改以 `cell()`(Paragraph, wordWrap=CJK) 包每格→長明細自動換行、不溢出；並把 included_for_analysis 的 label/detail 收斂為精簡寫法。
   - 已以 PyMuPDF 渲染頁面實檢：納入分析 52（基底 SR/MA 6＋佐證 RCT 46）明細換行正常、與『最終納入證據清單』表清楚分隔，無重疊。report_check／gate_guard 全綠。
   - **已持久化（committed）**：修在 `EBM_Search/scripts/build_search_pdf.py`（funnel 表 `fr` 以 `cell()` 包每格換行）＋ `SEARCH_SPEC.md` ⑥ 新增『★ PDF 表格長字串必換行』鐵律。

✅ 已修：**PRISMA『納入分析』明細：標籤不夾方法學附註、研究改用『作者+年份』非 PMID**（使用者本輪糾正）。
   - 問題：included_for_analysis 標籤夾『(grade=full；Phase 0 以 AMSTAR2/CCA 定非重疊基底)』方法學括註、SR/MA 明細用 PMID 清單。使用者要：附註拿掉、SR/MA 改作者+年份。
   - 本輪修改：_search_report.json included_for_analysis 標籤改乾淨類別名（Overview 基底 SR/MA／佐證原始 RCT）、SR/MA detail 改『第一作者 年份』（Hu 2026；Calderón-Montero 2025…，efetch 取）；移除 mode/note 等不顯示欄。
   - **已持久化（committed）**：`SEARCH_SPEC.md` ⑥ 新增『★ PRISMA 納入分析明細列法』鐵律（標籤不夾方法學附註；研究以作者+年份非 PMID）。已渲染頁面實檢、report_check／gate_guard 全綠。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
