# 審查交接簿（Claude Code ⇄ Antigravity）

> 協定見 `review-prompt.md`。輪次：Claude Code 在「## 待審查」記本輪修改＋自審重點（註明審查範圍＝哪幾個檔）；Antigravity 在「## 審查結果」只列當前仍存在的問題（🔴必修／🟡建議／⚪可接受＋檔名行號）；Claude Code 在「## 已處理」逐條結案（✅已修／❌不同意／❓存疑——**不同意紀錄不可刪**）；雙方無法收斂者進「## 僵局待裁決」交使用者。一塊結案後清空待審查/審查結果。

## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

**【初審】功能塊：修正 ⑥ PRISMA 流程表中段空格未填 ＋ 流程數字不對帳**

**本輪審查範圍：僅以下檔案**
- `EBM_Search/scripts/build_search_report_data.py`
- `EBM_Search/scripts/build_search_report.py`

**問題背景**：使用者實跑 SITT-vs-delayed-SITT 主題、產出 ⑥ PDF 後回報「PRISMA 流程中間有空格沒填清楚」。追因＝`build_search_report_data.py` 組流程數字時用了**與實際 `g2b_screen.json`／`g6_verified.json` 不符的鍵名**，讀不到值→格子留空、且數字不對帳。

**這次改了什麼（3 處，皆在 build_search_report_data.py 的 flow 數字段）**：
1. **②b 保留/剔除數**（原 line 176）：原本只讀 `g2b.get("survivors")`／`g2b.get("dropped")`，但實際 `g2b_screen.json` 無此鍵（用 `records`＋verdict kept/removed，計數鍵為 `kept_count`/`removed`）→ ②b「remain」與 ③「start」全空。改為**優先由 `records` 的 verdict 實算**，缺 records 才退回數值型計數鍵；並**特意排除直接取 `kept`/`survivors`**（這些在某些 run 是『清單』而非數字，直接 `str()` 會把整個 list 印進格子）。
2. **撤稿/無法驗證數**（line 64-65）：原讀 `r.get("verify")`，但 ⑤a 落檔 `g6_verified.json` 用的是 `verdict` 鍵 → retracted/unverified 恆為 0。改用 `_vv(r)=r.get("verify") or r.get("verdict")`（與 `gate_guard` 同樣相容寫法），並把 **UNRESOLVED**（無 PMID/DOI 可驗）一併計入 unverified。
3. **④ 引文追蹤新增切題數**（原 line 195）：原讀 `g4.get("n_new_concordant")`（我方檔案無此鍵）→ 恆顯示「+0」、流程不對帳（③ 22 vs ⑤b 9+15=24 對不上）。改為相容讀 `n_new_concordant`／`new_切題`／`g4_citation_tracking.json` 的 `new_relevant`／`g4.hits`。
   並同步把 ⑤a 流程語意由「UNVERIFIED 保留」改為「撤稿＋無法驗證皆剔除、不入分析」（與 `gate_guard.check_unverified_excluded`「UNVERIFIED 不得入⑤b」一致；remain 改為扣掉 retracted＋unverified）。

**另一處（`build_search_report.py`，同屬本 ⑥ 報告功能塊）**：PDF 渲染後回寫 `pdf_path` 用的是**相對路徑**（`cache/...`）。Stop hook 的 `gate_guard --auto --hook` 由 **repo 根**（`CLAUDE_PROJECT_DIR`）執行，相對路徑解析失敗→誤報「Phase1 PDF 不存在」。已改為登記 `os.path.abspath(out_pdf)`（絕對路徑），不受 CWD 影響。實測：自 repo 根跑 `gate_guard --auto --hook` 由 FAIL 轉 PASS（exit 0）。

**改後實測（本 run cache 重新產出）**：PRISMA 六列全部填滿且端到端對帳：
`1279 → ②b −92 →1187 → ③ −980離題−185皆無 →切題22 → ④ +3 →25 → ⑤a −1無法驗證 →24 → ⑤b 背景15→核心9`。`gate_guard --cache` 全 PASS、`build_search_report.py` 重產 PDF 成功（含 CJK 字型）。

**想被重點看 / 自己不確定的點**：
- (a) ⑤a 語意改動：把「UNVERIFIED 保留」改為「剔除」是否與 spec 一致？我的依據是 `check_unverified_excluded`（UNVERIFIED 不得入⑤b/交接/Zotero）＝實際就是剔除，原報告器文字「保留」與 gate 矛盾，故改。請確認此解讀。
- (b) 相容鍵名取值順序是否有遺漏的 run-schema 變體（特別是 `kept` 可能為 list 的防呆）。
- (c) **fresh-clone 限制（據實說明）**：此修改在 `build_search_report_data.py`，其輸出依賴本 run 的 cache 產物（g0~g7），無法在空 fresh-clone 有意義單獨重跑；本輪以「同一份 cache 重新產出報告＋全 gate PASS＋PDF 重產成功」為證，非空跑。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

（無。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
