---
name: ebm-framework
description: >-
  實證醫學（EBM）端到端助手：先把文獻找齊、用 Crossref／PubMed 交叉驗證去幻覺，再做 GRADE 證據評讀，
  最後出報告。**整條管線一律從檢索開始**，由 Claude 本身為運算引擎（不呼叫任何外部 LLM API）。
  當使用者說「EBM分析」「實證分析」「實證醫學分析」「對〈某主題／某藥〉做 EBM 分析」「幫我查文獻」
  「建立可信引用清單」「幫我查證這個主張」「驗證這些引用是不是真的」「交叉驗證 Crossref PubMed」，
  或要為 EBM 評讀／衛教文／報告建立經查證的參考文獻時，啟動此 skill。也處理 EBM 分析的「封存／歸檔」。
  An end-to-end evidence-based-medicine assistant: find the literature, cross-verify it against
  Crossref/PubMed to remove hallucinations, then run a GRADE appraisal and produce a report.
---

# EBM_Framework — 實證醫學端到端 Skill

把兩段接成一條龍：**EBM_Search（檢索＋交叉驗證）→ EBM_Analysis（GRADE 評讀）**，中間用交接包 `_corpus_seed.json` 銜接。**運算引擎＝Claude 本身**，不呼叫外部 LLM API。

## 資源位置（本 skill 資料夾）
所有檔案都在本 skill 資料夾底下；用 `${CLAUDE_SKILL_DIR}` 取得其絕對路徑，腳本一律以它為前綴呼叫：
- **檢索引擎規格（完整）**：`${CLAUDE_SKILL_DIR}/EBM_Search/SEARCH_SPEC.md`
- 檢索腳本：`${CLAUDE_SKILL_DIR}/EBM_Search/scripts/`（`xref_verify.py`／`journal_quartile.py`／`zotero_import.py`／`fulltext_fetch.py`／`build_corpus_seed.py`／**`build_search_report.py`＝檢索 SR 報告 PDF 正規產生器**：讀 `_search_report.json` 渲染、字形淨化、不硬編題目，與 GRADE 端 `_build_pdf.py` 對稱）
- 交接契約：`${CLAUDE_SKILL_DIR}/EBM_Search/references/corpus_seed_schema.json`
- **評讀引擎規格（完整）**：`${CLAUDE_SKILL_DIR}/EBM_Analysis/ANALYSIS_SPEC.md`
- 評讀規格檔：`${CLAUDE_SKILL_DIR}/EBM_Analysis/{phases,guardrails,schema}/`、`manifest.yaml`
- 評讀工具：`${CLAUDE_SKILL_DIR}/EBM_Analysis/tools/`（`ingest_seed.py`／`validate.py`／`build_reports.py`／`pdf_to_text.py`／`archive_run.py`／`absrisk.py`）
- 整合契約與流程：`${CLAUDE_SKILL_DIR}/INTEGRATION.md`

## 設定（機敏／個人路徑）
複製 `${CLAUDE_SKILL_DIR}/config/settings.example.yaml` 成 `${CLAUDE_SKILL_DIR}/config/settings.yaml`（**不進版控／打包**），填入 Crossref email、Zotero 金鑰、輸出路徑等。腳本以 `default_settings_path()` 解析：環境變數 `EBM_CONFIG` ＞ `<skill>/config/settings.yaml` ＞ 內建預設。金鑰建議改走環境變數（`ZOTERO_API_KEY`／`CROSSREF_MAILTO`／`EBM_CONFIG`）。

> **執行期資料夾（重要）**：評讀的 `inputs/cache/outputs/runs` 由 `analysis.work_dir` 決定（env `EBM_WORKDIR` 可覆寫）。**以打包 skill 安裝使用時務必把它設成你「文件」夾下的工作夾**（如 `…\EBM_Framework\work`），否則 run 資料會寫進安裝包資料夾、重匯入 skill 時被一起洗掉。留空才退回寫到本資料夾內（Claude Code 專案模式）。

