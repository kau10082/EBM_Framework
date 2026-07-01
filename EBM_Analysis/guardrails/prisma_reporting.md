---
id: prisma_reporting
title: 報告層對齊 PRISMA 2020（最終報告完整度）
applies_to: synthesis
trigger: 產最終報告
handbook_ref: Cochrane Part III、PRISMA 2020、PRISMA-S
feeds: report_completeness
---

最終報告除 MECIR＋SoF（見 report_completeness）外，對齊 PRISMA 2020 最低項目集：

1. **PRISMA 流程圖（必備）**：撈得 N → 去重 → 篩選（剔除數＋理由）→ 全文評估 → 納入；數字須與檢索報告閉合一致（本框架檢索報告已產此漏斗，分析報告應沿用同數字）。
2. **結構化摘要（PRISMA-for-Abstracts，12 項）**：背景/目的、合格條件、資料來源、RoB 方法、納入研究數與參與者數、主要結果效應＋CI＋確定性、限制、結論、註冊號、資金。
3. **通俗摘要（Plain Language Summary）**：以病人可懂語言陳述問題、做了什麼、發現、確定性、限制（本框架報告「第一部分為人閱讀」已部分達成）。
4. **Discussion 四子標**（§III.3.7）：證據總結、限制（研究層 RoB＋回顧層流程）、與其他證據一致性、適用性。
5. **Conclusions 兩節**：對臨床/實務的意涵（結合基準風險、絕對效應、價值與偏好）＋對研究的意涵——**禁籠統「需要更多研究」**，須具體指明缺口（族群/比較/結果/設計）。
6. **註冊與 protocol 偏離**：聲明事前 protocol（見 protocol 產物）與任何偏離。

輸出要求：產最終報告前，逐項自檢上列；缺漏者補齊或在報告明列「未含（理由）」。流程圖數字一律由 cache 帶、不硬編。

## 機器稽核 gate（27 項，非靠自律）
上列要點由 **`tools/prisma_audit.py`** 編成 PRISMA 2020 **27 個編號項**的硬稽核，逐項對檢索產物（`_search_report.json`）＋統合產物（`_synthesis.json`）判 **PASS／FAIL／MANUAL／ATTEST／PENDING**，並寫出 `cache/_prisma_checklist.json`（可作報告附錄與項 27「可得性」載體）。已併入 `verify_all.py`（定稿統一入口）。

- **FAIL**（自動可驗卻缺維度）→ 阻擋定稿。對照本檔：項 16＝流程圖＋排除理由、項 17/18＝特徵表/RoB、項 20/22＝統合結果/確定性、項 23＝討論四子標且**禁籠統「需要更多研究」**（須具體缺口）。
- **MANUAL**（結構化資料無法判定）＝項 9 資料蒐集流程、24 註冊/protocol、25 資金、26 利益衝突、（無報告產物時）27 可得性。預設不阻擋但**一律列出、不靜默跳過**；於報告補齊或在 `synthesis.prisma_attest`（鍵＝項號字串，如 `"24"`）寫聲明 → 轉 **ATTEST**。`--strict` 時未聲明的 MANUAL 也計失敗。
- **PENDING**＝該階段對應產物尚未產出（如只跑完檢索、評讀未做），中性、不阻擋。

與 `selfcheck_consistency`（C1–C18，查「寫出來的彼此矛盾」）互補：本 gate 查「該有的維度齊不齊」。與 `report_completeness`（feeds 來源）同源，數字一律由 cache 帶。
