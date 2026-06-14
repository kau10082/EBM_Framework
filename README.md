# EBM_Framework

> **實證醫學（EBM）端到端管線：多源文獻檢索＋交叉驗證 → GRADE 證據評讀，全程在 Claude Code 內運作。**
> **An end-to-end Evidence-Based-Medicine pipeline: multi-source literature retrieval + cross-verification → GRADE appraisal, running entirely inside Claude Code.**

---

## 這是什麼 · What is this

**中文**　EBM_Framework 把兩個子計畫整合成一條管線：

- **EBM_Search**（證據引擎層）：對一個主題/臨床問題做系統性回顧（SR）對齊的多源檢索，並用 Crossref／PubMed 交叉驗證、剔除幻覺引用，產出「經查證的引用清單＋PDF 報告」。
- **EBM_Analysis**（評讀層）：以 **Claude 本身為運算引擎**（不呼叫任何外部 LLM API），依結構化規格（phases／guardrails／schema）對文獻逐篇做 **GRADE** 證據分級、RoB 偏誤評估與跨篇統合，每階段設斷點。

兩者由**交接層**（`_corpus_seed.json`）銜接：檢索結果可直接餵進評讀，免手動搬檔、免重定 PICO。

**English**　EBM_Framework unifies two sub-projects into one pipeline:

- **EBM_Search** (evidence engine): runs a systematic-review-aligned, multi-source search for a topic/clinical question, cross-verifies every hit against Crossref/PubMed, strips hallucinated citations, and produces a *verified* reference list plus a PDF report.
- **EBM_Analysis** (appraisal): uses **Claude itself as the compute engine** (no external LLM API calls). Following a structured spec (phases/guardrails/schema), it performs per-paper **GRADE** certainty rating, risk-of-bias assessment, and cross-study synthesis, pausing at a checkpoint after each stage.

A **handoff layer** (`_corpus_seed.json`) connects them, so search results feed straight into appraisal — no manual file shuffling, no re-deriving the PICO.

---

## 架構 · Architecture

```
   使用者說「EBM分析 / 實證分析 / 查文獻」
   User says "EBM分析 / 實證分析 / find evidence"
                    │
                    ▼
   ┌─────────────────────────────────────┐
   │  ebm-search  （唯一入口 · sole entry）│
   │  四軸展開→多源檢索→交叉驗證→三表+PDF   │
   │  axis-expand → multi-source search →  │
   │  cross-verify → 3 tables + PDF report │
   └─────────────────────────────────────┘
                    │  寫交接包 _corpus_seed.json，問「是否繼續進入 EBM 分析？」
                    │  writes handoff seed, asks "continue to appraisal?"
                    ▼  使用者回「繼續」· user replies "繼續/continue"
   ┌─────────────────────────────────────┐
   │  ebm-analysis （下游 · downstream）   │
   │  Phase 0 分流 → 1 抽取 → 2 軌道 →     │
   │  3 GRADE → 4 報告＋統合（每階段斷點）  │
   │  triage → extract → track → GRADE →   │
   │  report + synthesis (checkpoint each) │
   └─────────────────────────────────────┘
                    │
                    ▼
   成品 PDF／報告 → <文件>\EBM_Framework\reports
   Deliverable PDFs/reports → <Documents>\EBM_Framework\reports
```

---

## 目錄結構 · Repository layout

```
EBM_Framework/
├── CLAUDE.md                      # Claude Code 專案指引（工作根、路徑前綴、單一入口）
├── INTEGRATION.md                 # 交接層契約與端到端流程 / handoff contract & flow
├── config/
│   ├── settings.example.yaml      # ★設定範本（佔位，進版控）/ settings template (committed)
│   └── settings.yaml              # 你的真值（金鑰/個資，gitignored，不上傳）/ your secrets (ignored)
├── .claude/skills/
│   ├── ebm-search/SKILL.md        # 入口啟動器 / entry launcher → EBM_Search/SKILL.md
│   └── ebm-analysis/SKILL.md      # 下游啟動器 / downstream launcher → EBM_Analysis/ANALYSIS_SPEC.md
├── EBM_Search/                    # 檢索＋驗證引擎（零相依 Python）/ retrieval+verify (zero-dep)
│   ├── SKILL.md                   #   完整規格 / full spec
│   ├── scripts/                   #   xref_verify / journal_quartile / zotero_import /
│   │                              #   fulltext_fetch / build_corpus_seed / pack_skill
│   └── references/                #   output_schema.json / corpus_seed_schema.json（交接契約）
└── EBM_Analysis/                  # GRADE 評讀（Claude 即引擎）/ GRADE appraisal (Claude is engine)
    ├── ANALYSIS_SPEC.md           #   評讀規格正本 / appraisal spec
    ├── phases/ guardrails/ schema/ #   階段指令／28 條護欄／JSON Schema 完整性強制
    ├── tools/                     #   validate / build_reports / ingest_seed / pdf_to_text / …
    └── manifest.yaml              #   中央地圖：護欄→GRADE 領域映射 / guardrail→domain map
```

