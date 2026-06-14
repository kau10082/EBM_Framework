# EBM_Framework

> 一條實證醫學（EBM）的端到端管線：先把文獻**找齊、查證**，再做 **GRADE 證據評讀**——全程在 Claude Code 內完成。
>
> An end-to-end evidence-based-medicine pipeline: first **find and verify** the literature, then run a **GRADE appraisal** — all inside Claude Code.

---

## 這是什麼 · Overview

這個框架把兩個子計畫接成一條龍：

- **EBM_Search（證據引擎）** 針對一個主題或臨床問題做系統性回顧式的多源檢索，逐筆用 Crossref／PubMed 交叉驗證、剔除不存在的「幻覺引用」，最後交出一份**經查證的引用清單與 PDF 報告**。
- **EBM_Analysis（評讀引擎）** 以 **Claude 本身**為運算核心（完全不呼叫外部 LLM API），照著結構化規格逐篇做 **GRADE 證據分級、RoB 偏誤評估與跨篇統合**，而且每個階段都會停下來等你確認。

兩者之間有一層**交接機制**（`_corpus_seed.json`）：檢索的成果可以直接送進評讀，不必手動搬檔，也不必把 PICO 重新定義一次。

This framework chains two sub-projects into a single workflow:

- **EBM_Search (the evidence engine)** runs a systematic-review-style, multi-source search for a topic or clinical question, cross-verifies every hit against Crossref/PubMed, drops non-existent "hallucinated" citations, and hands back a **verified reference list and a PDF report**.
- **EBM_Analysis (the appraisal engine)** uses **Claude itself** as the compute core (no external LLM API at all). Following a structured spec, it performs **GRADE certainty rating, risk-of-bias assessment, and cross-study synthesis** paper by paper, pausing for your confirmation at every stage.

A **handoff layer** (`_corpus_seed.json`) links the two, so the search results flow straight into the appraisal — no manual file shuffling, and no re-deriving the PICO.

---

## 運作方式 · How it flows

```
   你說：「EBM分析 / 實證分析 / 幫我查文獻」
   You say: "EBM分析 / 實證分析 / find me the evidence"
                    │
                    ▼
   ┌─────────────────────────────────────┐
   │  ebm-search   唯一入口 · the one door │
   │  展開主題 → 多源檢索 → 交叉驗證        │
   │  → 三張清單 + PDF 報告                 │
   └─────────────────────────────────────┘
                    │  寫下交接包，並問：「要繼續進入 EBM 評讀嗎？」
                    │  writes the handoff seed, asks: "continue to appraisal?"
                    ▼  你回「繼續」· you reply "繼續 / continue"
   ┌─────────────────────────────────────┐
   │  ebm-analysis   下游評讀 · downstream │
   │  Phase 0 分流 → 1 抽取 → 2 軌道       │
   │  → 3 GRADE → 4 報告＋統合（逐階段停）  │
   └─────────────────────────────────────┘
                    │
                    ▼
   成品報告 → <文件>\EBM_Framework\reports
   Final reports → <Documents>\EBM_Framework\reports
```

---

## 目錄結構 · Repository layout

