---
name: EBM_Search
description: |
  系統性回顧（SR）對齊的多源文獻檢索 ＋ Crossref／PubMed 交叉驗證引擎（原名 consensus-verify）。
  來源涵蓋 PubMed／Consensus／OpenEvidence ＋ ClinicalTrials.gov／OpenAlex／Europe PMC／Epistemonikos，
  敏感度優先、不在檢索階段以期刊分位篩（品質交下游 RoB／GRADE）。
  當使用者要對某主張或臨床問題做實證檢索、需要「可信引用清單」、要確認文獻是否
  真實存在、要剔除幻覺引用、或要為 EBM 評析／衛教文／報告建立經查證的參考文獻時,
  務必啟動此 skill —— 即使使用者只說「幫我查文獻」「這條 claim 有沒有證據」而未明講「驗證」。

  觸發情境:
  - 「幫我查證這個主張」「用 Consensus 找文獻」「建立可信引用清單」
  - 「驗證這些引用是不是真的」「這篇文獻真的存在嗎」「交叉驗證 Crossref PubMed」
  - 「幫 4+2R／某主張找實證」「這條 claim 有沒有證據」「幫我整理參考文獻」
  - 提供一段主張／一批引用,要求查證、去幻覺、標證據等級、做成參考清單
---

# Consensus 檢索 × Crossref／PubMed 交叉驗證 Skill — v0.20

本 skill 是 EBM 評析管線中的「**證據引擎層**」:只負責「找文獻 → 驗證真偽 → 標等級 →
產出三表」。不負責對 claim 做支持／反對的論證(那是上層評析的事)。

