## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】
- **功能塊**：把三條「檢索守門鐵律」從靠記性落為機器 gate／修好失效的 hook（triple vs dual COPD 案逐一被使用者糾正而立）：
  - **(A) 對照軸純度（comparator purity）**：檢索 query 只含 `in_query=true` 軸（P 疾病＋I 介入），**禁止對照軸 C（`in_query=false`）同義詞出現在任何腿 query**（否則砍掉標題/摘要沒提對照組的研究、傷 recall；C 軸留待 ③ 讀全文比對）。緣由：Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」。
  - **(B) 四軸展開必須真的做（axis expansion）**：四軸展開是鐵律，但既有 `axis_coverage_check` 只驗「每腿 query ≥1 同義詞命中」，**攔不到「同義詞庫根本沒展開」**（P 只寫 COPD、I 只寫 triple therapy 也會通過）。故新增稽核 **g0.axes 同義詞庫本身**：每條 in_query/mandatory_screen 軸須 ≥3 別名且含全文形式。緣由：第一版策略同義詞過於稀疏、未做四軸展開。
  - **(C) Stop hook 找不到 cache → 自動守門靜默失效（最嚴重）**：Stop hook 跑 `gate_guard.py --auto --hook` 不帶 `--cache`，靠 `_find_cache(None)` 自動發現；舊版只看 run_state＋硬編 Windows 路徑 `~/OneDrive/文件/...`，在本環境（cache 在 `EBM_Search/cache/<topic>/`、無 run_state、非 Windows）一律回 `None` → `_active(None)=False` → hook **靜默 exit 0**，整輪自動守門等同未啟用（gates 僅因人工 `--cache` 才跑到）。修法：新增 `_find_active_cache_by_flag()`——掃 repo 內 `EBM_Search/cache/*/` 找帶 `_search_active.flag` 的進行中 cache，列為 `_find_cache` 的**首要**發現法（哨兵旗標＝地真值，與 run_state/env/OneDrive 無關）。
  - **(D) 待評估只在 ②c 產生、③ 必須二元**：使用者再三強調「待評估只有 ②c 這一關會產生」。②c＝判有無可篩內容：先看有無摘要→有摘要進 ③；沒摘要者再看有無全文；**無全文且無摘要才踢待評估**（Stage A，不進 ③）。③(g3) 必須切題/離題二元，不得誤生待評估。新增 gate `check_awaiting_stage`（`awaiting_stage_check.py`）：g3 出現待評估類字樣＝FAIL。SEARCH_SPEC 補鐵律並聲明取代先前散見的「③待評估」寬鬆措辭。
  - **(I) ②c『有全文』必須 materialize 內容（批次抓摘要/全文），不可只記 OA 旗標**：使用者發現 ⑦ 有大量「未辨識」，質疑「又忘了 unpaywall」。查證屬實：②c 對 848 筆把 Unpaywall `is_oa` 直接標「有全文（OA）」卻**沒把摘要/全文抓回來**→⑦ 只能靠標題分類→未辨識（同「判 have 須實抓」家族的錯）。修法：批次補抓摘要＝OpenAlex 50/批＋Crossref＋EPMC/PMC fullTextXML，materialize 499 筆；citation-arm 19 筆摘要另存 `g4_abstracts.json`、`classify_units.py` 加讀作 fallback（程式修改）。修正後 ⑦ title-only 由 ~54 降至 **22**（全為 publisher-OA-PDF）。**環境限制誠實申報**：本雲端沙箱無可用 PDF parser（pdfminer 的 cryptography 壞、pypdf 裝不起、無 pdftotext、crude zlib 抽 0/22）→ 這 22 筆 OA-PDF 在此環境無法抽文字，於使用者本機（有 fulltext 工具）可解。註：未對此加硬 gate——殘餘屬環境 PDF 限制、非方法學選擇；hard gate 會因環境而誤擋。
  - **(H) ⑦ 決定納入單位須核對『標題＋摘要(方法學)』、非只靠標題/pubtype**：第一版 ⑦ 用標題＋pubtype 啟發式，導致 (i) `IMPACT` 當常用字被誤併（59 報告灌水）、(ii) DOI-only 缺 pubtype → 483「未分型」。改為**讀摘要方法學內容**判設計與對照臂，落為可重用 committed 腳本 `classify_units.py`：設計優先序（SR/MA→指引〔僅 pubtype/標題、不掃 abstract recommendation 以免誤併〕→計畫書→RCT→觀察→經濟→綜述）；RCT 以 **NCT 號優先**＋word-boundary 試驗縮寫（排除『IMPACT of/on』）歸併為 Study，並判對照臂含 LABA/LAMA 與否。實測修正後：指引 226→27、IMPACT 59→34、核心『三合一 vs LABA/LAMA』Study 清楚辨識（IMPACT/ETHOS/KRONOS/FULFIL/TRIBUTE/TRILOGY/TRINITY/TRISTAR/ETHOS-ext/TRIVERSYTI）；殘餘（未辨識試驗 RCT 報告、未分型背景）據實標待人工覆核。
  - **(G) 引文追蹤新候選須『標題＋摘要』批次篩，嚴禁只憑標題丟（Cochrane 紅線）**：我 ④ 一度為規避逐筆抓摘要太慢，改成「標題沒中 P/I 就丟、不抓摘要」——使用者指出這違反 Cochrane 高敏感初篩、會漏殺用成分名/縮寫/廣義詞發表的隱藏 RCT。正解＝**Batch API 批次抓摘要**（efetch 200/批、OpenAlex 50/批；數千摘要 ~20 次呼叫），再對**全部**新候選做標題＋摘要篩；無摘要可抓者才用「負向排除法」（明顯他題才丟、其餘從寬）。新增 gate `check_citation_screen`（`citation_screen_check.py`）：g4 逐輪須 `screened_on=title+abstract`、`title_only_dropped==0`、有 ID 新候選時 `abstracts_fetched>0`。**實測：同題改回標題＋摘要批次篩，引文追蹤新增切題 0→19**（4 輪收斂 15+3+1+0）。
  - **(F) build_stage1_corpus 忠實沿用 ②c 分流（停止重推）**：`_stage1_corpus.json` 應是 ②c 決定的『凍結快照』，但舊 builder **憑『有無摘要』重新推導** candidate/awaiting，導致 (i) 135 筆 CT.gov 登錄試驗（有結構化內容、無自由文字摘要）被誤推成 `none→兩者皆無`；(ii) awaiting `reason` 用 `channels_exhausted` 反推，把『兩者皆無』(也帶 channels_exhausted) 誤標成『待人工補全文』。修法：改為**依 ②c 的 `class` 分流**（待評估類→awaiting；有全文/登錄→have；有摘要→ai_summary_only），awaiting `reason` 以 ②c 明確 reason 為準。緣由：使用者問「Stage A corpus 是否真有幫助」時，誠實檢視發現它對單一連續執行非工作輸入、且因重推與 ②c 打架；此修讓它成為忠實快照（真正可用於跨 session 交班）。
  - **(E) 待評估＝三管道全失敗才成立（補上漏掉的 step2 線上全文）**：使用者再強調最省成本序＝(1)有無摘要→(2)無摘要者全文是否可線上閱讀(PMC/EPMC)→(3)再不行才 Unpaywall OA→三者皆失敗才待評估。先前 ②c 漏了 step2（直接 abstract→Unpaywall），把有 PMC 線上全文者誤丟待評估。新增 gate `check_awaiting_channels`（`awaiting_channels_check.py`）：每筆待評估須標 `abstract_checked ∧ online_fulltext_checked ∧ unpaywall_checked ∧ channels_exhausted`，『兩者皆無』須真的無任何 ID/OA；缺一＝FAIL。實測重查本案 798 待評估→補 step2 後救回 286（103 EPMC 摘要＋183 PMC/EPMC 線上全文）→待評估降至 512。
