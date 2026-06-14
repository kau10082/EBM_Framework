---
id: selective_reporting
title: 選擇性報告查核（註冊庫計畫 vs 發表）
feeds: Phase 2/3；RoB 2 領域5、非報告偏誤
trigger: 有試驗註冊號（NCT/EudraCT/PROSPERO）時
applies_to: 全部（尤其 RCT/SR-MA）
output_field: selective_reporting
source: 本檔即正本（v6.3·Cochrane Ch7/8 選擇性報告、Ch13 非報告偏誤）
---

[選擇性報告查核]（Cochrane：須比對「事前計畫」與「最終發表」）：對有註冊號的研究，**比對 ClinicalTrials.gov／EudraCT／PROSPERO 登錄的 pre-specified outcomes 與發表文獻實際報告的 outcomes**，偵測選擇性報告偏誤。

‧ **怎麼查（接 registry_backfill）**：取 NCT → ClinicalTrials.gov API 的 `protocolSection.outcomesModule`（primary/secondary outcome measures），與發表論文之主要/次要終點清單比對。

‧ **判讀**：
  - 註冊有、發表未報（或改報）某 outcome，且無合理說明 → **選擇性『不報告』** → 餵 RoB 2 領域5（研究內）／非報告偏誤護欄（綜整層）、列降級候選。
  - primary outcome 在註冊與發表之間被更換（outcome switching）、或時點/定義被改 → 高度可疑、降級候選。
  - 完全一致 → 於 RoB 2 領域5 記「已比對註冊、未見選擇性報告」、不降級。

‧ **輸出 `selective_reporting`**：{checked: bool, registry: NCT…, status: consistent / switched / unreported / unclear, detail, downgrade_candidate}。

‧ ⚠️ 誠實：若無法取得註冊 outcome 清單（無網路/無註冊），標 checked=false、status=unclear，不得假裝已比對。