---

## 前置需求 · Prerequisites

| 項目 / Item | 說明 / Notes |
|---|---|
| **Claude Code** | 本框架只在 Claude Code 內運作（不再打包成 Desktop skill）。/ Runs only inside Claude Code (no longer packaged as a Desktop skill). |
| **Python 3.8+** | EBM_Search 腳本為**零第三方相依**（純標準庫）。/ EBM_Search scripts are **zero-dependency** (stdlib only). |
| **MCP（檢索用）** | EBM_Search 的檢索腿需要連上 **Consensus**、**PubMed** MCP；建議加 **OpenEvidence**（`oe_ask`）。ClinicalTrials.gov／OpenAlex／Europe PMC 免金鑰、無需設定。/ EBM_Search needs **Consensus** & **PubMed** MCP connected; **OpenEvidence** recommended. ClinicalTrials.gov / OpenAlex / Europe PMC are keyless. |

---

## 設定方法 · Setup

### 步驟 1：取得程式碼並在 Claude Code 開啟 · Clone & open in Claude Code

```bash
git clone https://github.com/kau10082/EBM_Framework.git
```

**中文**　在 Claude Code 裡**開啟 `EBM_Framework` 這個資料夾當專案根**（不是開子資料夾）。這樣兩個 skill（`ebm-search`／`ebm-analysis`）才會被自動發現，工作根也會是 `EBM_Framework`。

**English**　In Claude Code, **open the `EBM_Framework` folder as the project root** (not a sub-folder). This is required for both skills (`ebm-search` / `ebm-analysis`) to be auto-discovered, and makes the working root `EBM_Framework`.

### 步驟 2：建立設定檔 · Create your settings file

**中文**　所有金鑰與個人路徑集中在**一個檔**：`config/settings.yaml`。它已被 `.gitignore` 排除、**永不進版控**。請複製範本後填入你的值：

**English**　All secrets and personal paths live in **one file**: `config/settings.yaml`. It is **git-ignored and never committed**. Copy the template and fill in your values:

```powershell
# 從 EBM_Framework 根目錄 / from the EBM_Framework root
Copy-Item config/settings.example.yaml config/settings.yaml
# 然後用編輯器填入下表欄位 / then edit the fields below
```

### 步驟 3：填寫欄位 · Fill in the fields

