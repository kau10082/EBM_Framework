## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊＝把兩個「使用者手動抓到的缺失」轉成機器 gate（SR filter 三成分強化 ＋ ⑤b 只消費切題）。

**本輪審查範圍：僅以下檔案（請只讀這幾個檔的當前內容，勿審其他檔）**
1. `EBM_Search/scripts/sr_filter_composite_check.py`（SR filter 三成分）
2. `EBM_Search/scripts/gate_guard.py`（新增 `check_units_only_concordant`、`check_no_unverified`；
   `check_no_retracted` 改相容 verdict/verify 兩鍵；皆已註冊；其餘不動）
3. `EBM_Search/scripts/selftest_guards.py`（SR 三成分 ＋ ⑤b 只消費切題 ＋ 無法驗證剔除 三組回歸）
4. `EBM_Search/SEARCH_SPEC.md`（第 107 行附近「★★ 三成分強化」一段）

**缺失③（本輪新增 gate）：無法驗證(UNVERIFIED) 未與撤稿同等剔除**
- 使用者定版：**『無法驗證』(⑤a Crossref／PubMed 查不到存在性、或完全無 ID 可查證) 要跟撤稿(RETRACTED)一樣剔除、不可入下一關**（⑤b／交接包／報告／Zotero）。先前只把無 ID 項『移背景』＝錯，應整筆排除。
- 修法：`gate_guard.check_no_unverified`（對稱 `check_no_retracted`）——g6_verified 標 UNVERIFIED 者，以 pmid/doi/uid 比對 g7_units／seed／報告／Zotero payload，命中即 FAIL。NCT 登錄＝registry-verified、不誤殺。
- 另把 `check_no_retracted` 的 verdict 判定改相容 `verify` 鍵（⑤a 寫 verdict、報告器寫 verify，避免鍵名不一致讓撤稿/無法驗證漏網）。
- 已註冊進 `_all_checks`，`selftest_guards` 加一負向（UNVERIFIED 當背景留存→FAIL）＋一正向（全 VERIFIED→通過）。

---

【初審・第二塊（EBM_Analysis 端）】偏誤風險『工具↔設計』三路徑路由（轉成機器 gate）。

**本塊審查範圍：僅以下檔案**
5. `EBM_Analysis/schema/phase2_triage.json`（新增 `rob_tool` enum、`robins_i` 七領域物件、`definitions.robins_domain`、track→tool 的 allOf 條件）
6. `EBM_Analysis/tools/validate.py`（新增 `check_p2_rob_routing` ＋ 在 p2 路徑接上）
7. `EBM_Analysis/tools/selftest_analysis_guards.py`（新檔；9 條雙向斷言）
8. `EBM_Analysis/guardrails/robins_i.md`（新檔；ROBINS-I 七領域＋目標試驗＋本題干擾因子＋Low 警語＋GRADE 映射）
9. `EBM_Analysis/phases/02_triage.md`（guardrails 增列 rob2/robins_i/amstar2；步驟 4 加 rob_tool 路由）
10. `EBM_Analysis/guardrails/amstar2.md`（補 16 題/透明表格/RCT+NRSI 混合/演算法機器看守）

**缺失⑤（使用者定版）：SR/MA 品質 AMSTAR 2 算法做成機器 gate**
- 規則：16 題、7 題關鍵(2,4,7,9,11,13,15)；整體信心＝`>1關鍵→critically_low｜1關鍵→low｜0關鍵且>1非關鍵→moderate｜0關鍵且≤1非關鍵→high`；Cochrane 要求透明表格（每題評分＋理由＋整體評等）。
- 修法：schema `amstar2` 物件（items[16]/critical_flaws/noncritical_weaknesses/overall_confidence/basis/search_recency/robis_concern），track A allOf 必帶 `amstar2`＋`protocol_completeness`＋`rob_tool=amstar2`；`validate.py check_p2_rob_routing` track A 分支驗：整體信心↔瑕疵數演算一致、items 關鍵題 no 數＝critical_flaws、basis 非空。
- 自測：`selftest_analysis_guards.py` 擴為 **20 條**（含 AMSTAR2 算法不一致/逐題不符/缺 basis 等負向＋正向防誤報）。

