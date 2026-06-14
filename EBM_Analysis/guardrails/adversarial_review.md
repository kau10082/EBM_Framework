---
id: adversarial_review
title: 對抗式第二遍複查（Phase 3 後的懷疑者 gate）
feeds: Phase 3 → Phase 4 之間的品質 gate
trigger: 每篇 GRADE 完成後、產報告前
applies_to: 全部（grade_track ∈ full/targeted_harms）
output: outputs/_adversarial_review.md（本機）
source: 本檔即正本（v6.2·對「自產自驗」核心弱點的補強）
---

[對抗式複查]：因「我即引擎」＝產出者與檢查者同一，schema/算術只擋形式錯、擋不了判斷錯。
故在 Phase 3 之後、產報告之前，**以「懷疑者」身分對自己的每個關鍵 verdict 重跑一遍，目標是『推翻它』**。

‧ **複查對象**（不必全 24 項，聚焦高風險）：
  - 每篇核心結論所依 outcome 的 `certainty_final`；
  - 所有 `risk_of_bias = not_serious`（問：我是否太寬鬆？有無未驗證就當低偏誤？）；
  - 所有 `imprecision`／`indirectness` 判定（問：界線是規則還是手感？）；
  - 任何 `audit_consistency.py` 標出的跨篇分歧；
  - 校準時與外部 GRADE 相符者（問：是真獨立得出，還是反推去對答案＝確認偏誤？）。

‧ **每項給裁定**：upheld（維持）／revise（提出具體改法與新等級）／uncertain（需人工或補資料）。
  - 對 revise/uncertain：寫明「最強的反方論證」與「為何」。

‧ **資料來源誠實檢查**：`data_source` 含 ai_synthesis/abstract 卻判 RoB「低」者→紅旗（未讀原文 Methods 無法驗證隨機化/隱藏/缺失處理）。逐字 quote 若來自合成而非第一手原文→標明「quote 為二手」。

‧ **處置**：revise 命中且明確者→回改 p3、重跑 `validate.py`（算術會重新檢查）、再產報告；屬「兩種判斷皆可」之臨床顯著性抉擇→不擅自改，列入報告『臨床限制』並交使用者裁定。

‧ ⚠️ 限制誠實：複查者仍是同一個我，無法完全消除盲點；這是「分開的批判性一遍」、非真正獨立第二方。
