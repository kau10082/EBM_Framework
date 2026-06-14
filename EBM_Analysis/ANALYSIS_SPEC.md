# EBM 評讀規格（ANALYSIS_SPEC）—— 由 `ebm-analysis` 啟動器載入

> **這是 EBM_Analysis 的評讀規格正本**，不是可獨立啟動的 skill（已無 `/ebm`）。
> 由框架啟動器 `EBM_Framework/.claude/skills/ebm-analysis/SKILL.md` 在「從 EBM_Search 接力」或「封存／歸檔」時讀取並依此執行。
>
> **路徑約定**：本規格內所有相對路徑（`phases/`、`guardrails/`、`schema/`、`tools/`、`cache/`、`inputs/`、`outputs/`、`manifest.yaml`）**相對於 `EBM_Analysis/`**。Claude Code 的工作根＝`EBM_Framework`，故實際執行時一律**加前綴 `EBM_Analysis/`**（例：`python EBM_Analysis/tools/validate.py …`、讀 `EBM_Analysis/phases/00_triage.md`）。個人/機敏設定見 `config/settings.yaml`（根）。

# EBM 評讀引擎（Claude 即引擎）

**核心模型：你（Claude）就是運算引擎。不呼叫 Anthropic API、不跑外部 LLM 程序。**
規格檔（相對 `EBM_Analysis/`；執行時加前綴）：
- `phases/0N.md`：每階段指令（frontmatter 列出該階段要套用的 guardrails 與 output_schema）
- `guardrails/*.md`：20 條護欄全文
- `schema/*.json`：每階段輸出的 JSON Schema（完整性強制依據）
- `tools/`：**無 API** 的確定性輔助（PDF 抽文字、schema 驗證、報告渲染）

## 入口守則（單一入口：EBM_Search）
本 skill 是 **EBM_Framework 管線的下游**，**不獨立冷啟動**。允許進入的情況只有：
1. **從 EBM_Search 接力**：使用者回「繼續（進入 EBM 分析）」，或指向／偵測到含 `_corpus_seed.json` 的交接包 → 走下方「從 EBM_Search 接力」。
2. **封存／歸檔**：見文末「封存／歸檔既有分析」（此功能不需交接包）。

**若使用者未經 EBM_Search 檢索就要 Claude 直接評讀 PDF（或打 `/ebm`／說「以EBM方式分析」）**：不要從零跑 Phase 0–4。改提醒——「本框架的證據必須先經 EBM_Search 檢索＋交叉驗證（去幻覺、查證來源、定必含軸），請先用 **EBM_Search** 對主題做檢索；收尾時回『繼續』即接力進入評讀」。除非使用者明確堅持跳過檢索，才在告知侷限（來源未查證）後便宜行事。

## 環境模式
- **Claude Code／Cowork（有檔案/終端）＝完整模式**：讀 spec 檔、寫 `cache/*.json`、用 `tools/validate.py` 驗證、用 `tools/build_reports.py` 渲染。
- **Claude Chat（無檔案）＝行內模式**：請使用者貼上 PDF/文字；你照同一套 phases+guardrails+schema 在對話內逐階段產出 JSON 與報告，並自我對照 schema 必填欄逐項檢查（無檔案可驗證時，靠你嚴格自檢）。

## 從 EBM_Search 接力（交接層）