- **動到哪些檔（本輪審查範圍：僅以下檔案）**：
  1. `EBM_Search/scripts/comparator_purity_check.py`（新增；(A) 核心判定）
  2. `EBM_Search/scripts/axis_expansion_check.py`（新增；(B) 核心判定）
  3. `EBM_Search/scripts/awaiting_stage_check.py`（新增；(D) 核心判定）
  4. `EBM_Search/scripts/awaiting_channels_check.py`（新增；(E) 核心判定）
  5. `EBM_Search/scripts/gate_guard.py`（新增 `check_comparator_purity`、`check_axis_expansion`、`check_awaiting_stage`、`check_awaiting_channels` 並掛進 `_all_checks`；(C) 新增 `_find_active_cache_by_flag` 並插為 `_find_cache` 首要發現法；abstract-first 調 `check_unpaywall_coverage` 略過有摘要者）
  6. `EBM_Search/scripts/selftest_guards.py`（新增五 gate 各自的「會 FAIL／防誤報」自測；(C) 旗標發現＋無旗標休眠回歸）
  7. `EBM_Search/scripts/build_stage1_corpus.py`（(F) 改為依 ②c `class` 忠實分流，不再憑有無摘要重推；awaiting reason 以明確 reason 為準）
  8. `EBM_Search/scripts/citation_screen_check.py`（新增；(G) 核心判定）
  9. `EBM_Search/scripts/classify_units.py`（新增＋更新；(H) ⑦ 以標題＋摘要精確分類；(I) 加讀 g4_abstracts.json 補 citation-arm 摘要）
  10. `EBM_Search/SEARCH_SPEC.md`（補「四軸展開」「對照軸純度」「Stop hook 必須找得到 cache」「待評估只在②c」「待評估＝三管道全失敗」「引文追蹤須標題+摘要批次篩」「⑦分類須讀標題+摘要」七條鐵律/規範，對齊已落地 gate/腳本）