## 需要的 MCP（檢索用）
檢索階段需連上 **Consensus**、**PubMed** MCP，建議再加 **OpenEvidence**（`htlin222/openevidence-mcp`，瀏覽器登入、免 API key）。ClinicalTrials.gov／OpenAlex／Europe PMC 由腳本直接走公開 API、免金鑰。各腿會回報狀態，沒連到的標「跳過」。評讀階段不需要任何 MCP。

---

## 執行流程（分階段、逐關停頓）

### Phase 1 — 檢索（★硬性逐關停頓；嚴禁跳關、嚴禁一次跑多關、嚴禁提早驗證）
**Phase 1 切兩段、契約交班（v0.21）**：**Stage A＝關 ⓪–②c（廣搜→去重→高敏初篩→全文/摘要取得性）** → 以 `build_stage1_corpus.py` 寫出交接契約 `_stage1_corpus.json`（每筆 metadata＋全文/摘要狀態＋取得管道；無內容者入 awaiting＝待評估），經邊界硬 gate `stage1_check.py` PASS（全文狀態 resolved、待評估不混入候選、每腿取盡）才進；**Stage B＝關 ③–⑦（嚴格篩→引文追蹤→交叉驗證→決定納入單位）只讀該 JSON**，輸出 `_corpus_seed.json`。此切割把「待評估屬哪關」釘成磁碟邊界、降分心強遵從。**每關報告前自己先 `gate_guard.py --cache <dir>` 並貼 PASS。**

完整規格讀 `EBM_Search/SEARCH_SPEC.md`。**下列停頓點是硬性規定**：每一關都必須「**做完該關 → 停下來逐項報告 → 等使用者明確確認**」才進下一關。**嚴禁合併關卡、嚴禁跳關、嚴禁在廣蒐／篩選階段就做 Crossref 驗證、嚴禁在篩選收斂前就建交接包。**

0. **搜尋策略報告**：先把四軸展開（縮寫↔全文／慣稱↔生化·基因別名／類別↔藥名(INN)↔代號／疾病縮寫↔全文）、各腿要送的**實際 query 字串**、**必含連言軸（＝納入/切題定義）**攤出來。**本關只定義「要搜什麼、什麼算切題」，不列『排除準則』、不做任何排除**——排除/篩選是第②關初篩與第④關離題篩才做的事（高敏感、寧留勿殺）。**先報告策略 → 停 → 等使用者確認 → 才開始廣蒐。**
1. **廣蒐**：依確認後的策略，四軸展開 → 六腿多源檢索（最大廣度、翻頁取盡）→ 跨腿去重聯集。**本關不做任何主旨篩選、不做 Crossref 驗證。**　→ 停，逐腿報告（命中／實際 query／限制／是否取盡／聯集數）。
2. **初步篩檢**（高敏感、寧留勿殺）：只剔「某核心軸明顯離題」者，模糊一律先留。　→ 停，報告保留 N／剔除 N（各缺哪軸）。
3. **搜尋全文**：對初篩保留者抓合法 OA 全文，分三類：有全文／只有摘要（無全文）／兩者皆無。**「兩者皆無」（試過所有來源仍無全文且無摘要）者一律歸「待評估研究」（studies awaiting classification）——不排除、不進主旨篩選的納入/排除。** 灰文獻或抓不到內文**不得**作為排除理由（Cochrane MECIR C28/C35）；留待正式發表或補到內容再定案。
   - **抓內容鐵律**：判「兩者皆無」前必須「實際嘗試抓內容」（不得用「有標題＝摘要一定取得到」的假設）：依序試 OA 全文 → PubMed／EuropePMC 摘要 → OpenAlex `abstract_inverted_index` → Crossref `abstract` → Consensus／OE AI 合成摘要。**全部試過仍取不到，才算「兩者皆無」。**
   - 欄位稀疏（截斷標題、缺 DOI）不得作為判定依據，須先補欄再判。
   　→ 停，報告有全文 N／只有摘要 N／待評估研究 N。