當使用者是**從 EBM_Search 接力**（在 Search 收尾的「是否繼續進入 EBM 分析？」回了「繼續/是」），或手上有一個含 `_corpus_seed.json` 的交接包資料夾（由根 config `report.fulltext_dir` 指定，現＝`OneDrive\文件\EBM_Framework\fulltext\<題目_日期>\`）：

1. **取得交接包資料夾路徑**。若使用者沒明講，讀根 `config/settings.yaml` 的 `report.fulltext_dir`、取其下最新的 `<題目_日期>\`（勿寫死含使用者名的路徑）；確認後使用。
2. **匯入**（完整模式，確定性工具；從 EBM_Framework 根執行）：
   ```powershell
   python EBM_Analysis/tools/ingest_seed.py --seed-dir "<交接包資料夾>"
   ```
   它會把交接包指向的全文 PDF **複製進 `inputs/`**（檔名 = `<paper_id>.pdf`），並產出**預填的 Phase 0 草稿** `cache/_corpus.draft.json`（review question 雛形＋每篇 relevance/role/grade_track 建議值，同一試驗多報告已自動 `overlap_with`）。先看它回報的「複製 N／缺檔／無 PDF」與分流預填。
3. **接著走 Phase 0（不是跳過！）**：把草稿攤給使用者覆核——**review question（注意 EBM_Search 不定 O 軸，O 需在此補定）＋逐篇 relevance/role/grade_track**。這些都只是 EBM_Search 的**建議**，要使用者確認或修正。確認後把草稿存成正式 `cache/_corpus.json`、`python tools/validate.py p0 cache/_corpus.json`，再照常進 Phase 1。
   - **無 PDF 者**（背景/僅 AI 合成摘要）預填為 `light_summary`；若使用者要對其跑 full，須先人工補全文 PDF 進 `inputs/`。
4. 行內模式（無終端）：依同一映射規則（見 `../INTEGRATION.md`）手動把交接包內容讀成 Phase 0 草稿，再覆核。

> 交接層只是**省去手動搬 PDF＋重定 PICO/分流**；Phase 0 的斷點覆核照舊，建議值非定稿。

## 執行流程（逐階段、逐篇、每階段一個斷點）

階段順序：`⓪ triage_corpus → ① extract → ② triage → ③ grade → ④ output`。**一次只做一個階段**，跑完摘要、**詢問使用者是否續跑**。

**⓪ 一定先做 corpus 分流**（≥2 篇時）：讀 `phases/00_triage.md`＋`schema/phase0_corpus.json`，定 review question、判每篇相關性/角色/grade_track，MA 記 included_trials。寫 `cache/_corpus.json`、驗證、摘要給使用者確認。**之後 Phase 1–4 只對 `grade_track ∈ {full, targeted_harms}` 的文獻跑**；light_summary 另出背景清單、none 排除。誠信查核（Phase 2）**一律以 WebSearch 實查撤稿/勘誤**（有網路即查、不可略過；附 PMID/DOI；僅真的無網路才退標「未驗證」）。

**全文不可得時的固定補救** [registry_backfill]：若某篇只有摘要/AI 合成摘要，或缺 RoB/各臂 N/AE/CI → 抽 NCT/EudraCT/PROSPERO 號，查 **ClinicalTrials.gov API v2**（`https://clinicaltrials.gov/api/v2/studies/<NCT>`）、PROSPERO、FDA/EMA 補齊，補來源於 source_locators 分列、跨來源不符標 [Conflict detected]；補不到 RoB → 確定性封頂。Phase 1 須標 `data_source`。

對每個階段 `N`：
1. **載入規格**：讀 `phases/0N.md`，依其 frontmatter 讀所列的 `guardrails/*.md` 與 `schema/phaseN.json`。
2. **逐篇執行**：對每篇文獻（PDF 用 Read 工具讀，或先 `python tools/pdf_to_text.py`），依階段指令＋護欄產出**符合該 schema 的 JSON**。
   - 完整模式：寫到 `cache/{paper}.pN.json`，然後 `python tools/validate.py pN cache/{paper}.pN.json` → 若報缺欄，補齊重存（這就是「不漏護欄」的檢查點）。
   - 行內模式：直接輸出 JSON，並逐項自檢 schema 必填欄。
3. **階段報告 ＋ 斷點**：摘要本階段結果（抽取的 PICO/N、軌道與起始確定性、各 outcome 的 GRADE），用 AskUserQuestion 或直接問「續跑下一階段？」。得到同意才進下一階段。
4. 全部階段完成後（完整模式）`python tools/build_reports.py` → `outputs/{paper}.report.md`、`synthesis.md`、`ledger.csv`；行內模式直接輸出報告＋統合。

