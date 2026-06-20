## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】
- **功能塊**：把兩條「檢索策略鐵律」從靠記性落為機器 gate（triple vs dual COPD 案逐一被使用者糾正而立）：
  - **(A) 對照軸純度（comparator purity）**：檢索 query 只含 `in_query=true` 軸（P 疾病＋I 介入），**禁止對照軸 C（`in_query=false`）同義詞出現在任何腿 query**（否則砍掉標題/摘要沒提對照組的研究、傷 recall；C 軸留待 ③ 讀全文比對）。緣由：Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」。
  - **(B) 四軸展開必須真的做（axis expansion）**：四軸展開是鐵律，但既有 `axis_coverage_check` 只驗「每腿 query ≥1 同義詞命中」，**攔不到「同義詞庫根本沒展開」**（P 只寫 COPD、I 只寫 triple therapy 也會通過）。故新增稽核 **g0.axes 同義詞庫本身**：每條 in_query/mandatory_screen 軸須 ≥3 別名且含全文形式。緣由：第一版策略同義詞過於稀疏、未做四軸展開。
- **動到哪些檔（本輪審查範圍：僅以下檔案）**：
  1. `EBM_Search/scripts/comparator_purity_check.py`（新增；(A) 核心判定）
  2. `EBM_Search/scripts/axis_expansion_check.py`（新增；(B) 核心判定）
  3. `EBM_Search/scripts/gate_guard.py`（新增 `check_comparator_purity`、`check_axis_expansion`，並掛進 `_all_checks`）
  4. `EBM_Search/scripts/selftest_guards.py`（新增兩 gate 各自的「會 FAIL」與「防誤報」自測）
  5. `EBM_Search/SEARCH_SPEC.md`（在防搶跑 gate 段後補「四軸展開」與「對照軸純度」兩條鐵律，對齊已落地 gate）
- **fresh-clone／實跑結果**：
  - `python selftest_guards.py` → 全綠（含四軸展開「P 裸詞→FAIL」「I 純縮寫無全文→FAIL」「兩軸展開→通過」、對照軸純度「摻 C→FAIL」「I 含 C 子字串→不誤判」），結尾「✅ 全部守門有效。」
  - `python axis_expansion_check.py` / `python comparator_purity_check.py`（對本案 g0）→ 皆 ✅。
  - `python gate_guard.py --cache <本案 cache>` → 新關「Gate⓪ 四軸展開」「Gate⓪／① 對照軸純度」皆 ✅（g0 存在即稽核，⓪ 策略階段就生效）。
- **想被重點看 / 不確定的點**：
  1. **(A) 遮蔽法防誤判**：比對 C 軸前先把所有 in_query 軸同義詞（長詞優先）從 query 遮蔽，讓 I 軸長詞（`ICS/LABA/LAMA`）內含的 C 子字串（`LABA/LAMA`）不被誤判。是否仍有跨邊界漏洞？
  2. **(B) 門檻 ≥3＋至少一全文形式**：刻意採低門檻（不要求塞滿 N 個，與 axis_coverage 設計一致避免 fail-closed）；是否足以擋稀疏策略又不誤殺高階 MeSH/CT.gov 字數受限的軸？
  3. **生效時機**：兩 gate 在 g0 存在（manifest 缺席時 (A) 退回 g0.legs）即稽核 → ⓪ 策略階段就攔，不必等廣蒐。請確認此早觸發不與只看 manifest 的既有 gate 衝突。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修：檢索 query 摻入對照軸 C 砍 recall 的 bug（triple vs dual COPD 案，Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」）。本輪修改：(1) 把該案 g0_strategy.json 各腿 query 改為只含 P＋I；(2) 新增 `comparator_purity_check.py` 並掛進 gate_guard，使「C 軸進 query」之偏離今後一律被機器攔下（含 ⓪ 策略階段）；(3) selftest 加兩條自測證明守門有效且不誤報；(4) SEARCH_SPEC 補鐵律對齊。

✅ 已修：四軸展開（鐵律）第一版沒做、且既有 `axis_coverage_check` 只驗「query ≥1 同義詞」攔不到稀疏同義詞庫的 bug。本輪修改：(1) 把該案 g0_strategy.json 各軸同義詞補成完整四軸展開（成分 INN／開發代號／品牌／疾病別名）；(2) 新增 `axis_expansion_check.py` 直接稽核 g0.axes 同義詞庫「真的展開」（≥3 別名且含全文形式），掛進 gate_guard 於 ⓪ 策略階段生效；(3) selftest 加三條自測（兩 FAIL＋一防誤報）；(4) SEARCH_SPEC 補「四軸展開必須真的做」鐵律對齊。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
