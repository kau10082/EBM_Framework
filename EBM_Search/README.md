# EBM_Search

> Evidence-retrieval engine for an evidence-based-medicine (EBM) pipeline (v0.22).
> Six-leg high-sensitivity literature search **+** tiered strict screening **+** Crossref / PubMed cross-verification **→** de-hallucinated corpus, a 5-section PDF report, and a handoff seed for GRADE appraisal.
>
> EBM 實證醫學管線的「**證據引擎層**」（v0.22）：六腿高敏感檢索 ＋ 分層嚴格篩選 ＋ Crossref／PubMed 交叉驗證 → 去幻覺語料、5 段固定版型 PDF 報告、交接包 `_corpus_seed.json`。

*(Skill name: `EBM_Search` · engine formerly named `consensus-verify` · zero-dependency Python 3.8+)*

---

## English

**What it does** — Given a topic, it runs a systematic-review-aligned search (recall first, 寧留勿殺 — grey literature is never a reason to exclude), screens candidates in tiers against mandatory conjunction axes, verifies every included item actually exists (anti-hallucination), and hands a verified corpus to the GRADE appraisal stage.

**Pipeline (v0.22 — the authoritative step numbering lives in `SEARCH_SPEC.md`)**
1. **⓪ Strategy** — four-axis expansion (abbreviation↔full, common↔biochemical alias, class↔INN↔code, disease abbr↔full); the strategy (including the SR-filter decision) must be approved by the user before any retrieval (machine-gated).
2. **① Six-leg retrieval** — Consensus · PubMed · OpenEvidence · Europe PMC · OpenAlex · ClinicalTrials.gov; paginated to exhaustion, per-leg status; union & dedupe by stable `uid`.
3. **②b High-sensitivity title+abstract screen** (title-only rejection is machine-blocked).
4. **③ Strict off-topic screen, Tier 1–4** (abstract → registry/AI synthesis → forced full-text fetch → Unpaywall) — "off-topic" may only be decided after real full-text retrieval; the no-content bucket requires machine-auditable fetch proofs.
5. **④ Citation tracking** to convergence (title+abstract screened, machine-gated).
6. **⑤ Post-convergence** — ⑤a Crossref+PubMed cross-verification incl. retraction & DOI↔title audit (`doi_title_audit.py`); ⑤b inclusion-unit classification (`classify_units.py`; core vs background, no grey "pending" bucket); ⑤c Zotero import; ⑤d manual full-text folder.
7. **⑥ Report** — deterministic data build (`build_search_report_data.py`) → **5-section PDF** (params / verbatim strings / PRISMA flow / included list / ongoing trials) with machine-checked format and flow-number closure; **⑦ handoff** `_corpus_seed.json` → EBM_Analysis.

**Design** — zero third-party dependencies for the engine (stdlib `urllib`/`json`/`difflib`; `reportlab` only for the PDF), every stop point and red line is enforced by `gate_guard.py` (Stop-hook capable), "no silent drops", journal quartile (`journal_quartile.py`) is **descriptive labeling only — not an exclusion gate**.

## 中文

**用途** — 給一個主題，跑「與系統性回顧對齊」的高敏感檢索（recall 優先、寧留勿殺——灰文獻不得作排除理由）→ 分層嚴格篩選（必含連言軸）→ 逐筆查證真實存在（去幻覺）→ 產出 5 段固定版型 PDF 報告與交接包，接力 GRADE 評讀。

**流程（v0.22；步驟編號唯一權威＝`SEARCH_SPEC.md`）**
1. **⓪ 策略**：四軸展開；策略（含 SR filter 決定）須經使用者核准才可檢索（機器看守防搶跑）。
2. **① 六腿廣蒐**：Consensus·PubMed·OpenEvidence·Europe PMC·OpenAlex·ClinicalTrials.gov，翻頁取盡、逐腿回報，跨腿以穩定 `uid` 去重聯集。
3. **②b 高敏初篩**：標題＋摘要（嚴禁只憑標題剔除，機器看守）。
4. **③ 嚴格離題篩 Tier 1–4**：摘要→登錄/AI 合成→強制實取全文→Unpaywall；「離題」只能在實取全文後定案，「全文及摘要皆無」須帶可稽核的實抓證明。
5. **④ 引文追蹤**至收斂（同樣標題＋摘要篩，機器看守）。
6. **⑤ 收斂後處理**：⑤a Crossref＋PubMed 交叉驗證（含撤稿剔除、DOI↔標題稽核 `doi_title_audit.py`）；⑤b 決定納入單位（`classify_units.py`，核心 vs 背景、無灰色 pending 桶）；⑤c Zotero 匯入；⑤d 人工補全文資料夾。
7. **⑥ 報告＋⑦ 交接**：`build_search_report_data.py` 確定性組資料 → **5 段固定版型 PDF**（參數／逐字檢索字串／PRISMA 流程／納入清單／進行中試驗），版型與流程數字閉合皆機器看守；交接包 `_corpus_seed.json` → EBM_Analysis。