## 不漏護欄／不自簡化（硬性）
- **phase3 最關鍵**：對**每個 outcome**，五下調（偏誤風險／不一致性／間接性／不精確／發表偏誤）＋三上調領域**逐一**給 `verdict`＋`rationale`，缺一即 schema 驗證失敗 → 補齊。
- 觸發到的護欄一定要在輸出留下結果，不可省略。各護欄觸發條件見 `manifest.yaml` 的 `guardrails:` 區。
- 報告一律由 JSON 渲染，不憑印象寫。

## 護欄速查（全文見 guardrails/，此處僅觸發提示）
| 護欄 | 觸發 |
|---|---|
| no_effect_interpretation | CI 跨無效線 |
| data_honesty / outcome_nature | 永遠（抽取時） |
| integrity_check | 每篇分級前（撤稿/勘誤） |
| protocol_completeness | 來源為 SR/MA |
| grade_assessment | 每個 outcome（phase3 框架） |
| rob2 | RCT 核心結果 |
| heterogeneity | outcome 來自 MA |
| coi | 有 COI/Funding 章節 |
| effect_measure | 讀已算好效應量 |
| nonreporting | 評讀 SR/MA 缺失證據 |
| surrogate / harms | 核心結論建於替代結果／未充分評 harms |
| vote_counting / overlap_indirect | 統合 ≥2 篇 |
| swim | SR 無 MA／敘事綜整 |
| nma | 含 NMA／間接比較訊號 |
| computation_check / output_selfcheck / wording_template | 輸出階段 |

## 封存／歸檔既有分析
當使用者說「封存／歸檔這次分析」「把這次存起來」「歸檔成 XXX」「封存後清空準備下一個主題」時：
1. **確定主題名稱（slug）**：用使用者給的名字（如 `DPP1-bronchiectasis`）；沒給就依 `cache/_corpus.json` 的 review_question 提一個並請對方確認。
2. **問兩件事**（用 AskUserQuestion 或直接問，得到答覆才執行）：
   - **要不要清空？** 清空＝封存後清除 `cache/`、`outputs/`（保留 .gitkeep），騰出空間給下一個主題；不清空＝保留工作檔。⚠️ 清空前務必確認（封存是先複製再清，資料不會丟，但仍要問）。
   - **要不要產生來源清單（sources.md）？** sources.md＝回顧問題＋各文獻角色／引用／註冊號，自 `_corpus.json` 生成。
3. **執行**（從 EBM_Framework 根）：
   ```powershell
   python EBM_Analysis/tools/archive_run.py <slug> [--clear] [--no-sources] [--with-text] [--date YYYY-MM]
   ```
   - 要清空→加 `--clear`；不要來源清單→加 `--no-sources`；要連抽取全文→加 `--with-text`。
4. **回報**：封存到 `runs/<日期>_<slug>/` 的 deliverables／audit 各幾檔、有無 sources.md、是否已清空。提醒 `runs/` 已 gitignore（含原文引用片段，留本機）。

## PDF 輸出（若使用者要 PDF 版報告）
用 reportlab ＋ Windows CJK 字型（微軟正黑 `C:/Windows/Fonts/msyh.ttc`，subfontIndex=0；後備 `STSong-Light`）；SoF 表放橫向頁。
**★ 所有中文 ParagraphStyle 必設 `wordWrap='CJK'`**：否則 reportlab 把中文當無空格長字、遇標點提前斷行，表格會「不滿一行就跳行」變得臃腫。
**★ 禁用 emoji／彩色符號字符**：微軟正黑沒有 emoji 字形，會渲染成方格（□）。常見地雷：`⚠️ ✅ ❌ ⭐ ⚡ 🚫`（含變化選擇符 U+FE0F）。
- 要表達警示／提示 → 改用**文字標記**（如「【注意】」「※」）或彩色底框，不要用 emoji。
- 安全可用（微軟正黑有）：`● ○ • → ① ② ③ ≈ – —`、GRADE 用「高確定性 ●●●●／●●●○／●●○○／●○○○」。
- 產出後務必把頁面渲染成圖目視，確認無方格再交付。

## 機敏
`inputs/`、`cache/`、`outputs/` 已被 `.gitignore`（版權 PDF／可能 PHI），不進公開 repo。