- **fresh-clone／實跑結果**：
  - `python selftest_guards.py` → 全綠（含 (A)(B) 各自 FAIL/防誤報、(C)「旗標 cache 找得到→通過」「無旗標→回 None 休眠」），結尾「✅ 全部守門有效。」
  - (C) 實證：修復前 `gate_guard._find_cache(None)` 回 `None`、`--auto --hook` 在本案進行中 cache 上仍 exit 0（dormant）；修復後 `_find_cache(None)` 正確回 `…/cache/triple_vs_dual_copd`，且對「帶旗標＋故意壞 g0」的暫時 cache 跑 `--auto --hook` → **exit 2（正確擋下）**。
  - `python gate_guard.py --cache <本案 cache>` → Gate⓪ 策略核准／取盡／策略遵從／四軸覆蓋／四軸展開／對照軸純度 全 ✅。
- **想被重點看 / 不確定的點**：
  1. **(A) 遮蔽法防誤判**：比對 C 軸前先把所有 in_query 軸同義詞（長詞優先）從 query 遮蔽，讓 I 軸長詞（`ICS/LABA/LAMA`）內含的 C 子字串（`LABA/LAMA`）不被誤判。是否仍有跨邊界漏洞？
  2. **(B) 門檻 ≥3＋至少一全文形式**：刻意採低門檻（不要求塞滿 N 個，與 axis_coverage 設計一致避免 fail-closed）；是否足以擋稀疏策略又不誤殺高階 MeSH/CT.gov 字數受限的軸？
  3. **(C) 多個進行中 cache**：`_find_active_cache_by_flag` 在有多個帶旗標 cache 時取最近修改者；是否需要更嚴（例如同時禁止多旗標並存）？另：把旗標掃描列為 `_find_cache` 首要（早於 run_state）是否會在「run_state 指向 A、旗標在 B」時造成非預期切換？（判斷：旗標＝進行中地真值，應優先）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修：檢索 query 摻入對照軸 C 砍 recall 的 bug（triple vs dual COPD 案，Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」）。本輪修改：(1) 把該案 g0_strategy.json 各腿 query 改為只含 P＋I；(2) 新增 `comparator_purity_check.py` 並掛進 gate_guard，使「C 軸進 query」之偏離今後一律被機器攔下（含 ⓪ 策略階段）；(3) selftest 加兩條自測證明守門有效且不誤報；(4) SEARCH_SPEC 補鐵律對齊。

