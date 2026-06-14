# EBM_Framework 整合：EBM_Search → EBM_Analysis 交接層

兩個子計畫各司其職、可獨立使用；本文件定義把 **EBM_Search 的檢索結果直接送進 EBM_Analysis 評讀** 的交接契約與流程。

```
EBM_Search（檢索＋交叉驗證）            EBM_Analysis（GRADE 評讀）
  找文獻 → 去幻覺 → 三表 → PDF            Phase 0 分流 → 1 抽取 → 2 軌道 → 3 GRADE → 4 報告
          │                                        ▲
          └──── _corpus_seed.json ＋ 全文 PDF ──────┘
                 （交接包＝同一個 fulltext 資料夾）
```

## 為什麼要交接層

EBM_Search 收尾時，其實**已經決定了 EBM_Analysis Phase 0 要決定的大半事情**：

| EBM_Search 已產出 | EBM_Analysis Phase 0 需要 |
|---|---|
| 必含連言軸（P／疾病／I／C） | review_question 的 PICO |
| `verdict:included`（表二）／`verdict:background`（表三背景） | relevance／grade_track |
| `study:<試驗名>` 標籤 | `overlap_with`／`included_trials`（去重） |
| 證據等級 L1–L5、研究設計 | role、起始確定性 |
| 全文狀態 ＋ 全文 PDF 資料夾 | `inputs/` 的 PDF |

沒有交接層時，使用者要**手動搬 PDF**、Claude 要**從零重定 PICO 與逐篇分流**——重工且易漂移。交接層把這些「已決定的事」打包傳遞，省掉重工，但**不取消 Phase 0 的覆核斷點**（建議值仍要使用者確認）。

## 交接契約：`_corpus_seed.json`

