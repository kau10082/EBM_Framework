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

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

（第 1–8 輪審查已全數結案、Antigravity 複審通過、防線完整，本簿已清空。歷史處置可由 git log 追溯：
最後一筆 `eca3f8a`「fix(review): address Antigravity rounds 4-8」。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