```
EBM_Framework/
├── CLAUDE.md                      # 給 Claude Code 的專案指引（工作根、路徑、單一入口）
├── INTEGRATION.md                 # 交接層契約與端到端流程 · handoff contract & flow
├── config/
│   ├── settings.example.yaml      # 設定範本（佔位，會進版控）· settings template (committed)
│   └── settings.yaml              # 你的真值（金鑰／個資，已 gitignore，不上傳）· your secrets (ignored)
├── .claude/skills/
│   ├── ebm-search/SKILL.md        # 入口啟動器 · entry launcher  → EBM_Search/SKILL.md
│   └── ebm-analysis/SKILL.md      # 下游啟動器 · downstream launcher → EBM_Analysis/ANALYSIS_SPEC.md
├── EBM_Search/                    # 檢索＋驗證引擎（零相依 Python）· retrieval + verify (zero-dep)
│   ├── SKILL.md                   #   完整規格 · full spec
│   ├── scripts/                   #   xref_verify · journal_quartile · zotero_import ·
│   │                              #   fulltext_fetch · build_corpus_seed · pack_skill
│   └── references/                #   output_schema.json · corpus_seed_schema.json（交接契約）
└── EBM_Analysis/                  # GRADE 評讀（Claude 即引擎）· GRADE appraisal (Claude is the engine)
    ├── ANALYSIS_SPEC.md           #   評讀規格正本 · appraisal spec
    ├── phases/ guardrails/ schema/ #   階段指令／28 條護欄／JSON Schema 完整性強制
    ├── tools/                     #   validate · build_reports · ingest_seed · pdf_to_text · …
    └── manifest.yaml              #   中央地圖：護欄→GRADE 領域映射 · guardrail→domain map
```

---

## 前置需求 · Prerequisites

