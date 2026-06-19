## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【本輪性質】**【初審】第二批守門已實作**（Bug1 四軸覆蓋＋Bug5 嚴格篩逐軸核對＋SPEC ③ 通則改 per-topic）。
（第一批已結案、審查全數通過，commit `6b2071f`。）

**本輪審查範圍：僅以下檔（版控內）：**
- `EBM_Search/scripts/axis_coverage_check.py`（**新增**，Bug1）：每腿 query 對每條 `in_query` 必含軸 ≥1 同義詞命中，否則 FAIL（採審查建議：≥1 存在性、不要求塞滿）。
- `EBM_Search/scripts/strict_screen_check.py`（**新增**，Bug5）：切題須**所有** mandatory_screen 必含軸命中（缺即放水 FAIL）；離題須至少一軸『確認缺』並標明（否則 FAIL）；P∧I 命中而 C 僅 unknown → 應移待評估，逕判離題即 FAIL。
- `EBM_Search/scripts/gate_guard.py`（接線 `check_axis_coverage`/`check_strict_screen` 進 `_all_checks`）。
- `EBM_Search/scripts/selftest_guards.py`（補 4 個 fixture：2 FAIL＋2 正向防誤報）。
- `EBM_Search/SEARCH_SPEC.md`（★第③關通則：「兩軸」改「必含軸由 g0 per-topic 宣告、比較型含 C」＋ P∧I 見、C 未見→待評估配套）。
- （`_fetch_legs.py` g0 寫出 `axes`（P/I/C 同義詞＋in_query/mandatory_screen）屬 run-local、不在版控。）

**契約（g0_strategy.json.axes）：** `{軸:{synonyms:[...],in_query:bool,mandatory_screen:bool}}`。`in_query` 軸＝axis_coverage 在 query 查存在；`mandatory_screen` 軸＝strict_screen 在 ③ 逐軸核對。比較型題 C＝`in_query:false`（搜尋不放入求 recall）但 `mandatory_screen:true`（③ 必核）。

**想被重點看：**
1. `strict_screen_check._state()` 對 axis_hits 值的判讀（present/absent/unknown）是否穩健、會不會把「非空證據字串」誤當命中而漏掉該抓的放水。
2. 離題分支「無任一軸 absent → FAIL」是否過嚴（grossly off-topic 但未逐軸標 no 的紀錄會被要求補標缺哪軸——刻意如此，對齊 SPEC「標明缺哪軸」）。
3. axis_coverage 對 `in_query=false` 的 C 軸不查 query，是否與「比較型題」意圖一致。

**自測：** `python EBM_Search/scripts/selftest_guards.py` → 21 項全綠（含本批新增 2 FAIL＋2 正向防誤報）；fresh-clone 結果見對話回報。
**第三批（未做）：** 分析端 Bug8。貫穿項：SKILL 啟動器「每關自跑 gate 貼 PASS」硬步驟。

---

### 共通根因（8 條幾乎同源）
- **R1 守門在手機/遠端/打包模式不會跑**：專案 Stop hook（`.claude/settings.json` 只掛 search 端 `gate_guard.py --auto --hook`）需要本機 python＋專案目錄；手機遠端/Desktop skill 兩者皆無 → **所有 gate 靜默不觸發**，且似乎連 SPEC 要求的「每關自跑 gate_guard 貼 PASS」也沒做 → 全面退回憑記性 → 漂移。
- **R2 部分關卡根本沒有對應守門**：四軸覆蓋、逐軸切題、⑥驗證覆蓋率、PRISMA/PDF 實體產出、分析端報告格式——目前無機器檢查。
- **R3 已定（使用者 2026-06 回答）：手機遠端模式「能跑 python」** → 採路徑 (i)＋(ii)：「每關自跑 `gate_guard.py` 貼 PASS」＋補齊缺口守門。問題僅在 Stop hook 未於遠端觸發、且未主動自跑 → 修法＝把「自跑 gate」寫成 SKILL 不可跳硬步驟。純 prose 退路 (iii) 降為備註（本環境用不到）。

### 改善總綱
- **(i) 可攜強制**：在 ebm-search／ebm-analysis 兩個 SKILL 啟動器寫入「**每關完成前必須自跑 `gate_guard.py --cache <dir>`（分析端 `verify_all.py`）並貼 PASS 才能往下**」為不可跳硬步驟。
- **(ii) 補齊缺口守門**（能跑 python 時）：新增/擴充下列 check，全部併入 gate_guard、commit＋selftest。
- **(iii) 無 code-exec 退路（本環境用不到，僅備註）**：純對話 skill 時靠 prose 硬指示＋誠實申報。R3 已確認手機端能跑 python，故以 (i)+(ii) 為主。

