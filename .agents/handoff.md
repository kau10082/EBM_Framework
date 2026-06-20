## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【本輪性質】**唯讀盤點報告（冗贅/效率，尚未修改任何程式）** — 依使用者「不造成 crash／正確性／漂移／分心／資料遺失」的前提，找安全的清理機會並先送審。

**盤點範圍：** 55 個版控內 .py（`_run_tmp/` 為 untracked＋已 gitignored，**不在範圍**，只是 throwaway run script，無須處理）。用 2 個唯讀 Explore agent 分別掃 `EBM_Search/scripts/` 與 `EBM_Analysis/tools/`＋人工複核關鍵點。

**總結論：repo 已相當有紀律。** 未發現 dead code、未用 import（`build_reports.py` 的 `csv` 一度被誤報未用、實際 line 130 有用）、O(n²)、或任何 crash／正確性／資料遺失隱患。可改的多為「跨檔小重複」，但**多數不建議動**（理由見下）。

---

### A. 唯一明確值得做、且零風險（已人工驗證）
**A1. `EBM_Analysis/_build_pdf.py` 同檔重複的字形對照表**（line 51–52 `_GLYPH_TR0` 與 line 82–84 `_GLYPH_SAFE`/`_GLYPH_TR`）
- 兩份 `maketrans` 映射**逐字元完全相同**（已比對：`≈→≒、≥→≧、≤→≦、−→-、◯→○、↔→／、⇔→／、▸→•、►→•`）；兩個函式 `_strip_bricks`（line 56）與 `safe_glyphs`（line 85）邏輯幾乎一致（差別僅後者多 `(s or '')` 空值保護）。
- **為何安全：** 同一檔內、純資料/純函式去重，無跨模組耦合；合併成單一 dict＋單一函式（保留 `(s or '')` 保護）後行為不變。
- **建議：** 可做（合併為一份 `_GLYPH_SAFE`＋一個 `safe_glyphs`，`_strip_bricks` 改呼叫它）。**仍須以 `render_smoketest.py`／實際渲染一張 PDF 驗證無磚塊再算數。**

### B. 真實存在但「不建議動」（耦合/漂移/分心 > 價值）
- **B1. UTF-8 console 樣板** `try: sys.stdout.reconfigure("utf-8") except: pass`（搜尋端 ~9 檔、分析端 ~11 檔）。
- **B2. 迷你 `_load()` JSON 讀取器**（gate_guard/analysis_gate 用 `_load(p)`；build_stage1_corpus/build_report_data 用 `_load(cache,f)`——**簽章本就不同**，非真正可直接共用）。
- **B3. `_norm_doi()`** 重複 2 份（`gate_guard.py:58`、`verify_have_fetchable.py:30`）。
- **B4. settings.yaml 路徑解析/讀取器** 在 `journal_quartile.py`/`fulltext_fetch.py`/`zotero_import.py` 以「try import xref_verify，except 本地 fallback」存在。
- **B5. `end_run.py` 與 `archive_run.py` 各自解析 `pdf_output_dir`**（與 `workdir.py` 的解析邏輯亦重疊）。
- **為何不建議動（共同理由）：** 把這些抽成共用 `lib_common.py`/`workdir` helper，等於對多個**目前可獨立執行**的腳本新增一條硬 import 依賴。B4 的「try-import-否則本地 fallback」是**刻意的韌性設計**（打包成 Desktop skill、子計畫單獨 clone 時仍能跑）；硬性集中化反而**降低韌性、且正是使用者要避免的「漂移/分心」**。這些重複都是 2–3 行、無狀態、零風險的樣板，留著比抽走更安全。

### C. 看似可優化、實則應略過
- **C1. `gate_guard.py` 同一份 cache JSON 被多個 check 各自 `_load` 重讀**：理論上可在 `run()` 載入一次再傳入；但這需要改所有 check 函式簽章＝**會動到守門結構、有漂移風險**，且檔案都很小（KB 級）、Stop hook 也只偶爾跑 → **明確略過**。
- **C2. 各種 metadata enrichment / schema 驗證的相似 fallback 鏈**（zotero_import vs verify_have_fetchable；verify_all 的 schema 驗證）：語意與 API 合約不同，合併會**模糊意圖**＝分心 → 略過。

---

**建議結論：** 只採 **A1**（同檔字形表去重，做完用渲染煙霧測試驗證）。**B、C 全部維持現狀**。

**【結案狀態，2026-06】審查核可：只做 A1、B/C 擱置。A1 已實作並驗證：**
- 動到的檔（唯一）：`EBM_Analysis/_build_pdf.py`——把同檔重複的 `_GLYPH_TR0`/`_strip_bricks`（早期 load-time 用）與 `_GLYPH_SAFE`/`_GLYPH_TR`/`safe_glyphs`（後段 render 用）**合併為單一 `_GLYPH_SAFE`＋`_GLYPH_TR`＋`safe_glyphs`**（保留 `(s or '')` 空值保護），`_deep_safe` 改呼叫 `safe_glyphs`。淨刪 6 行。
- 驗證：`py_compile` OK；**行為等價證明**——對同一批輸入（全部 9 個字形＋emoji＋GRADE 符號 ●●●○/①②③＋None＋混合文字）跑「舊邏輯 vs 新合併邏輯」輸出**逐筆完全相同**（emoji 一律剔除、字形正確替換、`None`→`''` 更安全）。
- 渲染煙霧測試說明：完整 GRADE PDF 需有效 `_synthesis.json`（目前無分析 run、無此 cache），故無法現render；惟 (a) 行為與現行可正常出 PDF 的程式**逐位元相同**＝不可能產生新磚塊；(b) `_build_pdf.py` 自帶磚塊稽核（line 395-401）＋`analysis_gate`/`verify_all` 會在**下次真實分析 run 自動 smoke-test**。
- B/C：依審查「強烈同意維持現狀」，未動任何一處。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

- ✅ 已執行：A1 `_build_pdf.py` 同檔重複字形表/函式合併（審查核可）。py_compile＋行為等價證明（舊≡新，逐筆相同）通過；完整 render 待下次真實分析 run 自動 smoke-test（無 synthesis cache 無法現render，已誠實說明）。
- ✅ 已確認（維持現狀）：B 類（UTF-8 樣板／`_load`／`_norm_doi`／settings 載入器／pdf 路徑解析跨檔小重複）與 C 類（gate_guard 重讀小 JSON／enrichment·schema fallback 鏈）——審查「強烈同意維持現狀」，依不過度工程/改動最小化全部不動。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
