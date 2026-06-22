## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

（檢索 run 進行中，尚未送審；本檔目前累積使用者於 run 中提出的流程糾正紀錄。）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

### 2026-06-22 triple-vs-dual COPD 檢索 run — 使用者即時糾正（累積紀錄）

✅ 已修：**OpenAlex 腿又把『引文追蹤』混進 ① 廣蒐階段**（本輪糾正）。
   - 問題：① 報告把 OpenAlex 腿描述成「廣檢＋④引文追蹤」，又在覆蓋限制寫「OpenAlex 原本擔任 ④ 引文追蹤」。引文追蹤（滾雪球）＝**第 ④ 關**，須等 ③ 嚴格篩定出核心後以核心為種子才做，**不屬 ① 廣蒐**。關責不外溢。
   - 本輪修改：g0_strategy.json 移除 OpenAlex 腿一切「引文追蹤/citation tracking」字眼；① 報告不再把引文追蹤掛在任何 ① 腿上；④ 的引文追蹤來源（OpenAlex 或 Europe PMC references/citations）留待 ④ 關再談。

✅ 已修：**SR filter 開啟時，SR 腿『完全取代』原搜尋腿——主檢腿不該出現、不該花力氣取盡**（本輪糾正）。
   - 問題：先前把非 PubMed DB 腿（Consensus／OpenAlex／EuropePMC）的『無過濾主檢』也跑出來（甚至把 EuropePMC main 取盡 4132 筆）只當 audit。使用者定版：**SR filter ON → 該腿只剩 -SR 變體，主檢腿整個不存在、不執行、不報告、不浪費力氣**。
   - 與舊 spec 文字的張力：SEARCH_SPEC §99「DB 腿的無過濾主檢若有實跑，只作為廣蒐取盡/稽核紀錄寫進 manifest」→ 使用者澄清語意為「**根本不要跑主檢**」（取代 audit-retain 寫法）。建議下次正式審查時一併更新 SEARCH_SPEC 措辭與 leg_exhaust_check 的 ≥4 計數假設（≥4 應以實際可跑之 SR/RCT/登錄腿為準，不靠主檢墊數）。
   - 本輪修改：g0_strategy.json 與 g1_legs_manifest.json **移除 Consensus-main、EuropePMC-main、OpenAlex-main**；不再 fetch/exhaust EP-main；語料庫腿＝PubMed(RCT)＋Consensus-SR＋OpenAlex-SR＋EuropePMC-SR＋ClinicalTrials.gov。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