**設計** — 引擎零第三方相依（標準庫 `urllib`/`json`/`difflib`；PDF 需 `reportlab`）；所有停頓點與紅線由 `gate_guard.py` 統一看守（可掛 Stop hook）；「不靜默吞掉」；期刊分位（`journal_quartile.py`）**只作描述性標註、不是排除閘**。

---

## Structure / 檔案結構

> **本子計畫是 EBM_Framework 的檢索引擎**；完整規格＝本資料夾的 `SEARCH_SPEC.md`，由框架的**單一 skill `ebm-framework`**（根 `SKILL.md`，可打包匯入 Claude Desktop）載入，亦可在 Claude Code 專案模式下由 `.claude/skills/ebm-search/` 啟動器載入。設定集中於 **`EBM_Framework/config/settings.yaml`**（根，gitignored）；腳本以 `default_settings_path()` 解析（env `EBM_CONFIG` > 根 config > 本地回退）。

```
EBM_Search/
├── SEARCH_SPEC.md                     # 完整規格（workflow, rules, changelog）/ 由框架 ebm-search 啟動器載入
├── scripts/
│   ├── gate_guard.py            # 總守門 orchestrator（停頓點/取盡/撤稿/⑤b/報告版型/流程閉合；可掛 Stop hook）
│   ├── xref_verify.py           # Crossref + PubMed cross-verification engine / 交叉驗證引擎（含 default_settings_path）
│   ├── doi_title_audit.py       # ⑤a DOI↔標題一致性稽核（防手填錯 DOI）
│   ├── classify_units.py        # ⑤b 決定納入單位（records_of＝g7 統一讀取層）
│   ├── screen_tiers.py / *_check.py  # ③ 分層篩選可重用器與各機器 gate（selftest_guards.py 回歸）
│   ├── fulltext_exhaust.py / pmc_fulltext.py / fulltext_fetch.py / fulltext_audit.py / verify_have_fetchable.py
│   │                            # 全文管道窮盡（Tier3/4）、PMC 速率限制、OA 抓取、have 實抓驗證
│   ├── build_search_report_data.py / build_search_report.py  # ⑥ 5 段報告：資料確定性組出 → PDF 渲染
│   ├── journal_quartile.py      # SCImago SJR 分位標註（描述性，非排除閘）
│   ├── zotero_import.py         # Zotero archiving (Crossref-enriched) / Zotero 歸檔
│   ├── build_corpus_seed.py     # 交接層：寫 _corpus_seed.json 給 EBM_Analysis / handoff
│   └── pack_skill.py            # （選用）子計畫單獨打包器；整框架打包改用根 pack_framework.py
├── config/
│   └── settings.example.yaml    # 指向根 config 的薄指標（真值集中於 EBM_Framework/config/settings.yaml）
└── references/
    ├── output_schema.json       # 引擎輸出 schema
    ├── search_report_schema.json # ⑥ 5 段報告資料契約
    └── corpus_seed_schema.json  # 交接契約
```

## Security / 安全

- **No secrets in this repo.** 真實金鑰（Crossref mailto、NCBI key、Zotero API key）只存在於 **`EBM_Framework/config/settings.yaml`（根、git-ignored、在本子репо之外）**；版控/分享只含 `*.example.yaml` 佔位範本。
- 金鑰建議優先走環境變數（`ZOTERO_API_KEY`／`CROSSREF_MAILTO`／`EBM_CONFIG`），不落地最安全。
- 若日後仍要打包外送：`python scripts/pack_skill.py`（正斜線、排除真值檔）——**勿**用 PowerShell `Compress-Archive`；且根 config 不在本資料夾內、本就不會被打包。
