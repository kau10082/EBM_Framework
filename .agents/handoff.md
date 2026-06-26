# 審查交接簿（Claude Code ⇄ Antigravity）

> 協定見 `review-prompt.md`。輪次：Claude Code 在「## 待審查」記本輪修改＋自審重點（註明審查範圍＝哪幾個檔）；Antigravity 在「## 審查結果」只列當前仍存在的問題（🔴必修／🟡建議／⚪可接受＋檔名行號）；Claude Code 在「## 已處理」逐條結案（✅已修／❌不同意／❓存疑——**不同意紀錄不可刪**）；雙方無法收斂者進「## 僵局待裁決」交使用者。一塊結案後清空待審查/審查結果。

## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-26（第十一輪【初審】）本輪審查範圍＝2 檔
- **修改 `EBM_Analysis/tools/analysis_scope.py`**（補全文夾改 honor config＋掃描偵測＋selftest）
- **修改 `EBM_Analysis/phases/00_triage.md`**（更正補全文夾解析說明）

**動機（使用者問『補充全文 PDF 資料夾在哪』而揭露）**：`analysis_scope.write_need_manual_list` 把 `需補全文清單.txt`
**寫死** `<inputs>/_fulltext_supplement`，**完全沒讀 config 的 fulltext_dir** → 與 00_triage『根 config fulltext_dir，
留空才回退』的宣稱不符（設定 vs 行為不一致）。深挖另發現：00_triage 與舊認知都寫 `analysis.fulltext_dir`，但
使用者實際設的鍵在 **`report.fulltext_dir`**（`settings.example.yaml` 兩鍵並存：`analysis.fulltext_dir`＝Phase0 補全文
專用、`report.fulltext_dir`＝人工補全文＋交接包根）——使用者只設了後者，故即使讀 config 也會落空。

**修正**：
1. 新增 `_supplement_dir(inputs_dir)`，三層解析：(1) `run_state.paths.fulltext_dir`（交接包 per-topic 夾，補件與
   `_corpus_seed.json` 同處）→ (2) config `analysis.fulltext_dir` **或** `report.fulltext_dir`（取一，附 `/<slug>` 子夾
   避免跨主題覆蓋）→ (3) 回退 `<inputs>/_fulltext_supplement/`。`write_need_manual_list` 與 `compute` 改用之，scope
   多回 `supplement_dir`，need-list 抬頭印出實際路徑。
2. `_has_fulltext` 加參數 `sup_dir`，**同時掃 inputs/ 與補全文夾**——使用者把 PDF 丟進補全文夾即被偵測為『有全文』，
   免再手動搬進 inputs（本輪即實測：上一主題是我手動 cp 補件→inputs 才被認到）。
3. `00_triage.md` 更正：補全文夾解析說明改為 `_supplement_dir` 三層、鍵名更正為 `report.fulltext_dir`。

**驗證**：`analysis_scope.py --selftest`（新增）4 案全過（補全文夾 PDF/夠長txt 被偵測、過短摘錄不算、皆無檔→無、
`_supplement_dir` 回 Path）；實機 `_supplement_dir` 現正確解析到 `…\OneDrive\文件\EBM_Framework\fulltext`（原本永遠回
inputs 後援）。`selftest_analysis_guards` 全綠。repo 單一副本。**尚未 commit。**

**請 Antigravity 審查**：(a) 補全文夾用 `/<run_state.slug>` 子夾，但交接包子夾名是 EBM_Search 的 `<題目_日期>` 格式
（與 slug 不同）→ 唯有 `run_state.paths.fulltext_dir`（branch 1）能精準與交接包同夾；branch 2 的 slug 子夾可能另開一夾。
是否該讓 ingest/handoff 確保把『交接包實際夾』寫進 `run_state.paths.fulltext_dir`，使 branch 1 永遠命中？(b) `analysis`
與 `report` 兩個 fulltext_dir 鍵語意重疊，是否該在 spec/example 釐清何者為 Phase0 補全文唯一真相。

