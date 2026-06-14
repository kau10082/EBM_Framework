# EBM_Search

> Evidence-retrieval engine for an evidence-based-medicine (EBM) pipeline.
> Three-source literature search **+** Crossref / PubMed cross-verification **→** three structured, de-hallucinated tables.
>
> EBM 實證醫學管線的「**證據引擎層**」：三源文獻檢索 ＋ Crossref／PubMed 交叉驗證 → 產出三張去幻覺的結構化清單。

*(Skill name: `EBM_Search` · engine formerly named `consensus-verify` · zero-dependency Python 3.8+)*

---

## English

**What it does** — Given a topic or claim, it finds the literature, verifies each item actually exists, strips hallucinated citations, grades evidence type, and outputs three tables (core / rejected) plus APA references and a portable PDF report.

**Pipeline**
1. **Topic → four-axis expansion** (abbreviation↔full, common↔biochemical/gene alias, class↔drug(INN)↔code, disease abbreviation↔full) — recall every way the literature is written.
2. **Three-source retrieval** — `C` Consensus (multi-phrasing) · `PM` PubMed MCP (deep, Boolean OR, tiered narrowing when >60 hits) · `OE` OpenEvidence (`oe_ask`, citations carry embedded Crossref validation). Per-leg diagnosable status report.
3. **Union & dedupe** (key: DOI → normalized title + first author + year).
4. **Q1 journal quality gate** (SCImago SJR; default Q1-only, Q2↓ kept in list-3, labeled).
5. **Topic filter (①′)** — original topic is decomposed into **mandatory conjunction axes** locked before expansion; every candidate is judged against *all* axes (+ year window + polarity). Missing an axis → list-3 with the missing axis named.
6. **Cross-verification** — Crossref + PubMed, independent sources; anti-hallucination disambiguation (title similarity ≥ 0.85). verdict ladder: RETRACTED > VERIFIED > PARTIAL > UNVERIFIED > UNRESOLVED > OFF_TOPIC.
7. **Output** — list-1 (retrieval funnel + reconciliation identity `M+(B+Q+V)=U`), list-2 (Q1 verified core + APA), list-3 (rejected, with reason), and a **PDF report** documenting the exact search terms used.

**Design** — zero third-party dependencies (stdlib `urllib`/`json`/`difflib`), source-independent verdict combiner, "no silent drops" (any narrowing/excluded item is declared), backward-compatible.

## 中文

**用途** — 給一個主題或主張，自動找文獻 → 驗證是否真實存在 → 剔除幻覺引用 → 標證據等級 → 產出三表（核心／剔除）＋ APA 參考 ＋ 可攜 PDF 報告。

**流程**
1. **主題 → 四軸展開**（縮寫↔全文／慣稱↔生化·基因別名／類別↔藥名(INN)↔代號／疾病縮寫↔全文）——召回文獻的各種寫法。
2. **三源檢索** — `C` Consensus（多措辭）·`PM` PubMed MCP（Boolean OR 深抓，命中 >60 分層收窄）·`OE` OpenEvidence（`oe_ask`，引用自帶 Crossref 驗證）。逐腿可診斷狀態回報。
3. **聯集去重**（鍵：DOI → 正規化標題＋第一作者＋年）。
4. **Q1 期刊品質閘**（SCImago SJR；預設只留 Q1，Q2↓ 完整列入清單三並標分位）。
5. **離題篩選（①′）** — 原始主題拆成**必含連言軸**、展開前鎖死；逐篇比對*全部*必含軸（＋年份窗＋極性）。缺任一軸 → 清單三並標明缺哪軸。
6. **交叉驗證** — Crossref＋PubMed 來源獨立；反幻覺消歧（標題相似度 ≥ 0.85）。verdict 階層：RETRACTED > VERIFIED > PARTIAL > UNVERIFIED > UNRESOLVED > OFF_TOPIC。
7. **輸出** — 清單一（檢索流程漏斗＋對帳恆等式 `M+(B+Q+V)=U`）、清單二（Q1 已驗證核心＋APA）、清單三（剔除＋原因），及一份**逐字記錄檢索用詞的 PDF 報告**。

**設計** — 零第三方相依（標準庫 `urllib`/`json`/`difflib`）、來源獨立判定、「不靜默吞掉」（任何收窄/剔除都申報）、向後相容。

---

## Structure / 檔案結構

> **本子計畫在 EBM_Framework 內僅於 Claude Code 運作**（入口 skill＝`EBM_Framework/.claude/skills/ebm-search/`，指向本資料夾的 `SKILL.md`）。不再打包成 Claude Desktop skill。設定集中於 **`EBM_Framework/config/settings.yaml`**（根，gitignored）；腳本以 `default_settings_path()` 解析（env `EBM_CONFIG` > 根 config > 本地回退）。

```
EBM_Search/
├── SKILL.md                     # 完整規格（workflow, rules, changelog）/ 由框架 ebm-search 啟動器載入
├── scripts/
│   ├── xref_verify.py           # Crossref + PubMed cross-verification engine / 交叉驗證引擎（含 default_settings_path）
│   ├── journal_quartile.py      # SCImago SJR quartile gate / 期刊分位品質閘
│   ├── zotero_import.py         # Zotero archiving (Crossref-enriched) / Zotero 歸檔
│   ├── fulltext_fetch.py        # Legal OA full-text fetch (Unpaywall + PMC) / 合法 OA 全文
│   ├── build_corpus_seed.py     # 交接層：寫 _corpus_seed.json 給 EBM_Analysis / handoff
│   └── pack_skill.py            # （選用）安全 ZIP 打包器；Claude-Code-only 下平常用不到
├── config/
│   └── settings.example.yaml    # 指向根 config 的薄指標（真值集中於 EBM_Framework/config/settings.yaml）
└── references/
    ├── output_schema.json       # 引擎輸出 schema
    └── corpus_seed_schema.json  # 交接契約
```

## Security / 安全

- **No secrets in this repo.** 真實金鑰（Crossref mailto、NCBI key、Zotero API key）只存在於 **`EBM_Framework/config/settings.yaml`（根、git-ignored、在本子репо之外）**；版控/分享只含 `*.example.yaml` 佔位範本。
- 金鑰建議優先走環境變數（`ZOTERO_API_KEY`／`CROSSREF_MAILTO`／`EBM_CONFIG`），不落地最安全。
- 若日後仍要打包外送：`python scripts/pack_skill.py`（正斜線、排除真值檔）——**勿**用 PowerShell `Compress-Archive`；且根 config 不在本資料夾內、本就不會被打包。
