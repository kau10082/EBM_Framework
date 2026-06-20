## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】
- **功能塊**：新增機器 gate「對照軸純度（comparator purity）」——強制檢索 query 只含 `in_query=true` 的軸（P 疾病軸＋I 介入軸），**禁止對照軸 C（`in_query=false`）的同義詞出現在任何腿的 query**。緣由：triple vs dual COPD 案，檢索策略連兩版被擅自把「versus dual therapy LABA/LAMA」（C 軸）塞進 Consensus／OpenAlex query → 會砍掉標題/摘要沒提對照組的研究、嚴重傷 recall。使用者要求修正並落為「之後不可再犯」的機器看守。
- **動到哪些檔（本輪審查範圍：僅以下檔案）**：
  1. `EBM_Search/scripts/comparator_purity_check.py`（新增；核心判定）
  2. `EBM_Search/scripts/gate_guard.py`（新增 `check_comparator_purity`，並掛進 `_all_checks`）
  3. `EBM_Search/scripts/selftest_guards.py`（新增此 gate 的「會 FAIL」與「防誤報」兩條自測）
  4. `EBM_Search/SEARCH_SPEC.md`（在防搶跑 gate 段後補一條「對照軸純度」鐵律，對齊已落地的 gate）
- **fresh-clone／實跑結果**：
  - `python selftest_guards.py` → 全綠（含新條目「對照軸純度 query 摻入 C 軸 → 會 FAIL」「I 軸含 C 子字串不誤判 → 通過」），結尾「✅ 全部守門有效。」
  - `python comparator_purity_check.py`（對本案 g0_strategy.json）→ ✅ 各腿 query 只含 in_query 軸。
  - `python gate_guard.py --cache <本案 cache>` → 新關「Gate⓪／① 對照軸純度」✅ 通過（manifest 未存在時退回 g0.legs 稽核，故 ⓪ 策略階段即生效）。
- **想被重點看 / 不確定的點**：
  1. **遮蔽法防誤判**：判定前先把所有 in_query 軸同義詞（長詞優先）從 query 遮蔽，再掃 in_query=false 軸同義詞；目的是讓 I 軸長詞（`ICS/LABA/LAMA`、`LABA/LAMA/ICS`）內含的 C 軸子字串（`LABA/LAMA`）不被誤判。請確認此法是否仍有漏洞（例：C 同義詞跨越被遮蔽詞的邊界）。
  2. **manifest 缺席時退回 g0.legs**：讓 ⓪ 策略階段就能稽核（不必等 Stage A 廣蒐才攔）。請確認此 fallback 不會與其他只看 manifest 的 gate 衝突。
  3. **範圍判定**：僅當策略宣告了至少一個 `in_query=false` 軸時才啟用（無對照軸的題＝無可違反、直接通過），避免對非比較型題誤報。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

✅ 已修：檢索 query 摻入對照軸 C 砍 recall 的 bug（triple vs dual COPD 案，Consensus／OpenAlex query 連兩版被塞「versus dual therapy LABA/LAMA」）。本輪修改：(1) 把該案 g0_strategy.json 各腿 query 改為只含 P＋I；(2) 新增 `comparator_purity_check.py` 並掛進 gate_guard，使「C 軸進 query」之偏離今後一律被機器攔下（含 ⓪ 策略階段）；(3) selftest 加兩條自測證明守門有效且不誤報；(4) SEARCH_SPEC 補鐵律對齊。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
