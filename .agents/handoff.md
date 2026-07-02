# 審查交接簿（Claude Code ⇄ Antigravity）

> 協定見 `review-prompt.md`。輪次：Claude Code 在「## 待審查」記本輪修改＋自審重點（註明審查範圍＝哪幾個檔）；Antigravity 在「## 審查結果」只列當前仍存在的問題（🔴必修／🟡建議／⚪可接受＋檔名行號）；Claude Code 在「## 已處理」逐條結案（✅已修／❌不同意／❓存疑——**不同意紀錄不可刪**）；雙方無法收斂者進「## 僵局待裁決」交使用者。一塊結案後清空待審查/審查結果。

## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【複審】功能塊＝「全 repo 品質體檢修正輪」第 2 輪：針對上一輪審查結果（1🔴/1🟡/2⚪）全數修正。

**本輪審查範圍：僅以下檔案**（其他檔未動，勿審）：
- `EBM_Search/scripts/funnel_check.py`
- `EBM_Search/scripts/gate_guard.py`
- `EBM_Search/scripts/verify_have_fetchable.py`
- `tests/test_g7_contract_and_gates.py`

這次改了什麼、對上一輪哪些項做了什麼：
1. 🔴 `funnel_check.py` 括號細項全加總→假 FAIL：**已修**。excluded 格改「多重解讀候選」`_delta_candidates`——(1) 原樣帶號加減、(2) 剝除括號註記後加減，**任一解讀閉合即通過**（『剔除 15（重複 10、離題 5）』剝括號後算得出 −15；『—（新增 +5）』的加項只在括號內、靠原樣解讀吃到，故兩種解讀都保留）；start/remain 抽數新增 `_single`（剝括號後恰 1 數優先，『核心 26（＋base 8）』→26，該列從「略過」變「可檢」）。真正錯的數字兩種解讀皆不閉合、照樣 FAIL。回歸測試 3 條已釘（細項不假 FAIL／括號加項吃得到／真錯照抓）。
2. 🟡 `gate_guard._recs` 形狀重合（JSON Schema 的 `items`）：**已修**。加嚴為「清單元素必須全為 dict」才視為紀錄；records→results→items 逐鍵檢查。回歸測試已釘（字串清單/schema 物件被拒、正常紀錄照收）。
3. ⚪ `verify_have_fetchable` 斷網探測單一端點：**已修（採納）**。`_network_ok` 改探兩個獨立端點（Crossref→NCBI einfo），單端點被防火牆拒連不誤判斷網。
4. ⚪ `_build_pdf.py` 改名無隱性依賴：審查端已確認無問題，**無需修改**。

上一輪 🔴 清單（原樣帶入，供逐項核對）：
- 🔴 `EBM_Search/scripts/funnel_check.py` 行 61：`_nums` 函數抽出帶號數字的邏輯會將儲存格內的所有數字（包含細項說明的數字）都一併加減。例如 `Excluded: 15 (duplicates: 10, off-topic: 5)` 會計算成 15+10+5 = 30（或扣除 -30），導致符合格式的細分說明反而造成 `delta` 算錯，出現假 FAIL。→ 本輪第 1 項已修。

fresh-clone 結果：全新時間戳目錄＋全新 venv → `pytest -m "not network"` 84 項全過（含本輪新增 4 條回歸）；`selftest_guards` 全過；`gate_guard.py --auto` exit 0。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（無——上一輪 1🔴/1🟡/2⚪ 已全數處理，見「## 已處理」。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

- ✅ 已修：funnel_check `_nums` 把儲存格內所有數字（含括號細項）一併加減→假 FAIL（本輪修改：funnel_check.py 新增 `_delta_candidates`／`_single` 多重解讀＋剝括號抽數；tests/test_g7_contract_and_gates.py 加 3 條回歸測試）
- ✅ 已修：gate_guard `_recs` 對 `items` 鍵容錯可能誤收 JSON Schema 等重合形狀（本輪修改：gate_guard.py `_recs` 加嚴為元素全 dict 才收；加回歸測試）
- ✅ 已修（⚪採納）：verify_have_fetchable 斷網探測依賴單一端點（本輪修改：verify_have_fetchable.py `_network_ok` 改探 Crossref＋NCBI 兩端點）
- ⚪ 確認無虞：`_build_pdf.py` 輸出改名 FINAL_REPORT_flowchart.pdf 無隱性依賴（審查端確認 analysis_gate 與後續驗證相容，無需修改）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）

（無。）
