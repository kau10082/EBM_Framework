# EBM_Framework

> 問一個醫療問題，它幫你找齊相關研究、確認每篇都真實存在、評估證據可不可信，再整理成一份報告。在 Claude Code 裡用白話就能啟動。
>
> Ask a medical question, and it finds the relevant research, confirms each study really exists, judges how trustworthy the evidence is, and writes you a report — all started in plain language inside Claude Code.

---

## 這個工具在做什麼 · What it does

當你想知道「某個藥對某個病到底有沒有用、證據夠不夠強」時，通常得翻過一大堆醫學研究，還得小心 AI 會「掰」出根本不存在的論文。這個工具替你把這件事做完：

你用白話問一句，它就會——

1. 到多個醫學資料庫**找出相關研究**；
2. **一篇篇查證是不是真的**，把假的、查無實據的剔除掉；
3. 依國際通用的標準**評估這些證據可不可信**（醫學界稱為 GRADE）；
4. 最後給你一份**整理好的報告**。

When you want to know whether a treatment actually works for a condition — and how strong the evidence is — you normally have to wade through piles of medical studies, and watch out for AI inventing papers that don't exist. This tool does that work for you. Ask one question in plain language, and it will:

1. **find the relevant research** across several medical databases;
2. **check each study one by one** and drop anything fake or unverifiable;
3. **judge how trustworthy the evidence is**, using the internationally recognized standard (known as GRADE);
4. hand you a **tidy report** at the end.

---

## 它扮演的角色 · Its role

它是一個**實證醫學的助手**：把「找文獻 → 查證 → 評分 → 寫報告」這串繁瑣又容易出錯的工作，變成一條有條理、可重複的流程。它在**每個步驟都會停下來，把結果攤給你看、問你要不要繼續**——你看過、點頭，它才往下走。

它是來**輔助**你做判斷的，不是取代專業判讀。最後的結論仍應由你把關。

It acts as an **evidence-based-medicine assistant**: it turns the tedious, error-prone chain of "search → verify → grade → report" into an orderly, repeatable flow. At **every step it pauses, shows you what it found, and asks whether to continue** — it only moves on once you've looked and agreed.

It is here to **support** your judgment, not replace expert reading. The final call remains yours.

---

## 怎麼用 · How to use

1. 在 Claude Code 裡**開啟這個資料夾**（`EBM_Framework`）。
2. 用白話對它說，例如：「**幫我對〈某個主題或藥物〉做 EBM 分析**」「**幫我查文獻**」「**幫我查證這個說法有沒有根據**」。
3. 它會**分階段進行**，每做完一段就停下來回報、問你是否繼續；你確認後它才往下。中途它會問你一次「**檢索做完了，要不要接著做證據評估？**」，回「**繼續**」即可。
4. 全部做完後，報告會放在你電腦「**文件**」夾的 `EBM_Framework\reports` 裡（PDF／Markdown）。

> 你**只要會用白話描述問題**就能用，不需要懂底下的技術。下面的〈安裝與設定〉是給**要自己把這套裝起來**的人看的。

1. **Open this folder** (`EBM_Framework`) in Claude Code.
2. Just talk to it in plain language, e.g. "**do an EBM analysis on ⟨a topic or drug⟩**", "**find me the literature**", "**check whether this claim is supported**".
3. It runs **stage by stage**, pausing to report after each one and asking whether to continue; it proceeds only once you confirm. Midway it asks once, "**the search is done — shall I go on to appraise the evidence?**" — reply "**繼續 / continue**".
4. When everything is finished, the reports land in your **Documents** folder under `EBM_Framework\reports` (PDF / Markdown).

> You only need to be able to **describe your question in plain words** — no technical knowledge required. The **Setup** section below is for people who want to **install and run the system themselves**.

---
---

# 安裝與設定（要自己架設才需要看）· Setup (only if you're installing it yourself)

> 以下開始才是技術細節。一般使用者可以略過。
> The technical details start here. Everyday users can skip this part.

## 前置需求 · Prerequisites