**缺失⑥（使用者定版）：三路徑對稱防『漏填/遺失/飄移』——補齊 RoB 2 結構 ＋ 起始確定性防飄移**
- 問題：RoB 2(track B) 原僅檢查 `rob_tool=rob2`，無五領域結構/完整性/木桶檢查，與 AMSTAR2、ROBINS-I 不對稱（會漏填/遺失/飄移）。
- 修法：
  - schema 加 `rob2` 物件（五領域 randomization/deviations/missing_outcome/measurement/selection_reported，judgement∈low/some_concerns/high，+overall+選填 signalling/effect_of_interest）＋`definitions.rob2_domain`；track B allOf 必帶 `rob2`＋`rob_tool=rob2`（**防遺失**）。
  - `validate.py check_p2_rob_routing`：track B 五領域不得缺（**防漏填**）、overall 木桶原則不得優於最不利領域（**防飄移**）。
  - 新增**起始確定性↔軌道**防飄移（涵蓋三路徑）：A/B→high、C(NRSI)→low 或 high(ROBINS-I)、low(case report 等)→very_low；偏離 FAIL。
  - `guardrails/rob2.md` 補 Phase 2 結構化落地與機器看守段。
- 三路徑現對稱：RCT→RoB2、NRSI→ROBINS-I、SR/MA→AMSTAR2 皆「結構必填＋木桶/演算法一致」機器防護。
- 自測：`selftest_analysis_guards.py` 擴為 **25 條**（新增 RoB2 遺失/漏填/木桶 ＋ grade_start 飄移 等）。
- 仍誠實標記：跨階段『Phase 2 偏誤結果忠實帶入 Phase 3 GRADE 領域1（防跨關遺失）』尚未加機器 gate（待 Phase 3 檔產出後可於 selfcheck_consistency 補 C 條）。

**缺失④（使用者定版，已強化）：回顧性/非隨機研究(NRSI) 須用 ROBINS-I，不可用 RoB2；三路徑各自評讀再整合**
- 規則（Cochrane Handbook Ch.25）：RCT→RoB2、**NRSI→ROBINS-I**、SR/MA→AMSTAR2；NRSI GRADE 起始低。
- ROBINS-I 細節落地（依使用者補充）：
  - **前置作業**：`effect_of_interest`(assignment/adherence)、`confounders_considered`(非空)、`cointerventions`——皆機器強制。
  - **七領域**＋時間軸三階段＋信號問題作答(Y/PY/PN/N/NI，`domains.<d>.signalling[]`)。
  - **四級**(low/moderate/serious/critical)＋ NRSI 判 low 極罕見(須 `low_justification`)。
  - **木桶原則**：`overall` 不得優於最不利領域（任一 serious→至少 serious、任一 critical→critical）。
  - **critical → 排除於統合**：`overall=critical` 須 `meta_analysis_action=exclude`。
- 機器看守 `validate.py check_p2_rob_routing`（接 p2；verify_all 自動帶）：拿錯工具／缺七領域／overall=low 無理由／
  過半 no_information 充數／**木桶原則違反**／**critical 未排除**／**缺前置作業(effect_of_interest、confounders)** → 各自 FAIL。
  schema(`phase2_triage.json`) 另以 allOf 強制 `rob_tool`↔`track`＋track C 須帶 `robins_i`，並加 `signalling`/`meta_analysis_action`/前置欄位。
- 自測：`selftest_analysis_guards.py` **14 條全綠**（9 負向＋5 正向防誤報）。
- 想被重點看：(a) 木桶原則 RANK 比較是否正確涵蓋 no_information（目前 no_information 不計入 floor、另以「過半 NI」擋充數）；
  (b) critical→exclude 僅在 phase2 標記，Phase3/4 SoF 是否需再補「critical 不得出現在池化結果」整合 gate；
  (c) 三路徑「整合到最後結果」目前在 phase2 路由＋robins_i.md 映射＋02_triage 步驟4（規格＋schema 層），Phase3/4 整合尚未加機器 gate，是否需補。

**缺失②（本輪新增 gate）：⑤b 誤把『離題』當『背景』灌進分析**
- 使用者定版：**『離題』(③ 清單三排除) 與『全文及摘要皆無/待評估』都等同丟棄、不入後續分析（corpus_seed）**；
  背景＝『切題中非核心』者，**不是離題**。先前實跑誤把 ③ 的 274 筆離題當背景餵進 ⑤b，使語料由 561 切題膨脹成 835。