| 項目 · Item | 說明 · Notes |
|---|---|
| **Claude Code** | 本框架只在 Claude Code 內運作，不再打包成桌面版 skill。· Runs only inside Claude Code; no longer packaged as a Desktop skill. |
| **Python 3.8+** | EBM_Search 的腳本零第三方相依（純標準庫）。· EBM_Search scripts have zero third-party dependencies (stdlib only). |
| **檢索用 MCP · Search MCPs** | 檢索階段需連上 **Consensus** 與 **PubMed** MCP，建議再加 **OpenEvidence**（設定見下方〈[連接檢索用的 MCP](#連接檢索用的-mcp--connecting-the-search-mcp-servers)〉）。ClinicalTrials.gov／OpenAlex／Europe PMC 免金鑰、不需設定。· The search stage needs **Consensus** and **PubMed** MCP, with **OpenEvidence** recommended (see *Connecting the search MCP servers* below). ClinicalTrials.gov / OpenAlex / Europe PMC are keyless. |

---

## 設定方法 · Setup

### 1. 取得程式碼，並在 Claude Code 開啟 · Clone, then open in Claude Code

```bash
git clone https://github.com/kau10082/EBM_Framework.git
```

請在 Claude Code 裡**把 `EBM_Framework` 這個資料夾當成專案根來開**（不要只開某個子資料夾）。唯有如此，兩個 skill（`ebm-search` 與 `ebm-analysis`）才會被自動偵測到，工作根目錄也才會是 `EBM_Framework`。

Open the **`EBM_Framework` folder itself as the project root** in Claude Code (not one of the sub-folders). Only then are both skills (`ebm-search` and `ebm-analysis`) auto-discovered, and the working root becomes `EBM_Framework`.

### 2. 建立你的設定檔 · Create your settings file

所有金鑰與個人路徑都集中在**同一個檔案**：`config/settings.yaml`。它已被 `.gitignore` 排除，永遠不會進版控。複製範本後填入你的值即可：

All keys and personal paths live in **one single file**: `config/settings.yaml`. It is git-ignored and never committed. Copy the template and fill in your own values:

```powershell
# 在 EBM_Framework 根目錄執行 · run from the EBM_Framework root
Copy-Item config/settings.example.yaml config/settings.yaml
```

### 3. 逐欄填寫 · Fill in the fields

| 區段.欄位 · Field | 必填？· Required | 說明 · Description |
|---|---|---|
| `crossref.mailto` | 建議 · recommended | 一個聯絡用 email，讓 Crossref 把你放進 polite pool；這**不是金鑰**。環境變數：`CROSSREF_MAILTO`。· A contact email so Crossref puts you in its polite pool — **not** an API key. |
| `pubmed.ncbi_api_key` | 否 · no | 走 PubMed MCP 時留空即可；只有要在本機直連 E-utilities 提速才需要。環境變數：`NCBI_API_KEY`。· Leave empty when using PubMed MCP; only needed for direct local E-utilities. |
| `zotero.api_key` | 選用 · optional | **真正的秘密**。只有要把納入清單歸檔到 Zotero 時才需要；建議改用環境變數 `ZOTERO_API_KEY`，不落地最安全。· A **real secret**, only for archiving into Zotero. Prefer the env var `ZOTERO_API_KEY`. |
| `zotero.library_id` · `library_type` · `collection_key` | 選用 · optional | 你的 Zotero userID（數字）、`user`/`group`、目標 collection 的 8 碼 key。· Your Zotero userID, library type, and target collection key. |
| `epistemonikos.api_token` | 選用 · optional | 系統性回顧專庫（EK）腿的免費 token，需向 `dev@epistemonikos.org` 申請；留空則此腿自動略過。· Free token for the Epistemonikos leg; if empty, that leg is skipped. |
| `source.mode` · `matching.*` · `verdict.*` | 否 · no | 驗證行為參數（非機敏）：來源模式、標題相似度門檻、`any`/`both` 判定。一般保留預設即可。· Verification behaviour (not sensitive); the defaults are fine. |
| `report.pdf_output_dir` | 是 · yes | EBM_Search 報告 PDF 的輸出夾，建議設成 `<文件>\EBM_Framework\reports`。· Where EBM_Search report PDFs go. |
| `report.fulltext_dir` | 是 · yes | 人工補全文 PDF 與交接包 `_corpus_seed.json` 的存放基底（各主題會在底下開子夾）；建議 `<文件>\EBM_Framework\fulltext`。· Base folder for manual full-text PDFs and the handoff seed. |
| `packaging.output_dir` | 否 · no | 打包 ZIP 的輸出夾（Claude-Code-only 模式平常用不到）；建議 `<文件>\EBM_Framework\packages`。· Where packaging ZIPs go (rarely needed). |
| `analysis.project_dir` | 是 · yes | `EBM_Analysis` 專案根的絕對路徑（屬個資）。· Absolute path to the `EBM_Analysis` project root (personal). |
| `analysis.pdf_output_dir` | 是 · yes | EBM_Analysis 評讀報告 PDF 的輸出夾，建議 `<文件>\EBM_Framework\reports`。· Where appraisal report PDFs go. |
| `analysis.cjk_font` | 是 · yes | PDF 報告用的中文字型路徑（系統字型，非個資），例如 `C:/Windows/Fonts/msjh.ttc`。· CJK font path for PDF reports. |

> **設定檔是怎麼被找到的 · How the settings file is located**
> 腳本透過 `default_settings_path()` 依序尋找，第一個存在的就採用：
> Scripts look it up via `default_settings_path()`, taking the first one that exists:
> 1. 環境變數 `EBM_CONFIG`（直接指向某個 `settings.yaml` 的絕對路徑）· the `EBM_CONFIG` env var (an absolute path to a settings.yaml)
> 2. 根目錄的 `EBM_Framework/config/settings.yaml`（平常就是這個）· the root `config/settings.yaml` (the normal case)
> 3. 子計畫本地的 `EBM_Search/config/settings.yaml`（後備，僅在單獨打包安裝時）· a sub-project local config (fallback)
>
> 整體優先序由高到低是：**CLI 旗標 ＞ 環境變數 ＞ settings.yaml ＞ 內建預設**。
> Overall precedence, high to low: **CLI flags ＞ env vars ＞ settings.yaml ＞ built-in defaults**.

### 4. 建好對外工作資料夾 · Create the work folders

成品、打包、人工補全文這三類對外檔案，都收在 `<文件>\EBM_Framework\` 底下。工具會自動建立，你也可以先手動開好：

Deliverables, packages, and manual full-text PDFs all live under `<Documents>\EBM_Framework\`. The tools create these on demand, but you may pre-create them:

```
<文件 · Documents>\EBM_Framework\
├── reports\                # 成品報告 PDF · report PDFs
├── fulltext\<題目_日期>\    # 人工補全文 + 交接包 · manual full-text + handoff seed
└── packages\               # 打包 ZIP（選用）· packaging ZIPs (optional)
```

### 5.（選用）安裝 EBM_Analysis 的輔助工具 · (Optional) install EBM_Analysis helpers

評讀的運算引擎就是 Claude 本身，**不需要任何 LLM API key**。只有「完整模式」會用到幾個確定性小工具（驗證 schema、抽 PDF 文字、渲染報告）：

The appraisal engine is Claude itself, so **no LLM API key is required**. Only "full mode" uses a few deterministic helpers (schema validation, PDF text extraction, report rendering):

```bash
pip install -r EBM_Analysis/requirements.txt   # jsonschema · PyYAML · pymupdf · pypdf
pip install reportlab                            # 只有要產 PDF 報告時 · only if you want PDF reports
```

EBM_Search 本身不需要 `pip install`（純標準庫）。· EBM_Search needs no `pip install` (stdlib only).

---

## 連接檢索用的 MCP · Connecting the search MCP servers

檢索階段（EBM_Search）靠幾個 MCP server 取得候選文獻。它們都是**每台機器各自連、屬於你的 Claude Code 環境，不會放進這個 repo**。每條檢索腿都會回報自己的狀態，所以**就算只連上其中幾個也能跑**——沒連到的腿會被標示為「跳過」。下游的評讀（EBM_Analysis）則完全不需要 MCP。

The search stage (EBM_Search) pulls candidate literature from a few MCP servers. They are **connected per-machine as part of your own Claude Code setup and are never committed to this repo**. Each search leg reports its own status, so **the pipeline runs even if you only connect some of them** — any leg you haven't connected is simply marked "skipped". The downstream appraisal (EBM_Analysis) needs no MCP at all.

> 在 Claude Code 加 MCP 的兩種方式：用 `claude mcp add <名稱> -- <啟動指令>`，或直接編輯使用者層的 `~/.claude.json`（也可放專案層 `.mcp.json`）。
> Two ways to add an MCP in Claude Code: run `claude mcp add <name> -- <launch-command>`, or edit the user-level `~/.claude.json` (a project-level `.mcp.json` also works).

### Consensus MCP（學術語意搜尋 · semantic literature search）

提供 AI 合成的候選文獻，框架以 `Consensus:search` 呼叫；屬「被驗證的來源」，真偽一律交給 Crossref／PubMed 把關。請依 Consensus 官方的 MCP 說明連上。

Supplies AI-synthesized candidate papers, called via `Consensus:search`; treated as a "to-be-verified" source whose existence is always checked against Crossref/PubMed. Connect it following Consensus's official MCP instructions.

### PubMed MCP（MEDLINE 檢索與驗證 · search + verification）

提供 `search_articles`、`get_article_metadata`、`get_full_text_article` 等工具，同時用於**深度檢索**與**驗證 lane**（自帶 PMID/DOI 可預過）。連上任一可用的 PubMed／NCBI MCP 即可。

Provides tools like `search_articles`, `get_article_metadata`, and `get_full_text_article`, used both for **deep retrieval** and as a **verification lane** (its built-in PMID/DOI pre-validates hits). Connect any working PubMed/NCBI MCP.

### OpenEvidence MCP（建議 · recommended）

採用社群維護的 **[`htlin222/openevidence-mcp`](https://github.com/htlin222/openevidence-mcp)**——**非官方**、**免 API key**，透過你**已登入的瀏覽器分頁**查詢 OpenEvidence；支援 fire-and-forget 提問、可並行的 relay daemon，回傳的引用自帶 **BibTeX ＋ Crossref 驗證**（所以高相似度者可直接視為預過）。

Uses the community-maintained **[`htlin222/openevidence-mcp`](https://github.com/htlin222/openevidence-mcp)** — **unofficial**, **no API key** — querying OpenEvidence through your **already-logged-in browser tab**. It supports fire-and-forget asks, a shared relay daemon for concurrent sessions, and returns citations carrying **BibTeX + Crossref validation** (so high-similarity hits count as pre-verified).

**安裝 · Install**（需 Node.js ≥ 20、Python 3）：

```bash
git clone https://github.com/htlin222/openevidence-mcp.git
cd openevidence-mcp
make all                       # 裝相依、建 server＋relay 擴充、註冊進 Claude/Codex
# 只想註冊到 Claude Code： make install-claude-global
```

**登入（一次性）· Authenticate (one-time)**：到 `chrome://extensions` 開啟「開發人員模式」→「載入未封裝」選 `extension/dist`，並在該瀏覽器**保持登入 openevidence.com、分頁不關**。驗證連線：

In `chrome://extensions`, enable Developer mode → Load unpacked → pick `extension/dist`, then **stay logged into openevidence.com in that browser and keep the tab open**. Check connectivity:

```bash
curl -s http://127.0.0.1:8787/health      # 預期 expect: {"ok":true,"connected":true,...}
```

框架用到的工具與旗標：`oe_ask`（提問，預設 fire-and-forget；`wait_for_completion:true` 可一次取回）、`oe_article_get`（取結果，`include_bibtex`）、`oe_auth_status`（查登入）；Crossref 驗證由 `OE_MCP_CROSSREF_VALIDATE=1`（預設開）控制。

Tools/flags the framework uses: `oe_ask` (fire-and-forget by default; `wait_for_completion:true` to block), `oe_article_get` (`include_bibtex`), and `oe_auth_status`; Crossref validation is controlled by `OE_MCP_CROSSREF_VALIDATE=1` (on by default).

> ⚠️ OpenEvidence 以美國為中心、已退出歐盟與英國；非美國使用者請先用 `oe_auth_status` 確認可存取，不能用時此腿自動跳過。
> OpenEvidence is US-centric and has withdrawn from the EU/UK; non-US users should confirm access via `oe_auth_status` first — the leg auto-skips when unavailable.

### 免設定的來源 · No-setup sources

**ClinicalTrials.gov、OpenAlex、Europe PMC** 由腳本直接走公開 HTTP API，**免金鑰、不需 MCP**。**Epistemonikos** 走直接 API，需要一個免費 token（填在 `config/settings.yaml` 的 `epistemonikos.api_token`），留空則該腿略過。

**ClinicalTrials.gov, OpenAlex, and Europe PMC** are called directly over public HTTP APIs by the scripts — **keyless, no MCP needed**. **Epistemonikos** uses a direct API and needs a free token (set `epistemonikos.api_token` in `config/settings.yaml`); leave it empty to skip that leg.

---

## 使用方法 · Usage

### 一句話啟動 · Start with one phrase

整條管線**只有一個入口，就是 `ebm-search`**，而且一律**從檢索開始**。在 Claude Code（已開好 `EBM_Framework`）裡，對 Claude 說下面任何一句就能啟動：

The whole pipeline has **a single door, `ebm-search`**, and it **always begins with a search**. With `EBM_Framework` open in Claude Code, just say any of:

- 「**EBM分析**」「**實證分析**」「**實證醫學分析**」「幫我對〈某主題／某藥〉做 EBM 分析」
- 「幫我查文獻」「建立一份可信的引用清單」「幫我查證這個主張」「驗證這些引用是不是真的」

> 本框架已經**取消 `/ebm` 指令**。評讀引擎（`ebm-analysis`）不會單獨啟動，只能由 `ebm-search` 收尾後接力，或用於「封存／歸檔」。如果你沒先檢索就要求直接評讀 PDF，Claude 會請你先走一次 `ebm-search`，確保證據都經過查證。
>
> The `/ebm` command has been **removed**. The appraisal engine (`ebm-analysis`) never cold-starts — it is reached only through the `ebm-search` handoff, or for archiving. If you ask to appraise PDFs without searching first, Claude will route you back through `ebm-search` so the evidence is verified.

### 走一遍完整流程 · A full run, step by step

**① 檢索與查證（ebm-search）· Search and verify**

Claude 會先把主題沿四個軸展開（縮寫↔全文、慣稱↔生化別名、藥物類別↔藥名↔開發代號、疾病縮寫↔全文），確保各種寫法都撈得到；接著從多個來源檢索、聯集去重、篩掉離題的，再沿著參考文獻逐輪追蹤到不再有新文獻為止；最後逐筆用 Crossref／PubMed 交叉驗證、剔除幻覺引用，交出**三張清單與一份 PDF 報告**。整個過程**每到一個關卡都會停下來回報、等你點頭**，不會一口氣跑完。

Claude expands the topic along four axes (abbreviation↔full term, common name↔biochemical alias, drug class↔drug name↔development code, disease abbreviation↔full name) so every phrasing is caught. It then searches several sources, merges and de-duplicates, screens out off-topic hits, and chases references round by round until nothing new turns up. Finally it cross-verifies each item against Crossref/PubMed, removes hallucinated citations, and delivers **three tables and a PDF report**. It **pauses and reports at every checkpoint**, waiting for your go-ahead rather than running straight through.

**② 交接（handoff）· The handoff**

檢索收尾時，Claude 會把「已經決定好的事」——PICO 雛形、納入／背景的分流、試驗（study）標籤、證據等級、全文取得狀態——寫成一份交接包 `_corpus_seed.json`，放進 `fulltext\<題目_日期>\`，然後問你：「**要繼續進入 EBM 評讀嗎？**」回一句「**繼續**」就接力下去。

When the search wraps up, Claude writes everything already decided — the seed PICO, the included/background split, study tags, evidence levels, and full-text status — into a handoff file `_corpus_seed.json` under `fulltext\<topic_date>\`, then asks: "**continue to the EBM appraisal?**" Reply "**繼續 / continue**" and it carries straight on.

**③ GRADE 評讀（ebm-analysis）· The appraisal**

接力之後，`ingest_seed.py` 會把全文 PDF 複製進 `EBM_Analysis/inputs/`，並先把第 0 階段的分流草稿預填好；接著逐階段評讀，**每個階段都有一個斷點**：

After the handoff, `ingest_seed.py` copies the full-text PDFs into `EBM_Analysis/inputs/` and pre-fills a Phase-0 triage draft. The appraisal then runs stage by stage, **with one checkpoint at each**:

- **Phase 0** — 確定回顧問題（PICO，並補上結果 O 軸），逐篇覆核交接帶來的分流建議。· Lock the review question (PICO, adding the outcome axis), and review the handoff's triage suggestions paper by paper.
- **Phase 1** — 結構化抽取 PICO／樣本數／研究設計，每個關鍵數字都附上原文逐字引用。· Structured extraction of PICO, sample sizes, and design, with each key number quoted from the source.
- **Phase 2** — 過研究誠信關卡，分到 A／B／C 軌，定出 GRADE 的起始確定性。· Run the research-integrity gate, assign tracks A/B/C, and set the starting GRADE certainty.
- **Phase 3** — 逐個 outcome 走完五個下調與三個上調領域，再用「懷疑者」視角做一次對抗式複查。· Work through the five downgrade and three upgrade domains per outcome, then run an adversarial second pass.
- **Phase 4** — 產出單篇報告、跨篇統合，以及 Summary of Findings 表（含絕對效應與 NNT）。· Produce per-paper reports, a cross-study synthesis, and a Summary-of-Findings table (absolute effects and NNT).

所有成品（`.md`／`.pdf`、統合、ledger）都由同一份 cache JSON 渲染，**報告與判定永遠同步、不會漂移**，最後輸出到 `reports\`。

Every deliverable (`.md`/`.pdf`, synthesis, ledger) is rendered from a single cache JSON, so **the reports never drift from the judgments**, and they all land in `reports\`.

### 封存與歸檔 · Archiving a run

評讀做完後，說一句「**封存這次分析**」「**歸檔成 XXX**」或「**封存後清空、準備下一個主題**」，Claude 就會把這次評讀收進 `EBM_Analysis/runs/<日期>_<主題>/`，並讓你選擇要不要清空工作檔、要不要一併產出來源清單。

Once the appraisal is done, say "**archive this analysis**", "**archive it as XXX**", or "**archive, then clear for the next topic**", and Claude files the run under `EBM_Analysis/runs/<date>_<slug>/`, letting you choose whether to clear the working files and whether to generate a sources list.

### 路徑的小規矩 · One path rule worth knowing

工作根永遠是 `EBM_Framework`。子計畫規格裡寫的相對路徑，都是相對於各自的資料夾，所以實際執行時會**自動補上前綴**，例如 `python EBM_Search/scripts/…`、`python EBM_Analysis/tools/…`。這條規則已經寫在 `CLAUDE.md` 與兩個啟動器裡，Claude 會自己遵守。

The working root is always `EBM_Framework`. Relative paths in each sub-project's spec are relative to that sub-project, so at run time they are **automatically prefixed**, e.g. `python EBM_Search/scripts/…` and `python EBM_Analysis/tools/…`. This rule lives in `CLAUDE.md` and both launchers, and Claude follows it on its own.

---

## 安全與隱私 · Security & Privacy

- **秘密集中、永不上傳**：Zotero 金鑰、email、本機絕對路徑都只待在 `config/settings.yaml`，已被 gitignore；版控裡只有 `*.example.yaml` 佔位範本。
  **Secrets are centralized and never pushed**: the Zotero key, email, and local absolute paths live only in `config/settings.yaml` (git-ignored); only `*.example.yaml` placeholders are committed.
- **版權與隱私內容不進 repo**：文獻 PDF 以及 `inputs/`、`cache/`、`outputs/`、`runs/` 一律 gitignore（可能含版權全文與病例資料）。
  **Copyrighted and private content stays out of the repo**: paper PDFs plus `inputs/`, `cache/`, `outputs/`, `runs/` are all git-ignored (they may hold copyrighted text and case data).
- **金鑰優先走環境變數**：`ZOTERO_API_KEY`、`CROSSREF_MAILTO`、`EBM_CONFIG`，不落地最安全。
  **Prefer env vars for secrets**: `ZOTERO_API_KEY`, `CROSSREF_MAILTO`, `EBM_CONFIG`.

---

## 方法學依據 · Methodology

EBM_Analysis 的每一步都逐條對照 **Cochrane Handbook v6.5**：GRADE 起始確定性、五下調與三上調領域、RoB 2 到 GRADE 的映射、異質性、不精確（OIS）、計票三層、NNT/RD 信賴區間，以及對相關 SR/MA 的 AMSTAR 2 評估。EBM_Search 則對齊 **Cochrane 第 4 章與 PRISMA-S／PRISMA 2020**：敏感度優先、不在檢索階段以期刊分位篩選、做引文追蹤、並誠實聲明覆蓋範圍的限制。

Every step of EBM_Analysis is cross-checked against the **Cochrane Handbook v6.5**: starting certainty, the five downgrade and three upgrade domains, the RoB 2→GRADE mapping, heterogeneity, imprecision (OIS), the three-tier vote-counting hierarchy, NNT/RD confidence intervals, and AMSTAR 2 for related reviews. EBM_Search aligns with **Cochrane Ch. 4 and PRISMA-S / PRISMA 2020**: sensitivity-first, no quartile filtering during the search, citation chasing, and an honest statement of coverage limits.

> ⚠️ **一個誠實的提醒**：評讀的判斷終究還是 Claude 做的。雖然有 schema 結構、GRADE 算術重算、跨篇稽核與對抗式複查層層把關，但複查者仍是同一個 Claude，並非真正獨立的第二方。
>
> **An honest caveat**: the appraisal judgments are ultimately Claude's. Despite schema enforcement, GRADE arithmetic re-checks, cross-study audits, and an adversarial pass, the reviewer is still the same Claude — not a genuinely independent second party.