4. **全文離題篩檢**（嚴格）：逐篇核對必含連言軸，**核對依據必須是「該篇的全文（有全文者）或其摘要（AI 合成／期刊摘要）」——嚴禁只憑標題判定。** 故進本關前須先把每篇的全文或摘要取齊（標題不足以判斷有無某軸）。判定：兩軸俱全→納入；可確認缺某軸→排除（標明缺哪軸）；內容確實取不到而無法判→待評估（寧留勿殺）。　→ 停，報告納入／排除（各缺哪軸）／待評估。
5. **引文追蹤至收斂**（滾雪球、逐輪，某輪新增＝0 才停）。　→ 停，逐輪報告（種子／反向·正向／新增）。
6. **交叉驗證（標記去幻覺）**：引文追蹤收斂後**立刻**做（**不要拖到最後**）。逐篇查 Crossref＋PubMed，標記 **VERIFIED／UNVERIFIED／RETRACTED**＋證據類型＋次級分析加註。**此關只是替每篇文獻「貼真實性標記」，永不作為剔除標準**——查無（UNVERIFIED）多半是非索引刊物或書目小誤，標「待補／未驗證」即可，**不得據此刪文**；唯撤稿（RETRACTED）另行處置。腳本 `python ${CLAUDE_SKILL_DIR}/EBM_Search/scripts/xref_verify.py …`。會議摘要請標 `doc_type=conference_abstract`。　→ 停，報告驗證分布＋查無清單。
7. **決定納入單位**（驗證標記後、補全文之前）：把納入候選定案分流——**原始研究**（以 **Study 為單位**，同一試驗多份報告連結成一筆，走 GRADE）／**背景參考**（MA/SR/指引/綜述/評論，不計入原始研究數、僅作對照）／**待評估研究**（會議摘要、無內容）。**一定先決定，再叫使用者補全文。**　→ 停，報告分流（哪些 Study 進分析、哪些 MA 當背景）。
8. **人工補全文**：只針對「決定後的原始研究＋關鍵背景 MA」中**無 OA 全文者**。做兩件事：(i) **務必明確印出補全文資料夾的完整絕對路徑**（＝config `report.fulltext_dir`／`<題目_日期>`／，例如 `C:\Users\…\OneDrive\文件\EBM_Framework\fulltext\<題目_日期>\`）；(ii) **在該資料夾內寫一個 txt 名單檔**（如 `_需補全文清單.txt`），逐筆附**完整書目**（標題／作者／期刊／年／卷期頁／DOI／PMID／角色／建議檔名＝DOI 去斜線）。(iii) **主動問使用者要不要把定案文獻匯入 Zotero、以及匯入範圍**（原始研究＋背景／只原始研究／全部納入候選／不匯入）——**這一問為必做、別漏**（`zotero_import.py`，config 已設 library/collection）。使用者放入 PDF 後重掃資料夾、更新全文狀態。　→ 停。

> **試驗登錄（ClinicalTrials.gov）平行處理**：CT 腿撈到的 NCT **不走上面文獻流的全文/摘要分類，也不走 Crossref/PubMed 驗證（以 NCT 號本身為憑）。** 各 NCT 依狀態分流：(a) **已發表**→連結到其論文、合併成同一個 **Study 單位**，隨論文走評讀；(b) **進行中／未發表**→列「進行中·待評估試驗」，供 PRISMA 完整度與**選擇性報告／非報告偏誤**查核，**不計入證據**；(c) **排除類**（他適應症、健康受試者 Ph1、擴大使用/觀察性）。註冊內容供下游 **registry-backfill**（補 RoB／各臂 N／AE、註冊 vs 發表 outcome 比對）。CT 分流同樣在第①關報告、隨第④/⑤關收斂。

以上全部確認後**才**進入：**三表＋PDF 報告 → 寫交接包**（每一步各自再停）。（交叉驗證已在第⑥關完成、僅作標記；三表沿用其 verdict 欄位，**不因 UNVERIFIED 刪文**。）

### 交接 — 寫交接包、問是否續評讀
三表/PDF 交付後，把「已決定的事」（必含軸→PICO 雛形、納入／背景分流、study 標籤、證據等級、全文狀態、PDF 檔名、**每篇「全文取得管道」`fulltext_channel`＋`fulltext_url`**＝本地人工補/Unpaywall 直連/機構綠色 OA(付費牆作者稿)/PMC/僅 AI 合成摘要…，供 Analysis 沿同管道重讀並標 `data_source`）寫成 `_corpus_seed.json`：
`python ${CLAUDE_SKILL_DIR}/EBM_Search/scripts/build_corpus_seed.py --in seed.json --out-dir "<全文資料夾>"`
然後**停下問「是否繼續進入 EBM 分析？」**。使用者回「繼續／是」才進 Phase 2。

### Phase 2 — GRADE 評讀（讀 `EBM_Analysis/ANALYSIS_SPEC.md` 全文照做）
`python ${CLAUDE_SKILL_DIR}/EBM_Analysis/tools/ingest_seed.py --seed-dir "<交接包資料夾>"` → 複製全文 PDF 進 `inputs/`、預填 Phase 0 草稿 → 逐階段評讀（**每階段一個斷點**）：Phase 0 分流（覆核交接建議、補 O 軸）→ 1 抽取 → 2 軌道/起始確定性 → 3 逐 outcome GRADE（五下調＋三上調＋對抗式複查）→ 4 單篇報告＋跨篇統合＋SoF 表。成品由單一 cache JSON 渲染（永不漂移）。schema 驗證 `python ${CLAUDE_SKILL_DIR}/EBM_Analysis/tools/validate.py …`。

### 封存／歸檔
使用者說「封存／歸檔這次分析」「歸檔成 XXX」「封存後清空準備下一個主題」時，依 `ANALYSIS_SPEC.md` 的封存流程，`python ${CLAUDE_SKILL_DIR}/EBM_Analysis/tools/archive_run.py <slug> [--clear] …`（只封存 cache/outputs）。

### 結案（軟指令「EBM分析結束／結案／清理下一輪」）
使用者說「**EBM分析結束**」「結案」「這輪結束、清理準備下一輪」時，跑 **`python ${CLAUDE_SKILL_DIR}/EBM_Analysis/tools/end_run.py`**：**先封存**這輪到 `runs/<YYYY-MM>_<slug>/`（audit＝cache JSON／deliverables＝outputs＋reports／handoff＝交接中繼檔＋MANIFEST），**再清空** cache／outputs／inputs／reports／交接全文資料夾（整夾刪，含手工/下載 PDF）／run_state。版權 PDF 不進封存、只記檔名。先 `--dry-run` 給使用者看再執行；OneDrive 偶鎖空夾屬正常（內容已清、無害）。執行前提醒：reports 與手工 PDF 會一併刪除（已封存於 runs/）。

## 入口守則
EBM 評讀**不獨立冷啟動**——一律先經 Phase 1 檢索＋查證再接力評讀。若使用者沒先檢索就要直接評讀手上的 PDF，提醒先做一次檢索查證，確保證據經查證（去幻覺、定必含軸）。除非使用者明確堅持跳過，才在告知侷限後便宜行事。

## 誠實限制
評讀判斷仍由 Claude 做；雖有 schema 強制＋GRADE 算術重算＋跨篇 audit＋對抗式複查多道把關，但複查者仍是同一個 Claude、非真正獨立第二方；結論請由你或專業人員覆核。方法學對照 Cochrane Handbook v6.5＋GRADE；檢索對齊 Cochrane Ch.4＋PRISMA-S／PRISMA 2020。