| 區段.欄位 / Section.key | 必填? / Required | 說明 / Description |
|---|---|---|
| `crossref.mailto` | 建議 / recommended | 一個聯絡 email，讓 Crossref 進 polite pool（**不是金鑰**）。env：`CROSSREF_MAILTO`。/ A contact email for Crossref's polite pool (**not an API key**). |
| `pubmed.ncbi_api_key` | 否 / no | PubMed 走 MCP 時留空；本機直打 E-utilities 提速才填。env：`NCBI_API_KEY`。/ Leave empty when using PubMed MCP; only for direct local E-utilities. |
| `zotero.api_key` | 選用 / optional | **真秘密**。要把納入清單歸檔到 Zotero 才需要。建議改用環境變數 `ZOTERO_API_KEY`（不落地最安全）。/ **A real secret.** Only needed to archive the included list into Zotero. Prefer env `ZOTERO_API_KEY`. |
| `zotero.library_id` / `library_type` / `collection_key` | 選用 / optional | 你的 Zotero userID（數字）、`user`/`group`、目標 collection 8 碼 key。/ Your Zotero userID, type, and target collection key. |
| `epistemonikos.api_token` | 選用 / optional | SR 專庫腿（EK）的免費 token（須 email `dev@epistemonikos.org` 申請）；留空則 EK 腿自動跳過。/ Free token for the Epistemonikos SR leg; empty = leg skipped. |
| `source.mode` / `matching.*` / `verdict.*` | 否 / no | 驗證行為參數（非機敏）：來源模式、標題相似度門檻、`any`/`both` 判定。一般用預設即可。/ Verification behavior (not sensitive); defaults are fine. |
| `report.pdf_output_dir` | 是 / yes | EBM_Search 報告 PDF 成品的輸出夾。建議 `<文件>\EBM_Framework\reports`。/ Output dir for EBM_Search report PDFs. |
| `report.fulltext_dir` | 是 / yes | 人工補全文 PDF ＋ 交接包 `_corpus_seed.json` 的基底（per-topic 子夾在其下）。建議 `<文件>\EBM_Framework\fulltext`。/ Base dir for manual full-text PDFs + the handoff seed. |
| `packaging.output_dir` | 否 / no | 打包 ZIP 輸出（Claude-Code-only 平常用不到）。建議 `<文件>\EBM_Framework\packages`。/ ZIP packaging output (rarely needed). |
| `analysis.project_dir` | 是 / yes | `EBM_Analysis` 專案根的絕對路徑（個資）。/ Absolute path to the `EBM_Analysis` project root (personal). |
| `analysis.pdf_output_dir` | 是 / yes | EBM_Analysis 評讀成品 PDF 輸出夾。建議 `<文件>\EBM_Framework\reports`。/ Output dir for appraisal report PDFs. |
| `analysis.cjk_font` | 是 / yes | PDF 報告用的 CJK 字型路徑（系統字型，非個資），如 `C:/Windows/Fonts/msjh.ttc`。/ CJK font path for PDF reports. |

> **設定檔解析順序 · How settings are resolved**
> 腳本以 `default_settings_path()` 依序尋找 ╱ Scripts resolve via `default_settings_path()` in order:
> 1. 環境變數 `EBM_CONFIG`（指向某個 `settings.yaml` 的絕對路徑）╱ env `EBM_CONFIG` (absolute path to a settings.yaml)
> 2. 根 `EBM_Framework/config/settings.yaml`（平常用這個）╱ the root config (the usual case)
> 3. 子計畫本地 `EBM_Search/config/settings.yaml`（回退；僅打包安裝時）╱ sub-project local config (fallback)
>
> 優先序（高→低）：**CLI 旗標 > 環境變數 > settings.yaml > 內建預設**。
> Precedence (high→low): **CLI flags > env vars > settings.yaml > built-in defaults**.

### 步驟 4：建立對外工作資料夾 · Create the work folders