---

### 逐條診斷 ＋ 改善計畫

**Bug1 四軸聯集搜索未確實執行**
- 規範：⓪四軸展開＋①六腿聯集。現有守門：leg_exhaust（取盡）、strategy_adherence（不加未核准過濾）——**無人檢查 query 是否真的展開四軸同義詞/別名**。
- 計畫：g0_strategy.json 擴充記錄每軸同義詞集；新增 **axis_coverage_check**：每腿 query 對**每條必含軸至少命中 1 個該軸同義詞/別名/代號**（驗『軸存在性』即可，**不**要求塞滿 N 個）；某必含軸 0 命中才 FAIL。SKILL 硬步驟「四軸展開表先寫成 g0_strategy.json 再開搜」。
  - **採審查 🟡 建議（2026-06）**：原「≥N 同義詞」會誤殺——精準高階 MeSH term 或 CT.gov 字數限制時不需塞滿；改為「每軸 ≥1 命中（存在性）」避免過嚴 fail-closed 無法通關。

**Bug2 初篩只篩標題、非標題+摘要**
- 規範：②b 對 title+abstract 高敏初篩。現有守門：stage1_check 要 abstract_status resolved、partition_provenance 要 screened 有 abstract。
- 根因額外發現：廣蒐 fetcher（run-local `_fetch_legs.py`）**根本沒抓 abstract**（PubMed esummary abstract=None）→ 無摘要可篩。
- 計畫：fetcher 在 ②b 前**回填 abstract**（efetch / EuropePMC core abstractText）；強化 stage1_check：abstract_status=have 但內容空 → FAIL。SKILL 明寫「無摘要者不得在 ②b 判離題，應送 awaiting」。

**Bug3 全文取得(②c)與嚴格篩(③)順序搞反**
- 規範：②c 在 ③ 前。現有守門：stage1_check 釘 Stage A/B 邊界，但**無顯式「③不得早於②c」順序檢查**。
- 計畫：新增 **order_check**（併 gate_guard）：見 g3_FINAL_screen.json 卻無 `_stage1_corpus.json`/`g2c_FINAL_content.json`（或其未 PASS）→ FAIL。SKILL 把「②c→stage1_check PASS→才可③」列為不可跳關。

**Bug4 找不到全文/摘要者不應進下一關，應以「待評估」分開**
- 規範：②c＋awaiting。現有守門：**stage1_check 已正確擋下**（fulltext=none∧abstract=none 列 candidate → FAIL；無內容須 awaiting）。
- 計畫：守門已存在且對 → 改善＝**確保手機端也會跑 stage1_check**（見 R1/總綱 i）。SKILL 明寫 awaiting 分流與「進③前必 stage1_check PASS」。

**Bug5 嚴格篩 P∧I∧C 全符才切題，未確實執行、放水**
- 規範：③切題判定。**注意張力**：原 SPEC ★第③關寫「疾病軸∧介入軸」**兩軸**；你要的是比較型題的 **P∧I∧C 三軸**。現有守門：report_check 只查二分/PMID，**不逐軸核對**。
- 計畫：g0_strategy.json 宣告「必含軸」清單（本題＝P,I,C；非比較型題可只 P,I）；③產物 g3 每筆切題者須記 `axis_hits:{P,I,C}` 證據；新增 **strict_screen_check**：verdict=切題卻缺任一必含軸 axis_hit → FAIL。SKILL 明寫逐軸核對、比較型題 C 軸必含。
- **已定（使用者 2026-06 拍板）**：「必含軸」改為由 g0_strategy.json **per-topic 宣告**，且**比較型題納入 C（對照）軸**（本題 triple vs dual＝P∧I∧C）。需同步修改 SPEC ★第③關「只兩軸」通則為「必含軸依 g0 宣告（比較型含 C）」。
- **配套（採審查 ⚪ 建議，2026-06）平衡 recall**：strict_screen_check 與 SKILL 規則須明定——**若摘要可見 P∧I 但看不出 C 軸，不得直接判離題，應移 awaiting 待看全文**（短摘要常省略對照組/SOC）；只有全文/AI 摘要確認確實缺 C 才判離題。避免「未明寫對照」被誤殺。

