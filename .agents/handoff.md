## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】
- **功能塊**：把三條「檢索守門鐵律」從靠記性落為機器 gate／修好失效的 hook（triple vs dual COPD 案逐一被使用者糾正而立）：
  - **(A) 對照軸純度（comparator purity）**：檢索 query 只含 `in_query=true` 軸（P 疾病＋I 介入），**禁止對照軸 C（`in_query=false`）同義詞出現在任何腿 query**（否則砍掉標題/摘要沒提對照組的研究、傷 recall；C 軸留待 ③ 讀全文比對）。緣由：Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」。
  - **(B) 四軸展開必須真的做（axis expansion）**：四軸展開是鐵律，但既有 `axis_coverage_check` 只驗「每腿 query ≥1 同義詞命中」，**攔不到「同義詞庫根本沒展開」**（P 只寫 COPD、I 只寫 triple therapy 也會通過）。故新增稽核 **g0.axes 同義詞庫本身**：每條 in_query/mandatory_screen 軸須 ≥3 別名且含全文形式。緣由：第一版策略同義詞過於稀疏、未做四軸展開。
  - **(C) Stop hook 找不到 cache → 自動守門靜默失效（最嚴重）**：Stop hook 跑 `gate_guard.py --auto --hook` 不帶 `--cache`，靠 `_find_cache(None)` 自動發現；舊版只看 run_state＋硬編 Windows 路徑 `~/OneDrive/文件/...`，在本環境（cache 在 `EBM_Search/cache/<topic>/`、無 run_state、非 Windows）一律回 `None` → `_active(None)=False` → hook **靜默 exit 0**，整輪自動守門等同未啟用（gates 僅因人工 `--cache` 才跑到）。修法：新增 `_find_active_cache_by_flag()`——掃 repo 內 `EBM_Search/cache/*/` 找帶 `_search_active.flag` 的進行中 cache，列為 `_find_cache` 的**首要**發現法（哨兵旗標＝地真值，與 run_state/env/OneDrive 無關）。
- **動到哪些檔（本輪審查範圍：僅以下檔案）**：
  1. `EBM_Search/scripts/comparator_purity_check.py`（新增；(A) 核心判定）
  2. `EBM_Search/scripts/axis_expansion_check.py`（新增；(B) 核心判定）
  3. `EBM_Search/scripts/gate_guard.py`（新增 `check_comparator_purity`、`check_axis_expansion` 並掛進 `_all_checks`；(C) 新增 `_find_active_cache_by_flag` 並插為 `_find_cache` 首要發現法）
  4. `EBM_Search/scripts/selftest_guards.py`（新增三 gate 各自的「會 FAIL／防誤報」自測；(C) 旗標發現＋無旗標休眠回歸）
  5. `EBM_Search/SEARCH_SPEC.md`（補「四軸展開」「對照軸純度」「Stop hook 必須找得到 cache」三條鐵律，對齊已落地 gate）
- **fresh-clone／實跑結果**：
  - `python selftest_guards.py` → 全綠（含 (A)(B) 各自 FAIL/防誤報、(C)「旗標 cache 找得到→通過」「無旗標→回 None 休眠」），結尾「✅ 全部守門有效。」
  - (C) 實證：修復前 `gate_guard._find_cache(None)` 回 `None`、`--auto --hook` 在本案進行中 cache 上仍 exit 0（dormant）；修復後 `_find_cache(None)` 正確回 `…/cache/triple_vs_dual_copd`，且對「帶旗標＋故意壞 g0」的暫時 cache 跑 `--auto --hook` → **exit 2（正確擋下）**。
  - `python gate_guard.py --cache <本案 cache>` → Gate⓪ 策略核准／取盡／策略遵從／四軸覆蓋／四軸展開／對照軸純度 全 ✅。
- **想被重點看 / 不確定的點**：
  1. **(A) 遮蔽法防誤判**：比對 C 軸前先把所有 in_query 軸同義詞（長詞優先）從 query 遮蔽，讓 I 軸長詞（`ICS/LABA/LAMA`）內含的 C 子字串（`LABA/LAMA`）不被誤判。是否仍有跨邊界漏洞？
  2. **(B) 門檻 ≥3＋至少一全文形式**：刻意採低門檻（不要求塞滿 N 個，與 axis_coverage 設計一致避免 fail-closed）；是否足以擋稀疏策略又不誤殺高階 MeSH/CT.gov 字數受限的軸？
  3. **(C) 多個進行中 cache**：`_find_active_cache_by_flag` 在有多個帶旗標 cache 時取最近修改者；是否需要更嚴（例如同時禁止多旗標並存）？另：把旗標掃描列為 `_find_cache` 首要（早於 run_state）是否會在「run_state 指向 A、旗標在 B」時造成非預期切換？（判斷：旗標＝進行中地真值，應優先）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修：檢索 query 摻入對照軸 C 砍 recall 的 bug（triple vs dual COPD 案，Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」）。本輪修改：(1) 把該案 g0_strategy.json 各腿 query 改為只含 P＋I；(2) 新增 `comparator_purity_check.py` 並掛進 gate_guard，使「C 軸進 query」之偏離今後一律被機器攔下（含 ⓪ 策略階段）；(3) selftest 加兩條自測證明守門有效且不誤報；(4) SEARCH_SPEC 補鐵律對齊。

✅ 已修：四軸展開（鐵律）第一版沒做、且既有 `axis_coverage_check` 只驗「query ≥1 同義詞」攔不到稀疏同義詞庫的 bug。本輪修改：(1) 把該案 g0_strategy.json 各軸同義詞補成完整四軸展開（成分 INN／開發代號／品牌／疾病別名）；(2) 新增 `axis_expansion_check.py` 直接稽核 g0.axes 同義詞庫「真的展開」（≥3 別名且含全文形式），掛進 gate_guard 於 ⓪ 策略階段生效；(3) selftest 加三條自測（兩 FAIL＋一防誤報）；(4) SEARCH_SPEC 補「四軸展開必須真的做」鐵律對齊。

✅ 已修（嚴重）：Stop hook 自動守門靜默失效——`gate_guard.py --auto --hook` 無 `--cache` 時 `_find_cache(None)` 在本環境（cache 在 `EBM_Search/cache/<topic>/`、無 run_state、非 Windows，硬編 OneDrive 路徑不存在）一律回 `None` → hook exit 0 dormant，整輪檢索自動守門等同未啟用（gates 僅靠人工 `--cache` 跑到）。這正是使用者觀察到「過程中斷」追查時發現的真 bug（中斷現象本身＝harness context 自動摘要，非 repo bug）。本輪修改：(1) 新增 `_find_active_cache_by_flag()` 掃 `EBM_Search/cache/*/_search_active.flag` 找進行中 cache，插為 `_find_cache` 首要發現法（哨兵旗標＝地真值，不依賴 run_state/env/OneDrive）；(2) selftest 加「旗標 cache 找得到／無旗標回 None 休眠」回歸；(3) 實證修復後 hook 對帶旗標＋壞 g0 的 cache 正確 exit 2、對本案通過的 cache exit 0；(4) SEARCH_SPEC 補「Stop hook 必須找得到 cache」鐵律。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
