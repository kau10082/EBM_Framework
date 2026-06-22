## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊：修正「SR filter 啟用時，非 PubMed DB 腿的『無過濾主檢』全文噪音被灌進篩選語料庫」的流程 bug，並落為機器守門避免復發。

**本輪審查範圍：僅以下檔案**
- `EBM_Search/scripts/sr_division_check.py`（新增：SR 分工硬 gate）
- `EBM_Search/scripts/gate_guard.py`（接線：新增 `check_sr_division`＋列入 `_all_checks`）
- `EBM_Search/scripts/selftest_guards.py`（新增 3 條 SR 分工回歸 fixture）
- `EBM_Search/SEARCH_SPEC.md`（第 93 行 SR 過濾器段：由「additive 聯集進池」改為「DB 腿只以 -SR 結果進語料庫」定版）

**背景（bug 怎麼來的）**：triple vs dual COPD 案，使用者選擇套用 SR filter。原本把 EuropePMC『無過濾主檢』（EuropePMC REST 預設全文檢索）的 3816 筆全文泛提及噪音直接 dedup 進 `g1_union`（語料庫），使用者糾正：「當我決定用 SR filter 時，DB 腿應只給我 SR 搜尋結果」。

**修法**：
- 規則（SEARCH_SPEC §SR filter）：SR filter 啟用時，有 SR 變體的非 PubMed DB 腿（EuropePMC/Consensus/OpenAlex）**只以 `<leg>-SR` 結果進語料庫**；原始 RCT 走 PubMed 腿、SR/MA 走 -SR 腿、登錄試驗走 CT.gov；無過濾主檢只留作 manifest 取盡/稽核紀錄，不進語料庫。
- 機器 gate `sr_division_check`：由 g0 判 SR filter 是否啟用（`sr_filter_decision=="applied"` 或 legs 含 `-SR`）；啟用時若 `g1_union` 任一筆 provenance 含「有 SR 變體之非 PubMed DB 腿的主檢（同 base、非 -SR）」即 FAIL。PubMed/CT.gov 天然不在受限集合。

**fresh-clone/實跑結果**：
- `selftest_guards.py` → 「✅ 全部守門有效」；新 3 條 SR fixture：FAIL 案有觸發、2 條防誤報（只 -SR/PubMed/CT.gov 進池；未啟用 SR filter）皆通過。
- 本案 cache 實跑：`sr_division_check` standalone PASS、`gate_guard --cache` 全部已抵達關卡通過（含新關「Gate① SR分工」✅）。

**想被重點看 / 不確定點**：
- (1) 我把 SEARCH_SPEC 既有「additive、不損 recall」定版**改成**「DB 腿主檢不進語料庫」。取捨：真實世界觀察性研究（非 RCT、非 SR）較不易進池——這是依使用者明確決策做的，已在對話告知並提供「要的話把 Consensus 主檢觀察性加回背景池」。請確認此 spec 改寫無自相矛盾、且與 leg_exhaust（主檢仍須取盡）不衝突。
- (2) gate 啟用條件用「union 是否存在」區分『SR 已啟用但語料庫未組（暫不適用）』vs『已組須稽核』，請看這個 None/[] 邏輯是否會漏擋。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
