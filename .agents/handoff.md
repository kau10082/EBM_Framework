## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-25 收尾：SR filter／⑤b gate／EBM_Analysis 偏誤路由＋多軌（本輪審查無 🔴）

【第一塊：SR filter 與 ⑤b gate — 審查端 3× ⚪ 確認設計正確】
✅ 已確認:`_has_freetext` 移除裸詞 fallback 設計正確（⚪；MECIR 要求精確控制、本框架腿集合皆需欄位綁定）。無須修改。
✅ 已確認:`_is_mesh_capable` 以字串包含＋`_norm_name` 處理變體（如 `Europe PMC-SR`）已足夠穩健（⚪）。無須修改。
✅ 已確認:`_has_mesh` 之 `(?<![a-z])mesh\s*[:=]` 能擋 `somemesh:` 誤判（⚪）。無須修改。

【第二塊：EBM_Analysis 偏誤路由與多軌】
✅ 採納為可接受折衷:ROBINS-I `no_information` 不計入木桶 RANK ⇒「多個 low＋單一 no_information」仍可判 overall=low（審查 🟡）。
   裁決：維持現狀。理由：(1) NRSI 判 overall=low 本就極罕見；(2) 已強制 `low_justification`（validate.py 之 check_p2_rob_routing，須書面說明殘餘干擾可忽略）；(3) 已有「≥4 領域 no_information＝充數 FAIL」護欄。三重緩解下，殘餘風險＝單一 NI 領域且仍書面證成 low，機率極低、可於評讀回溯，非 crash／非靜默資料遺失。
   未來觸發補強：若實務真出現「NRSI overall=low 且任一領域 no_information」，於 check_p2_rob_routing track C 加「任一 no_information ⇒ overall 至少 moderate」即可（約 2 行＋1 條 selftest）。
✅ 裁決·延後:Phase 2 `critical`→Phase 4 排除的「跨檔」一致性（審查 🟡）。
   現況：`check_synthesis_tracks` 僅做 Phase 4 檔內自洽（included vs excluded_critical 不重疊），未跨檔回查 phase2_triage.json 判 critical 者是否確實在 Phase 4 被排除。
   裁決：延後。理由：此屬跨階段 selfcheck_consistency（非單檔 validate）；repo 現無跨階段 harness 與真實 Phase 3/4 串接 fixture，現在加半套 gate 無法在 fresh-clone 有意義實測，違反 AGENTS.md 正確性硬規則（禁「應該可以」）。審查端亦同意「可之後再補」。
   未來觸發補強：待 Phase 3/4 實際輸出管線產出後，新增 selfcheck_consistency C 條——蒐集 phase2 overall=critical 的 paper_id，斷言每筆出現在 phase4 synthesis.nrsi.excluded_critical_ids 且不在任何 included 池。
✅ 已確認:多軌容器分隔（RCT／NRSI／SRMA）與防混池 gate 實作正確、符合 Cochrane Ch.25（審查 ✅）。無須處理。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