- **正本 schema**：[`EBM_Search/references/corpus_seed_schema.json`](EBM_Search/references/corpus_seed_schema.json)（生產者持有）。
- **位置**：寫在該次檢索的**全文資料夾**（由根 config `report.fulltext_dir` 指定，現＝`OneDrive\文件\EBM_Framework\fulltext\<題目_日期>\`），與全文 PDF 同處——**資料夾本身即交接包**，自帶、可攜。
- **內容**：`topic`／`search_date`／`review_question_seed`（PICO 雛形）＋ `papers[]`，每篇含 `verdict`、`study`、`evidence_level`、`design_hint`、`fulltext_status`、`pdf_file`，及 `suggested`（對 Analysis 欄位的建議映射）。
- **集合範圍**：**＝表二（納入）＋表三背景（background）**，與 EBM_Search 的 Zotero 一致性規則（SKILL ⑤a）同一真實來源。驗證不符／主旨不符／品質閘剔除者**不進交接**。

### `suggested` 映射規則（EBM_Search 填、EBM_Analysis 覆核）

| 條件（EBM_Search） | relevance | role | grade_track |
|---|---|---|---|
| `included` ＋ RCT（樞紐療效，L1/L2） | direct | pivotal_efficacy | full |
| `included` ＋ SR/MA | direct | meta_analysis | full |
| `included` ＋ 同試驗次分析/子群 | direct | supportive_secondary | full |
| `included` ＋ 安全性子研究 | direct | safety | targeted_harms |
| `background` ＋ 機制/PK/healthy | background | mechanism_pd／pharmacokinetic | light_summary |
| `background` ＋ 綜述 | background | narrative_review | light_summary |

- `study` 標籤相同的多篇 → 互填 `overlap_with`（同一試驗多報告，避免重複計入）。
- `included_trials`（僅 MA）→ 原樣帶入供統合去重。
- **O 軸**：EBM_Search 設計上**不以結果為檢索/篩選軸**，故 `review_question_seed.O` 通常為 `[]`；匯入時以佔位填入，**必須在 Phase 0 由使用者補定**。

## 端到端流程

### 1）EBM_Search 收尾（生產交接包）
Phase 1 ⑥（三表＋PDF 交付）之後，新增 **⑦**：組好 seed → 驗證並寫出。
```bash
# 在 EBM_Search/
python scripts/build_corpus_seed.py --in seed.json --out-dir "<全文資料夾>"
```
工具驗證契約（required／enum／全文-PDF 一致性）後寫出 `<全文資料夾>/_corpus_seed.json`，並**停下問「是否繼續進入 EBM 分析？」**。

### 2）接力（單一入口，取代 `/ebm`）
使用者回「**繼續／是**」即接力到 EBM_Analysis；回「否」則交接包留存，日後對 Claude 說「繼續（進入 EBM 分析）」或指向該交接包即可接上。

> **入口統一**：本框架**已取消 `/ebm`、「以EBM方式分析」等獨立啟動**——EBM 評讀一律由 EBM_Search 完成檢索＋交叉驗證後接力進入，確保被評讀的證據都經過查證（去幻覺、定必含軸）。未經檢索就要直接評讀 PDF 時，`ebm` skill 會導引使用者先走 EBM_Search。

### 3）EBM_Analysis 匯入（消費交接包）
Phase 0 第 0 步：
```bash
# 在 EBM_Analysis/
python tools/ingest_seed.py --seed-dir "<交接包資料夾>"
```
- 把 `fulltext_status ∈ {have, have_manual}` 的 PDF **複製進 `inputs/`**（檔名 `<paper_id>.pdf`）。
- 依 `suggested`＋`study` 去重，產出**預填草稿** `cache/_corpus.draft.json`（符合 `schema/phase0_corpus.json`）。
- 無 PDF 者（背景／僅 AI 合成摘要）預填 `light_summary`；要對其跑 full 須先人工補全文 PDF。

### 4）Phase 0 覆核 → 定稿
把草稿的 **review question（補 O 軸）＋逐篇 relevance/role/grade_track** 攤給使用者覆核確認 → 存成 `cache/_corpus.json` → `python tools/validate.py p0 cache/_corpus.json` → 照常進 Phase 1–4。

> **草稿 ≠ 定稿**：`ingest_seed.py` 只寫 `_corpus.draft.json`，不直接覆蓋 `_corpus.json`；確認後才定稿。這保住 EBM_Analysis「每階段斷點覆核、不靜默納入」的設計。

## 設計原則（兩邊一致）

- **單一真實來源**：交接包＝Zotero 匯入集合＝報告表二＋表三背景，三者一致。
- **不靜默**：交接只傳「建議」，Phase 0 斷點仍逐項覆核。
- **路徑無個資**：交接包與成品路徑一律由根 `config/settings.yaml`（gitignored）提供（現集中於 `OneDrive\文件\EBM_Framework\` 下 `fulltext`／`reports`／`packages`），committed 檔案不寫死含使用者名的絕對路徑。
- **零相依生產、確定性消費**：`build_corpus_seed.py`／`ingest_seed.py` 皆純標準庫；schema 驗證在 EBM_Analysis 用既有 `tools/validate.py`。

## 機敏／個人設定（集中於根 config）

兩個子計畫的**機敏資訊與個人設定一律集中**在 `EBM_Framework/config/settings.yaml`（**gitignored**，且位於兩個 git 子репо之外、打包帶不到）：

- **真秘密**：`zotero.api_key`（建議改用環境變數 `ZOTERO_API_KEY`）、`pubmed.ncbi_api_key`、`epistemonikos.api_token`。
- **PII／本機路徑**：`crossref.mailto`、`report.pdf_output_dir`（OneDrive 文件夾）、`analysis.project_dir`（EBM_Analysis 專案根）。
- **行為參數**：`source`／`matching`／`verdict`（非機敏，一起管理）。

**解析順序**（EBM_Search 腳本的 `default_settings_path()`；EBM_Analysis 的 `analysis` 區由 `/ebm` 讀）：
```
env EBM_CONFIG  >  EBM_Framework/config/settings.yaml（根）  >  各子計畫本地 config/settings.yaml（回退）
```
- 平常在 EBM_Framework 工作樹下開發 → 用根 config。
- 子計畫被打包成 skill 單獨安裝、看不到根 config → 用環境變數，或在安裝處放本地 `settings.yaml`。
- 範本（佔位、進版控）：`EBM_Framework/config/settings.example.yaml`（唯一正本）。

> **委任版控的檔案皆無個資**（已掃描確認無使用者名／email／金鑰）；真值只在 gitignored 的根 config。

## 檔案一覽

| 角色 | 檔案 |
|---|---|
| 契約 schema | `EBM_Search/references/corpus_seed_schema.json` |
| 生產工具 | `EBM_Search/scripts/build_corpus_seed.py` |
| 生產接線 | `EBM_Search/SKILL.md`（Phase 1 ⑦、跨 Phase 停頓點 7、v0.20 changelog） |
| 消費工具 | `EBM_Analysis/tools/ingest_seed.py` |
| 消費接線 | `EBM_Analysis/phases/00_triage.md`（步驟 0）、`EBM_Analysis/ANALYSIS_SPEC.md`（「從 EBM_Search 接力」段）、`EBM_Analysis/manifest.yaml`（handoff 區） |
| 目標 schema | `EBM_Analysis/schema/phase0_corpus.json`（草稿須符合） |
| 機敏設定（真值） | `EBM_Framework/config/settings.yaml`（gitignored，唯一真值來源） |
| 機敏設定（範本） | `EBM_Framework/config/settings.example.yaml`、`EBM_Framework/.gitignore` |
| 設定解析 | `EBM_Search/scripts/xref_verify.py` 的 `default_settings_path()`（其餘 3 腳本 import 之） |
| 單一入口（Claude Code skill） | `.claude/skills/ebm-search/`（入口啟動器）、`.claude/skills/ebm-analysis/`（下游啟動器）；`/ebm` 已徹底移除 |
| 框架指引 | `CLAUDE.md`（工作根、路徑前綴、單一入口、config）｜本框架僅在 Claude Code 運作 |