✅ 已修：四軸展開（鐵律）第一版沒做、且既有 `axis_coverage_check` 只驗「query ≥1 同義詞」攔不到稀疏同義詞庫的 bug。本輪修改：(1) 把該案 g0_strategy.json 各軸同義詞補成完整四軸展開（成分 INN／開發代號／品牌／疾病別名）；(2) 新增 `axis_expansion_check.py` 直接稽核 g0.axes 同義詞庫「真的展開」（≥3 別名且含全文形式），掛進 gate_guard 於 ⓪ 策略階段生效；(3) selftest 加三條自測（兩 FAIL＋一防誤報）；(4) SEARCH_SPEC 補「四軸展開必須真的做」鐵律對齊。

✅ 已做：把 ⑦ 收斂成『通用、可重現的固定步驟』。判斷＝適合固定（方法通用、每步補一個反覆失效模式）。本輪修改：(1) `classify_units.py` 新增 `--enrich`——把原本散在臨時腳本的 CT.gov NCT 補名＋介入相關性檢核**併進工具**，且改成**由 g0 的 I 軸同義詞／四軸展開成分驅動**（換主題自動適用、不改碼）；(2) 一道指令 `classify_units.py --cache <dir> --enrich` 完成 ⑦ 全流程（內容先到位→設計判別→NCT/縮寫/樣本數 Study 連結→I 軸介入相關性剔他藥→對帳＋誠實殘餘）；(3) SEARCH_SPEC 補「⑦ 標準固定步驟(通用)」五步。COPD 樞紐 NCT/樣本數降為選用 hint。實跑 `--enrich`：NCT 104→命名 102、I 軸在範圍 54／不在 48、核心 171／排除他藥 62（與手動結果一致）。註：classify_units 屬分類輔助、結果標 rapid-review 待人工，未設硬 gate（判別為啟發式，硬 gate 不合適）。

✅ 已做：129 無 NCT 報告再以『縮寫(摘要)＋樣本數特徵』保守連結。classify_units 新增 sig_link（樞紐試驗樣本數 IMPACT 10355/ETHOS 8588/KRONOS 1896/FULFIL 1810/TRILOGY 1368/TRIBUTE 1532/TRINITY 2691 ＋ 摘要內縮寫，排除 of/on）→ 再連 6 筆。讀殘餘 123 後判定**不宜再硬連**：它們多為(a)獨立/區域型小三合一 RCT〔本就各自為一個 Study、無樞紐試驗名〕、(b)會議摘要(~15)、(c)被 RCT 網過度納入的背景(成本/模型/綜述)與一筆非三合一藥(icenticaftor)。強連到樞紐試驗＝誤歸，故停在此、據實標待人工（標準 rapid-review 處置）。樞紐試驗連結已完成：IMPACT 54/ETHOS 32(+ext2)/FULFIL 18/KRONOS 16/TRILOGY 9/TRIBUTE 8/TRINITY 3 等。

✅ 已做：202 未連結 RCT 報告的 Study 連結＋他藥試驗剔除。(1) bug 修正：detect_trial 原本只認已知樞紐 NCT、其餘帶 NCT 也當未辨識→改成**任何 NCT 皆為 Study 鍵**（CT.gov 補名存 cache/nct_names.json），73/202 因此歸併；(2) 品質修正：用 CT.gov InterventionName 判每個連結到的 NCT 是否三合一（cache/nct_triple.json），發現 **66 筆其實是他藥/雙合一 RCT**（dupilumab/benralizumab/mepolizumab/tiotropium+olodaterol/QVA149/TORCH/Vitamin-E 等被 ③ 寬鬆篩掃入）→ classify_units 新增「排除:非三合一介入RCT」桶剔出核心；(3) 殘 129 無 NCT（次級分析/會議短摘/小型 RCT 未引試驗號）→ 待人工連結。結果：核心『三合一 vs LABA/LAMA』171 報告、他藥剔除 66、未連結 129。註：nct_names.json/nct_triple.json 為 cache（gitignored）run 產物，由 CT.gov 即時查；classify_units.py（committed）負責消費它們、NCT-as-key 與剔除邏輯。

