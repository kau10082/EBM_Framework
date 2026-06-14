---
id: integrity_check
title: 研究誠信查核
feeds: Phase 2 前置 gate；輸出前自檢
trigger: 每篇納入研究（分級與統合之前）
applies_to: 全部
output_field: integrity_check
source: 本檔即護欄正本（v6.0 規格）
---

[研究誠信查核]（前置；單篇即用，與 RoB 內部效度正交）：在分級與統合「之前」，先查每篇納入研究是否被撤稿 (retraction)／造假／附勘誤 (erratum)／關切聲明 (Expression of Concern, EoC)。
‧ 命中「撤稿」＝可信度紅線（撤稿最常見原因為科學不當行為：造假／抄襲／重複）→ 該研究排除於分級與統合之外，或標重大保留，「不只是降級」。
‧ 命中「勘誤／EoC」→ 於『臨床限制』標明，並評估是否影響核心結論。
‧ SR/MA 層級：另查該 SR 有無查核其納入研究的撤稿狀態（撤稿狀態跨期刊／資料庫顯示常不一致、SR 常未因納入研究撤稿而更正）。

‧ **如何查（routine 預設＝一律實查，不可空填）**：
  - **只要有 WebSearch（Claude Code/Cowork）就一律實查**，不可略過、不可僅憑「新文假定無撤稿」：檢索 `"<第一作者> <年> <期刊> retracted OR retraction OR erratum OR correction OR expression of concern"`，並確認 PubMed 該文未標 Retracted/有無 erratum。`note` 記檢索日期、PMID/DOI 與依據。
  - **僅當真的無網路**時，才退而標 `note`「**未經資料庫驗證（行內推定）**」——此為例外、非常態，且須提示「補網路後應實查」。
  - `retraction`/`erratum_or_eoc` 為 false 時，note 必須說明「依何種查核得出 false」（已實查附 PMID/DOI vs 未查）。
  - SR/MA 另查其是否聲明已核對納入研究之撤稿狀態。