**中文**　成品、打包、人工補全文都放在 `<Windows 文件>\EBM_Framework\` 底下的三個子夾（工具會自動建立，也可先手動建好）：

**English**　Deliverables, packages, and manual full-text PDFs all live under `<Documents>\EBM_Framework\` in three sub-folders (tools auto-create them; you may also pre-create):

```
<文件 / Documents>\EBM_Framework\
├── reports\                # 成品 PDF / report PDFs
├── fulltext\<題目_日期>\    # 人工補全文 + 交接包 / manual full-text + handoff seed
└── packages\               # 打包 ZIP（選用）/ packaging ZIPs (optional)
```

### 步驟 5（選用）：安裝 EBM_Analysis 的無 API 輔助工具 · (Optional) install EBM_Analysis helper deps

**中文**　評讀的運算引擎是 Claude 本身，**不需要任何 LLM API key**。但「完整模式」會用到幾個確定性小工具（schema 驗證、PDF 抽文字、報告渲染）：

**English**　The appraisal engine is Claude itself — **no LLM API key needed**. "Full mode" uses a few deterministic helpers (schema validation, PDF text extraction, report rendering):

```bash
pip install -r EBM_Analysis/requirements.txt   # jsonschema / PyYAML / pymupdf / pypdf
pip install reportlab                            # 僅在需要產出 PDF 報告時 / only if you want PDF reports
```

> EBM_Search 不需要 `pip install`（純標準庫）。/ EBM_Search needs no `pip install` (stdlib only).

---

## 使用方法 · Usage

### 唯一入口：軟指令 · Single entry: the soft command

**中文**　整條管線**只有一個入口＝`ebm-search`**，而且**一律從檢索開始**。在 Claude Code（已開 `EBM_Framework`）對 Claude 說下列任一句即可啟動：

- 「**EBM分析**」「**實證分析**」「**實證醫學分析**」「對〈某主題／某藥〉做 EBM 分析」
- 「幫我查文獻」「建立可信引用清單」「幫我查證這個主張」「驗證這些引用是不是真的」

> 註：本框架已**取消 `/ebm` 指令**。評讀（`ebm-analysis`）不獨立啟動，只能由 `ebm-search` 收尾接力，或用於「封存／歸檔」。若沒先檢索就要直接評讀 PDF，Claude 會導引你先走 `ebm-search`（確保證據經查證）。

**English**　The pipeline has **one entry = `ebm-search`**, and it **always starts from a literature search**. In Claude Code (with `EBM_Framework` open), say any of:

- "**EBM分析**" / "**實證分析**" / "do an EBM analysis on ⟨topic/drug⟩"
- "find me the literature" / "build a trustworthy reference list" / "verify these citations"

> Note: the `/ebm` command has been **removed**. Appraisal (`ebm-analysis`) does not cold-start; it is reached only via the `ebm-search` handoff, or for archiving. If you ask to appraise PDFs without searching first, Claude redirects you to `ebm-search` so the evidence is verified.

### 完整流程 · The full flow

**1️⃣ 檢索＋驗證（ebm-search）· Retrieve & verify**

**中文**　Claude 會：四軸展開主題（縮寫↔全文／慣稱↔生化別名／類別↔藥名↔代號／疾病縮寫↔全文）→ 多源檢索（Consensus／PubMed／OpenEvidence ＋ ClinicalTrials.gov／OpenAlex／Europe PMC／Epistemonikos）→ 聯集去重 → 主旨篩選 → 引文追蹤至收斂 → Crossref／PubMed 交叉驗證去幻覺 → 產出**三表＋PDF 報告**。**每個關卡都會停下來報告並等你確認**，不會一口氣跑完。

**English**　Claude expands the topic along four axes, searches multiple sources, de-duplicates, screens for topicality, snowballs citations to saturation, cross-verifies against Crossref/PubMed to remove hallucinations, and produces **three tables + a PDF report**. **It pauses at every checkpoint** and waits for your confirmation.

**2️⃣ 接力 · Handoff**

**中文**　檢索收尾時，Claude 把「已決定的事」（PICO 雛形、納入／背景分流、study 標籤、證據等級、全文狀態）寫成交接包 `_corpus_seed.json`（放在 `fulltext\<題目_日期>\`），然後問「**是否繼續進入 EBM 分析？**」。回「**繼續**」即接力。

**English**　At the end of the search, Claude writes everything already decided (seed PICO, included/background split, study tags, evidence levels, full-text status) into a handoff `_corpus_seed.json`, then asks "**continue to EBM appraisal?**". Reply "**繼續 / continue**" to proceed.

**3️⃣ GRADE 評讀（ebm-analysis）· Appraise**

**中文**　接力後，`ingest_seed.py` 把全文 PDF 複製進 `EBM_Analysis/inputs/`、預填 Phase 0 分流草稿；接著逐階段評讀（**每階段一個斷點**）：

- **Phase 0** 定 review question（PICO，補 O 軸）＋逐篇分流（覆核交接的建議值）
- **Phase 1** 結構化抽取（PICO／N／設計，每筆數字附原文 quote）
- **Phase 2** 研究誠信 gate → 軌道 A/B/C → GRADE 起始確定性
- **Phase 3** 逐 outcome 五下調＋三上調領域逐一給判定，並做對抗式第二遍複查
- **Phase 4** 單篇報告＋跨篇統合＋ Summary of Findings 表（絕對效應／NNT）

成品（`.md` / `.pdf`、synthesis、ledger）由單一份 cache JSON 渲染，**永不與判定漂移**，輸出到 `reports\`。

**English**　After the handoff, `ingest_seed.py` copies full-text PDFs into `EBM_Analysis/inputs/` and pre-fills a Phase-0 triage draft. Appraisal then proceeds stage by stage (**one checkpoint per stage**): define the PICO review question, structured extraction (each number quoted from source), integrity gate → track → starting certainty, per-outcome GRADE with an adversarial second pass, and finally per-paper reports + cross-study synthesis + a Summary-of-Findings table (absolute effects / NNT). All deliverables are rendered from a single cache JSON (so reports never drift from the judgments) into `reports\`.

### 封存／歸檔 · Archiving

**中文**　評讀完成後，說「**封存／歸檔這次分析**」「**歸檔成 XXX**」「**封存後清空準備下一個主題**」，Claude 會把這次評讀歸檔到 `EBM_Analysis/runs/<日期>_<主題>/`（可選擇是否清空工作檔、是否產來源清單）。

**English**　After appraisal, say "**archive this analysis**" / "**archive as XXX**" / "**archive then clear for the next topic**". Claude files the run under `EBM_Analysis/runs/<date>_<slug>/` (optionally clearing the working files and generating a sources list).

### 路徑約定（重要）· Path convention (important)

**中文**　工作根＝`EBM_Framework`。子計畫規格裡的相對路徑都相對於各自資料夾，執行時一律**加前綴**：`python EBM_Search/scripts/…`、`python EBM_Analysis/tools/…`。Claude 已被 `CLAUDE.md` 與啟動器告知此規則。

**English**　The working root is `EBM_Framework`. Relative paths in each sub-project's spec are relative to that sub-project, so commands are **prefixed** at run time: `python EBM_Search/scripts/…`, `python EBM_Analysis/tools/…`. Claude is told this by `CLAUDE.md` and the launchers.

---

## 安全與隱私 · Security & Privacy

**中文**
- **真值集中、永不上傳**：金鑰（Zotero）、email、本機絕對路徑只存在於 `config/settings.yaml`，已被 `.gitignore` 排除。版控只含 `*.example.yaml` 佔位範本。
- **版權／隱私內容不進 repo**：文獻 PDF、`inputs/`、`cache/`、`outputs/`、`runs/` 一律 gitignored（可能含版權與病例資料）。
- **金鑰建議走環境變數**：`ZOTERO_API_KEY`／`CROSSREF_MAILTO`／`EBM_CONFIG`，不落地最安全。

**English**
- **Secrets are centralized and never pushed**: the Zotero key, email, and local absolute paths live only in `config/settings.yaml`, which is git-ignored. Only `*.example.yaml` placeholders are committed.
- **Copyrighted/private content stays out of the repo**: paper PDFs, `inputs/`, `cache/`, `outputs/`, `runs/` are all git-ignored (may contain copyrighted text and case data).
- **Prefer env vars for secrets**: `ZOTERO_API_KEY` / `CROSSREF_MAILTO` / `EBM_CONFIG`.

---

## 方法學依據 · Methodology

**中文**　EBM_Analysis 的流程逐條對照 **Cochrane Handbook v6.5**（GRADE 起始確定性、五下調／三上調、RoB 2→GRADE 映射、異質性、不精確 OIS、計票三層、NNT/RD 信賴區間、相關 SR/MA 之 AMSTAR 2）。EBM_Search 對齊 **Cochrane 第 4 章＋PRISMA-S／PRISMA 2020**（敏感度優先、不在檢索階段以分位篩、引文追蹤、覆蓋限制誠實聲明）。

**English**　EBM_Analysis is cross-checked clause-by-clause against the **Cochrane Handbook v6.5** (starting certainty, the five downgrade / three upgrade domains, RoB 2→GRADE mapping, heterogeneity, imprecision/OIS, the three-tier vote-counting hierarchy, NNT/RD confidence intervals, AMSTAR 2 for related reviews). EBM_Search aligns with **Cochrane Ch.4 + PRISMA-S / PRISMA 2020** (sensitivity-first, no quartile filtering at the search stage, citation chasing, honest coverage-limitation statements).

> ⚠️ **誠實限制 · Honest caveat**：評讀的判斷仍由 Claude 做；已用 schema 結構＋GRADE 算術重算＋跨篇 audit＋對抗式複查多道把關，但複查者仍是同一個 Claude、非真正獨立第二方。
> The appraisal judgments are still made by Claude; despite schema enforcement, arithmetic re-checks, cross-study audits, and an adversarial pass, the reviewer is the same Claude — not a truly independent second party.