✅ 已修（矛盾自省）：⑦ 把「有內容但 classifier 沒接住」誤報成「無法分類」。使用者點出矛盾：③ 已用標題＋摘要做過切題判斷＝有內容可讀，⑦ 卻說不能分類。實讀殘餘 129 證實裡面藏了**真原始 RCT 與 CT.gov 登錄試驗**（如「…Versus…」比較試驗、roflumilast/herbal add-on、「A Comparative Study Between FF/UMEC/VI…」登錄試驗——後者因『給了合成摘要後 is_ct&not ab 失效』落入未分型）。本輪修改 `classify_units.py`：(1) `is_ct` 一律先歸「進行中/登錄試驗」(不論有無合成摘要)；(2) 放寬 R_PRIM2 接住 comparison/add-on/versus 等原始研究；(3) 終端 bucket 改名「背景:其他次級文獻(社論/會議短摘/討論)」＝確定歸類為背景、非「無法分類」。結果：未分型 129→92（且再掃僅 3 筆殘原始訊號、皆非核心）、登錄試驗 0→29、核心 RCT 194。**每筆都已分類，無『不能分析』桶**；殘餘 92＝確為背景次級、202 未辨識試驗名 RCT 報告＝待人工連結到 Study（rapid-review 定位）。

✅ 已修：⑦「未分型」過多——改用三段 cascade 分析（摘要→全文→Unpaywall）。使用者指出進到 ⑦ 的都該有摘要/全文可分析、不該未分型。查證：281「未分型」中 259 其實有摘要，只是 classifier pattern 太窄（漏了 RCT 事後/次級分析〔post hoc/responder/subgroup/「analysis of the X trial」→應歸該試驗報告〕、藥學/裝置/方法學、共識/調查、其他原始臨床設計）。本輪修改：(1) `classify_units.py` 大幅擴充摘要 pattern（step1）→未分型 281→140；(2) 對殘餘以 EuropePMC/PMC fullTextXML 補全文再分類（step2）→140→129；(3) Unpaywall PDF（step3）本沙箱無 parser、env-limited。結果：未分型 281→129、title-only 33（22 為 OA-PDF env-limited）。核心 9 個樞紐 RCT Study 始終穩定。註：擴充 RCT 次級分析偵測會使「未辨識試驗名」RCT 報告增加（次級分析常不寫試驗名）→ 屬待人工連結，據實申報。

✅ 已修：②c『有全文』未 materialize 內容→⑦ 未辨識。本輪修改：(1) 批次補抓 499 筆摘要(OpenAlex/Crossref/EPMC/PMC)、citation-arm 19 筆存 `g4_abstracts.json`；(2) `classify_units.py` 加讀 `g4_abstracts.json` 作 citation-arm fallback；(3) ⑦ title-only 由 ~54→22（全為 OA-PDF，本沙箱無 PDF parser、本機可解，誠實申報）。教訓＝②c 標「有全文」必須真的抓回摘要/全文（abstract-first 批次），不可只信 OA 旗標。

✅ 已做：⑦ 決定納入單位改為核對『標題＋摘要(方法學)』精確分類（committed `classify_units.py`）。本輪修改：(1) 新增可重用腳本，設計優先序＋NCT/word-boundary 試驗歸併＋對照臂 LABA/LAMA 判別；(2) SEARCH_SPEC 補 ⑦ 分類鐵律。實測：指引 226→27、IMPACT 59→34，核心三合一 vs LABA/LAMA Study 清楚辨識，殘餘據實標待人工。注意：classify_units.py 屬分類輔助、目前無對應 selftest（判別為啟發式、結果本就標 rapid-review 待人工覆核）；審查可評估是否需為其關鍵分支補 selftest。

