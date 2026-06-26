# 審查交接簿（Claude Code ⇄ Antigravity）

> 協定見 `review-prompt.md`。輪次：Claude Code 在「## 待審查」記本輪修改＋自審重點（註明審查範圍＝哪幾個檔）；Antigravity 在「## 審查結果」只列當前仍存在的問題（🔴必修／🟡建議／⚪可接受＋檔名行號）；Claude Code 在「## 已處理」逐條結案（✅已修／❌不同意／❓存疑——**不同意紀錄不可刪**）；雙方無法收斂者進「## 僵局待裁決」交使用者。一塊結案後清空待審查/審查結果。

## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-26（第九輪【初審】）本輪審查範圍＝3 檔
- **新增 `EBM_Analysis/tools/fulltext_title_audit.py`**
- **修改 `EBM_Analysis/tools/selftest_analysis_guards.py`**（加此守門回歸）
- **修改 `EBM_Analysis/phases/00_triage.md`**（步驟 5 加『進抽取前必跑內容稽核』鐵律）

**動機（使用者糾正而立）**：EBM_Search ⑤a 有 `doi_title_audit`／`check_doi_title_audited` 守『DOI↔標題』，但
**EBM_Analysis 這側（補全文→抽取）完全沒有「本機全文的實際內容是否就是該 paper_id 那篇」的稽核**。實測 base
`10.23736_s0026-4806.21.07623-0`（標題「…an **updated** NMA」）的 inputs .txt/.pdf 其實是另一篇 Edris
「…a **systematic review and** NMA」的誤存（與另一 base 重複內容）——這種「內容放錯 paper_id」會**靜默通過、
直接進 GRADE 抽取**。先前是人工逐筆 Crossref＋讀 PDF 才抓到；現補成 committed 守門。

**設計**：對每篇 base 有本機全文者——
  • `own`＝自己標題最長連續片段在『前 8000 字』出現比例；
  • `best_other`＝其他 base 標題在『首頁前 1500 字』出現的最高比例（只看開頭，避免被內文引用別篇標題誤判）；
  • `own ≥ OK(0.62)` → ok；否則 `best_other ≥ STRONG(0.65)` 且 `best_other − own ≥ MARGIN(0.18)` → **mismatch**
    （開頭是別篇的標題＝內容放錯）；其餘 → unverifiable（標題缺如，多為 .txt 截掉封面；只警示不阻擋）。
  保守設計：只在『明確是別篇』時才 FAIL，標題找不到只降級 unverifiable、不誤殺。

**驗證**：`fulltext_title_audit.py --selftest` 5 案全過（內容放錯→mismatch 且正確指出來源 paper_id／正確全文→ok／
自己標題在內文→ok／標題缺如→unverifiable 不誤殺／無檔→no_fulltext）。對**實機 12 base 實跑**：正確攔下
`s0026-4806`（🔴 mismatch，best_other→`s12931-019-1138-3` Edris），5 篇 PDF→ok、6 篇 .txt(封面被截)→unverifiable、
**0 誤報**。`selftest_analysis_guards.py`＝「全部分析端守門有效」。repo 單一副本(無 AppData 分身)。**尚未 commit。**

**請 Antigravity 審查**：(a) 門檻 OK/STRONG/MARGIN 是否穩健——尤其 base NMA 互相引用時，別篇標題出現在
**首頁前 1500 字**會不會把正確全文誤判 mismatch（目前靠 own≥OK 先放行＋best_other 只看 head 緩解，是否足）；
(b) `_lcs_frac` 用最長連續片段比例，對副標題缺失/標點差異是否過嚴或過鬆；(c) 是否該把它從『Phase 0 步驟必跑＋
selftest 回歸』再升成像 `gate_guard` 那樣的 Stop-hook 機器 gate（分析端目前無 Stop-hook gate 基建，需評估）。

### 2026-06-26（第十輪【初審】）本輪審查範圍＝3 檔
- **修改 `EBM_Analysis/tools/build_grade_pdf.py`**（🔴 跳脫 bug ＋ 2 項版型增強）
- **修改 `EBM_Analysis/tools/build_reports.py`**（MD 同步增強，與 PDF 同資料源）
- **修改 `EBM_Analysis/tools/selftest_analysis_guards.py`**（加跳脫回歸）

**動機**：產 FINAL_REPORT 時連續 failed＝**真 committed bug** ＋ 使用者另提 2 項版型要求：
1. **(🔴 會 crash) PDF 渲染器未跳脫 XML 特殊字元**：`build_grade_pdf` 的 `P()`／`cell()` 只做 TOFU 淨化(`_safe`)、
   **未跳脫 `< > &`**。任何資料含字面 `<`（如 SoF 的 `<MCID`、`<10研究`）會被 reportlab paragraph parser 當成標籤
   → `ValueError: Parse error: saw </para> instead of </font>` → PDF 產不出（這就是先前一直 failed 的根因）。
   且 `TOFU_MAP` 把 `≤→'<='` 反而**引入** `<`，更易觸發。
2. **(🟡 標題不符分析法) RoB2 段標題寫死「Risk of Bias 2」**：本案為 Overview（單位＝SR/NMA/MAIC），用 RoB2 名稱不當；
   使用者要求隨分析法改（AMSTAR2／MAIC）。
3. **(🟡 缺篩選流程) 報告最前缺 PRISMA 篩選流程**：使用者要求表格最前新增文獻篩選 section。

**修正**：
1. 新增 module 級 `_markup(t)`＝`_safe`(TOFU)→跳脫 `& < >`→**還原白名單行內標籤**(`<b>/<i>/<sup>/<sub>/<br/>`)；
   `P()`／`cell()` 改用 `_markup`（不再用 `_safe`）。刻意粗體仍有效、資料含 `<` 不再崩潰。
2. 第 2 段標題/前言/欄名改**資料驅動**：讀 `syn.rob_section.{title,intro,columns}`，無則回退 RoB2 預設（通用、換主題自適用）。
3. 新增 `syn.screening_flow`（PRISMA-style）→ 渲染為**第 0 段**（cochrane5 layout，置於納入特徵表之前）。
   `build_reports.py` 同步加 MD 版的『〇、文獻篩選流程』與資料驅動的第二段標題（PDF/MD 同格式同源）。

**驗證**：以含字面 `<` 的 `_synthesis.json` 重產 → **成功**（266→271KB、4 頁、tofu 0）；篩選流程數字(1,061→921→切題517→3 anchors)、
AMSTAR2 標題、新欄名、`<MCID` 皆正確顯示。`render_smoketest` 另揪出 **C11 SoF 須含死亡**（已補全因死亡列＋腳註 h，誠實標『未綜整、事件罕見』）。
`selfcheck_consistency` ✅、`render_smoketest` ✅、`selftest_analysis_guards`（新增跳脫回歸 `_markup` 跳脫 `<>&` 且保留 `<b>`）✅。**尚未 commit。**

**請 Antigravity 審查**：(a) `_markup` 白名單還原是否會被資料中字面 `<b>` 誤觸（極罕見，可接受？）；(b) `rob_section` 欄名代換
（AMSTAR2 關鍵領域塞進 RoB2 欄位）是否清楚、或應另設 Overview 專用版面；(c) screening_flow 數字應否由工具自 `_search_report.flow`＋
analysis funnel 自動帶入（目前手填於 `_synthesis.json`，有漂移風險）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

（第 1–8 輪審查已全數結案、Antigravity 複審通過、防線完整，本簿已清空。歷史處置可由 git log 追溯：
最後一筆 `eca3f8a`「fix(review): address Antigravity rounds 4-8」。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
