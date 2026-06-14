# EBM_Framework — Claude Code 專案指引

實證醫學（EBM）管線，兩個子計畫整合為一：**EBM_Search**（多源檢索＋Crossref/PubMed 交叉驗證、去幻覺）→ **EBM_Analysis**（GRADE 評讀、Claude 即引擎、無外部 API）。本框架有兩種用法：**(a) 當 Claude Code 專案**開啟使用；**(b) 用 `pack_framework.py` 打包成單一 skill**（`EBM_Framework_skill.zip`）匯入 **Claude Desktop**（已上傳，skill 名 `ebm-framework`）。兩種模式並存。

## 工作根與路徑規則（重要）
- **工作目錄＝本資料夾 `EBM_Framework`**（使用者在 Claude Code 開啟的專案根）。
- 子計畫的規格／腳本以**子計畫為相對基準**書寫；從本根執行時**一律加前綴**：
  - EBM_Search：`python EBM_Search/scripts/<x>.py …`
  - EBM_Analysis：`python EBM_Analysis/tools/<x>.py …`，規格讀 `EBM_Analysis/phases|guardrails|schema/…`
- 子計畫各自的 `inputs/ cache/ outputs/ runs/` 都在各自資料夾下（已被各自 `.gitignore`）。

## 單一入口（已取消 `/ebm`）
- **一切從 `ebm-search` 開始**：對某主題先做檢索＋交叉驗證。觸發詞如「幫我查文獻／建立可信引用清單／驗證引用」。
- **EBM 評讀（`ebm-analysis`）不獨立啟動**：只能由 `ebm-search` 收尾的「**是否繼續進入 EBM 分析？**」回「繼續」接力，或處理「封存／歸檔」。`/ebm` 已徹底移除（無 `ebm` skill 資料夾）。
- 若使用者沒先檢索就要直接評讀 PDF → **不冷啟動評讀**，導引先用 `ebm-search`（確保證據經查證、定必含軸）。

## Skill 位置
`.claude/skills/ebm-search/` 與 `.claude/skills/ebm-analysis/` 為**薄啟動器**（攜帶觸發 description ＋ 路徑前綴規則），各自指向子計畫的完整規格正本：
- 入口規格：[`EBM_Search/SEARCH_SPEC.md`](EBM_Search/SEARCH_SPEC.md)
- 評讀規格：[`EBM_Analysis/ANALYSIS_SPEC.md`](EBM_Analysis/ANALYSIS_SPEC.md)

## 機敏／個人設定（單一真值來源）
- 全部集中在 **[`config/settings.yaml`](config/settings.example.yaml)**（**gitignored**，在兩個 git 子репо之外、不進任何打包）：Zotero 金鑰、Crossref email、本機輸出路徑、`analysis.project_dir`、字型等。範本＝`config/settings.example.yaml`。
- 腳本以 `default_settings_path()` 解析：env `EBM_CONFIG` > 根 `config/settings.yaml` > 子計畫本地 `config/`（回退）。
- **委任版控的檔案皆無個資**；要分享/打包只帶 `*.example.yaml`。

## 對外工作資料夾（成品／打包／人工補全文）
都放在 **`<Windows 文件>\EBM_Framework\`** 底下（實際絕對路徑為個資、只存在根 `config/settings.yaml`，勿寫進任何 committed 檔）：
- `reports\` — 成品 PDF（EBM_Search 檢索報告、EBM_Analysis 評讀報告）＝ `report.pdf_output_dir`／`analysis.pdf_output_dir`
- `fulltext\<題目_日期>\` — 人工補全文 PDF ＋ 交接包 `_corpus_seed.json` ＝ `report.fulltext_dir`
- `packages\` — 打包 ZIP（選用）＝ `packaging.output_dir`

## 交接層（Search → Analysis）
EBM_Search 收尾寫交接包 `_corpus_seed.json`（契約 `EBM_Search/references/corpus_seed_schema.json`）→ `EBM_Analysis/tools/ingest_seed.py` 複製 PDF 進 `EBM_Analysis/inputs/`＋預填 Phase 0 草稿 `cache/_corpus.draft.json`，Phase 0 斷點覆核後定稿。映射規則與端到端流程見 **[`INTEGRATION.md`](INTEGRATION.md)**。

## 慣例
- 改 skill／規格後**在 Claude Code 即時生效**（重開或重新載入即可，**無需打包上傳**）。
- 保留兩邊「**逐階段停頓、逐關確認**」的設計；交接的建議值非定稿、仍須覆核。