| 項目 · Item | 說明 · Notes |
|---|---|
| **Claude Code** | 本工具只在 Claude Code 內運作。· Runs only inside Claude Code. |
| **Python 3.8+** | 檢索部分的腳本零第三方相依（純標準庫）。· The search scripts have zero third-party dependencies (stdlib only). |
| **檢索用 MCP · Search MCPs** | 找文獻會用到 **Consensus**、**PubMed** 等 MCP，建議再加 **OpenEvidence**（設定見下方〈[連接檢索用的 MCP](#連接檢索用的-mcp--connecting-the-search-mcp-servers)〉）。· Finding literature uses MCP servers such as **Consensus** and **PubMed**, with **OpenEvidence** recommended (see below). |

## 第一次設定 · First-time setup

### 1. 取得程式碼，並在 Claude Code 開啟 · Clone, then open in Claude Code

```bash
git clone https://github.com/kau10082/EBM_Framework.git
```

請在 Claude Code 裡**把 `EBM_Framework` 整個資料夾當成專案根來開**（不要只開某個子資料夾），這樣兩個功能（檢索與評讀）才會被自動偵測到。

In Claude Code, **open the whole `EBM_Framework` folder as the project root** (not a sub-folder) so both halves (search and appraisal) are auto-detected.

### 2. 建立你的設定檔 · Create your settings file

所有金鑰與個人路徑都集中在**同一個檔案**：`config/settings.yaml`。它已被排除在版控之外，**永遠不會上傳**。複製範本後填入你的值：

All keys and personal paths live in **one single file**, `config/settings.yaml`, which is kept out of version control and **never uploaded**. Copy the template and fill in your values:

```powershell
# 在 EBM_Framework 根目錄執行 · run from the EBM_Framework root
Copy-Item config/settings.example.yaml config/settings.yaml
```

### 3. 逐欄填寫 · Fill in the fields

| 區段.欄位 · Field | 必填？· Required | 說明 · Description |
|---|---|---|
| `crossref.mailto` | 建議 · recommended | 一個聯絡用 email，讓 Crossref 把你放進 polite pool；這**不是金鑰**。環境變數：`CROSSREF_MAILTO`。· A contact email for Crossref's polite pool — **not** an API key. |
| `pubmed.ncbi_api_key` | 否 · no | 走 PubMed MCP 時留空即可；只有要在本機直連 E-utilities 提速才需要。環境變數：`NCBI_API_KEY`。· Leave empty when using PubMed MCP; only for direct local E-utilities. |
| `zotero.api_key` | 選用 · optional | **真正的秘密**。只有要把納入清單歸檔到 Zotero 時才需要；建議改用環境變數 `ZOTERO_API_KEY`。· A **real secret**, only for archiving into Zotero. Prefer the env var `ZOTERO_API_KEY`. |
| `zotero.library_id` · `library_type` · `collection_key` | 選用 · optional | 你的 Zotero userID（數字）、`user`/`group`、目標 collection 的 8 碼 key。· Your Zotero userID, library type, and target collection key. |
| `epistemonikos.api_token` | 選用 · optional | 系統性回顧專庫腿的免費 token，需向 `dev@epistemonikos.org` 申請；留空則此腿略過。· Free token for the Epistemonikos leg; if empty, that leg is skipped. |
| `source.mode` · `matching.*` · `verdict.*` | 否 · no | 驗證行為參數（非機敏）；一般保留預設即可。· Verification behaviour (not sensitive); defaults are fine. |
| `report.pdf_output_dir` | 是 · yes | 檢索報告 PDF 的輸出夾，建議 `<文件>\EBM_Framework\reports`。· Where the search-report PDFs go. |
| `report.fulltext_dir` | 是 · yes | 人工補全文 PDF 與交接檔的存放基底；建議 `<文件>\EBM_Framework\fulltext`。· Base folder for manual full-text PDFs and the handoff file. |
| `packaging.output_dir` | 否 · no | 打包檔的輸出夾（平常用不到）；建議 `<文件>\EBM_Framework\packages`。· Where packaging files go (rarely needed). |
| `analysis.project_dir` | 是 · yes | `EBM_Analysis` 資料夾的絕對路徑（屬個資）。· Absolute path to the `EBM_Analysis` folder (personal). |
| `analysis.pdf_output_dir` | 是 · yes | 評讀報告 PDF 的輸出夾，建議 `<文件>\EBM_Framework\reports`。· Where appraisal-report PDFs go. |
| `analysis.cjk_font` | 是 · yes | PDF 報告用的中文字型路徑，例如 `C:/Windows/Fonts/msjh.ttc`。· CJK font path for PDF reports. |

> **設定檔是怎麼被找到的 · How the settings file is located** — 依序找，第一個存在的就採用 · checked in order, first match wins：
> ① 環境變數 `EBM_CONFIG` → ② 根目錄 `config/settings.yaml`（平常就是這個）→ ③ 子資料夾本地的回退。
> 整體優先序：**指令旗標 ＞ 環境變數 ＞ settings.yaml ＞ 內建預設**。· Precedence: **CLI flags ＞ env vars ＞ settings.yaml ＞ defaults**.

### 4. 建好放成品的資料夾 · Create the output folders

成品報告、打包檔、人工補全文都收在你「文件」夾的 `EBM_Framework\` 底下（工具會自動建立，也可先手動開好）：

Reports, packages, and manual full-text PDFs all live under `EBM_Framework\` in your Documents folder (the tools create these on demand):

```
<文件 · Documents>\EBM_Framework\
├── reports\                # 成品報告 · reports
├── fulltext\<題目_日期>\    # 人工補全文 + 交接檔 · manual full-text + handoff file
└── packages\               # 打包檔（選用）· packages (optional)
```

### 5.（選用）安裝評讀用的小工具 · (Optional) install appraisal helpers

評讀的運算核心就是 Claude 本身，**不需要任何 LLM API key**。只有「完整模式」會用到幾個小工具：

The appraisal engine is Claude itself, so **no LLM API key is needed**. Only "full mode" uses a few helpers:

```bash
pip install -r EBM_Analysis/requirements.txt   # jsonschema · PyYAML · pymupdf · pypdf
pip install reportlab                            # 只有要產 PDF 報告時 · only for PDF reports
```

檢索部分不需要 `pip install`（純標準庫）。· The search part needs no `pip install` (stdlib only).

---

## 連接檢索用的 MCP · Connecting the search MCP servers

找文獻會用到幾個 MCP server。它們都是**每台機器各自連、屬於你的 Claude Code 環境，不會放進這個 repo**。每條檢索腿都會回報狀態，所以**只連上其中幾個也能跑**——沒連到的會被標示「跳過」。評讀部分完全不需要 MCP。

Finding literature uses a few MCP servers. They are **connected per-machine as part of your own Claude Code setup, never committed to this repo**. Each leg reports its status, so **it runs even if you connect only some** — any leg you skip is marked "skipped". The appraisal part needs no MCP at all.

> 在 Claude Code 加 MCP 的方式：`claude mcp add <名稱> -- <啟動指令>`，或直接編輯使用者層的 `~/.claude.json`。
> To add an MCP in Claude Code: `claude mcp add <name> -- <launch-command>`, or edit the user-level `~/.claude.json`.

### Consensus MCP

提供 AI 整理過的候選文獻（以 `Consensus:search` 呼叫）。它屬「待查證的來源」，真偽一律交給 Crossref／PubMed 把關。依 Consensus 官方的 MCP 說明連上。

Supplies AI-curated candidate papers (called via `Consensus:search`); a "to-be-verified" source whose existence is always checked against Crossref/PubMed. Connect it per Consensus's official MCP instructions.

### PubMed MCP

提供 `search_articles`、`get_article_metadata`、`get_full_text_article` 等工具，同時用於檢索與查證。連上任一可用的 PubMed／NCBI MCP 即可。

Provides tools like `search_articles`, `get_article_metadata`, `get_full_text_article`, used for both search and verification. Connect any working PubMed/NCBI MCP.

### OpenEvidence MCP（建議 · recommended）

採用社群維護的 **[`htlin222/openevidence-mcp`](https://github.com/htlin222/openevidence-mcp)**——**非官方、免 API key**，透過你**已登入的瀏覽器分頁**查詢 OpenEvidence；回傳的引用自帶 **BibTeX ＋ Crossref 驗證**。

Uses the community-maintained **[`htlin222/openevidence-mcp`](https://github.com/htlin222/openevidence-mcp)** — **unofficial, no API key** — querying OpenEvidence through your **already-logged-in browser tab**; its citations come with **BibTeX + Crossref validation**.

**安裝 · Install**（需 Node.js ≥ 20、Python 3）：

```bash
git clone https://github.com/htlin222/openevidence-mcp.git
cd openevidence-mcp
make all                       # 裝相依、建 server＋relay 擴充、註冊進 Claude/Codex
# 只想註冊到 Claude Code： make install-claude-global
```

**登入（一次性）· Authenticate (one-time)**：到 `chrome://extensions` 開啟「開發人員模式」→「載入未封裝」選 `extension/dist`，並在該瀏覽器**保持登入 openevidence.com、分頁不關**。檢查連線：

In `chrome://extensions`, enable Developer mode → Load unpacked → pick `extension/dist`, then **stay logged into openevidence.com and keep the tab open**. Check the connection:

```bash
curl -s http://127.0.0.1:8787/health      # 預期 expect: {"ok":true,"connected":true,...}
```

> ⚠️ OpenEvidence 以美國為中心、已退出歐盟與英國；非美國使用者請先確認可存取，不能用時此腿自動跳過。
> OpenEvidence is US-centric and has withdrawn from the EU/UK; non-US users should confirm access first — the leg auto-skips when unavailable.

### 免設定的來源 · No-setup sources

**ClinicalTrials.gov、OpenAlex、Europe PMC** 由腳本直接走公開 API，**免金鑰、不需 MCP**。**Epistemonikos** 需要一個免費 token（填在 `config/settings.yaml`），留空則略過。

**ClinicalTrials.gov, OpenAlex, Europe PMC** are called directly over public APIs — **keyless, no MCP**. **Epistemonikos** needs a free token (set in `config/settings.yaml`); leave it empty to skip.

---

## 安全與隱私 · Security & Privacy

- **秘密集中、永不上傳**：金鑰、email、本機路徑只待在 `config/settings.yaml`（已排除在版控之外）；版控裡只有 `*.example.yaml` 範本。· Secrets (key, email, local paths) live only in `config/settings.yaml` (kept out of version control); only `*.example.yaml` templates are committed.
- **版權與隱私內容不進 repo**：文獻 PDF 以及 `inputs/`、`cache/`、`outputs/`、`runs/` 一律排除（可能含版權全文與病例資料）。· Paper PDFs and `inputs/`, `cache/`, `outputs/`, `runs/` are all excluded (they may hold copyrighted text and case data).

---

## 給想深入的人 · For the curious

評讀流程逐條對照國際標準 **Cochrane Handbook v6.5** 與 **GRADE**；檢索流程對齊 **Cochrane 第 4 章與 PRISMA-S／PRISMA 2020**（敏感度優先、做引文追蹤、誠實聲明覆蓋限制）。完整規格見 `EBM_Search/SKILL.md`、`EBM_Analysis/ANALYSIS_SPEC.md`，整合流程見 `INTEGRATION.md`。

The appraisal is cross-checked against the **Cochrane Handbook v6.5** and **GRADE**; the search aligns with **Cochrane Ch. 4 and PRISMA-S / PRISMA 2020**. Full specs are in `EBM_Search/SKILL.md` and `EBM_Analysis/ANALYSIS_SPEC.md`; the integration is in `INTEGRATION.md`.

> ⚠️ **誠實的提醒**：評讀的判斷終究是 Claude 做的。雖然有多道結構與複查把關，但複查者仍是同一個 Claude，不是真正獨立的第二方；結論請務必由你或專業人員覆核。
> **An honest caveat**: the appraisal judgments are ultimately Claude's. Despite several structural checks and a review pass, the reviewer is the same Claude — not a truly independent second party; please have a human expert confirm the conclusions.