> ## ★ 執行規範(v0.12,務必遵守)
> **(A) 分階段停頓、逐關確認**:EBM 管線各階段之間**必須停下來報告該階段結果＋等使用者點頭**才續,不可一口氣跑到底。**Phase 1(檢索→篩選→引文追蹤→三表)內部的停頓點(v0.19.9,務必逐一停)**:
> **① 六腿完整檢索 ＋ 去重完成 → 停**,**逐腿報告**:搜尋結果(命中數)、搜尋策略(實際 query)、搜尋限制(各腿單次上限/未涵蓋/AI 合成腿無法窮盡)、**是否確實翻頁取盡**、跨腿去重後聯集數。**此時尚未做任何主旨篩選。**
> > **★ 六腿逐一點名(鐵律,v0.20.1):** 六腿＝**Consensus／PubMed／OpenEvidence／OpenAlex／Europe PMC／ClinicalTrials.gov**(Epistemonikos 為可選第七腿,有 token 才跑)。第①關報告**必須把六腿全部列出**,每腿只能是兩種狀態之一:**①命中數(已實跑)** 或 **②跳過＋硬理由**。**唯一合法的跳過理由＝技術硬限制**:MCP 未連線/relay 未連、無金鑰、管轄封鎖(如 OE `oe_auth_status` 失敗)。**嚴禁以『價值低／與他腿重疊高／問答型用處不大／應該已被涵蓋』等主觀判斷略過任何一腿**——是否重疊要『跑完去重後用數字證明』,不是『跑之前用直覺假設』。**能跑而未跑＝本關未通關,不得進第②關。** (本鐵律因實測一度擅自省略 OpenEvidence 而立。)
> **② → 停**,報告**接下來的篩選策略**(必含連言軸、可用的四型軸、納入/排除準則;含「初步篩選＋嚴格篩選」兩階),等使用者確認後才篩。
> **②b 初步篩選(高敏感,寧留勿殺)完成 → 停**,報告**初篩狀況**(保留 N、明顯離題剔除 N 及各自缺哪軸);只移除「某核心軸明顯離題」者、模糊先留,等確認後才進。
> **②c 搜尋全文(對初篩保留者)完成 → 停**,報告:有全文 N／只有 AI 合成摘要 N／全無 N;**逐篇記錄全文取得狀態作為標記、帶到最終 PDF 表**(v0.19.14:**預設不在此匯 Zotero**,避免灌入會議摘要與未嚴格篩之雜訊;Zotero 留待 §⑤〔引文追蹤收斂後、PDF 之前〕或使用者明確要求),等確認後才進嚴格篩選。
> **③ 嚴格主旨篩選完成 → 停**(此階**改對全文／AI 合成摘要**核對,非僅 title/abstract),報告**篩選狀況**(切題/離題/待覆核各幾篇與理由),等確認。
> > **★ 第③關只判『主旨切題與否』(鐵律,v0.20.1;v0.21 必含軸改 per-topic):** 本關**唯一輸出＝所有必含軸是否同時成立**——**必含軸由 `g0_strategy.json` per-topic 宣告**(一般題＝疾病軸 ∧ 介入軸;**比較型題另含對照 C 軸**,如 triple vs dual LABA/LAMA＝P∧I∧C)。切題(所有必含軸都現)＝清單二候選／離題(缺至少一軸,標明缺哪軸)＝清單三。每筆切題者須記 `axis_hits`(逐軸證據)供機器守門 `strict_screen_check` 核對,**缺任一必含軸證據即視為放水→FAIL**。**`axis_hits` 值須為明確 token(`yes`/`no`/`unknown`)或結構 `{"status":<token>,"evidence":"原文片段"}`;嚴禁直接填自然語言說明(如「未提及對照組」)——不認得的自由文字一律當 `unknown`(不放水),絕不可當命中。****配套(v0.21,平衡 recall):若 P∧I 已現、但摘要看不出 C 軸(短摘要常省略對照/SOC),不得逕判離題,應移『待評估』待看全文;唯全文/AI 合成摘要確認確實缺 C 才判離題。**
> > **★ 登錄試驗用欄位判軸、勿用標題(鐵律,v0.20.1):** ClinicalTrials.gov 等**登錄記錄的標題極短又常被截斷**,用標題關鍵字判軸會**誤殺真試驗**(實測:GSK2793660、HSK31858 兩筆 DPP-1×支擴試驗因標題截斷被誤判離題)。登錄腿**判軸一律讀 `Condition`(疾病軸)＋`InterventionName`(介入軸)兩欄**,不夠時回 CT.gov API v2 `fields=Condition,InterventionName,StudyType,Phase,OverallStatus` 補抓。**廣蒐時就應把這些欄位存進腿記錄**(別只存 title),否則後段判軸失據。**嚴禁在本關做文獻型態分類或決定『納入單位』**(哪些是 RCT／SR-MA／背景、哪些當分析主體 vs 背景)——那是**第⑦關 決定納入單位**的事,且須在 ⑤引文追蹤、⑥交叉驗證**之後**才做。報告用語一律「切題／離題」,**不要用「納入／背景」**(那兩詞是 ⑦ 的 `verdict:included/background`,在此誤用會把後關工作提前、污染分流)。(本鐵律因實測在第③關擅自做了 RCT/SR-MA/背景型態分類而立。)
> **④ 確認後才做引文追蹤(C30,可能多輪、逐輪至收斂)**;**待全部收斂後才停**,一次報告各輪(種子/反向·正向筆數/新增)與最終納入。
> **⑤ 引文追蹤收斂後 → 停(v0.19.15:Zotero 與人工補全文「都在 PDF 之前」)**,做兩件事並等使用者確認:
>   (a) **問「是否要將最終納入結果匯入 Zotero 資料夾?」**——未得明確同意不得匯入(若同意,先乾跑顯示 payload 再 `--commit`)。**Zotero 清單＝單一真實來源,須與報告表二/表三完全一致(v0.19.15)**:匯入集合必須**恰等於**「表二 納入(後續要分析者)＋表三 背景(當背景者)」,不多不少;並以標籤標明用途讓 Zotero 可直接篩出與報告一致的子集——**納入者標 `verdict:included` ＋ `study:<試驗名>`**(對齊分析單位 Study,MECIR C42;同一試驗多報告共用同一 study 標籤)、**背景者標 `verdict:background`**。如此「後續分析清單(篩 verdict:included→依 study 收斂為 N 個 Study)」與「背景清單(篩 verdict:background)」皆可由 Zotero 重現、不與報告脫節。
>   > **★ 決定納入單位：Study≠藥、報告數必對帳(鐵律,v0.20.1):** (1) **分析單位＝Study(同一試驗)**,非「篇」也非「藥」;同一試驗的主報告＋子報告(機轉/子分析/protocol/baseline/會議摘要)**共用 `study:<試驗名>`、合併為一個分析單位**。(2) **同藥≠同 Study**:同一藥物的『不同試驗』是**不同 Study**——如 BI 1291583 的 AIRLEAF(Ph2,納入) vs AIRTIVITY(Ph3)、CLAIRLEAF(延伸)、CF/PK 試驗(各為獨立試驗,無結果或他病→背景),**嚴禁把整個藥物程序併成一個 Study**(實測曾誤把 AIRTIVITY/CLAIRLEAF/CF/PK 全塞進 AIRLEAF,報告數 24→正確 4)。(3) **報告數不可省略、且必對帳**:決定關報告**每個靶子 Study 底下幾篇報告**,並硬性核對恆等式 **`Σ靶子研究報告 ＋ SR/MA ＋ 背景 ＝ 切題候選總數`**;對不上即有歸錯,須查到平。(本鐵律因實測一度只報「4 個 Study」卻略過各 Study 報告數、且把同藥他試驗誤併,導致下游數量對不起來而立。)
>   > **★ Zotero 匯入範圍校正(鐵律,v0.20.1):** Zotero 匯入的**唯一相符範圍＝「表二納入＋表三背景」全匯**(即上句『恰等於表二+表三』)——只有它能保 Zotero≡報告。**`--dry-run→--commit` 是任何匯入都要走的執行步驟,不是一種『範圍』**(勿把它跟範圍選項並列)。若使用者要更窄範圍(只原始研究/只 4 Study/全部候選),**允許但須當面告知『這會讓 Zotero≠報告表二三』並取得同意**,不可預設。問法:先問「是否匯入(預設全匯=表二+表三)」,要匯入再確認是否縮範圍。
>   (b) **提供一個本機「人工補全文」資料夾**(由根 `config/settings.yaml` 的 `report.fulltext_dir` 指定,現＝`OneDrive\文件\EBM_Framework\fulltext\<題目_日期>\`;留空才回退 Windows『文件』下 `EBM_fulltext\<題目_日期>\`),**逐筆列出「僅 AI 合成摘要／無全文無摘要」者**(檔名建議 = DOI 去斜線 或 PMID),讓使用者**人工把缺的全文 PDF 放進去**。使用者完成後,**重新掃描該資料夾、更新各篇全文狀態標記**(人工補入者改標「有全文(人工補)」),再請使用者確認。
>   > **★ 補全文三鐵律(v0.20.1,因本階段連犯三錯而立):**
>   > **(1) 全文有無＝實際抓取為準,不可臆測。** 判定一篇能不能讀全文,**要真的去抓全文**(PMC `fullTextXML`／開放 PDF／efetch)並確認拿到正文(字元數遠大於摘要);**嚴禁憑期刊名臆測『付費＝缺』(NEJM/Lancet 也可能有 PMC),也不可只看 OA 旗標**(旗標≠我抓得到)。實測:曾憑期刊猜「5 篇付費需補」,真抓後才知 AIRLEAF/Emara 有 PMC 全文、真正抓不到的是另 4 篇。**取全文順序(v0.20.2)：PMC fullTextXML → `tools/unpaywall.py`(Unpaywall 免金鑰、只要 email,找 green/gold OA PDF;機構典藏要用瀏覽器 UA 抓) → 人工補 PDF → ai_synthesis(二手)。** 退 ai_synthesis 前『必先過 Unpaywall』(實測 ASPEN 在 Dundee 有 green OA、AIRLEAF 可直接抓回 7.4 萬字)——quote_verify 已內建此 fallback。
>   > **(2) 主詞是『我(Claude)』的存取,不是使用者的機構權限。** 要回答的是「**我**線上讀得到哪幾篇全文、讀不到哪幾篇」——因為評讀的是我。**別答成『你機構帳號可讀』**(那是使用者的權限,與我能否評讀無關)。讀不到的(只剩摘要)才需使用者補 PDF 或退 AI 合成摘要(見 analysis-read-fulltext-not-download)。
>   > **(3) 資料夾與清單 txt 要『實際建立』,不是用文字描述。** 本關必須真的 `os.makedirs` 建出 `report.fulltext_dir/<題目_日期>/` 並**寫出實體 `需補全文清單.txt`**(列待補各篇:標題／DOI／建議檔名／為何需要,＋免補清單),讓使用者打開資料夾就看得到。**嚴禁只在對話裡描述路徑卻沒建檔**(實測使用者『找不到資料夾跟 txt』即因此)。
>   **(a)(b) 都確認後才進 ⑥。**
> **⑥ 三表 ＋ PDF 報告交付 → 停**。以 ⑤ 更新後的全文狀態標記產 PDF(三表＋全文狀態欄＋交叉檢核欄＋APA＋方法學註記)。**無 PDF 不算 Phase 1 完成。**
> **⑦ 寫交接包 ＋ 問是否續進 EBM 分析(v0.20,交接層) → 停**。三表/PDF 交付後,把本次「已決定的事」寫成 **交接包 `_corpus_seed.json`**(放全文資料夾,與 PDF 同處),供下游 **EBM_Analysis** 的 Phase 0 直接吃,免使用者手動搬 PDF、免 Claude 重定 PICO/分流。內容＝**必含軸→PICO 雛形** ＋ 每篇 **verdict(included=表二納入／background=表三背景)、study 標籤、證據等級、全文狀態、PDF 檔名、suggested(relevance/role/grade_track) 映射**。**交接包＝表二(納入)＋表三背景(background),與 Zotero 一致性規則同一真實來源(⑤a);驗證不符/主旨不符/品質閘剔除者不進交接。** 組好 seed dict 後以 `python scripts/build_corpus_seed.py --in seed.json --out-dir "<全文資料夾>"` **驗證契約並寫出**(契約正本 `references/corpus_seed_schema.json`;映射規則見 `EBM_Framework/INTEGRATION.md`)。寫出後**停下問使用者「是否繼續進入 EBM 分析?」**——回「**繼續/是**」即接力(切到 EBM_Analysis,Phase 0 讀交接包預填分流、仍在斷點讓使用者覆核);回「否」就停在此,交接包留存,日後對 Claude 說「繼續(進入 EBM 分析)」或指向該交接包即可接上(本框架已取消 `/ebm` 獨立啟動,評讀一律由本檢索接力)。
> **跨 Phase 停頓點**:
> 6. **Zotero 匯入完成** → 停,報匯入結果(成功幾筆),問「是否進 Phase 3 全文?」
> 7. **交接包寫出完成(⑦)** → 停,問「**是否繼續進入 EBM 分析?**」;同意則接力 EBM_Analysis(讀 `_corpus_seed.json`),否則停在此。
> 任一階段做完先**呈現結果＋等使用者點頭**才進下一關;使用者喊停就停在當關。
> > **★ 機器守門優先於記性(鐵律 v0.20.3,因『取盡偷工』『漏跑 Unpaywall』各復發而立):** 凡有對應守門腳本的關卡,**報告該關完成前必先跑守門、貼 PASS 才算通關**——不可只靠記憶/自律。守門對照:**Gate ① 取盡**＝`scripts/leg_exhaust_check.py`(讀 `g1_legs_manifest.json`,逐腿斷言可窮盡腿 fetched≥hitCount;廣蒐時就要逐腿寫 hitCount/fetched/exhaustible/skipped+reason 進 manifest)、**Gate ②c Unpaywall**＝`scripts/fulltext_audit.py`/`gate_guard.py` 的 Unpaywall 覆蓋稽核(每筆非全文且有 DOI 必須已過 Unpaywall 且未誤判)、**流程數字**＝`funnel_check.py`；**Gate ③ 反坍縮**＝`gate_guard.py` `check_partition_provenance`(每筆配穩定唯一 `uid`、全程只用 uid 當鍵；嚴禁用 `pmid+'|'+doi` 之類複合鍵當 dict key——無 ID 記錄會全坍縮成同一鍵造成污染。守門以 uid 獨立重算:screened⊎awaiting 恰覆蓋 base 且互斥無重複、且每筆 screened 須真有 abstract 或在 fetched 表)。**判 have 須實抓驗證**＝`verify_have_fetchable.py`＋`gate_guard.py` `check_have_verified`：與 `fulltext_audit.py`(查 not-have 是否其實 OA、防低估)對稱——**凡 included 且要評讀(full/targeted_harms)、fulltext_status=have(online 無本機 pdf)者,必須以 `verify_have_fetchable.py` 實抓確認『真全文』(PMC/PDF/夠長且含方法-結果-CI 多特徵的 HTML;單純 OA 旗標或中繼著陸頁不算)、蓋 `fulltext_verified=true`**;否則守門 FAIL。**嚴禁只憑 Unpaywall `is_oa` 旗標判 have**(實測 IMPACT/ETHOS 旗標 OA 但 NEJM 出版商 URL 403、ETHOS 還因錯 DOI 假陽性,拖到評讀才爆;此器在 ②c/⑧ 就抓出假 have、降 need-supplement)。**`have(online)` 之全文取得性要窮盡 Unpaywall `oa_locations`(非只 best),別只試一個來源。**
> > **報告資料制式化**＝`build_report_data.py`(確定性從 cache 組三表、**固定欄位**〔核心 5 欄/背景 6 欄/進行中 3 欄〕、**每格務實填滿**〔缺 title/全文狀態/登錄號自動 EuropePMC/Unpaywall 回填〕、排除撤稿、寫出前自我驗證無缺格；`--merge-into _search_report.json`)。**嚴禁再手拼 _search_report.json 的三表**(手拼＝欄位飄、常缺格的根因)——一律走此產生器。
> > **報告版型/內容**＝`report_check.py`(③只能切題/離題二分、核心表 PMID 欄不得空、研究名不得佔位『待確認/請見』、子報告逐筆不得『另含N篇』、背景表須含 PMID＋檢核欄、進行中試驗表必存在、閉合須含二分算式——皆為 2026-06 使用者逐條糾正之缺失轉成的機器檢查)。**撤稿管控**＝`gate_guard.py` `check_no_retracted`：⑥交叉驗證**統一查撤稿**（PubMed `Retracted Publication`[PT]＋標題 `Retracted:`＋**Crossref `is-retracted`/`update-to:retraction`**），RETRACTED 一律剔出 納入/背景/報告表/**Zotero payload**/交接包（實測撤稿 SR 36072633 曾被當背景匯入 Zotero→須先剔除再匯入；已匯入才發現則以 Zotero API 刪除）。
> > **★ 可攜可靠性(鐵律 v0.20.4,因『記憶不隨 repo、別人 clone 會重犯』而立):** auto-memory 是**個人本機、不進 repo、不被 pack_skill 打包**→別人拿不到、不可作為唯一防線。**真正可攜的防線＝committed 進 repo 的 SEARCH_SPEC＋scripts/{gate_guard,leg_exhaust_check,report_check,fulltext_audit,funnel_check}＋專案級 `.claude/settings.json`(Stop hook,用 `${CLAUDE_PROJECT_DIR}` 相對路徑)。** 凡新建守門腳本**必 commit**(未追蹤＝別人沒有)。**每關報告完成前自己先 `gate_guard.py --cache <dir>` 並貼 PASS**(打包成 Desktop skill 時無專案 hook,只能靠此自律＋SKILL 指示)。**安裝/clone 後先 `python scripts/selftest_guards.py`** 證明守門有效。**每當使用者人工抓到新缺失,優先把它轉成 report_check/gate_guard 一條檢查(而非只寫記憶)。**
> > **★ 防『未查全文就丟兩者皆無』(機器 gate,v0.21;因 2026-06 使用者糾正而立)：** ②c 對初篩保留者**逐筆抓全文**，**無全文且無摘要才列待評估**。但「待評估」分兩種、不可混：**有 DOI/PMID＝有全文路徑**，必須先查 Unpaywall／PMC，若仍取不到內容→判 `待人工補全文`(`channels_exhausted=true`，記 OA 連結)，**嚴禁逕判 `兩者皆無`**；`兩者皆無` 僅限**完全無 ID／無任何全文路徑**者。此規已落為 `stage1_check`(併入 `gate_guard` Stage A→B 邊界)：awaiting 標 `兩者皆無` 卻帶 doi/pmid → FAIL。
> > **★ 防搶跑：策略須先經使用者核准才可檢索(機器 gate,v0.21;因 2026-06 使用者糾正而立)：** 本管線最前面的停頓點＝**先報告檢索策略(必含軸／各腿 query／納入排除／範圍決策)、停下等使用者確認**,**嚴禁未報告策略或未得確認就執行檢索,亦嚴禁檢索時自行縮放範圍**。此要求已落為機器 gate `gate_guard.py` `check_strategy_approved`：**`g1_legs_manifest.json`(廣蒐產物)存在時,`g0_strategy.json` 必須帶 `approved_by_user:true`**(使用者確認策略後才設),否則 FAIL＝搶跑。任何範圍變更(收窄/放寬 query、改腿、加設計過濾)都須回到此停頓點重新報告並重得核准,不得自行決定。
> > 總入口 `scripts/gate_guard.py`(`--cache <dir>` 人工跑；`--auto --hook` 供 harness Stop hook 自動跑,FAIL→exit 2 擋住回合)。**守門只在 cache 內有哨兵 `_search_active.flag` 時生效**:Gate ① 開始建旗標、⑦交接寫出或結案時刪旗標(平時全域休眠零打擾)。**嚴禁繞過守門用手刻臨時腳本完成關卡卻不跑稽核**(本輪即因全程手刻 Python 而讓既有 `fulltext_audit.py` 沒被觸發)。
> > **★ 檢索切兩段＋契約交班(架構,v0.21,降分心/強遵從):** 把易漂移的檢索中段釘成磁碟邊界——
> > **Stage A＝⓪策略→①廣蒐去重→②b高敏初篩→②c全文/摘要取得性**；收尾以 `build_stage1_corpus.py` 確定性寫出**交接契約 `_stage1_corpus.json`**(schema＝`references/stage1_corpus_schema.json`,欄位與 `_corpus_seed.json` 同族,差別僅 `verdict:"candidate"`):每筆 metadata＋`fulltext_status`(have/ai_summary_only/none)＋`abstract_status`＋`fulltext_channel`/`fulltext_url`＋內容(摘要);無內容者入 `awaiting`(待評估,設旁不進 Stage B)。
> > **邊界硬 gate `stage1_check.py`**(併入 gate_guard):斷言每筆全文狀態 resolved(無`?`)、**無內容者不得列 candidate(待評估屬 Stage A)**、每腿取盡、candidate/awaiting 互斥。**PASS 才准進 Stage B。**
> > **Stage B＝③嚴格篩→④引文追蹤→⑥交叉驗證→⑦決定納入單位**,**只讀 `_stage1_corpus.json`**(看不到 Stage A 原始混沌),輸出＝`_corpus_seed.json`(verdict 定案 included/background)。
> > **此切割直接根治本框架最常犯的「待評估屬②c還③」邊界混淆**;但切段只是必要非充分,段內失誤仍靠各 gate_guard 檢查——兩者互補。
> > **★ 關責不外溢(總則,鐵律 v0.20.1):** 每一關**只做該關定義的事,不把後段關的工作提前**。這是本管線反覆出現的失效模式——已實測兩次:**第⓪關(策略)**曾擅自列「排除準則」(排除是第②/③關才做)、**第③關(嚴格篩)**曾擅自做「文獻型態分類/決定納入單位」(那是第⑦關)。**自我檢查徵兆:** 若我在某關的輸出開始出現「下一關才該有的詞」(策略關出現『排除』、嚴格篩出現『納入單位/RCT/SR-MA/背景型態』、引文追蹤前出現『verdict』),即為外溢,**立即收回、退回本關該有的輸出**。各關產物邊界一覽:⓪只定義『要搜什麼·什麼算切題』;①只廣蒐去重(不篩主旨/不驗證);②只報篩選策略(不動手篩);②b高敏感初篩(只砍明顯離題);②c只記全文狀態(不剔除);③只判主旨切題與否(不分型態);⑤才做引文追蹤;⑥才交叉驗證;⑦才決定納入單位(verdict/study)。
> **(B) 清單二、三 完整呈現,嚴禁省略;清單一 改流程帳(v0.15)**:**清單二、清單三逐筆列全**,**不可用「…」「(共 N 篇)」「以下略」截斷**,篇數多也要全列(可分區塊,每筆都在);清單二固定 6 欄＋完整 APA、清單三固定 6 欄(含 DOI/PMID,缺顯「缺」)＋逐筆剔除原因(含品質閘 Q2↓)。**清單一不列文獻表**,改為**檢索流程數字漏斗＋對帳恆等式**(見 §4)。寧長勿略(指二、三)。
> **(C) Phase 1 完成一律附 PDF 報告,且報告須說明「檢索原則」(v0.16,務必遵守)**:三表交付後**一律額外輸出一份可攜 PDF 報告**(中文,reportlab＋系統 CJK 字型如微軟正黑體 `C:/Windows/Fonts/msjh.ttc`;A4 橫向容寬表;**輸出資料夾＝`config/settings.yaml` 的 `report.pdf_output_dir`**(個資、gitignored、不進 repo;留空則解析 Windows『文件』已知資料夾 `GetFolderPath('MyDocuments')`,正確處理 OneDrive 重導);見 §4 報告規格)。報告**必含一節「檢索原則／方法」**,逐項白紙黑字寫出:
> 1. **四軸展開實際用的字眼**——逐軸列出本次 query 真正用的詞(軸A 縮寫↔全文、軸B 慣稱↔生化/基因別名、軸C 類別↔藥名↔代號、軸D 疾病縮寫↔全文),含三腿各自送出的完整 query 字串(C 措辭、PM Boolean、OE 題目)。
> 2. **主旨軸(必含連言軸)篩選用的字眼**——列出 ①′ 拆出的每一條必含軸,以及判定該軸「有無出現」所比對的同義詞清單(如 ①COVID-19 軸＝COVID-19／SARS-CoV-2／coronavirus；②疫苗軸＝vaccine／vaccination／immunization／mRNA／BNT162b2…；③疾病軸＝bronchiectasis／NCFB)。讓「為何某篇被判缺軸→清單三」可被人工複核。
> 報告同時含三表(清單二 header 回顯原始主題＋必含軸)、對帳恆等式、Zotero 匯入紀錄(若有)。**無 PDF 不算 Phase 1 完成。**

> **v0.15 變更**(三表欄位定版:清單一改流程帳、二/三固定欄位):
> - **清單一**由「文字簡述」改為**檢索流程數字漏斗**:逐腿命中(C N₁／PM N₂→分層 N₂′／OE N₃)→ 去重聯集 U(重疊 w)→ 剔除 off-topic B／品質閘 Q／驗證不符 V → 進清單二 M;附**對帳恆等式** `M＋(B+Q+V)＝U`。
> - **清單二固定 6 欄**:`試驗/文件 ｜ 原始英文主體 ｜ 第一作者 ｜ 期刊(SJR) ｜ PMID/DOI ｜ 驗證`;原始英文標題**照錄不翻譯**;表後附 APA。
> - **清單三固定 6 欄(v0.15.1)**:`原始英文主題 ｜ 作者,年 ｜ 期刊 ｜ 分位 ｜ DOI/PMID(缺則顯「缺」)｜ 剔除原因`(首欄由「文獻」改為原始英文標題照錄)。
> - **§1①(2′) 命中收斂後選核心(v0.15.1)**:PM 分層至 N 篇後**不逐篇讀 N**——N 當證據庫分母(寫進清單一);核心取「**過濾後 relevance 前 ~30–40 工作集 ∪ C／OE 命中**」,落多腿交集者為核心,PM 對交集篇做身分驗證(PMID/DOI);仍不收斂則續收窄工作集。
> - 純 SKILL.md 變更(§4＋§1① 改寫),引擎/判定/schema 不動、向後相容。

> **v0.14 變更**(輸出精簡:清單一改簡述,二/三維持完整):
> - **清單一不再列全表**,改為一段**含數字流向的簡述**(聯集 N、來源分布、on/off-topic、流向二/三)——因清單一與清單二＋三重疊,逐筆列出冗長;靠 §1①(4) 檢索腿狀態＋簡述即可對帳。
> - **清單二、清單三維持完整、逐筆列全、嚴禁省略**(清單二附 APA、清單三附剔除原因含品質閘 Q2↓)。
> - ★執行規範(B) 同步改:「逐筆列全」只約束清單二、三;清單一簡述。純 SKILL.md 變更,引擎/判定/schema 不動、向後相容。
>
> **v0.13 變更**(品質閘預設改 **Q1**;Q2 不刪、進清單三):
> - **§1①(3′) 品質閘預設由 Q1+Q2 改為 Q1-only**(`sjr_max=1`／`--max-quartile 1`):本工具求**最強公信力**,核心清單二只留 Q1。可 `--max-quartile 2` 放寬回 Q1+Q2。
> - **被分位剔除者(Q2↓)→ 完整列入清單三並標分位,不刪不省略**(配合 v0.12「三表完整呈現」):使用者可從清單三**自行挑有興趣的 Q2 試驗**——「Q1 核心、Q2 留檔可自選」。先前 v0.11/v0.12 的「Q1+Q2 預設」由此版取代。
> - 純 SKILL.md＋helper 預設值,引擎/判定/schema 不動、向後相容。
>
> **v0.12 變更**(分階段互動 ＋ 三表完整呈現 ＋ Q1+Q2 helper 落地):
> - **新增「★ 執行規範」(見上)**:(A) **分階段停頓**——檢索+三表 / Zotero 匯入 / 全文 / 分析 各關之間**停下問使用者是否繼續**,不一口氣跑完;(B) **三表完整呈現**——清單一/二/三**逐筆列全、嚴禁「…」「(共 N)」截斷**。
> - **§1①(3′) Q1+Q2 helper 落地**:`scripts/journal_quartile.py`(SCImago 快取＋Crossref 取期刊→查 best quartile→留 ≤Q2,未收錄不誤殺)——PM/OE 分位過濾由「文件協定」變「可執行」。
> - 純 SKILL.md＋新增 helper,引擎/判定/schema 不動、向後相容。
>
> **v0.11 變更**(可選**期刊品質閘 Q1+Q2**,三腿分工＋可申報):
> - **新增 §1①(3′) 期刊品質閘(預設 Q1+Q2,可關)**:對「被大量研究、想再收斂到可信期刊」的題,加一道**期刊分位**篩(SJR 分位)。
> - **三腿能力不同**:**C｜Consensus 原生**支援 `sjr_max`(1=Q1…4=Q4)→ 設 **`sjr_max=2`** 即 Q1+Q2;**PM／OE 無原生分位** → **事後**對照 SCImago SJR 分位表(ISSN/正規化期刊名 → best quartile,跨類取最佳),留 ≤Q2;無表時 best-effort 並標註。
> - **為何 Q1+Q2 而非只 Q1**:Q1-only 易誤砍「好的專科/學會期刊裡的正當 RCT」;Q1+Q2 砍掉的是 Q3/Q4 低品質尾巴,保住有效證據,recall 與品質較平衡(系統性回顧常用門檻)。
> - **三閘分工(關鍵)**:**分位閘(Q1+Q2)管期刊聲望** ／ **證據閘(v0.10 pubtype)管研究設計** ／ **主旨閘(①′)管離題**——三者**獨立併用**,別用任一個代替另一個(實測:`sjr_max=2` 一樣會放進高分位的 DPP-4 糖尿病離題篇,topic drift 仍要靠 ①′)。
> - **但書**:分位看 category(用 best quartile 最不誤砍);**無分位者**(新刊、會議摘要)別被分位閘誤殺——會議摘要本走 C/OE 另計;Q1+Q2 仍**次於**設計層篩(EBM 重設計>聲望)。
> - **必申報**:套分位閘須於 §1①(4) 寫明「已套 Q1+Q2、砍掉 N 篇低分位(哪些)」,不靜默砍。**預設可關**(未要求品質閘時不套,維持最大 recall)。純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。
>
> **v0.10 變更**(PM 腿命中過多時:**分層精度過濾 ＋ 可申報**,不靜默砍):
> - **問題**:`(別名 OR …) AND 疾病` 對被大量研究的藥(如 nintedanib,`total_count`＝974)會爆量;爆量來源多半是**疾病詞落在 `[All Fields]` 太廣**,非藥名(別名本就精確)。爆量使後段特徵化/剔離題成本不可行。
> - **協定(recall 優先,條件式 escalate)**:(1) 先小 `max_results` 拿 `total_count`;(2) **`≤ 60`(預設門檻,非死值)→ 一次 `max_results`≈80–100 抓回(此量級通常一次回完、`has_more=false`,不需翻頁;僅 `has_more` 仍真才 `retstart` 補頁)**;(3) **`> 60` → 分層收窄(不靠翻頁硬抓數百筆)**:先把**疾病詞改 `[Title/Abstract]`**(藥名別名仍 All Fields);若仍多,再疊**證據型 pubtype**:`AND (Randomized Controlled Trial[ptyp] OR Meta-Analysis[ptyp] OR Systematic Review[ptyp] OR Clinical Trial[ptyp] OR Guideline[ptyp])`。
> - **鐵律:不靜默吞掉**。任何收窄**必須**寫進 §1①(4):原始 `total_count`、套了哪層 filter、縮到幾筆、原因。被收窄掉的低證據/舊文視為「**未納本輪、可手動加軸補抓**」,非「不存在」。
> - **為何證據型 filter 不傷核心**:它砍的是 case report/社論/基礎研究噪音,**保住 PM 的獨家高價值貢獻**(實測 HSK31858〔Lancet RM RCT〕、AIRLEAF〔ERJ RCT〕都會留下);會議摘要本就 PubMed 不索引、走 C/OE,不受影響。
> - 僅改 PM 腿(§1①(2) 與 §1①(4) 申報格式);純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。判定/驗證邏輯不變。
>
> **v0.9 變更**(OE 手動腿 → **OE MCP 腿**,可腳本化＋自帶 Crossref 預過):
> - **OpenEvidence 由「手動網頁腿」升級為「MCP 腿」**:裝 `openevidence` MCP 後,改用 `oe_ask`(自然語言臨床問題)送題,fire-and-forget(回 `article_id` 後 `oe_article_get` 取)或 `wait_for_completion:true` 一次取回。**不再需要網頁手動貼題、抽引用** → v0.8 的「無公開 API、僅能手動、不可腳本化」**作廢**。
> - **OE 引用自帶 Crossref 預過(關鍵)**:`oe_ask`(`crossref_validate:true`、`include_bibtex:true`)回傳的每筆引用已含 **DOI＋PMID＋嵌入式 Crossref 驗證**(`crossref.status:"validated"`、`method:"doi"`、`similarity`)。→ **`status=validated` 且 `similarity` 高者視同預過**(同 PubMed「自帶 PMID 預過」),§1③ Lane A/B **只需補驗未驗/低相似度者**;v0.8 的「OE 引用一律不可預過、全送驗」改為「**已 Crossref 驗證者預過、其餘送驗**」。
> - **反循環論證仍成立**:不信 OE 的「綜述論述」,但引用的**存在性**是 MCP 內嵌的 **Crossref(獨立來源)**驗證,故可信。OE 仍是「被驗證的檢索來源」,只是驗證已在 MCP 內完成。
> - **來源系統標記不變**(C／PM／OE 及組合);三源同中(C+PM+OE)仍為最強跨源一致訊號。
> - **存取前提不變**:OE 以美國為中心、已退出歐盟英國;非美國使用者須先確認可存取(本部署已確認台灣 `oe_auth_status` 正常)。無法存取時 OE 腿仍標 ⚠️ 跳過。
> - **Light 模式抽取較精簡**:`Ask OpenEvidence Light with citations` 內文標號可能多於 bibtex 實抽筆數;要更全引用收割可換 `article_type`。實測(nintedanib×PF-ILD):OE 回 6 筆全 Crossref 驗證,三源同中 4 篇(含 whole-INBUILD 直接給 `ERJ 59(3):2004538`)、獨家補回 Chen 2021 安全性 SR&MA(PLOS ONE,PMID 33989328)。純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。
>
> **v0.8 變更**(三源檢索:＋OpenEvidence 手動腿、＋每腿可診斷):
> - **§1① 由「雙源檢索」擴為「三源檢索」**:Consensus 多措辭、PubMed MCP 深抓之外,新增 **來源 OE｜OpenEvidence 手動腿**(網頁貼題、抽引用併入 intake)。
> - **OE 角色＝被驗證的檢索來源(同 Consensus 級)**:引用為 AI 合成、**不可預過**,須全部走 §1③ Lane A/B 驗證(與 PubMed 來源項「自帶 PMID 預過」相反)。
> - **來源系統標記擴充**:C／PM／C+PM → 增 OE、C+OE、PM+OE、C+PM+OE(三源同中＝最強跨源一致訊號)。
> - **新增 §1①(4) 三源檢索狀態回報(每腿可診斷)**:每次 run 在清單一前先逐腿報告 query／原始命中／去重淨增／狀態(✅/⚠️空/❌錯誤＋原因),任一腿異常**必須明列、不可靜默吞掉** → 出 bug 時可立即定位是哪一腿。
> - **無公開 API**:OE 僅能手動,不可腳本化、不進 `xref_verify.py` → v0.8 為**純 SKILL.md 變更**,腳本/設定/schema 不動、向後相容。
> - **存取/管轄權前提**:OE 以美國為中心、2026 已退出歐盟英國,非美國使用者須先確認可存取與身分驗證(本部署已確認台灣可正常使用)。
>
> **v0.7 變更**(雙源檢索聯集):
> - **§1① 由「Consensus 多措辭」升級為「雙源檢索」**:同主題同時跑 ⓐ Consensus 多措辭(每輪上限 20、`page`>0 需 Enterprise → 靠措辭擴廣)＋ ⓑ PubMed MCP 深抓(四軸別名 Boolean OR 成單條 query、`max_results` 開大、可 `retstart` 翻頁、無 20 上限),兩源聯集去重。
> - **PubMed 來源項附帶效益**:撈回即帶 PMID/DOI/metadata → §1③ Lane B 驗證視同預過,只需補驗 Consensus 獨有項。
> - **跨源去重**:鍵不變(DOI→標題+作者+年);每筆記來源系統 **C／PM／C+PM**;C+PM 同時命中＝跨源一致軟性信心訊號。清單一 `來源query` 欄改為 `來源`(系統＋query)。
> - 會議摘要(ASPEN/WILLOW 次組等)PubMed 多不索引 → 仍只能 Consensus 撈、留 Crossref(本機 Lane A)。
> - 實測(DPP-1×支氣管擴張症):PubMed 單條深抓 ＝ 81 篇(可翻頁抓滿)、Consensus 多措辭 ~27;聯集後最完整。判定/驗證邏輯不變、向後相容。
>
> **v0.6 變更**(多措辭檢索聯集):
> - **§1 流程由 5 步擴為 6 步**:① 改為「主題 → 四軸展開 → 多輪檢索 ＋ 聯集去重」;新增 **①′「對原始主題剔離題」**(進驗證前的防漂移閘)。後段 ②③④ 不變。
> - **四軸展開原則**:縮寫↔全文、臨床慣稱↔生化／基因別名、藥物類別↔藥名(INN)↔開發代號、疾病縮寫↔全文。設計 query 時優先放「精度錨點」(別名／代號)以降低同字根鄰近領域污染。
> - **去重鍵**:DOI → 正規化標題＋第一作者＋年;每筆記錄來源 query;**清單一＝聯集全集**。
> - **剔離題以「原始主題」為尺**(非展開後的 query),寧驗勿殺。
> - 實測(DPP-1×支氣管擴張症):四措辭聯集 on-topic 11→~27,獨家補回整條 BI 1291583(cathepsin C)臨床線;同字串重跑 +0。判定／驗證邏輯不變、向後相容。
>
> **v0.5.1**:新增零相依設定讀取層(CLI＞env＞`config/settings.yaml`＞內建預設;`--config`／`--no-config`),判定邏輯不變。
>
> **v0.5 變更**(實跑 DPP-1×支氣管擴張症後校正):
> - **P1** PubMed-MCP 手動腿由附註升格為 **§1③ 一級驗證 lane**,與本機腳本並列(容器內 Crossref／eutils 永不可達,MCP 腿才是對話內的真正主幹)。
> - **P2** 會議摘要(ATS／CHEST)PubMed miss **不再誤判 `UNVERIFIED`**,改判 `UNRESOLVED` 並路由清單三-A(輸入加 `doc_type`;Crossref `proceedings-article` 亦自動偵測)。
> - **P3** 「查無」細分 `reason`:未索引/ahead-of-print、衍生性非原始、真實查無。
> - **P4** 主旨不符者可走 `off_topic` **免全驗**(判 `OFF_TOPIC`,不查來源、省搜尋額度)。
> - **P5** 次級分析／substudy(pubtype 仍是 RCT)加 `evidence_note` 提醒降階,避免高估等級。
> v0.4 沿用:連線探測前置(`--source-mode auto`);Crossref 不可用時自動退回單用 PubMed;輸出 `run_mode`。
> v0.3 沿用:判定規則預設 **`any`**;`UNRESOLVED`(待補跑);三表輸出格式。
> v0.2 沿用:① 證據等級 title 語意 fallback;② PubMed 多候選消歧;③ 多式查詢 + STOPWORDS。

---

## 0. 連線需求

| 來源 | 角色 | 取得方式 |
|---|---|---|
| Consensus MCP | **被驗證的檢索來源**(提供候選文獻) | 已連線,直接呼叫 `Consensus:search` |
| PubMed | 驗證來源之一 | **兩個並列 lane**:Lane A `scripts/xref_verify.py` 內建 E-utilities(本機);Lane B 對話內 **PubMed MCP 手動腿**(容器內唯一可行,見 §1③) |
| Crossref | 驗證來源之一 | `scripts/xref_verify.py` 內建 REST API(無需金鑰,建議帶 mailto);**容器內不可達,須本機** |
| OpenEvidence | **被驗證的檢索來源(MCP,v0.9)** | 裝 `openevidence` MCP → `oe_ask` 送題(可腳本化);引用**自帶 DOI/PMID＋嵌入式 Crossref 驗證**,`status=validated` 者視同預過,只補驗未驗者。非美國使用者須先確認可存取(OE 已退出歐盟英國;台灣已確認 `oe_auth_status` 正常) |

> ⚠️ Consensus 與 OpenEvidence 都是「被驗證對象」(AI 合成檢索源),不可拿它們自己當驗證來源(循環論證)。驗證一律靠 Crossref／PubMed。

---

## 1. 工作流程(6 步)

### 檢索定位：SR 系統性回顧對齊（唯一模式，v0.19.6 起）

本 skill 只有**一種檢索定位:SR 模式(系統性回顧對齊)**——**敏感度／recall 優先**,對齊 Cochrane Handbook 第 4 章:**盡量撈全,品質交下游 RoB／GRADE,不在檢索階段砍**。

> **原『公信力／快速』模式已於 v0.19.6 移除**(它以 Q1 閘＋分層 quartile 收窄求精確,與 SR 方向相反、會在檢索階段引入 selection bias、漏掉 Q2↓ 正當 RCT)。**不再有模式切換、預設判定或語意詢問**;以下 SR 原則一律適用。

| 維度 | SR 原則（唯一，Cochrane 對齊） |
|---|---|
| 目標 | **敏感度最大化、盡量撈全** |
| **Q1 品質閘** | **關閉**——品質改交下游 RoB／GRADE 判,**不在檢索砍 quartile**(砍了＝引入 selection bias、漏 Q2↓ 正當 RCT);分位仍標註、不砍 |
| 命中過多(>60) | **不以 quartile 收窄**;改用驗證過的 RCT／SR 過濾器收斂;高命中是預期,`total_count` 當分母全報 |
| 限制 | **不設語言／出版狀態／日期／格式限制**(要設須在報告寫明理由) |
| 查詢結構 | **概念塊**:族群／疾病 AND 介入 [AND 對照] [AND 研究類型過濾器];塊內 OR;四軸別名**填滿每塊同義詞**。**只用 P／疾病／I／研究類型四型,不含結果/預後(O)軸**(硬規見 ①′(a)) |
| 詞彙 | **控制詞＋自由文字並用**:明確 MeSH(適當 exploded)＋ free-text(同義詞／縮寫／拼字變體／截詞 `*`) |
| 設計過濾 | **PubMed 官方 Cochrane 高敏感 RCT 過濾器**(見下) |
| 來源 | C／PM／OE ＋ **ClinicalTrials.gov**(`CT`)＋ **OpenAlex**(`OA`,引文追蹤)＋ **Europe PMC**(`EP`,廣覆蓋)〔皆免金鑰〕＋ **Epistemonikos**(`EK`,SR 專庫,**需免費 token**) |
| 策略品管 | **PRESS 自檢**(見下) |
| 報告 | **PRISMA-S** ＋ PRISMA 2020 流程 ＋ 字串原樣可複製 ＋ **覆蓋限制聲明** |
| 時效 | **記錄檢索日**;重用／更新 >6–12 月須重跑並註記 |

**誠實覆蓋限制(報告開頭必載)**:本管線可及 ＝ MEDLINE(PubMed) ＋ Consensus ＋ OpenEvidence ＋ ClinicalTrials.gov ＋ **OpenAlex** ＋ **Europe PMC** ＋ **Epistemonikos**(有 token 時);**未覆蓋 ＝ Embase、CENTRAL、CINAHL、區域庫(LILACS)、法規(FDA／EMA)／CSR**(需機構訂閱／圖書館員,無免費 API);**WHO ICTRP 僅能手動入口匯出**(實測無免費即時 API,bulk 須申請、web service 付費)。**篩選為單一 AI 演算法、未達 MECIR C39「≥2 人獨立篩選」→ 自動結果定位「初篩」,最終納入/排除建議人工覆核。**故本管線產出定位為 **rapid-review(快速回顧)等級的「系統性回顧輔助」,非可直接發表的完整 Cochrane 檢索**(此處「rapid review」指方法學產出等級,與已移除的『快速模式』無關)。Consensus／OE 是 AI 合成層、**不可替代** MEDLINE／Embase／CENTRAL。

**PubMed 官方 Cochrane 高敏感 RCT 過濾器（HSSS *sensitivity-maximizing* 版,2008 revision；v0.21 校正）**:
```
((randomized controlled trial[pt] OR controlled clinical trial[pt] OR randomized[tiab]
  OR placebo[tiab] OR drug therapy[sh] OR randomly[tiab] OR trial[tiab] OR groups[tiab])
 NOT (animals[mh] NOT humans[mh]))
```
> 源自 **Cochrane Handbook Box 6.4.a（Handbook 5.1）/ Box 4.4.b 的 sensitivity-maximizing 版**——Cochrane 建議檢索試驗「先以本敏感度最大化版起手」。
> **v0.21 校正**:先前此處誤標「sensitivity-maximizing」卻貼成 *sensitivity- and precision-maximizing* 變體（`clinical trials as topic[mesh:noexp]`＋`trial[ti]`，無 `drug therapy[sh]`/`groups[tiab]`/`trial[tiab]`）;現更正為**真正的 sensitivity-maximizing 版**（更廣、recall 更高，契合 SR 敏感度優先）。需要更精確版（precision 取捨）時才改用 sens+precision 變體。
> **只套在 PubMed 腿**（`g0_strategy.json` 的 `design_filter_allowed:true`）;其餘腿維持無設計過濾以保 recall。**非僅 RCT 的題**(觀察性／診斷準確度)改用對應過濾器,或**不套設計過濾器**。**勿在已預過濾庫(如 CENTRAL)套過濾器**(本管線無 CENTRAL,記原則)。

**ClinicalTrials.gov 試驗註冊腿(SR 模式新增,來源標 `CT`)**:以 API v2 查未發表／進行中試驗——`https://clinicaltrials.gov/api/v2/studies?query.cond=<疾病>&query.intr=<介入>&pageSize=…`;抽 **NCT 號／狀態／有無結果**,併入聯集。NCT 以**註冊號本身為憑**(不走 Crossref／PubMed 驗證)。WHO ICTRP **實測無免費自動化**(即時 API 404;官方 bulk 須填表經 SharePoint 核准、web service 付費)→ **不建自動腿**,列「人工補檢」缺口(可從 trialsearch.who.int 手動匯出),涵蓋非美國登錄庫由人工補。

**OpenAlex 引文追蹤腿(SR 模式新增,來源 `OA`;免金鑰,帶 `mailto` 進 polite pool)**:
- **廣檢**:`https://api.openalex.org/works?search=<PICO 詞>&per-page=…&mailto=<crossref.mailto>`;回 title／authors／year／DOI／venue／cited_by_count。
- **引文追蹤(Cochrane 補充法「滾雪球」,SR 模式核心價值)**:對**清單二每篇核心**,以 DOI 取 work(`/works/doi:<DOI>`)→ ① **backward** `referenced_works`(它引用了誰)② **forward** `cited_by_api_url`(誰引用了它);把未在 PM／EP 命中的新候選併入聯集、再走①′ 與驗證。
  > **★ 引文追蹤＝真引文鏈,不可用『相似度』冒充(鐵律,v0.20.1):** backward/forward 必須是**真正的『誰引用誰』**——OpenAlex `referenced_works`／`cited_by_api_url`,或 **Europe PMC** `/<source>/<id>/references`(反向)＋`/citations`(正向)端點(免金鑰、容器內可達)。**嚴禁用 PubMed `find_related_articles`(link_type=`pubmed_pubmed`) 充當引文追蹤**——那是『詞權相似(similar articles)』、不是引文鏈,用它做滾雪球會找錯東西且永不收斂於正確集合。(本鐵律因實測一度誤用 pubmed_pubmed 相似度當引文而立;改用 Europe PMC references/citations 後 6 種子→423 引文、新筆 0 漏網試驗、第1輪即收斂。)
- OA 回傳自帶 DOI／(部分)PMID → 與 PM 同,**Lane B 視同預過**,§1③ 只補驗無 ID 者。

**Europe PMC 廣覆蓋腿(SR 模式新增,來源 `EP`;免金鑰)**:
- **廣檢**:`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=<PICO>&format=json&pageSize=…`;覆蓋 **MEDLINE＋PMC＋preprints＋Agricola＋部分非 MEDLINE**。回 id／source／pmid／doi／title／journalTitle／pubYear。
- **引文／參考(備援 snowball)**:`…/{source}/{id}/citations`、`…/{source}/{id}/references`。
- 自帶 PMID／DOI → **Lane B 預過**;命中 OA 全文者可佐 Phase 3。

**Epistemonikos 系統性回顧庫腿(SR 模式新增,來源 `EK`;需免費 token)**:
- **端點**:`GET https://api.epistemonikos.org/v1/documents/search?q=<PICO>&classification=systematic-review,broad-synthesis&sort=-score`;header `Authorization: Token token="<token>"`;回 **JSON**(實測:無 token 回 401、端點存在)。
- **價值**:**SR 專庫**——直接找**系統性回顧／broad synthesis**＋多語,正中 Cochrane「檢索相關系統性回顧／既有合成」建議;`classification` 可篩 `systematic-review`／`structured-summary-of-systematic-review`／`broad-synthesis`／`primary-study`。
- **token(必要)**:免費但**須 email `dev@epistemonikos.org` 註冊應用取得**(非即時自助);放 `config/settings.yaml` 的 `epistemonikos.api_token`(金鑰→gitignored、勿進 repo/ZIP)。**無 token → 本腿標 ⚠️ 跳過**(同 OE relay 未連),不影響其他腿。
- 回傳含 DOI／PMID 者 → Lane B 預過;EK 找到的 SR 之「納入研究」可再餵 OpenAlex／PM 滾雪球。

**PRESS 自檢(SR 模式,執行檢索前)**:對每條策略自審(仿 PRESS 2015 檢核):① 是否扣合 PICO;② Boolean／括號邏輯;③ 行內語法／欄位標籤;④ MeSH 對映恰當、該 explode 是否漏;⑤ free-text 同義詞／拼字／截詞是否漏;⑥ 過濾器版本正確、未誤用於預過濾庫;⑦ 有無不當限制(語言／日期／出版狀態)。自審結果寫進報告「檢索原則」節。

**PRISMA-S 報告(SR 模式)**:逐源列 平台／介面、**檢索日**、**原樣字串(複製貼上、勿重打)**、命中數;附 PRISMA 2020 流程數(辨識→去重→篩選→納入);對帳恆等式照舊。

**SR 模式 MECIR 補充(v0.18.3)**:
- **① 會議摘要不在篩選階段排除(C35 禁出版格式限制／C28 灰文獻)**:摘要不因「未正式發表」被剔,改列**「待評估研究(studies awaiting classification)」**——其數據仍可能供 meta-analysis,待正式論文出再定案。流程圖另設「待評估」格,不計入「排除」。
- **② 參考文獻追蹤(C30,反向引文)**:對**納入研究 ＋ 相關綜述／SR(含被排除的敘述綜述)**掃參考清單(OpenAlex `referenced_works`／Europe PMC references / OA cited_by 正向),補抓藏在其中的原始 RCT;於報告註記已掃對象與新增筆數。被排除的敘述綜述仍有此「剩餘價值」。
  > **鐵律(v0.18.5):必須「實際執行」、不可只報連結數**。要真的把反向(`referenced_works`)與正向(`cites:<id>`,可加 `title.search` 聚焦)的紀錄**逐筆抓回→去重→雙軸篩選**,才能宣稱「新增納入 N」。**禁止**僅取得 `cited_by_count`／`referenced_works.Count` 等數字就斷言 N=0。報告與流程圖第二臂須寫**實際比對的筆數**(反向 x 篇、正向聚焦 y 篇)與篩選結果。`cited_by` 數百筆時用 `title.search` 或近年篩聚焦,並申報只掃了聚焦子集。
  > **全面執行(v0.18.6)**:反向須涵蓋**所有納入研究 ＋ 所有納入的統合分析／指引 ＋ 相關(含被排除)綜述**的參考清單(統合分析/指引/綜述的 refs 最富含原始試驗),正向取關鍵 RCT 的 `cites:`;**不可只挑單一代表研究**。實測教訓:DPP-1 案只掃 ASPEN 得「0 新」,**全面掃 8 個種子(308 篇反向去重＋正向)才抓到漏掉的 SAVE-BE(HSK31858 Ph2,Lancet Respir Med 2025;PubMed 當時未索引)**——證明代表性執行會漏、且凸顯缺 Embase 之風險。報告須寫掃描範圍(種子數、反向/正向筆數)與真實新增。
  > **逐輪至收斂(v0.19,迭代)**:引文追蹤是**滾雪球**——把**每輪新納入者當下一輪種子**,再做反向＋正向,直到某輪「新增納入 ＝ 0」才停(飽和)。**每一輪都要畫進流程圖**(輪次／種子／反向·正向筆數／新增)。實測 DPP-1:第1輪 8 種子→新增 SAVE-BE;第2輪 以 SAVE-BE 為種子(反向 24＋正向 33)→新增 0→收斂。
  > **種子來源含「翻頁新撈到的紀錄」(v0.19.4)**:不只「清單二核心」當種子——**任何階段新浮現的相關紀錄**(含 §③ 全頁取盡後才出現、且被歸到「進行中試驗／待評估」而非核心納入者),只要與主題相關,**都要餵進這個迭代迴圈再追一輪**。**且若中途發現「全新藥名/開發代號」**(例:本案翻頁撈到 florensocatib),等於多了一條檢索軸,**必須以該新 token 回頭做一次各腿全文補搜**,再把命中接回滾雪球。實測 DPP-1 第3輪:以 HOPE-BE(florensocatib)、AIRTIVITY 為新種子→反向/正向 0(論文太新、citation graph 尚未建立、DOI 未索引)＋florensocatib 新軸全文補搜(OpenAlex/Europe PMC/PubMed)僅命中 HOPE-BE 本身→**新增 0→收斂**。教訓:翻頁找到的東西也要追,否則迴圈不算閉合。

- **③ 大量初始命中的穩健處理(v0.19;SR 模式禁用 relevance-top-N)**:SR 要**篩選每一筆**,故命中量大時**不可只取 relevance 前 N**(會漏低排名者——本案 SAVE-BE 即在 PubMed 母體外/未索引)。穩健作法:(a) 先取**全部 ID**(PubMed esearch 只回 PMID、便宜);(b) **分批拉 `get_article_metadata`→逐批雙軸篩選→累加去重**(分段處理,不需一次載入全部)——**注意對話內 `get_article_metadata` MCP 每次約上限 20 筆(實測超過會只回 20),故以 ~20 為一批、迴圈取盡**;(c) **每一條腿都要取盡,不只 PubMed**:OpenAlex／Europe PMC 用 **`cursor=*`** 逐頁翻到盡(非僅第一頁);ClinicalTrials.gov 翻 `nextPageToken`;Consensus／OE 為 AI 合成腿、單次本就有上限(~20)、無法窮盡,**須在報告申報此先天限制**。(d) **數千筆也一樣要全篩**(分批/分段累加),**不可因量大就截斷**;唯一能縮小命中的是**讓 query 本身更精準**(收緊 PICO／加 MeSH exploded／套驗證過濾器——這是改變「比對集合」、合法),縮小後**仍須篩選新 query 的每一筆**。**鐵律:嚴禁靠相關度(relevance)排序截斷固定 query 的結果**——relevance 只決定先看誰、不決定看不看。報告須**逐腿**寫真實母體 N 與「已全數篩選」;**任一腿未及全篩(如本機只取第一頁)必須明白申報為缺口、不可假裝完整**。

> 上述為 SR 唯一行為;§1①～③ 其餘流程(四軸別名、聯集去重、交叉驗證、反幻覺消歧、三表)照常;判定／schema 不變。

### ⓪ 連線探測(前置,自動)

跑驗證前先確認本次環境能用哪些來源。腳本 `--source-mode auto`(預設)會:
1. 探測 **Crossref** 是否可用(對已知 DOI 做一次輕量 GET,短逾時)。
2. 探測 **PubMed** E-utilities 是否可用。
3. 依結果決定模式:

| Crossref | PubMed | 結果模式 |
|---|---|---|
| ✅ | ✅ | 跑雙源(`any` 規則) |
| ❌ | ✅ | **自動退回:單用 PubMed API 篩選** |
| ✅ | ❌ | 單用 Crossref |
| ❌ | ❌ | 不跑,全部標 `UNRESOLVED`(待補跑) |

> 在 Anthropic 容器內,Crossref／E-utilities 通常**都不可達** → auto 會判 `UNRESOLVED`。
> 此時改在**本機**跑腳本;或在對話內改用 Consensus + PubMed MCP 手動完成 PubMed leg(見 §6)。
> 結果模式會寫進輸出 JSON 的 `run_mode` 與 stderr,便於追溯本次走哪條路。

### ① 主題 → 四軸展開 → 三源檢索 ＋ 聯集去重(v0.8)

使用者給「**原始主題**」後,**不要只用一條最直覺的 query**——實測單一 query 會整段漏掉用別名/代號發表的文獻。

**(1) 四軸展開**:把主題沿下列四軸列出文獻可能的寫法,組成數條互補 query。條數不設限;但每多一條會增加後段驗證成本,故先剔離題(①′)再驗證。
- **軸 A 縮寫 ↔ 全文**:DPP-1 ↔ dipeptidyl peptidase-1
- **軸 B 臨床慣稱 ↔ 生化／基因別名**(最容易漏,務必涵蓋):DPP-1 ↔ cathepsin C／CTSC
- **軸 C 藥物類別 ↔ 細部藥名(INN) ↔ 開發代號**:DPP-1 inhibitor ↔ brensocatib ↔ INS1007／AZD7986
- **軸 D 疾病縮寫 ↔ 全文**:NCFB ↔ non-cystic fibrosis bronchiectasis

> **通則(非 DPP-1 限定)**:任何主題都先問「這個標的／藥物／疾病在文獻裡還有哪些寫法?」例:acetaminophen↔paracetamol↔APAP;GLP-1 受體促效劑↔semaglutide／liraglutide↔glucagon-like peptide-1;vitamin B1↔thiamine。設計 query 時優先放「**精度錨點**」(生化/基因別名或細部藥名),可大幅降低同字根鄰近領域污染(DPP-1 題用 `cathepsin C` 幾乎不會撈到 DPP-4 糖尿病文獻)。
> > **★ 別名回填求可重製(鐵律,v0.20.1):** 若**檢索結果的標題/摘要裡冒出一個原字串沒列的別名/INN/代號**(例:撈到含 `verducatib` 的文獻,而藥物軸只寫了開發代號 `BI 1291583`),**必須把該別名正式回填進報告第五節的藥物軸字串與交接包 `axis_synonyms`**——否則別人照你字串重跑無法保證重製同一聯集。回填後**要實跑該別名一次、比對既有聯集**:若 0 篇新增→於方法註記載明「補此字眼不改變聯集數(原以○○共現已涵蓋)」;若有新增→**更新聯集數並補跑後段**。(本鐵律因使用者指出 `verducatib`=BI 1291583 之 INN 未列入字串而立;實測 verducatib 17 命中全在 729 內、0 新增。)

**(2) 三源檢索(三條 lane 並行)**:
- **來源 C｜Consensus(比照其他腿,v0.19.8)**:**用與 PM/OA/EP 相同的「兩軸概念塊」query**(措施軸所有同義詞 OR-block × 疾病軸),送 `Consensus:search`。**不預設文獻類型/格式/分位**——**`medical_mode`、`exclude_preprints`、`study_types`、`sjr_max` 一律不設**(除非使用者明指);這些是出版狀態/類型/分位限制,違反 SR 最大敏感度。單輪上限 20、`page`>0 需 Enterprise → **無法窮盡**,**依 PRISMA-S 在報告申報此先天上限**;廣度可再用語意等價的同概念措辭補(非同字串重跑——deterministic、+0)。提供研究類型/被引/期刊分位等 EBM 欄位(僅供標註,不作篩選)。
- **來源 PM｜PubMed MCP 深抓**:把四軸別名用 **Boolean OR 串成一條** query(`(別名1 OR 別名2 OR …) AND 疾病`)。先讀 `total_count`,`max_results` 開大(**80–100,一次即涵蓋多數題、`has_more` 多為 false**);僅當 MCP 單次有上限、`has_more` 仍為真才以 `retstart` 補頁(罕用 fallback)。`total_count` 過大(命中過多)時**不硬翻頁抓滿,改走下方 v0.10 分層過濾**。PubMed **無 20 篇上限**,一條即可深抓。
	- **附帶效益**:PubMed 撈回即含 PMID/DOI/metadata → 這些項 **Lane B 驗證視同預過**,§1③ 只需補驗 Consensus／OE 獨有項。
	- **限制**:PubMed 多不索引會議摘要(如 ASPEN/WILLOW 次組 → 0 命中),那些仍只能靠 Consensus 撈、留待 Crossref(本機 Lane A)。
	- **命中過多時的分層精度過濾(v0.10)**:先用小 `max_results` 取 `total_count`。**`≤ 60`(門檻,非死值)→ 一次 `max_results`≈80–100 抓回全部(此量級通常一次回完、`has_more=false`;僅 MCP 單次有上限且 `has_more` 仍真才 `retstart` 補頁——罕用)**。**`> 60`(SR 唯一行為)**:**不以 quartile 收窄、不砍分位**;設計過濾改用官方 Cochrane 高敏感 RCT 過濾器,高 `total_count` 是預期、**當分母全報並依 §③ 全頁取盡逐筆篩**。以下「分層」僅作**聚焦工作集**之用(母體仍全報、被聚焦排除者不刪),逐層 escalate、每層後重看 `total_count`:
		1. **疾病詞改 `[Title/Abstract]`**(藥名別名仍 All Fields,因別名已精確;爆量主因是疾病太廣)。
		2. 若仍多,疊**證據型 pubtype**:`AND (Randomized Controlled Trial[ptyp] OR Meta-Analysis[ptyp] OR Systematic Review[ptyp] OR Clinical Trial[ptyp] OR Guideline[ptyp])`(對齊清單二要的 L1–L2＋指引;砍 case report/社論/基礎研究噪音)。以上為**第一層篩檢**。
		3. **（已移除）第二層 Q1 期刊閘**:隨『公信力／快速』模式於 v0.19.6 移除而**永久關閉**——SR **不以分位收窄**。命中仍多時改以**收緊 PICO 概念塊**或**官方 Cochrane 高敏感 RCT／SR 過濾器**聚焦,**分位只標註、不作刪除依據**(品質交下游 RoB／GRADE)。
		4.(選用)`date_from` 近 N 年——**SR 預設不設日期限制**,要設須在報告寫明理由。
		- **必申報(鐵律)**:於 §1①(4) 寫明原始 `total_count`、套到第幾層(含「第二層 Q1 閘剔除 N 篇」)、各層縮後筆數、原因;被收窄掉者標「未納本輪、可手動加軸補抓」,**非「不存在」**。
		- **注意**:證據型 filter 會排除 L4 觀察性/真實世界與會議摘要——前者若為核心題需求應**手動保留或另跑一條不帶 pubtype 的窄 query**;後者本就走 C/OE,不受影響。Q1 閘同理:被剔 Q2↓ 不丟、列清單三供自挑。
- **來源 OE｜OpenEvidence MCP(v0.9;比照其他腿 v0.19.8)**:`oe_ask` 的題目須涵蓋**與其他腿相同的兩軸概念塊**(逐一列出措施軸所有藥名/代號同義詞 × 疾病軸),並**明示「不限研究類型」**(RCT/MA/SR/指引/觀察/藥動/機轉/會議摘要全要)——不預設文獻類型。建議 `crossref_validate:true`、`include_bibtex:true`(此處 Crossref 僅標註驗證狀態、不作篩選);fire-and-forget(回 `article_id` 後 `oe_article_get` 取)或 `wait_for_completion:true` 一次取回。回傳 `citations.json` 每筆含**標題／作者／年／DOI／PMID／期刊**＋嵌入式 `crossref`(`status`、`method`、`similarity`、完整 work metadata)。先 `oe_auth_status` 確認登入。
	- **引用自帶 Crossref 預過**:`crossref.status=="validated"` 且 `similarity` 高者**視同預過**(同 PM 的 PMID 預過),併入 intake 時標來源 OE、§1③ 只補驗 **未驗/低相似度** 者。**反循環論證仍守**:信的是內嵌 Crossref(獨立),非 OE 綜述本身。
	- **存取前提**:OE 以美國為中心、已退出歐盟英國;非美國使用者須先 `oe_auth_status` 確認(台灣已確認正常)。無法存取/relay 未連時本腿標 ⚠️ 跳過(見 (4))。
	- **價值定位**:與 Consensus 同為合成引擎、重疊度高;相對優勢為高影響力來源整理＋自帶驗證。對本管線貢獻**候選廣度**(實測獨家補回 Chen 2021 安全性 SR&MA)＋**預驗證**,降低後段成本 → 「補候選、引用已自驗、綜述仍不盡信」。

**(2′) 命中收斂後如何選核心(v0.15.1,接 v0.10 分層之後)**:PM 分層收窄到 **N 篇**(如 930)後,**不逐篇讀 N**——讀不完、也不必。流程:
1. **N＝證據庫分母**:寫進清單一當「規模/完整度指標」,不是逐篇消化的對象。
2. **建工作集(screening set)**:取**過濾後 relevance 排序前 ~30–40 篇** ∪ **C／OE 命中**。
3. **核心＝多腿交集**:落在 **C∩PM∩OE / C∩PM / PM∩OE** 者即核心候選(多源同中＝強信心);加錨點(樞紐試驗名、最新最全 MA、現行指引)。
4. **PM 對核心做身分驗證**:逐篇核 PMID/DOI/標題(Lane B)。
5. **仍不收斂(交集少/工作集太雜)→ 續收窄工作集**:縮 pubtype 到只 `RCT+Meta-Analysis+Guideline`、加近 N 年、或加**結局/族群錨點**詞,把*工作集*壓小;但 N 仍照報當分母。
> **風險與守則**:若某重要 Q1 試驗「只在 PM 排得到、C／OE 都沒撈」,可能落在工作集之外被略過 → **熱門題三腿高度收斂、風險低;冷門/新題務必把工作集前段(relevance top)真的拉回來 screen**,別只靠 C／OE 收斂。此步驟透明度要寫進清單一(工作集大小、是否補抓 relevance 前段)。

**(3) 跨源聯集去重**:合併 C、PM、OE 全部結果,去重鍵 **DOI → 正規化標題＋第一作者＋年**。每筆記來源系統(**C／PM／OE／C+PM／C+OE／PM+OE／C+PM+OE**);**多源同時命中＝跨源一致的軟性信心訊號**(三源同中最強),供清單一追溯。

**(3′) 期刊品質閘(SR:一律關閉,v0.19.6 起為唯一行為)**:**品質閘關閉**——SR 求最大 recall,**品質交下游 RoB／GRADE,不在檢索階段砍 quartile**(砍了＝引入 selection bias、漏 Q2↓ 正當 RCT)。`journal_quartile.py` 仍可用來**標註**分位供讀者參考,**但不作刪除依據(預設不 `--drop`)**;唯有使用者**明確要求**加品質閘(非 SR 標準作法)時,才以 `--max-quartile` 套用並於報告申報。各腿分位標註機制:
- **C｜Consensus(原生)**:`Consensus:search` 帶 **`sjr_max=1`**(1=Q1…4=Q4)→ 只回 Q1。
- **PM／OE(無原生分位)**:**事後**對照 **SCImago SJR 分位表**(以 ISSN 或正規化期刊名 → **best quartile**,跨類取最佳),留 **Q1**。**已實作:`scripts/journal_quartile.py`**——`--build` 下載 SCImago(須瀏覽器標頭,腳本內建)建快取(~31k 期刊);`--in verified.json --max-quartile 1` 自動以 DOI 打 Crossref 取期刊/ISSN→查分位→留 Q1,**未收錄者預設保留不誤殺**(`--drop-unranked` 可改),並印剔除清單供 §1①(4) 申報。
- **(僅在使用者明確要求加品質閘時)被分位閘剔除者(Q2 及以下)→ 進清單三、標清楚分位,不可丟棄/省略**:使用者可從清單三自行挑有興趣的 Q2 試驗來看。**SR 預設不套此閘**,核心清單不以分位篩。
- **為何 SR 不砍分位**:SR 求「盡量撈全」,期刊分位高低**不等於**研究偏倚高低;在檢索階段砍 Q2↓＝引入 selection bias、可能漏掉專科期刊的正當 RCT。分位**只標註供讀者參考**,品質高低交下游 RoB／GRADE 正式評估。(已移除的『公信力』模式才以 Q1 當核心,SR 不沿用。)
- **三閘獨立併用**:分位閘(Q1,管期刊)／證據閘(§4 P / v0.10 pubtype,管設計)／主旨閘(①′,管離題)——**互不取代**。實測:`sjr_max=1` 仍會放進高分位的 DPP-4 糖尿病離題篇,topic drift 要靠 ①′ 精度錨點。
- **無分位者**(新刊、會議摘要)**別被分位閘誤殺**:會議摘要本走 C/OE、留 Crossref 另計,不因「查無分位」剔除。
- **必申報**:於 §1①(4) 寫明「已套 Q1+Q2、砍掉 N 篇低分位(列出)」,不靜默砍。

**(4) 三源檢索狀態回報(每腿可診斷,v0.8)**:在輸出清單一**之前**,固定先報一段「檢索腿狀態」,讓任一腿出 bug 時能立即定位。格式:

```
🔎 檢索腿狀態(本次 run)
- C ｜Consensus 多措辭:措辭 N 條 → 原始 X 篇 → 去重淨增 Y｜狀態 ✅ / ⚠️空 / ❌錯誤(原因)
- PM｜PubMed MCP 深抓:query「(別名 OR …) AND 疾病」→ total_count T → [若 T>60 套 filter:疾病[TIAB]／＋pubtype,縮到 T′] → 回 X(has_more=…,翻頁 P 次)→ 淨增 Y｜✅ / ⚠️已過濾(原因:命中過多) / ⚠️空 / ❌
- OE｜OpenEvidence MCP:oe_ask 題「…」→ 引用 X(crossref 驗證 V／未驗 U)→ 淨增 Y｜✅ / ⚠️無法存取(跳過) / ⚠️空 / ❌
聯集去重後總數 Z(C-only a／PM-only b／OE-only c／重疊 d)
- 品質閘:**SR 預設關閉**(分位只標註、不刪;品質交下游 RoB／GRADE)｜僅在使用者明確要求時才套 `--max-quartile` 並申報移除 N 篇
```

逐腿失敗類型(供你對症):
- **C**:⚠️空(措辭未命中,換措辭/放寬)｜❌(`Consensus:search` MCP 錯誤/逾時)｜註:每輪硬上限 20、`page`>0 擋掉 → 廣度只能靠加措辭。
- **PM**:⚠️空(query 太窄/別名拼錯/`AND 疾病` 過嚴)｜❌(MCP 錯誤、翻頁中斷未抓滿——以 `has_more` 與翻頁次數判斷)。
- **OE**:⚠️無法存取(`oe_auth_status` 失敗/relay 未連/管轄權封鎖 → 整腿跳過,不影響 C/PM)｜⚠️空(綜述無引用或抽取失敗)｜❌(`oe_ask` 送題後錯誤/逾時)。

> **鐵律**:任一腿 ⚠️/❌ **必須**列在清單一上方並標明腿名＋失敗類型,**不可靜默吞掉**。某腿掛掉不等於整體失敗——其餘腿照常聯集,該腿標記待補跑(同 `UNRESOLVED` 精神)。
> **鐵律延伸(v0.20.1,堵『能跑卻略過』):** 上句的 ⚠️/❌ 指**技術失敗**(連不上/空/錯誤)。另有一種更隱蔽的漏洞＝**腿能跑、卻被以主觀價值判斷略過**(例:「OE 是問答型、廣蒐階段價值低」)。**這不算合法跳過**。每條腿的去留只有兩條路:**實跑**(填命中數),或**技術硬限制下跳過**(未連線/無金鑰/管轄封鎖)。**『價值低／重疊高／應已被涵蓋』不是跳過理由**——重疊與否要等聯集去重後用數字講(如本案 OE 5 筆全重疊、淨增 0,是『跑完才知道』,不是『跑前假設』)。違反此律的徵兆:第①關報告六腿少於六行、或某腿狀態寫成『省略/略過』卻無技術理由。

### ①′ 對原始主題剔離題(防漂移閘;v0.16 重構;v0.19.10:純四軸、不用極性/結果)

**(a) 先拆主題規格(展開前鎖死,關鍵)**:把使用者「原始主題」拆成數條**必含連言軸**(mandatory conjunction axes),例:
- 「COVID-19 vaccine and bronchiectasis」→ **三軸【①COVID-19／SARS-CoV-2 ②疫苗／vaccination ③支氣管擴張症】,三軸全為必含**。
- 「DPP-1 inhibitor and bronchiectasis」→ 兩軸【①DPP-1／cathepsin C 抑制劑 ②支氣管擴張症】。

四軸展開(§1①(1))只是為了**擴召回每一軸的別名寫法**,**絕不可丟掉任何一條必含軸**——展開後仍須所有必含軸同時成立。先前 COVID 案的 bug 正是展開把「COVID-19」軸稀釋掉,①′ 比對基準縮成兩連言(疫苗×支擴),誤放行 Barker(NCFB 總論)/O'Grady(支擴疫苗但非 COVID)。

> **★硬規:軸＝由問句萃取的 PICO 合格準則;排除＝缺某條被指定的軸(v0.19.7;v0.19.11 PICO 化)**——可作為「檢索軸／離題篩選軸」的型別只有 **①族群／狀況(Population/Condition)②措施／介入(Intervention,含藥名·藥類·開發代號)③對照(Comparison)④研究設計(Study design)**。
>   - **(A) 軸由「使用者問句」萃取,且只取問句真的有指定的**:不一定每型都有(例「DPP-1 inhibitor and bronchiectasis」只指定了 P＝bronchiectasis、I＝DPP-1;C 與研究設計未指定)。**問句沒指定的軸,一律不施加**(不可擅自加「只要 RCT」「要對照組」等問句沒要求的限制——那會引入未授權的 selection)。
>   - **(B) 排除＝合格準則的補集**:一篇被排除,只能因為**缺某條「被指定」的軸**,且須標明**缺哪一軸**(例:健康受試者 Ph1 ＝缺 P 軸〔非該病人群〕;動物/臨床前 ＝缺 P 軸〔非人類病人〕;談 DPP-4 糖尿病 ＝缺 P 軸〔非支擴〕;談支擴但無 DPP-1 ＝缺 I 軸)。排除理由一律用軸名,**不得用 outcome 措辭**。
>   - **(C) 非原始數據(綜述/社論/MA/指引)不是「排除」,而是「分類」**:它們通常兩軸都成立、屬合格,只是**歸到背景/對照參考(乙)而非原始研究(甲)**(見清單二分區),不可當「排除」剔掉。
>   - **(D) 嚴禁以「結果／預後(Outcome、endpoint、prognosis、療效指標如惡化率/FEV1/死亡率、效果方向/極性)」作為任何軸或篩選依據**(Cochrane Handbook 第 4 章:結局索引不全＋選擇性報告→降敏感度、引 selection bias);**結局只在後段資料抽取/合成/GRADE 處理**。

**(b) 何時判(管線順序,v0.19.6 更新:SR 品質閘預設關閉)**:三腿聯集 → 去重 → **①′ 離題判定**(對**全聯集**逐篇,吃 **title/abstract**、不耗搜尋額度);驗證階段才解析 metadata/DOI/PMID。**SR 預設不跑 Q1 品質閘**(分位只標註不刪);僅在使用者**明確要求**加品質閘時,才把它排在 ①′ 之前、只對收斂集合細判。對帳恆等式 `M+(B+Q+V)=U` 不變(**SR 預設 Q＝0**)。

**(b2) 初步篩選 ── 高敏感第一階(v0.19.12;寧留勿殺)**:在 (c) 嚴格離題判定**之前**先做一道**高敏感初篩**——同讀 title／abstract、同樣只看四型軸,但**只有當「某一核心軸明顯離題」時才剔除**(整篇與疾病軸或介入軸明確無關者,例:純 DPP-4 糖尿病、純他病、健康受試者/動物);**判定困難或模糊者一律先保留**,留待 (c) 嚴格階再定。此階只移除「明顯不相關」者(對應 PRISMA title/abstract 高敏感初篩)。**做完此階須停下來報告初篩狀況(保留 N、明顯剔除 N 及各自缺哪軸),經使用者確認後才進 (c)**。理由:兩階篩選＝先敏感(初篩只殺明顯離題)、後精確((c) 嚴格連言),避免一刀切誤殺模糊個案。

**(b3) 搜尋全文 ── 初篩與嚴格篩之間(v0.19.13;v0.19.14 改標註不匯入)**:對初步篩選**保留**的每篇,嘗試取得**全文**(合法 OA：Unpaywall＋PMC,見 `scripts/fulltext_fetch.py`)。**做完此階須停下來報告**:① **有全文** 幾篇 ② **只有 AI 合成摘要**(OE／Consensus 內容)幾篇 ③ **全無**(無全文亦無可用摘要)幾篇,經使用者確認後才進 (c)。**全文取得狀態須逐篇記錄、作為「標記」一路帶到最終 PDF 核心證據表**(見 §報告規格:標「全文／僅 AI 合成摘要／無全文無摘要」)。**(v0.19.14:此階預設不匯入 Zotero**——實測發現此處集合多為會議摘要與尚未嚴格篩的雜訊,照灌會污染庫;Zotero 匯入統一留待 §⑤ 最終核心證據歸檔,或使用者明確要求時才做。)理由:對齊 Cochrane 兩階篩選——標題/摘要初篩 → **取全文** → 全文複篩;嚴格離題判定 (c) 改以全文為據,需先備齊;無全文者以摘要判並標記。

**(c) 逐篇判定 ── 嚴格階(v0.19.13:改對「全文／AI 合成摘要」,比對全部必含軸)**:
> **★鐵律:篩選不得用任何形式的「結果/outcome」(v0.19.10)**——判定只看四型軸(族群/疾病/介入/研究設計)是否同時成立,**嚴禁以「效果方向/極性(有效 vs 無效、療效 vs 傷害、正向 vs 反向)、有無達到某 endpoint、有無顯著」作為納入或排除依據**。一篇談「DPP-1 抑制劑×支氣管擴張症」的文獻,不論結果是正向、無效、甚至顯示傷害,只要四軸成立就**一律納入**;效果只在後段資料抽取/合成/GRADE 處理。(同一藥物若被當「致病因」而非「介入」研究,屬**介入軸語意不符**、以軸別處理,不以效果方向判。)
> **判定依據(v0.19.13):嚴格階改對 (b3) 取得的「全文」核對**(比初篩的 title/abstract 更深更準);**無全文者用 AI 合成摘要(OE／Consensus)核對**;**兩者皆無**則暫以 title/abstract 判定並標「待全文覆核」。同一組必含軸條件,只是核對基礎由摘要升級為全文。
- **必含軸全現 ＋ 年份窗合理(反幻覺消歧用,非日期限制)** → 候選清單二。
- **缺任一必含軸** → 清單三-B,剔除原因標明**缺哪一軸**(如「缺 COVID-19 軸」)。
- **只剩族群/疾病軸、介入/主題軸全無** → 清單三-D(主旨不符)。
- **模糊翻轉「寧驗勿殺」**:某軸**明確缺**→直接清單三(不浪費驗證額度);軸是否成立**模糊**→留清單三-B(標模糊)、**不升清單二**(清單二只收所有必含軸**明確**出現者,寧缺勿濫)。

**(d) 清單二 header 回顯(v0.16)**:輸出清單二時,標題列**逐字回顯原始主題＋必含軸**(如「清單二〔主題:COVID-19 vaccine AND bronchiectasis;必含三軸〕」),讓任何主題漂移**一眼有聲**。

> ⚠️ **標題相似度 0.85 是反幻覺消歧(§2)、不是主題篩選**:離題但真實存在的文獻相似度反而高、照樣過驗證 → 主題篩選只能靠本節①′ 的必含軸判定,**勿拿相似度當離題閘**。
> ⚠️ 比較基準必須是**原始主題的全部必含軸**,不是展開後的 query(展開會擴張到鄰近領域;拿它當尺會放行離題)。
> **範例(本 skill 校準案例):主題「DPP-1 inhibitor and bronchiectasis」** — 展開 4 條:cathepsin C 錨點／DPP-1 全文+exacerbation／藥名聚合(brensocatib·HSK31858·BI 1291583)／代號軸錨定疾病(AZD7986·INS1007·GSK2793660)。單跑「DPP-1 inhibitor bronchiectasis」只得 11 篇 on-topic 且混入 9 篇 DPP-4;四措辭聯集得 ~27 篇 on-topic,**獨家補回整條 BI 1291583(自稱 cathepsin C inhibitor、不寫 DPP-1)臨床線**(AIRLEAF 2 期／AIRTIVITY 3 期／Ph1)。各 query 剖面:cathepsin C 最乾淨(0 DPP-4);藥名聚合試驗完整度最高;peptidase+exacerbation 會帶回 DPP-4 須配 cathepsin C;純代號+機轉漂移到基礎研究故④錨定疾病。
> **v0.7 雙源實測**:同主題 PubMed 單條深抓(別名 OR)＝ 81 篇(回 50、可 `retstart` 翻頁抓滿),Consensus 多措辭 ~27;兩源聯集去重後最完整,PubMed 項 Lane B 預過、ASPEN／WILLOW 會議摘要仍 Consensus-only 待 Crossref。

DPP-1／CatC 抑制劑 INN ↔ 代號對照:

| INN | 代號／別名 | 廠商 | 主要試驗 |
|---|---|---|---|
| brensocatib | INS1007、AZD7986 | Insmed | ASPEN、WILLOW、STOP-COVID19 |
| HSK31858 | — | Haisco | SAVE-BE |
| BI 1291583 | — | Boehringer Ingelheim | AIRLEAF、AIRTIVITY |
| (已停) | GSK2793660 | GSK | Ph1 |

### ② 取出驗證鍵

每筆抽出比對鍵:**DOI 優先**;無 DOI 時用「正規化標題 + 第一作者姓 + 年份」。
整理成 JSON(`title` 必填;`year`/`doi`/`first_author` 選填)。

**型態提示(v0.5,選填但強烈建議)**:Consensus 結果顯示為 ATS／CHEST 會議摘要時填 `doc_type:"conference_abstract"`;
ACP Journal Club／評論／社論等衍生性文獻填 `doc_type:"synopsis"`(或 comment/editorial);
主旨明顯不符本題者填 `off_topic:true`(見 §4 的 P4 政策)。

### ③ 交叉驗證 —— 兩個並列 lane,擇可行者

> 容器內 `api.crossref.org` 與 `eutils.ncbi.nlm.nih.gov` **永不可達**,Lane A 的線上查詢在對話中會全判 `UNRESOLVED`。
> 因此**對話內的真正主幹是 Lane B(PubMed-MCP 手動腿)**;Lane A 留給**本機**完整雙源(含 Crossref)。
> **v0.7**:凡來自 §1① PubMed 深抓的來源項(來源含 PM)已具 PMID/DOI/metadata → PubMed leg 視同已過,Lane B 只需補驗 **Consensus 獨有項**,省大量逐筆 `search_articles`。
> **v0.9 更新**:OE MCP 回傳的引用若 `crossref.status=="validated"`(高 similarity)→ 已具獨立 Crossref 驗證,**視同已過**,Lane B 只需補驗 **Consensus 獨有項＋OE 未驗/低相似度項**。(v0.8 的「OE 一律不可預過」作廢。)

**Lane A — 本機腳本(完整雙源,離線於對話之外)**

```bash
python scripts/xref_verify.py --in consensus.json --out verified.json \
       --mailto you@example.com --md verified.md
```

`--source-mode auto`(預設)先做⓪探測再決定來源。腳本對每筆**獨立**查可用來源,各自得出
match／soft／miss／retracted,依規則合併出 verdict 並標證據等級。可強制 `--source-mode pubmed-only`/`both`/`crossref-only`,
或硬性略過單邊 `--no-crossref`/`--no-pubmed`(優先於 source-mode)。

**Lane B — 對話內 PubMed-MCP 手動腿(容器內首選,等同 `run_mode=PubMed-only`)**

以 PubMed MCP 工具親手完成 PubMed leg,標準步驟:
1. **逐筆 `search_articles`**:用「標題去 STOPWORDS 後的內容詞 + 第一作者 + 年」組查詢式(對應腳本的多式查詢);命中即取 PMID。
2. **批次 `get_article_metadata`** 抓回候選的標題／作者／年／期刊卷期頁／DOI／pubtype。
3. **反幻覺消歧**(同 §2):取標題相似度最高且 ≥0.85、年份 ±1 者;無人達標即判 miss,**絕不硬抓同藥不同篇**。
	多搜尋字串常帶回「同主題他篇」,務必逐筆比對標題與 PMID 才採用。
4. **直接成果即 APA 材料**:metadata 已含卷期頁與 DOI,可直接寫清單二的 APA 引用。
5. **判定**:PubMed match → `any` 下即 `VERIFIED`;miss 依 §2 的 P2/P3 規則細分(會議摘要 miss → `UNRESOLVED`)。

> PubMed MCP 會強制附 PubMed 署名與 DOI —— 正好滿足 §4 的「PubMed 署名義務」,勿省略。
> 兩 lane 結束後,於輸出標明本次 `run_mode`(PubMed-only / both / …),便於追溯。

> **鐵律(v0.15.1):驗證涵蓋全體 on-topic 候選,不可只驗核心。**
> C 腿／OE 腿回傳常**只有標題＋作者＋年、沒有 DOI/PMID**(Consensus search 即如此)。**不可**因「手上沒 ID」就把它標『無法驗證』丟進清單三 —— 那是**沒去查**,不是查不到。每一筆無 ID 的 on-topic 候選都要走 Lane A/B 以「標題＋作者＋年」**解析 PMID/DOI 並判 verdict**(本機 `xref_verify.py` 直接吃 `{title,first_author,year}`;對話內用 `search_articles`→`get_article_metadata`)。
> - 解析後 **VERIFIED ＋ Q1 → 應入清單二**(不是清單三);清單三只留**真正 miss(`UNVERIFIED`)／off-topic／品質閘 Q2↓／會議摘要等非完整原著**。
> - 清單三的 `DOI/PMID` 欄填**解析所得**識別碼;**唯有 Crossref＋PubMed 都查無此筆**才填「缺」(此時 verdict 為 `UNVERIFIED`/`UNRESOLVED`,與「缺」一致)。
> - 實測教訓(SGLT2i×HF):14 筆「C 腿來源無 ID」起初誤置清單三,補跑 `xref_verify` 後 **14/14 VERIFIED 且全解析出 PMID＋DOI**,其中 10 篇 Q1 應升清單二 → 清單三實際只剩 4 篇(會議摘要×1、Q2×1、未收錄×2)。

### ④ 判定 + 標等級 + 產出三表

依 verdict 與主題相關性,整理成下方「標準輸出格式」的三張表。

---

## 2. 判定規則

### verified_requires(預設 `any`)
- **`any`(預設)**:PubMed 或 Crossref **任一** match → `VERIFIED`。
	⇒ 只跑得到一個來源(例如本機連不到 Crossref、只跑 PubMed)時,仍能得到確定的 `VERIFIED`。
- **`both`**:兩來源都 match 才 `VERIFIED`(寧嚴勿鬆,可用 `--verified-requires both` 切回)。

### verdict 階層(由高到低)

| verdict | 意義 |
|---|---|
| 🚫 `RETRACTED` | 任一來源標記撤稿 → 最高優先,一律剔除 |
| ✅ `VERIFIED` | 依規則達標(any:≥1 match;both:皆 match) |
| ⚠️ `PARTIAL` | 找到接近候選但未達 match 門檻;或 both 規則下只一邊 match |
| ❌ `UNVERIFIED` | 所有「實際查過」的來源都 miss(查無此文) |
| ⏳ `UNRESOLVED` | 沒有來源實際查到資料(全 skipped／error),**或會議摘要 miss(未索引)**→ **待補跑**,不可當成失敗 |
| ⛔ `OFF_TOPIC` | 主旨不符,依 P4 政策僅做主旨剔除、未送驗證 |

> ⚠️ **來源獨立原則**:被略過或出錯的來源「不算數」,不會把另一個已 match 的來源拖下水。
> 例:Crossref 連不到(skipped/error)+ PubMed match,在 `any` 下 = `VERIFIED`;在 `both` 下 = `PARTIAL`。

### 會議摘要規則(v0.5,P2)

ATS／CHEST 等**會議摘要**常無 PubMed 索引,但這是「**未索引**」不是「**不存在**」。
故當 `doc_type` 為 conference_abstract／abstract／poster／proceedings(或 Crossref 命中 `proceedings-article`)
而 PubMed miss 時,**改判 `UNRESOLVED`(非 `UNVERIFIED`)**,路由至清單三-A 待 Crossref 定案。

> 這條是 pubmed-only(對話內 Lane B)最常見的誤判來源:沒有它,真實存在的摘要會被當成「查無此文」剔除。

### reason 細分(v0.5,P3)

非 `VERIFIED` 結果在 `reason` 欄細分,別把不同成因混為一談:

| reason | 意義 / 後續 |
|---|---|
| `not_indexed:conference_abstract` | 會議摘要未索引 → `UNRESOLVED`,本機補 Crossref |
| `derivative_non_original` | 衍生性文獻(摘要評論/評論/社論) → 非原始研究,通常不進清單二 |
| `ahead_of_print/not_indexed?` | 出版年為當年度,疑尚未被索引 → 本機/Crossref 複查 |
| `not_found` | 已實際查詢仍無相符 → 疑幻覺引用或書目有誤 |
| `no_source_queried` | 全 skipped/error(如容器內) → 待補跑 |

### 反幻覺消歧(關鍵)

每來源取回多個候選(`--pm-candidates`,預設 5),只取「標題相似度最高且 ≥ 門檻(0.85)」者;
**無人達標即判 miss,絕不硬抓同藥不同篇**。年份容差 ±1。

> 實例:搜尋 brensocatib 腎功能 PK 會同時撈到「肝功能不全 PK」一篇,須靠標題比對才不會選錯。
> Lane B(MCP 手動腿)尤其要小心:多搜尋字串常帶回同主題他篇,務必逐筆核對 PMID。

---

## 3. 證據等級(僅反映文獻「類型」,非支持強度)

| 等級 | 文獻類型 |
|---|---|
| L1 | 系統性回顧 / 統合分析(含網絡統合分析) |
| L2 | 隨機對照試驗 RCT(含 Phase I–IV) |
| L3 | 非隨機臨床試驗 |
| L4 | 觀察性研究(世代、病例對照、橫斷) |
| L5 | 敘述性綜述 / 臨床指引 / 藥物上市回顧 |
| 未分類 | pubtype 與標題皆無法判定 |

判定優先序:**PubMed pubtype > 標題語意 fallback**(ahead-of-print 常缺 pubtype,故掃標題補救)。

### 次級分析／substudy 加註(v0.5,P5)

主試驗的**次級分析／機轉 substudy／subgroup／post-hoc／multi-omics／biomarker** 其 pubtype 往往仍是 RCT,
直接套表會被標 `L2`,**高估**其作為「主要試驗主報告」的證據力。故當標題命中 substudy 語意時,
`evidence_level` 仍照類型標(不動),但另加 `evidence_note` 提醒:**此為衍生分析,引用時宜降階看待**。(此處僅分「主報告 vs 衍生分析」之報告層級,與篩選無關、不涉結果方向。)

> 實例:WILLOW 機轉次分析、STOP-COVID19 multi-omics —— 都是 RCT 衍生報告,不是主要試驗主報告。

---

## 4. 標準輸出格式(三表)

輸出 **清單一＝檢索流程帳(數字漏斗,不列文獻表)**、**清單二＝完整表＋APA**、**清單三＝完整表＋剔除原因**(v0.15)。

**清單一 — 檢索流程說明(v0.15,改為「逐腿命中＋漏斗流向」的數字帳,不列文獻表)**
報告整個檢索→去重→剔除的漏斗,逐項給數字(供對帳;**不逐筆列文獻**):
- **第一腿 C｜Consensus**:命中 **N₁** 篇
- **第二腿 PM｜PubMed**:廣檢 **N₂** 篇(若觸發 v0.10 分層過濾,註明收斂後 **N₂′**;取用前段 **k** 篇逐筆驗)
- **第三腿 OE｜OpenEvidence**:命中/引用 **N₃** 篇(relay 未連則標 ⚠️ 0,見 §1①(4))
- **跨源去重後聯集**:合計 **U** 篇(重疊 **w**)
- **剔除不符主題(off-topic)**:**−B** 篇 → 清單三「主旨不符」
- **品質閘剔除(Q2↓／未收錄)**:**−Q** 篇 → 清單三「品質閘剔除」(**SR 預設 Q＝0**:品質閘關閉、分位只標註不刪;僅在使用者明確要求加閘時 Q 才 >0)
- **驗證不符／待確認(UNVERIFIED／RETRACTED／UNRESOLVED)**:**−V** 篇 → 清單三「驗證不符／待確認」
- **最終進清單二(已驗證核心)**:**M** 篇

> **對帳恆等式**:`清單二 M ＋ 清單三(B+Q+V) ＝ 聯集 U`。數字湊不攏代表有筆漏接,須回查。

**清單二 — 篩選後核心清單(已驗證 ＋ 主題聚焦;SR 不以分位篩,分位僅標註)**

> **★分析單位＝原始研究(Study),且原始 vs 次級/三級文獻分區(v0.19.9,MECIR C42)**:清單二須**分兩區**——**(甲) 納入的原始研究**:以**研究(Study)為單位**(同一試驗多份報告連結成一個 Study:主報告＋次分析合為一筆,標「對應 k 篇報告」),這才是介入成效 SR 的分析單位與「納入 N」;**(乙) 背景／對照參考文獻**:統合分析、系統回顧、臨床指引、綜述等**次級·三級文獻**——**不計入「納入 N」**(否則原始試驗數據被 double-counting),僅作引文追蹤種子與討論對照,獨立列、獨立計數。流程圖終點數字只認(甲)。
**固定欄位(v0.15)**:`試驗/文件 ｜ 原始英文主體 ｜ 第一作者 ｜ 期刊 ｜ PMID/DOI ｜ 驗證`
- **原始英文主體**=該文獻原始英文標題(原文照錄,不翻譯、不縮寫);
- **期刊**=期刊名(附 SJR 分位,如 `NEJM (Q1)`);
- **PMID/DOI**=兩者並列(缺 PMID 留空、保留 DOI);
- **驗證**=驗證來源/結果(如 `PM✅`／`OE-Xref✅`／`Lane A✅`)。
並於表後附**每篇 APA 完整引用**。
篩選準則:① verdict 為 `VERIFIED`(或暫 `PARTIAL/UNRESOLVED` 但人工確認);② 主題聚焦;③ 為完整論文(非會議摘要/衍生性);④ 通過 Q1 品質閘。

**清單三 — 被剔除文獻**
**固定欄位(v0.15.1)**:`原始英文主題 ｜ 作者,年 ｜ 期刊 ｜ 分位 ｜ DOI/PMID ｜ 剔除原因`
(`原始英文主題`=原始英文標題照錄;`分位`=SJR 如 `Q2`／`未收錄`／`Q1`;**`DOI/PMID`=兩識別碼,任一缺即顯示「缺」**——對 C 腿來源「未經 Lane A/B 獨立驗證」者,此欄通常為「缺」,正好佐證剔除原因)。**排序固定**:
先「**驗證不符／待確認**」(`UNVERIFIED`/`RETRACTED`/`UNRESOLVED`,含會議摘要待 Crossref),
再「**主旨不符**」(①′ 對原始主題剔出的 `OFF_TOPIC`,或已驗證但主題不聚焦),
再「**品質閘剔除**」(v0.13:已驗證、on-topic,但**非 Q1**——剔除原因標明分位如 `Q2(品質閘)`,**完整列出供使用者自挑**)。剔除原因前綴標明屬哪一類。

> ⚠️ 會議摘要在 v0.5 預設落在清單三-A 並標 `UNRESOLVED`(未索引、待 Crossref);
> 本機補 Crossref 後若轉 `VERIFIED`,是否升級進清單二改以「會議摘要 vs 完整論文」的**品質**標準判斷,而非驗證。

### Phase 1 PDF 報告規格(v0.16,★執行規範 C)

Phase 1 三表完成後**一律**產出一份 PDF(中文)。技術:`reportlab`(Platypus)＋註冊系統 CJK 字型(Windows:`C:/Windows/Fonts/msjh.ttc` 微軟正黑體,`.ttc` 用 `subfontIndex=0`;粗體 `msjhbd.ttc`);A4 橫向(`pagesize=(A4[1],A4[0])`)容納寬表;表格長英文標題用 `Paragraph` 自動換行。**避免**用 Unicode 上下標(內建字型缺字成黑塊;改 `<sub>/<super>`)。CID 字型 ToUnicode 限制會使「複製中文」亂碼但**視覺渲染正確**(可 `pymupdf` 轉圖肉眼複核);需可複製中文時改 HTML→WeasyPrint。

> **行文原則(v0.18.1)**:PDF 是**寫給人讀**的——用**通暢完整的中文句子**說明,避免代號/術語/縮寫堆疊;必要術語附白話解釋。流程圖每階段數字要能對得起來。
> > **★ 報告自足、勿 punt 給機器檔(鐵律,v0.20.1):** PDF 是**人類唯一會看的成品**——**嚴禁在 PDF 裡叫人「見交接包／見 _corpus_seed.json／見某 JSON」**(人不會去翻機器檔)。(a) **核心證據表(納入)必須逐篇列出每個 Study 底下的『主報告＋全部子報告』細目(標題＋DOI＋全文狀態),不得省略、不得以「＋N 篇子報告(見交接包)」帶過**;納入是核心、量不大(本案 22 報告),務必列全。(b) 背景量大(本案 135)可 curated 列代表＋給**類別計數**(類別計數本身即完整交代),需要時另出**附錄**,但**不可指向交接包**。(c) **流程圖末格只呈現分流結果**(如「納入 22 報告→4 Study＋2 SR/MA｜背景 135」),**不要再標一個不好核對的『尚餘 N 單位/篇』**(單位與篇數混用會造成混淆)。(本鐵律因實測在核心表寫「見交接包」省略子報告、且末格多標「尚餘 6 單位」造成困惑而立。)
>
> **排版／呈現原則(v0.19.5)**:(a) **標題不可孤行**——用 `KeepTogether` 把每個章節標題與其後第一個內容(段落/表格/流程圖)綁在同頁;標題若會落在頁底、其內容卻被擠到次頁,則**整組推到下一頁**(標題與內文一起出現),避免「標題後直接跳頁」的視覺斷裂。(b) **流程圖檢索腿一律用全名**(Consensus／PubMed／OpenEvidence／OpenAlex／Europe PMC／ClinicalTrials.gov／Epistemonikos),不用 C/PM/OE/CT/OA/EP 縮寫。(c) **核心證據(清單二)區塊**:標題**不出現「清單二」字樣**(對外只說「納入的核心證據」);若拆多張子表,**共用欄寬、右側欄(PMID/DOI、交叉檢核)跨表對齊**以求整齊。(d) **新增「交叉檢核(PubMed／Crossref)」欄**,**僅呈現**每篇雙源比對狀況(皆通過/單通過/缺),**不以此欄作為納入或排除的篩選依據**(附註聲明)。(e) **核心證據表後附「全部納入文獻」APA 清單**(依表順序),書目以 **Crossref／PubMed 實際 metadata** 產生(作者、年、刊名、卷期頁、DOI),**勿杜撰作者**。
> **排版／呈現原則(v0.20.1 補,因實測連犯三錯而立)**:(f) **字形淨化要含實際用到的所有符號**——`safe()` 除既有 `≈≥≤−◯↔▸` 外,**務必再淨化 `™ ✅ ✓ ✔ ∧ ≠`**(msjh 常缺→磚塊):`™→`(去)、`✅✓✔→○`、`∧→且`、`≠→不等於`。**新增符號到資料前先確認字型有字形,否則加進 `safe()` 對映**(別只測 `≈≥−`,要測實際用到的字)。(g) **標題不孤行的正解(SPAN 表)**:核心表每個 Study 用跨列合併(SPAN)→**首個 Study 區塊不可拆**;`CondPageBreak` 門檻**不可用固定小值(如 52mm)**,須**動態≈首個 study 列數×列高＋表頭裕度**(本案 WILLOW 11 列→約 109mm),否則整塊跳頁、標題留前頁(實測 52mm 失敗、動態值成功)。(h) **核心證據表文獻名用中文＋標主/子報告**:報告名以**中文簡述**(如「Emara 2025:DPP-1 抑制劑 GRADE 統合分析」「AIRLEAF:BI 1291583 第二期劑量探索試驗」),每個 Study 的**主報告冠粗體 `【主報告】`、子報告冠粗體 `【子研究】`**(勿用「(子)」小括號,視覺較弱),一眼分清主結果與次級報告。(i) **funnel 不可跳關**:流程圖須含**全部管線階段**,特別是**初篩與嚴格篩之間的『全文搜索』**(實測曾漏畫此格)。**此關是真正的篩除步驟,非 no-op**:剔除「**全文與摘要皆無、且無 DOI/PMID/NCT 可回補→無法評估**」者(多為會議論文集索引等無內容容器),其餘(含以識別碼回補 metadata 者)保留。funnel 要顯示「−N 無法評估｜尚餘 M」,且 **Σ(無法評估剔除＋嚴格篩離題＋切題)＝初篩保留數**(本案 42＋270＋157＝469)。(j) **參考文獻＝核心證據表『全部』報告**(非只主報告):section 四 APA **逐篇列出表二所有 Study 的主＋子報告＋SR/MA(本案 22 筆)**,書目回 **Europe PMC/Crossref 抓真實 metadata**;**會議摘要 EPMC 常無收錄→用「標題＋會議出處(刊名年卷)＋DOI」並標『(會議摘要)』,絕不杜撰作者**(實測 22 筆中 10 筆會議摘要即如此處理)。

報告固定章節:
1. **標題 ＋ meta**(引擎版本、三源、日期)。
2. **臨床重點**(一段 bottom line)。
3. **檢索原則／方法(必含,見 ★執行規範 C)**:(a) 四軸展開實際字眼＋三腿完整 query 字串;(b) 必含連言軸清單＋每軸判定同義詞。
4. **檢索腿狀態**表。
5. **清單一**檢索流程帳(漏斗＋對帳恆等式)。
6. **檢索流程圖(PRISMA-style 視覺,必含,v0.18.1 細化)**:以 `reportlab.graphics`(`Drawing`/`Rect`/`String`/`Line`/`Polygon`) 把漏斗畫成**逐階段方塊流程圖**,每階段都要有**明確數字**且前後**相加一致**:
   (a) **辨識**——各腿命中數一排小框(**腿名用全名:Consensus/PubMed/OpenEvidence/OpenAlex/Europe PMC/ClinicalTrials.gov/Epistemonikos**,不用縮寫;跳過者標「跳過」);**另列「監管文件臂」(FDA Drugs@FDA／EMA EPAR／CSR,v0.19.9)**——藥廠期刊論文常有選擇性報告偏誤,新藥(如已核准的 brensocatib)應查監管文件取真實數據;目前多需人工查閱、列為來源並申報取得方式(無免費 API 即標「人工/未及」缺口);
   (b) **去重後總數**——「移除跨來源重複（及廣檢無關尾巴）後，進入逐篇篩選＝N 篇」**必須給出 N**;**若用自動化工具去重/初篩,須依 PRISMA 2020 另標一格「Records removed by automation tools ＝ x」**;
   (c) **逐篇篩選＋分批剔除**——篩選框**須標明審查方式**:本工具＝**單一 AI 演算法初篩**(非 MECIR C39「雙人獨立審查」;PRISMA 2020 自動化標示)。**每一批剔除各自一行、原因＋篇數**,且**排除理由只能用 PICO 四域(族群/疾病/介入/研究設計)措辭,嚴禁用「結果/療效」字眼**(例:**族群不符**:健康受試者／非該病人群 ＝x；**研究設計不符**:臨床前/動物/Ph1-健康志願者 ＝x；缺「介入」軸 ＝x；缺「疾病」軸 ＝x；敘述綜述/社論(非原始數據) ＝x;**嚴禁寫「非○○療效」這種以結果暗示的措辭**),Σ剔除 ＋ 納入 ＝ N;
   (d) **納入——以「研究(Study)」為單位、非「報告(Report)」(MECIR C42),且只算原始研究**:終點框寫「**納入 N 項獨立原始研究(RCT),對應 M 篇關聯報告(主報告＋次分析)**」,同一試驗的多份報告**連結為一個 Study**(例:WILLOW ＝ 1 主報告＋N 次分析)、不可當成 N 個獨立試驗。**統合分析/系統回顧/臨床指引/綜述屬次級·三級文獻,絕不計入「納入 N」**(否則原始試驗數據被 double-counting)——**另畫「背景／對照參考文獻」框**(MA/指引/綜述),僅作引文追蹤種子與討論對照、獨立計數、不混入原始研究納入數。SR 模式另畫試驗登錄分流(CT：已發表/進行中/其他)。
   (e) **★全程數學對帳閉環(PRISMA 2020,v0.19.12;務必逐一追溯)**:**每一個 N 都要能完美追溯、不得有未交代差額(黑洞)**。鐵律:**進入篩選 N ＝ Σ(各階明確排除) ＋ Σ(所有下游終端框)**;下游終端框要用**「合格分流的完整桶數」對帳,而非「精選子集數」**(常見錯誤:流程圖寫了精選的「納入 9＋背景 7」卻不等於合格總數→憑空消失一批)。終端框須涵蓋:登錄分流＋待評估＋背景參考(完整桶)＋原始研究相關報告(完整桶)。**若下游再策劃**(Study 單位連結、去重、把誤標的綜述重新分類為背景),該縮減也要**逐步交代**(原始相關報告完整桶 X 篇 → 連結去重、剔重複/重新歸類後 ＝ Y 篇關聯報告對應 Z 個 Study;其餘 X−Y 標明流向：重複/語言版本/重歸背景),使每一層都可加總回 N。產 PDF 前**自我核對**：456 排除＋保留＝聯集;保留＝各終端框相加;原始相關桶＝關聯報告＋移出項。對不攏不可出圖。
   箭頭＝`Line`＋三角 `Polygon`;CJK 用 `String(fontName="MSJH")`;**避免 `↔`/`⚠`/`✓`/`≥`/`≈` 等該字體缺字字元(會變空框□),改 `／`、文字、「通過」、「以上」、「約」**。讓「哪腿撈到多少、每批為何被排除」一眼看懂。**(SR 模式)** 另設「**待評估研究**」格(會議摘要等不排除、待發表;不計入排除);**並在流程圖內以 PRISMA 2020「其他方法」第二臂畫出「參考文獻追蹤(C30)」**——反向(納入研究＋相關/排除綜述的參考清單)＋正向(被引用)引文,標**找到候選數與「新增納入 N 篇」**,匯入最終納入框(納入＝資料庫臂 ＋ 引文追蹤臂)。不可只寫在內文、圖上缺這條臂。**引文追蹤逐輪進行,流程圖第二臂須逐行列出每一輪(第1輪／第2輪…)的種子、反向·正向筆數與新增納入,直到某輪新增 0(收斂)。**
   (f) **「人工補全文」須誠實畫為流程最末端的獨立步驟(v0.19.15)**:中段「搜尋全文」框只標**自動取得(Unpaywall＋PMC)**的結果,封閉期刊此時僅摘要/書目;**真正的人工補全文發生在篩選→引文追蹤→Zotero 歸檔全部完成「之後」**(★執行規範 ⑤b),故流程圖須在「最終納入」之後另設一個**末端步驟框「人工補全文(最後一步)」**(視覺上以不同色標示、不參與納入數對帳),反映真實時序——**不可把人工補全文混進中段搜尋全文步驟**(否則暗示補全文在篩選前發生,與事實不符)。緣由:使用者指出補全文確實是最後才做、應誠實置於流程最後。
7. **納入的核心證據**(header 回顯原始主題＋必含軸;**標題不用「清單二」字樣**;多子表右側欄跨表對齊;**含「交叉檢核(PubMed／Crossref)」欄、僅呈現不篩選**;**含「全文狀態」標記欄(v0.19.14):每篇標「全文／僅 AI 合成摘要／無全文無摘要」,讓讀者知道該篇判定所據的證據深度**)＋**表後附全部納入文獻 APA 清單**(Crossref／PubMed 實際書目)。
8. **清單三**(B 缺軸/C 品質閘/D 主旨不符,完整)。
9. **Zotero 匯入紀錄**(若已匯入)。
10. **未納入來源與方法學侷限(透明度,必含,v0.18.2)**:**逐一列「曾考慮但未納入的來源＋為什麼」**,並標各來源 Cochrane 地位(MECIR)——Embase／CENTRAL(C24 必備)＝需機構訂閱、無免費 API(Elsevier 個人金鑰只給 Scopus 不含 Embase);CINAHL＝EBSCO 訂閱無免費 API;WHO ICTRP(C27 與 CT.gov 並列強制)＝無免費即時 API、bulk 須申請／web service 付費→僅手動匯出;Google Scholar＝無官方 API、禁爬、不可重現(違 PRISMA-S);Scopus／ScienceDirect＝個人金鑰無授權(綁機構 IP);Epistemonikos＝待免費 token;**監管文件(FDA Drugs@FDA／EMA EPAR／CSR,v0.19.9)＝抗選擇性報告偏誤的真實數據來源,但無統一免費 API、多需人工下載或申請(EMA 臨床數據、FDA review documents)→ 列為來源並標「人工/未及」**。**＋雙人獨立篩選侷限**:本工具辨識/排除為單一 AI 演算法(去重＋兩軸＋sim≥0.85),**未達 MECIR C39「≥2 人獨立篩選」**;故定位「初篩/排序」,**最終納入/排除建議人工(或第二次獨立)覆核**。誠實說明「能做什麼、沒做什麼、為什麼」正是 EBM 透明度核心。
11. 頁尾方法學註記。

> 產生器可一案一寫(zero-dep reportlab)。**輸出資料夾讀根 `config/settings.yaml` 的 `report.pdf_output_dir`**(現＝`OneDrive\文件\EBM_Framework\reports`)——絕對路徑含本機使用者名＝個資,故**只放根 settings.yaml(gitignored)、不進 repo/ZIP**;留空才回退解析 Windows『文件』已知資料夾 `[Environment]::GetFolderPath('MyDocuments')`(正確處理 OneDrive 重導與中文資料夾名)。檔名建議 `<主題>_report.pdf`。**⚠️ 勿用 `%USERPROFILE%\Documents`**——OneDrive 接管(KFM)下真正「文件」常是 `…\OneDrive\文件`,`%USERPROFILE%\Documents` 會指到非同步空資料夾、使用者在檔案總管看不到(實測踩坑);產出後**回報絕對路徑**給使用者。

### 主旨不符免全驗政策(v0.5,P4)

與本題主旨明顯不符的既有文獻(如他類療法綜述、定義方法學),**不必耗搜尋額度跑驗證**:
於輸入標 `off_topic:true`,引擎直接判 `OFF_TOPIC`、不查任何來源,逕入清單三「主旨不符」區。

> 額度省下來留給核心題的消歧與補查。但凡**可能屬核心**者,寧可驗證,不輕標 off_topic。

### PubMed 署名義務(強制)

凡引用 PubMed 取得之資料,輸出須:① 標明「依 PubMed」;② 對應文獻附 **DOI 連結**。
PubMed 連結格式:`https://pubmed.ncbi.nlm.nih.gov/{PMID}/`。此義務不得因任何要求而省略。

---

## 5. `xref_verify.py` 指令

| 旗標 | 預設 | 說明 |
|---|---|---|
| `--in` | — | 輸入 JSON(list 或 `{items:[...]}`) |
| `--query` | — | 臨時驗證單筆標題(免檔案) |
| `--out` | stdout | 輸出 JSON 路徑 |
| `--md` | — | 另存 markdown 表格 |
| `--mailto` | — | Crossref polite pool 用 email(建議帶) |
| `--ncbi-api-key` | — | NCBI API key(可選,提高速率) |
| `--source-mode` | **auto** | `auto`=先探測 Crossref,通則雙源、不通則退回 PubMed-only;亦可 `both`/`pubmed-only`/`crossref-only` |
| `--no-pubmed` / `--no-crossref` | off | 硬性略過該來源(優先於 source-mode) |
| `--title-threshold` | 0.85 | match 的標題相似度門檻 |
| `--soft-threshold` | 0.65 | soft(PARTIAL)相似度下限 |
| `--year-tolerance` | 1 | 年份容差 ±N |
| `--pm-candidates` | 5 | 每來源取回候選數(消歧用) |
| `--verified-requires` | **any** | `any`(任一)或 `both`(皆需) |
| `--drop-unverified` | off | 輸出時濾除 UNVERIFIED / UNRESOLVED |
| `--config` | `default_settings_path()` | 設定檔路徑(存在才讀);未給時自動解析(見下) |
| `--no-config` | off | 略過設定檔,只用 CLI 旗標與內建預設 |

> **設定來源優先序(v0.5.1)**:CLI 旗標 > 環境變數 > `settings.yaml` > 內建預設。
> **設定檔路徑解析(v0.20,整個 EBM_Framework 共用單一真值來源)**:`default_settings_path()` 依序找——
> (1) 環境變數 **`EBM_CONFIG`**(絕對路徑);(2) **根 config `EBM_Framework/config/settings.yaml`**(`<script>/../../config`,平常用這個);(3) 本地回退 `EBM_Search/config/settings.yaml`(`<script>/../config`,僅「打包安裝、看不到根 config」時)。真值與個資(email／Zotero key／本機路徑)集中於根 config,**gitignored、不進打包**;欄位範本見 `EBM_Framework/config/settings.example.yaml`。
> 金鑰建議走環境變數 `ZOTERO_API_KEY`、`NCBI_API_KEY`、`CROSSREF_MAILTO`(打包安裝時尤其);設定檔含金鑰時務必 `.gitignore`。
> 讀檔用內建極簡 YAML parser,維持零相依(不需 pyyaml)。`crossref` 不需金鑰,只需 `mailto` 進 polite pool。

輸入 JSON 範例(含 v0.5 選填欄位):

```json
[{"id": 1, "title": "Phase 3 Trial of the DPP-1 Inhibitor Brensocatib in Bronchiectasis",
  "first_author": "Chalmers JD", "year": 2025, "doi": "10.1056/NEJMoa2411664"},
 {"id": 3, "title": "Brensocatib With vs Without Macrolides: ASPEN",
  "year": 2025, "doc_type": "conference_abstract"},
 {"id": 13, "title": "Inhaled Antibiotics for Bronchiectasis", "off_topic": true}]
```

> v0.5 選填輸入欄位:`doc_type`(conference_abstract/abstract/poster/proceedings → miss 改判 `UNRESOLVED`;
> synopsis/comment/editorial/journal_club/letter → 標衍生性)、`off_topic`(true → 直接 `OFF_TOPIC` 不查來源)。
> v0.5 新增輸出欄位:`evidence_note`(substudy 加註)、`reason`(非 VERIFIED 細分);皆向後相容,不影響舊輸入。

---

## 6. 已知陷阱

- **沙箱連不到 Crossref／PubMed**:Anthropic 容器網路白名單不含 `api.crossref.org`、
	`eutils.ncbi.nlm.nih.gov`。Lane A 的 `--source-mode auto` 會探測到兩者皆不可達 → 全部 `UNRESOLVED`(不是失敗)。
	**對話內請改走 §1③ Lane B(PubMed-MCP 手動腿)**;完整雙源(含 Crossref)留待**本機** Lane A。
- **會議摘要**(CHEST/ATS 等):PubMed 常無索引 → v0.5 已改判 `UNRESOLVED`(非 `UNVERIFIED`),需標 `doc_type` 觸發;本機補 Crossref 多有 DOI。
- **ahead-of-print / 當年度 NMA**:pubtype 可能空白 → 靠標題 fallback 標等級;reason 標 `ahead_of_print/not_indexed?`,卷/期/頁可能未定。
- **多候選同藥**:務必看 `similarity` 與 `pmid`,確認選到的是同一篇而非同主題他篇(Lane B 手動腿尤甚)。
- **次級分析高估等級**:pubtype=RCT 的 substudy 會標 `L2`,務必看 `evidence_note` 是否提示降階。
- **OE MCP 引用自帶 Crossref 預過,但綜述論述仍不盡信**(v0.9):`oe_ask` 回傳引用含 DOI/PMID＋嵌入 Crossref 驗證,`status=validated` 者可預過;惟 OE 的**綜述敘述/數據**仍是 AI 合成,只拿它做候選與引用、不直接當證據結論。偶有引用為指引/教科書(非 Crossref 索引)→ `similarity` 低或未驗 → 落 `UNRESOLVED`/送 Lane A/B,屬正常。
- **OE 存取＋relay 前提**(v0.9):先 `oe_auth_status` 確認登入;`oe_ask` 走瀏覽器擴充 relay(須在已登入分頁連線)。OE 以美國為中心、已退出歐盟英國;非美國使用者(含台灣)須自行確認可存取。無法存取/relay 未連時 OE 腿標 ⚠️ 跳過,**不影響 C/PM 兩腿**。
- **哪一腿出 bug 看 §1①(4) 狀態回報**(v0.8):清單一前的「檢索腿狀態」逐腿列 query/命中/淨增/狀態;某腿 ⚠️/❌ 不得靜默吞掉,據其失敗類型對症(C 換措辭、PM 放寬 query/查翻頁、OE 查存取)。

---

## 7. 檔案結構

```
consensus-verify/
├── SKILL.md
├── scripts/
│   ├── xref_verify.py          # 零相依交叉驗證(Crossref + PubMed)── 引擎層
│   ├── journal_quartile.py     # 〔Phase 1〕SJR 分位查詢/過濾(Q1+Q2 品質閘,§1①(3′));SCImago 快取
│   ├── zotero_import.py        # 〔Phase 2〕匯入 Zotero(Crossref 補欄);與引擎分離,本機執行
│   ├── fulltext_fetch.py       # 〔Phase 3 骨架〕查/抓合法 OA 全文(Unpaywall+PMC);付費牆走醫院
│   ├── build_corpus_seed.py    # 〔交接層 v0.20〕驗證並寫出 _corpus_seed.json 給 EBM_Analysis 吃
│   └── pack_skill.py           # 〔工具〕安全打包 ZIP(正斜線、排除真值檔);勿用 PS Compress-Archive
├── config/
│   ├── settings.example.yaml   # 範本(進 Git;含 zotero 區範例,永遠留空)
│   └── settings.yaml           # 你的真值版(複製範本;含金鑰/Zotero key→.gitignore,不進 Git)
├── references/
│   ├── output_schema.json      # 引擎輸出 JSON schema
│   └── corpus_seed_schema.json # 〔交接層 v0.20〕_corpus_seed.json 契約(→ EBM_Analysis Phase 0)
└── .gitignore                  # 排除 settings.yaml / .env / *.zip(真值與打包產物)
```

## 變更紀錄

- **v0.20.1** — **設定集中到 EBM_Framework 根目錄（機敏／個資單一真值來源）**：新增 `default_settings_path()`（xref_verify.py），四支讀設定的腳本（xref_verify／fulltext_fetch／zotero_import／journal_quartile）統一以它解析設定檔——**env `EBM_CONFIG` > 根 `EBM_Framework/config/settings.yaml` > 本地 `EBM_Search/config/settings.yaml`（回退）**。真值（Crossref email／Zotero api_key·library_id·collection／report 路徑）連同 EBM_Analysis 的個人路徑（`analysis.project_dir` 等）集中於**根 config（gitignored、在兩個 git 子репо之外、打包帶不到）**；`EBM_Search/config/settings.yaml` 已刪除、本地 `settings.example.yaml` 改為指向根 config 的薄指標。範本正本＝`EBM_Framework/config/settings.example.yaml`。腳本邏輯／判定不變、向後相容（找不到根 config 自動回退本地或 env）。
- **v0.20** — **新增「交接層」：EBM_Search 結果直接進 EBM_Analysis(整合兩子計畫)**。Phase 1 收尾(⑥ PDF 後)新增 **⑦ 寫交接包 `_corpus_seed.json`**(放全文資料夾、與 PDF 同處)＋**停下問「是否繼續進入 EBM 分析?」**(取代要使用者另打 `/ebm`;回「繼續/是」即接力 EBM_Analysis,讀交接包預填 Phase 0 分流並仍在斷點覆核)。交接包攜帶本次「已決定的事」——**必含軸→PICO 雛形** ＋ 每篇 **verdict(included=表二／background=表三背景)、study 標籤、證據等級、全文狀態、PDF 檔名、suggested(relevance/role/grade_track) 映射**;**集合＝表二納入＋表三背景,與 Zotero 一致性規則(⑤a)同一真實來源**,被驗證/主旨/品質閘剔除者不進交接。新增契約 `references/corpus_seed_schema.json` 與零相依工具 `scripts/build_corpus_seed.py`(驗證 required/enum/一致性後寫檔)。跨 Phase 停頓點 7 由「全文取得→問是否分析」改為「交接包寫出→問是否續進 EBM 分析」。映射規則與端到端流程見 `EBM_Framework/INTEGRATION.md`。純 SKILL.md＋新增工具/契約,引擎/判定/三表/既有 schema 不動、向後相容。
- **v0.19.15** — **流程改序:引文追蹤後「先問 Zotero ＋給本機補全文資料夾」,PDF 後移到最後**:★執行規範 (A) 原 ⑤(三表＋PDF→再問 Zotero) 拆成新 **⑤(引文追蹤收斂後即停)** 與 **⑥(PDF 交付)**。新 ⑤ 同時做兩件事並等確認:(a) **問是否匯入 Zotero**(同意則先乾跑 payload 再 `--commit`);(b) **提供本機「人工補全文」資料夾**(預設 `OneDrive\文件\EBM_fulltext\<題目_日期>\`,可由 `settings.yaml` 的 `report.fulltext_dir` 覆寫),逐筆列出「僅 AI 合成摘要／無全文無摘要」者(檔名建議 = DOI 去斜線／PMID)讓使用者人工放入全文 PDF;使用者完成後**重掃資料夾、更新全文狀態標記(補入者改標「有全文(人工補)」)**再確認。(a)(b) 皆確認後才進 ⑥ 以更新後標記產 PDF。緣由:使用者要在生成 PDF 前先決定 Zotero、並有機會人工補齊封閉期刊全文,使 PDF 的「全文狀態」欄反映補全後的真實深度。**另定 Zotero 一致性規則**:匯入集合須**恰等於報告表二(納入/待分析)＋表三(背景)**、以 `verdict:included`＋`study:<試驗>` 與 `verdict:background` 標籤標明用途,使 Zotero 成為與報告、與後續 EBM 分析一致的單一真實來源(緣由:使用者指出匯入清單須與後續要分析或當背景的清單一致)。純 SKILL.md 規格(新增 `settings.yaml` 選用鍵 `report.fulltext_dir`)。**另**:流程圖規格 6(f) 要求把「人工補全文」誠實畫為流程**最末端**獨立步驟(中段搜尋全文只標自動取得;補全文在篩選/引文追蹤/Zotero 之後才發生),且第一節改為**左流程圖＋右逐階段白話說明並行對照**(緣由:使用者要求表格與流程圖並行、說明改通順、並補上搜尋全文與人工補全文細節、且補全文須置於流程最後)。
- **v0.19.14** — **搜尋全文步驟改「標註不匯入」＋核心表加全文狀態欄**:(b3) 取消「無全文者 APA＋匯 Zotero」的強制動作——實測 DPP-1 案該集合 101 筆中多為會議摘要與尚未嚴格篩的雜訊(甚至混入有機化學論文),照灌會污染 Zotero。改為:**逐篇記錄全文取得狀態(有全文／只有 AI 合成摘要／全無)作為「標記」,一路帶到最終 PDF 核心證據表**(§報告規格 7 新增「全文狀態」欄,標示判定所據證據深度);**Zotero 匯入統一留待 §⑤ 最終核心歸檔或使用者明確要求**。嚴格篩 (c) 仍以全文為主、無全文用摘要判並標記。緣由:使用者選擇不匯入、直接以現有資訊嚴格篩,並要求最終表標註「只有 AI 合成摘要」「無全文無摘要」。純 SKILL.md 規格。
- **v0.19.13** — **初篩與嚴格篩之間插入「搜尋全文」步驟＋嚴格篩改對全文核對(對齊 Cochrane 兩階篩選)**:(1) **(b3) 搜尋全文**:對初步篩選保留者取合法 OA 全文(Unpaywall＋PMC),**停下報告**有全文 N／只有 AI 合成摘要 N／全無 N,並把**無法取得全文者(後二類)以 APA 表列＋匯入 Zotero 待人工補**(此 Zotero 觸點與 §⑤ 最終核心歸檔不同),確認後才進。(2) **(c) 嚴格離題判定改以「全文」為核對基礎**(無全文用 AI 合成摘要;皆無則暫 title/abstract 判並標『待全文覆核』)——同一組必含軸條件,核對基礎由摘要升級為全文、更準。★執行規範 (A) 對應插入停頓點 ②c。緣由:把 Cochrane「標題摘要初篩→取全文→全文複篩」完整落地。純 SKILL.md 規格。
- **v0.19.12** — **新增「初步篩選」高敏感階(寧留勿殺)＋PRISMA 全程數學對帳閉環**:(1) **兩階篩選**:①′ 在嚴格離題判定 (c) **之前**新增 **(b2) 初步篩選**——讀 title/abstract、同樣只看四型軸,但**只剔除「某核心軸明顯離題」者(純他病/他藥/健康/動物),模糊一律先保留**;做完**停下報告初篩狀況**(★執行規範 A 插入停頓點 ②b)再進嚴格階。先敏感後精確,避免一刀切誤殺模糊個案。(2) **PRISMA 數學閉環(流程圖規格 6(e))**:每一 N 須可追溯,**進入篩選 ＝ Σ排除 ＋ Σ所有下游終端框**;終端框用**完整桶數非精選子集**(修正先前用「納入9＋背景7」對帳→憑空 39 筆黑洞的缺陷);下游策劃(Study 連結/去重/重歸背景)須**逐步交代** X→Y→Z、無未交代差額;出圖前自我核對對不攏不出圖。緣由:使用者指出 DPP-1 流程圖 467−356＝111 但只交代 72、39 筆黑洞;根因＝用精選數而非完整合格桶數對帳。純 SKILL.md 規格。
- **v0.19.11** — **篩選 PICO 化:軸由問句萃取、排除＝缺被指定軸(更貼 Cochrane)**:①′(a) 硬規改寫——軸＝從**使用者問句**萃取的 PICO 合格準則(P/I/C/研究設計四型,**只取問句真的指定的**,不一定每型都有);**問句沒指定的軸不施加**(不可擅自加「只要 RCT」「要對照」等未授權限制);**排除＝缺某條被指定的軸**、須標缺哪軸(健康受試者/動物=缺 P 軸;DPP-4 糖尿病=缺 P;支擴無 DPP-1=缺 I);**非原始數據(綜述/MA/指引)是「分類為背景參考」非「排除」**;**outcome/極性永不為軸**。緣由:使用者指出排除準則應為納入軸之補集、且只用問句萃取的軸,才合 Cochrane eligibility 邏輯。純 SKILL.md 規格。
- **v0.19.10** — **拔除 ①′ 篩選殘留的 outcome 漏洞(重申:篩選不得用任何形式的結果)**:①′(c) 移除「極性正確/極性相反(主題問療效、文獻反向)」這條以**效果方向**判定的準則——它等於用 outcome 篩。新增鐵律:**判定只看四型軸(族群/疾病/介入/研究設計),嚴禁以效果方向/極性(有效vs無效、療效vs傷害)、有無達 endpoint、有無顯著作為納入或排除依據**;結果一律留到資料抽取/合成/GRADE。同藥被當「致病因」研究＝介入軸語意不符、以軸別處理而非效果方向。連帶把證據分級段「主療效問題/主療效 RCT」措辭改為中性的「主要試驗主報告」(僅報告層級、不涉結果)。純 SKILL.md 規格。
- **v0.19.9** — **Phase 1 內部停頓點固定化 ＋ 四項篩選/流程圖瑕疵修正**:(1)**停頓點**:★執行規範(A) 明訂 Phase 1 內部依序停——①六腿檢索+去重→逐腿報告(結果/策略/限制/是否翻頁/去重數)②→報告篩選策略③篩選完→報告篩選狀況④確認後做引文追蹤(多輪至收斂)、收斂後才報⑤三表+PDF→問 Zotero。(2)**瑕疵一+二(MECIR C42)**:分析單位＝**原始研究(Study)非報告(Report)**,同試驗多報告連結成一筆;**統合分析/指引/綜述為次級·三級文獻,移出「納入 N」改列「背景/對照參考」**,杜絕 double-counting;流程圖終點只算原始研究、標「N 項研究對應 M 篇報告」。(3)**瑕疵三**:排除理由**只用 PICO 四域措辭、嚴禁「結果/療效」字眼**(健康受試者=族群不符;臨床前/Ph1=研究設計不符;不可寫「非○○療效」)。(4)**監管文件來源**:辨識臂加 FDA Drugs@FDA／EMA EPAR／CSR(抗選擇性報告偏誤),無免費 API 則標人工/未及。(5)**自動化透明度(PRISMA 2020)**:流程圖標「Records removed by automation tools」、篩選框標明「單一 AI 初篩(非 MECIR C39 雙人獨立)」。純 SKILL.md 規格。
- **v0.19.8** — **Consensus／OE 檢索方法比照其他腿(Cochrane 對齊)＋不預設文獻類型**:明訂 C 與 OE 用**與 PM/OA/EP 相同的「兩軸概念塊」query**(措施軸同義詞 OR-block × 疾病軸),**不設 `medical_mode`／`exclude_preprints`／`study_types`／`sjr_max` 等任何類型/格式/出版狀態/分位預設**(除非使用者明指——這些違反 SR 最大敏感度);OE 題目須明示「不限研究類型」。因 C/OE 為 AI 合成腿(單輪上限~20、`page`>0 需 Enterprise、OE 為合成),**無法窮盡**,**依 PRISMA-S 在報告逐源申報此先天上限**。緣由:先前 C 用鬆散措辭＋medical_mode/exclude_preprints 預設,與其他腿不一致、帶進離題(DPP-4)雜訊且預篩了類型;改用結構化兩軸後 C 回傳全 on-topic。純 SKILL.md 規格。
- **v0.19.7** — **檢索/篩選軸硬規(只 P/疾病/I/研究類型,禁 Outcome)＋ PDF 後暫停問 Zotero**:(1) **①′(a) 新增硬規**——可作為檢索軸與離題篩選軸的型別**只有四種**:族群／疾病·狀況／措施·介入／研究類型;**嚴禁以結果·預後(outcome/endpoint/prognosis,如惡化率·FEV1·死亡率)作為檢索或篩選策略**(Cochrane:結局索引不全＋選擇性報告→降敏感度、引 selection bias;結局只在資料抽取/合成/GRADE 處理)。即便使用者以複雜問句提問,亦只萃取此四型組軸。檢索模式 PICO 列同步註明「不含 O 軸」。(2) **★執行規範(A) 停頓點1 改為「三表＋PDF 交付後才暫停問 Zotero」**——先把結論 PDF 給使用者,再暫停詢問是否匯入 Zotero 資料夾,未同意不匯入。(3) 順修 ①′(b) 管線順序敘述以對齊 v0.19.6(SR 品質閘預設關閉、①′ 對全聯集判、Q＝0)。純 SKILL.md 規格。
- **v0.19.6** — **移除『公信力／快速』模式,SR 為唯一檢索定位**:本 skill 不再有雙模式與切換——刪掉公信力(精確/Q1 閘/分層 quartile 收窄)那條線,只留 **SR(系統性回顧對齊、敏感度優先)**。連帶:(1)「檢索模式」節由雙欄對照改為單一 SR 原則表、移除預設判定與語意詢問;(2) **期刊品質閘預設關閉**(分位只標註不刪、品質交下游 RoB/GRADE;唯使用者明確要求才套 `--max-quartile` 並申報)——§1①(3′)、PM 第二層 Q1 閘(永久關閉)、檢索腿狀態模板、對帳恆等式(SR 預設 Q＝0)、清單二標題均同步;(3) 高命中改以 Cochrane 高敏感過濾器/收緊 PICO 聚焦、`total_count` 全報。前言區 v0.11–v0.13 之品質閘歷史註記保留為版本沿革。純 SKILL.md 規格。
- **v0.19.5** — **PDF 呈現規範(回應排版回饋)**:新增報告**排版／呈現原則**——(a) 章節標題以 `KeepTogether` 與其後第一個內容綁同頁、**禁止標題後直接跳頁**(會跳就整組推下一頁);(b) 流程圖檢索腿**一律全名**(Consensus/PubMed/OpenEvidence/OpenAlex/Europe PMC/ClinicalTrials.gov),不用縮寫;(c) 核心證據標題**不用「清單二」字樣**、多子表**右欄(PMID/DOI、交叉檢核)跨表對齊**;(d) **新增「交叉檢核(PubMed/Crossref)」欄,僅呈現雙源比對狀況、不作篩選依據**;(e) **核心證據表後附全部納入文獻 APA 清單**,書目用 **Crossref/PubMed 實際 metadata**(勿杜撰作者)。DPP-1 報告已照此重產(13 篇全通過雙源檢核;SAVE-BE 現已獲 PMID 40154523)。
- **v0.19.4** — **翻頁新撈到的紀錄也要餵回引文追蹤迴圈＋新藥軸補搜(閉合迴圈)**:明訂滾雪球種子**不限「清單二核心」**——§③ 全頁取盡後新浮現、即使歸到「進行中試驗／待評估」的紀錄,也要當新種子再追一輪;**中途發現全新藥名/代號**(本案 florensocatib)須以該 token 回頭各腿全文補搜再接回。實測 DPP-1 第3輪:新種子 HOPE-BE(florensocatib)、AIRTIVITY→反向/正向 0(論文太新、citation graph 未建、DOI 未索引)＋florensocatib 全網補搜(OpenAlex/Europe PMC/PubMed)僅命中 HOPE-BE 本身→**新增 0→收斂**。誠實補記:v0.19.3 當下漏了對翻頁新發現做引文追蹤,本版補做並寫成規則。
- **v0.19.3** — **實際關閉 OpenAlex／Europe PMC 翻頁缺口(印證 v0.19.2 鐵律可執行)**:DPP-1 案把兩條 broad 全文腿**逐頁取盡**——OpenAlex(DPP-1 限制軸全取)母體 **284**(`cursor` 2 頁)、含 bronchiectasis 軸 124;Europe PMC(兩軸 AND)母體 **500**(`cursorMark` 取盡);合併去重(兩軸皆中)**322**,逐筆篩 310 筆非既納入者。**無新「已完成原始 RCT」**(核心 4 RCT 不變),但全頁取盡**撈到 targeted PubMed 沒有的 3 件**:**HOPE-BE(florensocatib,全新 DPP-1 藥,protocol＋baseline,`10.1183/23120541.00182-2026`)**、**verducatib＝BI 1291583 正式 INN＋AIRTIVITY Ph3 設計論文(`10.1183/23120541.01068-2025`)**、AIRLEAF＋CLAIRLEAF Ph2 pooled(D92-07 會議摘要)。佐證鐵律價值:broad 腿不翻到盡會漏掉新藥/新試驗。報告 OA/EP 由「僅第一頁(缺口)」改為「已全頁取盡」。
- **v0.19.2** — **翻頁鐵律強化(回應外部評論;每腿取盡、禁 relevance 截斷)**:明訂 SR 模式須**逐腿取盡所有符合 query 的紀錄**(PubMed 全 PMID;OpenAlex／Europe PMC `cursor=*` 翻到盡;CT `nextPageToken`;Consensus／OE 為 AI 合成腿先天有上限、須申報),**數千筆也分批全篩、不得因量大截斷**;唯一能縮小命中的是**讓 query 更精準(改變比對集合)**,縮小後仍篩每一筆;**嚴禁靠 relevance 排序截斷固定 query 結果**。報告**逐腿**寫真實母體 N 與「已全數篩選」,**任一腿未全篩須明白申報為缺口**。誠實補記:DPP-1 案 PubMed 已全篩(85),但 OpenAlex(355)／Europe PMC(250)僅取第一頁＋引文追蹤、未逐頁取盡——屬本次缺口。
- **v0.19.1** — **實際執行完整翻頁(印證 v0.19)＋校正批量上限**:DPP-1 案把 PubMed 母體 **85 筆全數取得、分 4 批(40/20/20/5)逐筆雙軸篩選**——相關度前 40 以外的 45 筆均為綜述/社論/藥動/臨床前/他病(PCD),**無新原始 RCT**(確認主臂完整;SAVE-BE 仍只在引文追蹤、不在 PubMed)。校正:對話內 `get_article_metadata` MCP **每次約上限 20 筆**(實測超過只回 20)→ 批量改以 ~20 為單位迴圈取盡。報告「翻頁」由侷限改為「已執行」。
- **v0.19** — 兩條穩健性原則:**(1) 引文追蹤逐輪至收斂(迭代)**——每輪把新納入者當種子再追反向＋正向,直到某輪新增 0(雪球至飽和);**每輪都畫進流程圖**(輪次/種子/反向·正向/新增)。實測 DPP-1:第1輪+SAVE-BE、第2輪(SAVE-BE 種子,反向24+正向33)+0→收斂。**(2) 大量初始命中禁用 relevance-top-N**——SR 須篩每一筆,故先取全部 ID→**分批(~100–200)拉 metadata→逐批雙軸篩選→累加去重**(分段處理);OpenAlex/Europe PMC 用 `cursor=*` 取盡;數千筆才以 PICO 精度＋過濾器收斂但須申報。報告寫真實母體 N 與「已全數篩選」。緣由:DPP-1 案先前只取 PM relevance 前 40/85、未翻頁,且引文僅做 1 輪。純 SKILL.md 規格＋報告。
- **v0.18.6** — **引文追蹤「全面執行」原則**:C30 反向須掃**所有納入研究＋統合分析/指引＋相關(含被排除)綜述**的參考清單(非單一代表研究)＋關鍵 RCT 正向。**實證價值**:DPP-1 案只掃 ASPEN 得 0 新;全面掃 8 種子(308 篇反向去重＋正向 WILLOW64/AIRLEAF14)**抓到漏掉的 SAVE-BE(HSK31858 Ph2, Lancet Respir Med 2025, PubMed 當時未索引)**→ 清單二 RCT 3→4、納入 12→13、引文追蹤新增 0→1。凸顯代表性執行會漏、且缺 Embase 之風險。純 SKILL.md 規格＋報告更新。
- **v0.18.5** — **引文追蹤誠實鐵律**:C30 引文追蹤**必須實際執行**(逐筆抓回反向 `referenced_works`＋正向 `cites:<id>` 紀錄→去重→雙軸篩選),**禁止只取 `cited_by_count`／`referenced_works.Count` 數字就斷言「新增 N」**;報告與流程圖第二臂須寫**實際比對筆數**(反向 x／正向聚焦 y)與結果。緣由:自評發現先前 DPP-1 報告只取了引文「數量」就標「新增 0」、未真正逐筆比對;補做後 ASPEN 反向 29＋正向(談支擴)70 逐筆篩選,確認 0 新原始試驗(另記 AIR-NET 進行中平台試驗)。純 SKILL.md 規格。
- **v0.18.4** — **流程圖補上「引文追蹤」第二臂**(原 v0.18.3 只把 C30 寫在內文、圖上缺):依 PRISMA 2020,流程圖須畫出「經其他方法(引文追蹤/參考清單)找到的紀錄」第二臂——反向(納入研究＋排除綜述參考清單)＋正向(被引用)→ 篩選 → 標「新增納入 N 篇」→ 匯入最終納入(納入＝資料庫臂＋引文追蹤臂)。DPP-1 案誠實標：ASPEN 反向 29／正向 130,經雙軸篩選**新增納入 0**(已涵蓋於資料庫命中)。純 SKILL.md＋產生器。
- **v0.18.3** — SR 模式再對齊兩條 MECIR(回應第二輪 EBM 評論):**① 會議摘要不在篩選階段排除**(C35 禁出版格式限制／C28 灰文獻)→ 改列「待評估研究(awaiting classification)」、流程圖另設專格、不計入排除(故 DPP-1 案排除 29→28、待評估 1);**② 參考文獻追蹤(C30)**——對納入研究＋相關綜述/SR(含被排除的敘述綜述)做反向引文(OpenAlex referenced_works／Europe PMC references)補抓藏在其中的原始 RCT,報告註記已掃對象與新增數。純 SKILL.md＋報告產生器。
- **v0.18.2** — **新增「未納入來源與方法學侷限」必含透明度章節**(回應外部 EBM 評論＋使用者要求「說明其他腿的限制」):逐一列曾考慮但未納入的來源及原因(Embase／CENTRAL／CINAHL 需機構訂閱無免費 API、WHO ICTRP 無免費即時 API、Google Scholar 不可重現、Scopus 個人金鑰無授權、Epistemonikos 待 token),並標各來源 MECIR 地位(C24／C27);**並誠實聲明雙人獨立篩選侷限**——本工具單一 AI 演算法篩選未達 MECIR C39(≥2 人獨立),定位「初篩」、最終納入建議人工覆核。SR 模式覆蓋聲明同步補此 caveat。純 SKILL.md＋報告產生器。
- **v0.18.1** — 流程圖**細化＋行文白話化**:流程圖每階段須給明確數字且相加一致——(a) 各腿命中→(b) **去重後總數 N**→(c) **逐批剔除各自一行寫原因＋篇數**(綜述/社論、臨床前/Ph1、會議摘要、缺介入軸、缺疾病軸…;不可籠統一框)→(d) 納入分型;Σ剔除＋納入＝N。新增**行文原則**:PDF 寫給人讀,用通暢完整中文句、術語附白話。純 SKILL.md 規格＋產生器。
- **v0.18** — **PDF 報告新增「檢索流程圖(PRISMA-style 視覺)」必含章節**(§4 第6項):以 `reportlab.graphics` 畫方塊流程圖把檢索漏斗視覺化——辨識層各腿命中數(C/PM/OE/CT/OA/EP/EK)→ 去重＋①′ 兩軸篩選 → 排除框(逐條列原因＋數:缺哪軸／品質閘 Q2↓／驗證不符)→ 納入框(清單二分型計數＋進行中試驗)。讓「哪腿撈到多少、為何被排除」一眼看懂。純 SKILL.md 規格＋產生器(zero-dep reportlab.graphics)。
- **v0.17.4** — **修 PDF 輸出路徑的 OneDrive 坑**:實測使用者「文件」被 OneDrive 接管且中文名(`C:\Users\<user>\OneDrive\文件`),而舊規範「留空預設 `%USERPROFILE%\Documents`」會指到**非同步的空資料夾**(`C:\Users\<user>\Documents`)→ 使用者在檔案總管看不到產出。改為**留空時解析 Windows 已知資料夾 `[Environment]::GetFolderPath('MyDocuments')`**(正確處理 OneDrive KFM 與中文名);明令勿用 `%USERPROFILE%\Documents`;並要求產出後**回報絕對路徑**。settings.yaml 的 `report.pdf_output_dir` 已校為真正文件夾。純 SKILL.md＋範本＋本機設定。
- **v0.17.3** — SR 模式評估並接入第三方來源(兩者實測):**Epistemonikos 腿(`EK`)落地**——系統性回顧專庫(JSON,端點 `/v1/documents/search`,`classification` 可篩 systematic-review／broad-synthesis),補 Cochrane「找相關 SR／既有合成」;**需免費 token**(email `dev@epistemonikos.org` 申請)、放 `settings.yaml` `epistemonikos.api_token`(gitignored),**無 token → 腿 ⚠️ 跳過**。**WHO ICTRP 確認無免費自動化**(即時 API 404、bulk 須 SharePoint 申請、web service 付費)→ 不建自動腿,改列「人工補檢」缺口(手動入口匯出)。**Google Scholar 排除**(無合法免費 API、結果不可重現→違反 PRISMA-S;廣覆蓋/引文已由 OpenAlex＋Europe PMC 免費取得)。覆蓋限制聲明同步更新。純 SKILL.md＋範本。
- **v0.17.2** — **個資隔離**:Phase 1 PDF 輸出路徑真值(含本機使用者名 `C:\Users\<user>\Documents`＝個資)從 SKILL.md 移出 → 改放 **gitignored 的 `config/settings.yaml` 之 `report.pdf_output_dir`**;SKILL.md／範本改用泛用 `%USERPROFILE%\Documents` 並指向 settings;changelog 內 GitHub handle 去個人化。追蹤檔(SKILL.md／scripts／README／example)再掃描:**無 email／Zotero key／library_id／collection／本機使用者名**;settings.yaml 始終 gitignored。純文件/設定隔離,引擎/判定/schema 不動。
- **v0.17.1** — SR 模式新增兩條**免金鑰**來源腿(補 recall ＋ Cochrane 引文追蹤):**OpenAlex**(`OA`,2.4 億文獻引文圖譜——對清單二核心做 backward `referenced_works` ＋ forward `cited_by` 滾雪球;帶 mailto polite pool)、**Europe PMC**(`EP`,MEDLINE＋PMC＋preprints＋部分非 MEDLINE,REST 免 key)。兩者自帶 DOI／PMID → Lane B 預過。覆蓋限制聲明更新可及來源(仍缺 Embase／CENTRAL／CINAHL／ICTRP——無免費 API)。緣由:Elsevier 個人免費 key 對 Scopus／ScienceDirect 無實際 entitlement(授權綁機構 IP／insttoken)→ 改用免費等效來源達成「廣覆蓋＋引文追蹤」。純 SKILL.md。
- **v0.17** — **新增「SR(系統性回顧)模式」(Cochrane Handbook 第 4 章對齊)**,與既有「公信力模式」並存、預設仍公信力。SR 模式翻轉預設求**敏感度／recall 優先**:(1) **Q1 品質閘關閉**(品質交下游 RoB／GRADE,不在檢索砍 quartile——砍了＝selection bias、漏 Q2↓ 正當 RCT);(2) **不設語言／出版狀態／日期／格式限制**(要設須書面理由);(3) 查詢改 **PICO 概念塊**(族群 AND 介入 [AND 對照／設計];塊內 OR),控制詞(MeSH exploded)＋自由文字(同義詞／截詞)並用;(4) 設計過濾改 **PubMed 官方 Cochrane 高敏感 RCT 過濾器**(取代 v0.10 自製 pubtype);(5) **命中過多不以 quartile 收窄**,高 total_count 當分母全報;(6) 新增 **ClinicalTrials.gov 試驗註冊腿**(來源 `CT`,未發表／進行中,API v2);(7) **PRESS 自檢**(執行前審策略);(8) **PRISMA-S／PRISMA 2020 報告** ＋ 字串原樣可複製 ＋ **覆蓋限制聲明**(誠實標明缺 Embase／CENTRAL／CINAHL／ICTRP 存取→產出為「SR 輔助／rapid review 級」非完整 Cochrane 檢索);(9) **記檢索日**,>6–12 月重用須重跑。純 SKILL.md(新增「檢索模式」節＋§1①(2)/(3′) 交叉註記),引擎/判定/schema 不動、向後相容。
- **v0.16.1** — **skill 更名 `consensus-verify` → `EBM_Search`**（frontmatter `name:`；使用者統一專案/資料夾/repo/skill 為 EBM_Search）。本機資料夾 `…/Projects/EBM_Search`、GitHub repo `EBM_Search`、Notion 專案 `EBM_Search` 均已對齊。**永久生效須從 Claude Desktop→Settings→Skills 重新上傳 dev**（會以新名 `EBM_Search` 註冊；舊 `consensus-verify` skill 需手動移除避免重複）。純 metadata 變更，引擎/判定/流程/schema 全部不動。
- **v0.16** — **①′ 離題篩選重構（防主題漂移）**。根因：四軸展開把主題「最關鍵的必含限定軸」稀釋掉，①′ 比對基準從三連言縮成兩連言，導致 COVID-19 疫苗×支擴 題的清單二誤升 Barker（NCFB 總論）/O'Grady（支擴疫苗但非 COVID）。重構：(a) **主題拆成「必含連言軸」、展開前鎖死、整軸不可丟**（COVID 題＝COVID/SARS-CoV-2 × 疫苗 × 支擴 三軸全必含）；(b) **管線順序改「聯集→去重→Q1 品質閘→①′ 離題」**（離題判定吃 title/abstract 不耗額度、且只對收斂後小 Q1 集逐篇判，零額外成本；對帳恆等式不變，僅 Q 在 B 前算）；(c) 逐篇對 title/abstract 比對**全部必含軸＋年份窗＋極性**：缺軸→清單三-B（標缺哪軸）、極性反→清單三-B、只剩族群軸→清單三-D；(d) **模糊翻轉「寧驗勿殺」**（軸明確缺直接清單三、模糊不升清單二）；(e) **清單二 header 逐字回顯原始主題＋必含軸**使漂移有聲。釐清：**標題相似度 0.85 是反幻覺消歧、非主題篩選**（離題但真實的文獻相似度反高）。**另新增 ★執行規範 (C)：Phase 1 完成一律附 PDF 報告，且報告必含「檢索原則」節（四軸實際字眼＋三腿完整 query＋必含連言軸的判定同義詞）**；§4 增「PDF 報告規格」子節（reportlab＋CJK 字型、固定章節）。純 SKILL.md 變更，引擎/判定/schema 不動、向後相容。實測 COVID-19 疫苗×支擴：套 v0.16 後清單二由 3→1（僅 Stenlander；Barker/O'Grady 落清單三-B 缺 COVID 軸）。
- **v0.15** — 三表欄位定版。**清單一**由文字簡述改為**檢索流程數字漏斗**:逐腿命中(C N₁／PM 廣檢 N₂→v0.10 分層 N₂′／OE N₃)→去重聯集 U(重疊 w)→剔 off-topic B／品質閘 Q／驗證不符 V→進清單二 M,附**對帳恆等式 `M＋(B+Q+V)＝U`**。**清單二固定 6 欄**:`試驗/文件｜原始英文主體｜第一作者｜期刊(SJR)｜PMID/DOI｜驗證`(英文標題照錄不翻譯,表後附 APA)。**清單三固定 5 欄**:`原始英文主題｜作者,年｜期刊｜分位｜剔除原因`(首欄由「文獻」改原始英文標題照錄)。純 SKILL.md(§4＋★執行規範 B)改寫,引擎/判定/schema 不動、向後相容。實測 SGLT2i×HF:C 20／PM 5,100→分層 930／OE 15,聯集後清單二 11(全 Q1 驗證)、清單三 14。
- **v0.15.1** — (1) **PM 分層新增第二層 Q1 期刊閘**(§1①(2)):第一層(疾病[TIAB]＋證據型 pubtype)後若 `total_count` 仍 `> 60`,進第二層**只取 Q1**(取 PMID→`get_article_metadata` 抓期刊→`journal_quartile.py --max-quartile 1`),Q2↓列清單三標分位。(2) **驗證涵蓋全體 on-topic 候選鐵律**(§1③):C/OE 來源無 DOI/PMID 者**不可**標『無法驗證』丟清單三——須以 `{title,first_author,year}` 跑 Lane A/B 解析 ID＋判 verdict;VERIFIED＋Q1 應入清單二,清單三只留真 miss/off-topic/Q2↓/會議摘要。(3) **清單三加 `DOI/PMID` 欄**,**唯 Crossref＋PubMed 都查無才填「缺」**(固定欄位 5→6)。(4) **§1①(2′) 命中收斂後選核心**:PM 分層至 N 後不逐篇讀 N(N 當分母);核心取「relevance 前 ~30–40 工作集 ∪ C／OE 命中」之多腿交集,仍不收斂續收窄。實測 SGLT2i×HF:14 筆「C 腿無 ID」補跑後 14/14 VERIFIED、全解析出 PMID＋DOI,10 篇 Q1 升清單二、Crossref 腿確認正常。純 SKILL.md＋既有 helper,引擎/判定/schema 不動、向後相容。
- **v0.15** — 三表欄位定版。**清單一**改檢索流程數字漏斗(逐腿命中→去重聯集 U→剔 off-topic B／品質閘 Q／驗證不符 V→進清單二 M,附對帳恆等式 `M＋(B+Q+V)＝U`)。**清單二固定 6 欄**:`試驗/文件｜原始英文主體｜第一作者｜期刊(SJR)｜PMID/DOI｜驗證`(英文標題照錄,表後附 APA)。**清單三固定欄位**(首欄改原始英文標題照錄)。§4＋★執行規範 B 改寫,引擎/判定/schema 不動、向後相容。
- **v0.14** — 輸出精簡:**清單一改簡述、不再列全表**(與清單二＋三重疊;改用 §1①(4) 檢索腿狀態＋一段含數字流向的簡述對帳)。**清單二、清單三維持完整逐筆、嚴禁省略**(二附 APA、三附剔除原因含品質閘 Q2↓)。★執行規範(B)「逐筆列全」改為只約束清單二、三。§4 改寫。純 SKILL.md 變更,引擎/判定/schema 不動、向後相容。
- **v0.13** — 品質閘**預設由 Q1+Q2 改為 Q1-only**(`sjr_max=1`／`journal_quartile.py --max-quartile` 預設 1):本工具求最強公信力,核心清單二只留 Q1;`--max-quartile 2` 可放寬回 Q1+Q2。被分位剔除者(Q2 及以下)**完整列入清單三並標分位、不刪不省略**(配合 v0.12 三表完整呈現),使用者可從清單三自挑有興趣的 Q2 試驗。取代 v0.11/v0.12 的 Q1+Q2 預設。純 SKILL.md＋helper 預設值,引擎/判定/schema 不動、向後相容。
- **v0.12** — (A) 新增「★ 執行規範」:**分階段停頓**(檢索+三表/Zotero/全文/分析 各關之間停下問使用者是否繼續,不一口氣跑完)＋**三表完整呈現**(清單一/二/三逐筆列全,嚴禁「…」「(共 N)」截斷)。(B) §1①(3′) Q1+Q2 helper 落地:`scripts/journal_quartile.py`(SCImago 快取＋Crossref 取期刊→best quartile→留 ≤Q2,未收錄不誤殺;修掉與 v0.8.2 同款的單篇 endpoint select 誤用),PM/OE 分位過濾由協定變可執行;實測 DPP-1×bronchiectasis 18 篇全 Q1/Q2(17 Q1+1 Q2)、0 剔除。純 SKILL.md＋新增 helper,引擎/判定/schema 不動、向後相容。
- **v0.11** — 可選**期刊品質閘 Q1+Q2**(§1①(3′)):被大量研究的題可加期刊分位(SJR quartile)篩。C｜Consensus 原生 `sjr_max=2`(Q1+Q2);PM／OE 無原生 → 事後對 SCImago SJR 表(ISSN/期刊名→best quartile)留 ≤Q2,無表時 best-effort 標註。為何 Q1+Q2 不用 Q1-only:Q1-only 易誤砍專科/學會期刊的正當 RCT,Q1+Q2 砍 Q3/Q4 低品質尾巴、品質與 recall 平衡。三閘獨立併用:分位閘(管期刊)／證據閘(pubtype,管設計)／主旨閘(①′,管離題),互不取代(實測 sjr_max=2 仍放進 DPP-4 離題篇)。無分位者(新刊/會議摘要)不誤殺;預設可關;套用須於 §1①(4) 申報砍掉幾篇。純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。
- **v0.10** — PM 腿命中過多時的**分層精度過濾 ＋ 可申報**:`(別名 OR …) AND 疾病` 對被大量研究的藥會爆 `total_count`(實測 nintedanib＝974),爆量主因是疾病詞落 `[All Fields]` 太廣。新增條件式協定:先取 `total_count`,`≤60`(門檻非死值)以 `max_results`≈80–100 一次抓回(通常 `has_more=false`、不需翻頁,retstart 僅罕用 fallback);`>60` 分層收窄(不靠翻頁硬抓數百筆)——(1) 疾病改 `[Title/Abstract]`、(2) 疊證據型 pubtype(`RCT/Meta-Analysis/Systematic Review/Clinical Trial/Guideline[ptyp]`)、(3) 選用 `date_from`。**鐵律:不靜默吞掉**,收窄須於 §1①(4) 申報原始 total_count／套用層級／縮後筆數／原因,被收窄者標「未納本輪、可手動補抓」非「不存在」。證據型 filter 保住 PM 獨家高價值(HSK31858/AIRLEAF 等 RCT 留存),砍的是 case report/社論/基礎研究噪音;L4 觀察性與會議摘要需保留時手動另跑窄 query(會議摘要本走 C/OE)。僅改 §1①(2)/(4),純 SKILL.md 變更,腳本/設定/schema 不動、判定邏輯不變、向後相容。
- **v0.9** — OpenEvidence 由「手動網頁腿」升級為 **MCP 腿**:裝 `openevidence` MCP 後用 `oe_ask` 送題(fire-and-forget／`wait_for_completion`),不再需網頁手動貼題抽引用 → v0.8 的「無公開 API、僅能手動、不可腳本化」作廢。OE 回傳引用**自帶 DOI/PMID＋嵌入式 Crossref 驗證**(`crossref.status`、`similarity`)→ `validated` 高相似度者**視同預過**(同 PM 的 PMID 預過),§1③ 只補驗未驗/低相似度者;v0.8 的「OE 一律不可預過」改為「已 Crossref 驗證者預過」。反循環論證仍守(信內嵌 Crossref〔獨立〕,非 OE 綜述)。§0 表、§1①(2)/(4)、§1③、§6 同步改寫;存取前提不變(先 `oe_auth_status`、relay 須連、台灣已確認)。實測 nintedanib×PF-ILD:OE 回 6 筆全 Crossref 驗證,三源同中 4(含 whole-INBUILD 直給 `ERJ 59(3):2004538`)、獨家補 Chen 2021 安全性 SR&MA(PLOS ONE,PMID 33989328)。純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。
- **v0.8.2** — 修 §1③ Crossref leg(`crossref_check`)的 `query.bibliographic` 查詢:`select` 含 **`subtype`**,但 Crossref `/works` 列表路由不支援該欄位 → 每筆回 **HTTP 400 validation-failure**,整個 Crossref leg 變 `error`,雙源(`both`/`auto`)實質退化成 PubMed-only。改 `select` 為 `DOI,title,issued,type,update-to`(皆合法);撤稿偵測改靠 `type`=='retraction' 與 `update-to` 標籤(單篇 `/works/{DOI}` 裸 GET 仍可取 `subtype`,不受限)。實測:修後 Crossref leg 回 `match`/`miss`、與 PubMed 真正雙源驗證,反幻覺門檻照常生效。與 v0.8.1 同屬 Crossref/Lane A 連通修正。純腳本修正,判定/schema 不變、向後相容。
- **v0.8.1** — 修 §0／⓪ 連線探測 bug:`crossref_available()` 心跳 URL 誤用 `?select=DOI`,但 Crossref 單篇 endpoint `/works/{DOI}` 不支援 `select`(僅列表 endpoint 支援)→ 一律回 HTTP 400 → 探測誤判 Crossref 不可達 → **任何可上網的機器都會錯誤退回 pubmed-only**,Lane A 雙源驗證失效。改查裸 DOI 即可(實際驗證查詢走列表 endpoint,本即正常,不受影響)。另加 `_force_utf8_console()`:Windows cp950 主控台印中文 `reason`/log 不再亂碼(輸出檔本就 UTF-8)。純腳本修正,判定/schema 不變、向後相容。
- **v0.8** — 三源檢索:§1① 加 **來源 OE｜OpenEvidence 手動腿**(網頁貼題、抽引用併入 intake;角色同 Consensus、**不可預過**、全送 Lane A/B;無公開 API 故僅手動);來源系統標記擴充 C/PM/OE 及組合;**新增 §1①(4) 三源檢索狀態回報(每腿可診斷)**——清單一前逐腿報 query/命中/淨增/狀態,任一腿異常須明列不可靜默吞掉;§6 加 OE 幻覺/存取/診斷三條。純 SKILL.md 變更,腳本/設定/schema 不動、向後相容。
- **v0.7** — §1① 由「Consensus 多措辭」升級為**雙源檢索聯集**:加 PubMed MCP 深抓(四軸別名 Boolean OR 單條、`max_results` 開大、`retstart` 翻頁、無 20 上限);跨源去重(鍵不變)、每筆記來源系統 C/PM/C+PM;PubMed 來源項 Lane B 視同預過;清單一 `來源query`→`來源`。會議摘要仍 Consensus-only 待 Crossref。實測 DPP-1:PubMed 深抓 81、Consensus ~27,聯集最完整。判定/驗證邏輯不變、向後相容。
- **v0.6** — §1 擴為 6 步:① 改「主題→四軸展開→多輪檢索＋聯集去重」,新增 ①′「對原始主題剔離題」(防漂移閘);四軸展開原則(縮寫↔全文、慣稱↔生化/基因別名、類別↔藥名↔代號、疾病縮寫↔全文)＋精度錨點;去重鍵 DOI→標題+作者+年;清單一改＝聯集全集(加 `來源query`)。判定/驗證邏輯不變、向後相容。
- **v0.5.1** — 新增設定讀取層:`config/settings.yaml`(自動探尋)＋環境變數(`NCBI_API_KEY`／`CROSSREF_MAILTO`),優先序 CLI > env > 檔 > 預設;內建零相依迷你 YAML reader(不需 pyyaml);新增 `--config`／`--no-config`。判定邏輯不變、向後相容。
- **v0.5** — P1 PubMed-MCP 升格 §1③ 一級 lane(含手動腿標準步驟);P2 會議摘要 miss 改判 `UNRESOLVED`(輸入 `doc_type`、Crossref type 自動偵測);P3 `reason` 細分;P4 `off_topic` 免全驗(`OFF_TOPIC`);P5 substudy `evidence_note` 加註。向後相容。
- **v0.4** — 新增連線探測前置(`--source-mode auto`):Crossref 不可用時自動退回單用 PubMed;輸出 `run_mode`。
- **v0.3** — 預設規則 `both`→`any`;新增 `UNRESOLVED`;命名統一 any/both;標準化三表輸出格式;`--no-crossref`。
- **v0.2** — 證據等級 title fallback;PubMed 多候選消歧;多式查詢 + STOPWORDS。
- **v0.1** — 初版:Consensus + Crossref/PubMed 四步流程。