### 2026-06-26（第十二輪【初審】）本輪審查範圍＝5 檔（落實先前 2 項延後 🟡 增強）
- **新增 `EBM_Analysis/tools/build_screening_flow.py`**（R10c：screening_flow 自動化）
- **修改 `EBM_Analysis/tools/build_reports.py`**（渲染前自動帶入 screening_flow）
- **修改 `EBM_Analysis/tools/analysis_gate.py`**（R9c：內容稽核升 Stop-hook 硬 gate）
- **修改 `EBM_Analysis/tools/fulltext_title_audit.py`**（加 `--out` 落檔供 gate 讀）
- **修改 `EBM_Analysis/phases/00_triage.md`**（步驟 5 命令補 `--out cache/_fulltext_audit.json`）

**動機**：處理 Antigravity 第 9–10 輪採納為待辦的 2 項 🟡 增強。先前『分析端無 Stop-hook gate 基建』的前提
**已過時**——`analysis_gate.py` 早已是分析端輕量 Stop-hook 守門（比照 search 端 gate_guard）。

**A. screening_flow 自動化（R10c：防手填漂移）**
  `build_screening_flow.build()`：檢索漏斗自 `_search_report.json` 的 `flow`（位置同 prisma_audit：
  `run_state.paths.fulltext_dir/_search_report.json`）＋分析尾段自 `_corpus.json` grade_track 計數（最終 anchors＝
  full(＋targeted_harms)、降背景＝light_summary）衍生；找不到檢索報告則優雅降級。`merge_into_synthesis()` 預設
  **僅當缺漏才寫**（手填值保留；`--force`/`--refresh-flow` 才覆寫）。`build_reports.main` 渲染前自動帶入。

**B. 內容稽核升硬 gate（R9c）**
  `fulltext_title_audit.py` 加 `--out` 把結果（含 `mismatch` 計數＋清單）落 `cache/_fulltext_audit.json`；
  `analysis_gate.check_fulltext_content_audited`：**定稿階段(stage∈FINAL_MARKERS)＋有 base＋_synthesis 已在**時，
  缺 `_fulltext_audit.json` 或 `mismatch>0` → FAIL（離線讀產物、不連網不跑子程序，比照 search 端
  `check_doi_title_audited`）。已併入 `analysis_gate.run` 的檢查串。

**驗證**：`build_screening_flow --selftest`（4 案：漏斗+尾段組裝／anchor 標註／無報告降級／merge 三態）✅；
`analysis_gate --selftest`（PDF gate 2 案＋內容稽核 gate 3 案：缺產物 FAIL／mismatch FAIL／乾淨放行）✅；
`fulltext_title_audit --selftest` ✅；`selftest_analysis_guards` ✅；5 檔 py_compile 全過、import OK。**尚未 commit。**

**請 Antigravity 審查**：(a) screening_flow 分析尾段僅自 corpus 推『最終 anchors＋降背景數』，中間態(候選→收斂)
無法自動還原——這樣的『漏斗＋單一尾段』是否足夠，或該另記 Phase 0 各階段計數供完整還原；(b) 內容稽核 gate 綁
`FINAL_MARKERS` 定稿觸發，但 `_fulltext_audit.json` 是否該在 inputs 仍在時(Phase 0)就強制存在、而非等定稿才檢；
(c) `build_reports` 自動覆寫策略（缺漏才填、手填優先）是否合理。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

（第 1–10 輪審查已全數結案、Antigravity 複審通過、防線穩健，本簿已清空。歷史處置由 git log 追溯。
最後相關 commit：`8106649`。第 9–10 輪 Antigravity 皆 ⚪/接受，另有 2 項 🟡『未來增強』已採納為待辦、不阻擋：
 - 🟡(R9c) 待 EBM_Analysis 端有 Stop-hook 攔截基建時，把 `fulltext_title_audit` 由『Phase 0 必跑＋selftest』升為硬性 gate。
 - 🟡(R10c) `screening_flow` 數字目前手填於 `_synthesis.json`，宜由合成工具自動從 `_search_report.flow`＋分析漏斗帶入以防漂移。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