✅ 已修（Cochrane 紅線）：引文追蹤 ④ 一度「只憑標題丟、不抓摘要」→改為批次抓摘要＋標題＋摘要高敏初篩。本輪修改：(1) ④ 重做＝efetch 200/批＋OpenAlex 50/批批次抓回所有新候選摘要，對全部新候選做標題＋摘要 P∧I∧C 篩，無摘要可抓者才負向排除；(2) 新增 `citation_screen_check.py`＋`check_citation_screen`：g4 逐輪須 title+abstract、title_only_dropped==0、有 ID 時 abstracts_fetched>0；(3) selftest 加「只憑標題丟→FAIL／批次抓摘要篩→通過」；(4) SEARCH_SPEC 補鐵律。實測新增切題 0→19（4 輪收斂）。

✅ 已修：build_stage1_corpus 忠實沿用 ②c 分流（停止重推）。本輪修改：(1) builder 改依 ②c `class` 分流（待評估類→awaiting；有全文/登錄→fulltext_status=have；有摘要→ai_summary_only），不再憑『有無摘要』重推→根治 135 筆 CT.gov 登錄被誤丟 awaiting；(2) awaiting `reason` 以 ②c 明確 reason 為準，不用 channels_exhausted 反推→根治『兩者皆無』被誤標『待人工補全文』；(3) selftest 加兩條回歸（登錄無摘要→candidate/have；兩者皆無 reason 不被竄改）；(4) 重建 _stage1_corpus.json（candidates 6247／awaiting 511），全 gate 綠。

✅ 已修：待評估＝三管道全失敗才成立（補上漏掉的 step2 線上全文）。本輪修改：(1) 新增 `awaiting_channels_check.py`＋`check_awaiting_channels`：待評估須標 abstract_checked∧online_fulltext_checked∧unpaywall_checked∧channels_exhausted，『兩者皆無』須無任何 ID/OA；(2) ②c 重查本案 798 待評估補 step2（Europe PMC inEPMC/isOpenAccess/pmcid＋EPMC 摘要），救回 286→待評估降 512；(3) selftest 加「缺 online_fulltext_checked→FAIL／兩者皆無帶ID→FAIL／三管道全查盡→通過」；(4) SEARCH_SPEC 待評估鐵律改寫為明確三段管道序。

✅ 已修：待評估關責——澄清並機器化「待評估只在 ②c 產生、③ 必須二元」。本輪修改：(1) 新增 `awaiting_stage_check.py`＋`check_awaiting_stage`：③(g3) 出現待評估類字樣＝FAIL；(2) ②c 採「先摘要後全文」效率序，無全文且無摘要才路由待評估；(3) selftest 加「③誤生待評估→FAIL／③全二元→通過」；(4) SEARCH_SPEC 補鐵律並聲明取代先前散見「③待評估」寬鬆措辭；(5) 配合 abstract-first：`check_unpaywall_coverage` 加「有摘要即跳過」（有摘要＝已有可篩內容、②c 不在此抓全文、無『宣稱無全文』之虞；全文留待 ③ 後納入集 verify_have_fetchable），避免與「不對有摘要者抓全文」directive 打架。

✅ 已修（嚴重）：Stop hook 自動守門靜默失效——`gate_guard.py --auto --hook` 無 `--cache` 時 `_find_cache(None)` 在本環境（cache 在 `EBM_Search/cache/<topic>/`、無 run_state、非 Windows，硬編 OneDrive 路徑不存在）一律回 `None` → hook exit 0 dormant，整輪檢索自動守門等同未啟用（gates 僅靠人工 `--cache` 跑到）。這正是使用者觀察到「過程中斷」追查時發現的真 bug（中斷現象本身＝harness context 自動摘要，非 repo bug）。本輪修改：(1) 新增 `_find_active_cache_by_flag()` 掃 `EBM_Search/cache/*/_search_active.flag` 找進行中 cache，插為 `_find_cache` 首要發現法（哨兵旗標＝地真值，不依賴 run_state/env/OneDrive）；(2) selftest 加「旗標 cache 找得到／無旗標回 None 休眠」回歸；(3) 實證修復後 hook 對帶旗標＋壞 g0 的 cache 正確 exit 2、對本案通過的 cache exit 0；(4) SEARCH_SPEC 補「Stop hook 必須找得到 cache」鐵律。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