- 修法：`gate_guard.check_units_only_concordant`——g7_units 每筆 uid 必須是 ③ `verdict=='切題'` 或 ④ 新切題；
  出現 ③ 判 `離題/全文及摘要皆無` 的 uid → FAIL。已註冊進 `_all_checks` 與 `selftest_guards`（一負向＋一正向回歸）。
- fresh-clone 自測：見下方對話（`selftest_guards.py` 全綠，含本 gate 兩條新測）。

**背景／為何改**：執行 benralizumab vs mepolizumab 檢索的 Phase ⓪ 時，使用者人工抓到我寫的 `EuropePMC-SR` 過濾器
不符其定版要求「出版類型(PubType) ＋ 主題詞(MeSH/Emtree) ＋ 自由文字(Title/Abstract)」三成分。追因發現
**既有 gate 太鬆、放行了兩種缺失**，故依 AGENTS.md「使用者人工抓到的缺失優先轉成機器 gate」把它修進守門：
- 缺失①：gate 把 EuropePMC/OpenAlex 的『裸詞』當合格自由文字，但這些 DB 預設搜**全文**，裸詞＝全文泛提及噪音、非 Title/Abstract。
- 缺失②：gate 對 MeSH-capable DB（EuropePMC 索引 MEDLINE）未強制 MeSH 成分，致只有 PubType＋自由文字也過關。

**這次改了什麼（逐檔）**：
- `sr_filter_composite_check.py`：
  - `_has_freetext()` 改為**只認欄位綁定**的 Title/Abstract（`[tiab]`/`TITLE:`/`ABSTRACT:`/`title_and_abstract.search:`），
    移除「裸詞 fallback」（連同不再需要的 `_is_bracket_dialect`）。
  - 新增 `_has_mesh()`（偵測 `[mesh]/[mh]/[majr]`、`MESH_TERM:`、`mesh:`、Emtree）＋ `_is_mesh_capable(name, meta)`
    （DB 名判定 + `mesh_unavailable:true` 誠實豁免）＋ `MESH_CAPABLE_DB` 清單、`_norm_name()`。
  - `check()` 改為逐成分核對：缺欄位綁定自由文字 / 缺控制詞彙 / （MeSH-capable 而）缺 MeSH → 各自 FAIL，訊息明確。
  - 更新 module docstring 說明三成分與欄位綁定規則。
- `selftest_guards.py`：更新 SR-composite 測試區——
  - 修正兩個原『裸詞/無 MeSH 仍應通過』的防誤報案（它們正是被放行的鬆綁行為）。
  - **新增兩條負向回歸**（對應使用者抓到的缺失①②）：MeSH-capable DB 用裸詞自由文字＝FAIL、MeSH-capable DB 略過 MeSH＝FAIL。
  - 新增三條正向防誤報：EuropePMC 三成分（PubType＋MeSH＋欄位綁定）通過、PubMed 方括號三成分（[pt]＋[mesh]＋[tiab]）通過、
    OpenAlex（`mesh_unavailable`）豁免 MeSH＋欄位綁定通過；AI 合成腿維持豁免。
- `SEARCH_SPEC.md`：第 107 行附近新增「★★ 三成分強化」一段，使規格與強化後的 gate 一致（避免 spec 範例與 gate 矛盾）。

**fresh-clone 自測結果**：見下方對話回報（`selftest_guards.py` 在新 clone 全綠）。

**想被重點看 / 我自己不確定的點**：
1. `_has_freetext` 移除裸詞 fallback 後，是否對「真的預設只搜 title/abstract 的 DB」過嚴？（我判斷本框架腿集合
   PubMed[方括號]/EuropePMC[全文]/OpenAlex[含全文] 皆需欄位綁定，故移除 fallback 是對的；若日後加入別的 DB 需再評估。）
2. `_is_mesh_capable` 以 DB 名子字串判定（pubmed/medline/europepmc/epmc/embase/ovid/cochrane/central）＋ `mesh_unavailable` 旗標豁免，
   是否夠穩健？（`_norm_name` 去除非英數，故 "Europe PMC-SR"→"europepmcsr" 可命中 "europepmc"。）
3. `_has_mesh` 的 `mesh:` 偵測用 `(?<![a-z])mesh\s*[:=]`，是否可能誤命中（如某 DB 有別義的 mesh 欄位）？目前框架未用，風險低。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
