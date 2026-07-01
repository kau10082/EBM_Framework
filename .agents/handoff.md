# 審查交接簿（Claude Code ⇄ Antigravity）

> 協定見 `review-prompt.md`。輪次：Claude Code 在「## 待審查」記本輪修改＋自審重點（註明審查範圍＝哪幾個檔）；Antigravity 在「## 審查結果」只列當前仍存在的問題（🔴必修／🟡建議／⚪可接受＋檔名行號）；Claude Code 在「## 已處理」逐條結案（✅已修／❌不同意／❓存疑——**不同意紀錄不可刪**）；雙方無法收斂者進「## 僵局待裁決」交使用者。一塊結案後清空待審查/審查結果。

## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊＝「全 repo 品質體檢修正輪」：使用者委託對整個 repo 做 crash／正確性／飄移／分心／資料遺失體檢，除「打包機敏外洩」一項使用者明示保留現狀外，其餘發現全數修正（commit `bf45b5d`）。

**本輪審查範圍：僅以下檔案**（其他檔未動，勿審）：
- 測試/CI：`tests/test_report_data_validate.py`、`tests/test_session_regressions.py`、`tests/test_g7_contract_and_gates.py`（新增）、`tests/test_quote_numeric_guard.py`
- EBM_Search/scripts：`gate_guard.py`、`classify_units.py`、`funnel_check.py`、`selftest_guards.py`、`build_search_report.py`、`build_search_report_data.py`、`fulltext_fetch.py`、`doi_title_audit.py`、`fulltext_audit.py`、`verify_have_fetchable.py`、`fulltext_exhaust.py`、`pmc_fulltext.py`、`xref_verify.py`、`zotero_import.py`、`citation_screen_check.py`、`screen_2b_abstract_check.py`
- EBM_Analysis：`tools/validate.py`、`tools/quote_verify.py`、`tools/audit_consistency.py`、`tools/absrisk.py`、`tools/pdf_to_text.py`、`tools/end_run.py`、`tools/archive_run.py`、`tools/ingest_seed.py`、`tools/build_reports.py`、`tools/build_grade_pdf.py`、`_build_pdf.py`、`schema/phase0_corpus.json`、`schema/phase4_output.json`
- 文件：`SKILL.md`、`.claude/skills/ebm-search/SKILL.md`、`EBM_Search/SEARCH_SPEC.md`、`EBM_Search/README.md`、`EBM_Analysis/ANALYSIS_SPEC.md`、`EBM_Analysis/README.md`、`EBM_Analysis/manifest.yaml`、`EBM_Analysis/guardrails/prisma_reporting.md`、`INTEGRATION.md`
- 其他：`pack_framework.py`（僅修一行寫反的註解，打包行為依使用者指示不變）

主要修正類別（詳見 commit message）：
1. CI 復活：tests 舊 import（build_report_data）致 collection error；補回 OFF_TOPIC 報告表守門（build_search_report_data.validate）。
2. 守門 fail-open 關閉：gate_guard stderr 編碼（cp950 攔截反放行）／壞 JSON fail-closed（_CORRUPT）／g7 rows↔records 契約統一（classify_units.records_of 單一真值層，gate 與報告器一律經此讀）／quote_verify 空轉不得 ✅／doi_title_audit 404 vs 斷網三態分離／flow 數字閉合（funnel_check.check_flow）接進 orchestrator。
3. 正確性：renderer 不再硬編「多中心雙盲平行」與主題敘述；design_detail/evidence_base_label/rob_section/screening_flow 納入 phase4 schema（原設計感知路徑因 additionalProperties:false 是死碼，NRSI 被誤稱 RCT）；validate.py 子 schema 帶根 definitions（$ref crash）；phase0 補 doi/pmid；Unpaywall/PMC 查詢失敗≠來源沒有（lookup_failed 分類、失敗計數）。
4. crash：end_run f-string 反斜線（Py≤3.11 SyntaxError 整支跑不起來）；fulltext_audit/verify_have_fetchable 頂層 list 輸入 AttributeError；build_search_report CID 字型 fallback 斷鏈；xref_verify 空作者 IndexError。
5. 資料保全：end_run 封存碰撞加序號（防 unknown_run 覆蓋 MANIFEST）；archive_run --clear 的 .txt 記名 MANIFEST＋刪除失敗計數回報；end_run reports regex 不再誤抓 report.pdf_output_dir（Search 報告夾）；ingest_seed 不覆蓋 inputs/ 人工 PDF。
6. 文件飄移：SKILL.md 與 SEARCH_SPEC 的 Stage A/B／stage1_check／build_search_pdf／build_report_data 殘留清除或加「已廢除」標記；INTEGRATION /ebm 殘留；ANALYSIS_SPEC/manifest/README 護欄數 36、selfcheck C1-C18 對齊；manifest 補列 robins_i/amstar2/multitrack_integration；EBM_Search/README 重寫對齊 v0.22。

fresh-clone 結果：全新時間戳目錄＋全新 venv（pytest/pypdf/jsonschema/reportlab/pyyaml）→ `pytest -m "not network"` 81 項全過；`absrisk --selftest`／`selftest_guards`／`screen_tiers --selftest`／`selftest_analysis_guards` 全過；Stop-hook 進入點 `gate_guard.py --auto`、`analysis_gate.py --auto` exit 0；全部 .py 可解析（含曾 SyntaxError 的 end_run.py）。

想被重點看／自己不確定的點：
- `funnel_check.check_flow` 的帶號數字解析（+＝加項、無號/−＝扣項；格內非恰 1 數即略過該列）——對某些合法 flow 寫法會不會假 FAIL？
- `gate_guard._recs`（records/results/items 容錯）會不會意外接受不該接受的形狀？
- `verify_have_fetchable` 的整體斷網探測（打 api.crossref.org/types）在防火牆環境的行為。
- `_build_pdf.py` 輸出改名 `FINAL_REPORT_flowchart.pdf`（規格版 FINAL_REPORT.pdf 保留給 build_grade_pdf）——請確認無其他隱性依賴。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

（無。）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