**Bug6 忘了 Crossref＋PubMed 雙重檢核(⑥)**
- 規範：⑥ xref_verify（Crossref＋PubMed）。現有守門：check_no_retracted 只查撤稿殘留，**無人強制「included/background 每筆都過⑥」**。
- 計畫：新增 **verification_coverage_check**：⑦交接/報告前，included＋background 每筆須在 g6_verified.json 有 verdict，缺漏 → FAIL。SKILL 明寫「未驗證不得進交接包/Zotero/報告表二三」。

**Bug7 第一階段 PDF 漏 PRISMA 流程圖＋進行中 trial 表**
- 規範：⑥ PDF（PRISMA-S＋流程圖＋進行中表）。現有守門：report_check 已查 ongoing_trials 必存在＋二分算式，**但不檢查 PRISMA 流程圖區塊，也不保證真的產出 PDF 檔**。
- 計畫：report_check 增「prisma_flow 區塊必存在且含 identification/screening/included 數」；新增 **pdf_emitted_check**：宣稱 Phase1 完成前，PDF 須實際存在且非空。SKILL 明寫「無 PDF 不算 Phase1 完成」＋PDF 必含節清單。
  - **採審查 ⚪ 建議（2026-06）**：pdf_emitted_check 路徑解析**須沿用報告產生器同一邏輯**——讀 `config/settings.yaml` 的 `report.pdf_output_dir`，留空則回退 Windows『文件』已知資料夾，**不得寫死路徑**，以免誤報。

**Bug8 最終階段 PDF（EBM_Analysis 評讀報告）完全不照規範**
- 規範：ANALYSIS_SPEC 最終報告。現況：分析端**已有** verify_all/audit_consistency/prisma_audit/validate/build_reports，**但未掛進 Stop hook、手機端不跑**。
- 計畫：(a) 分析端比照 search 端做一個 `gate_guard`（或擴 .claude/settings.json Stop hook 也跑分析端 `verify_all.py --hook`）；(b) 確認/補 analysis 報告格式 check（固定章節/SoF 表/GRADE 欄/證據體對帳）；(c) ANALYSIS_SPEC 明寫必含節＋「無合規 PDF 不算完成」。**此條需先細讀 ANALYSIS_SPEC＋tools 才能定稿，列為第二批。**

---

### 實作批次建議（待核准後動工）
- **第一批（搜尋端，風險低、可立即）**：order_check、verification_coverage_check、pdf_emitted_check、report_check 增 PRISMA、stage1 abstract 內容檢查、fetcher 回填 abstract。各自 commit＋selftest＋fresh-clone。
- **第二批（需你拍板策略）**：axis_coverage_check＋g0 軸同義詞落地、strict_screen_check＋「必含軸 per-topic（比較型納 C）」改 SPEC。
- **第三批（分析端）**：Bug8，先讀 ANALYSIS_SPEC/tools 再定稿。
- **貫穿全批**：SKILL 啟動器加「每關自跑 gate 貼 PASS」硬步驟（i）；視 R3 答案決定是否補 prose-only 退路（iii）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（Batch-2 無待修問題，全數通過。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

【Batch-2 複審（commit 待補）】
- ✅ 已修：🟡 strict_screen_check `_state()` fallback「非空字串→present」放水漏洞——AI 填自然語言（如「未提及對照組」）會被誤判命中→假切題。**改：不認得的自由文字一律 `unknown`（不得 present）**，並支援 `{status,evidence}` 結構；契約寫進 SPEC③（值須明確 token 或 {status,evidence}）。+selftest 補回歸（自由文字當證據→FAIL）＋正向改用明確 token。比 SKILL 提醒更硬（機器擋）。
- ✅ 已確認（無需改動）：⚪ 離題分支「至少一軸 absent」對齊 SR「剔除原因＝第一個不符 PICO 軸」，不過嚴。
- ✅ 已確認（無需改動）：⚪ `in_query` 與 `mandatory_screen` 脫鉤設計契合真實 EBM 檢索意圖（C 軸不入 query、留 ③ 核對）。
- ✅ 已確認（無需改動）：⚪ Batch-2 實作完整、edge case 處理精細、selftest 有效，可進 Batch 3。

（Batch-1 與計畫初審之處理歷史已隨 commit 6b2071f／ac5deef 保存。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
