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

✅ 已修：**③ 分層篩升級『鐵律』——只有切題可早停，其餘一律逐層往下推，不得偷懶**（本輪糾正）。
   - 使用者定版鐵律：**Tier1 只要不是切題 → 全部進 Tier2；Tier2 只要不是切題 → 全部進 Tier3；Tier3 只要找不到全文 → 全部進 Tier4**。離題／皆無只能在記錄實際抵達的最底層定案。
   - 問題（舊碼）：(1) 登錄(CT)/AI(Consensus) 記錄在 **Tier2 就逕判離題**、沒被推進 Tier3/Tier4；(2) 只有「帶摘要的 PM/EP」被升 Tier3，純標題等其他非切題未一律逐層推進。＝偷懶早停。
   - 本輪修改（screen_3_run.py 重寫）：每筆非切題一律 Tier1→2→3→4 逐層累積內容、逐層判（命中切題才停）；登錄/AI 非切題也必須過 Tier3（全文嘗試）＋Tier4（Unpaywall）才可判離題；Tier3 找不到全文者**全部**進 Tier4 跑 Unpaywall。`tier` 欄記錄該筆實際抵達的最底層。
   - 註：gate `check_excl_requires_fulltext` 對登錄/AI 有「免 Tier3」例外（因無全文可取）；本鐵律比 gate 更嚴（仍逐層推進），故 gate 必過、且更誠實。

✅ 已修：**用語沿用舊編號『②c 關 / ③ 關』分開講，但 v0.22 已整合**（本輪糾正）。
   - 問題：對話說明（如 ②b 收尾「③ 嚴格篩需先 ②c 抓摘要/全文，再進 ③」）仍把 ②c 與 ③ 當兩關講。**v0.22 定版已取消獨立 ②c**：舊「②c 搜尋全文/取得性」整個併入 **③「全文/摘要搜尋及嚴格離題篩選」**——③ 內含 Tier1 既有摘要、Tier2 登錄/AI、Tier3 實取全文、Tier4 Unpaywall，全文取得＝③ 的 Tier3/Tier4，不是前置的 ②c。
   - 本輪修改：後續說明一律稱「③（含 Tier1–4）」，不再出現「②c」字眼；「待評估」桶亦已取消（③ 三桶＝切題/離題/全文及摘要皆無）。管線編號＝① 廣蒐去重 → ② 篩選策略 → ②b 高敏初篩 → ③ 全文/摘要搜尋及嚴格離題篩選（Tier1–4） → ④ 引文追蹤 → ⑤ 收斂後處理 → ⑥ 三表+PDF → ⑦ 交接包。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
