---
id: amstar2
title: 相關 SR/MA 之 AMSTAR 2 品質評估
feeds: 三、證據品質與完整度（related_reviews）
trigger: corpus 內納入或參考 ≥1 篇系統性回顧／統合分析（SR/MA）
applies_to: SR/MA
output_field: synthesis.related_reviews
source: 本檔即護欄正本（v6.3·AMSTAR 2 / Cochrane Ch V）
---

[相關 SR/MA 之 AMSTAR 2 評估]（當報告納入或參考其他 SR/MA 作為對照/校準/類別參照時）：以 AMSTAR 2 評其方法學信心，並**獨立於 4 RCT「納入研究特徵表」之外**呈現，維持 Cochrane「研究單位（study）vs 回顧單位（review）」之區分（Ch V）；去重後該 SR/MA 不與其所納入之個別 RCT 結論疊加（連動 [overlap_indirect]）。

‧ **七個關鍵領域（critical domains）**（缺陷直接壓低整體信心）：
  - item 2 事前 protocol／PROSPERO 註冊；
  - item 4 檢索是否充分（多資料庫＋未以語言/出版狀態設限）；
  - item 7 是否提供「排除研究清單＋逐一理由」；
  - item 9 是否以適當工具評各納入研究偏誤風險（RCT 用 RoB 2）；
  - item 11 合成方法是否適當（效果量/模型/異質性處理）；
  - item 13 詮釋結果時是否納入偏誤風險考量（常經 GRADE）；
  - item 15 是否評估發表偏誤並討論其影響（⚠️ 研究 <10 時漏斗圖檢定力低、不宜做；此時「未做＋說明理由」屬可接受，不以缺陷論）。

‧ **整體信心分級（依關鍵領域缺陷數）**：
  - high：0 個關鍵缺陷、至多 1 個非關鍵弱點；
  - moderate：0 個關鍵缺陷、>1 個非關鍵弱點；
  - low：1 個關鍵缺陷（不論非關鍵弱點數）；
  - critically_low：>1 個關鍵缺陷。

‧ **誠實標註**：若僅取得摘要而非全文，AMSTAR 2 受限，須標「基於可得資訊」並保守給級；item 7（排除清單）多數已發表 MA 不全，據實扣分；跨不同藥物/劑量 pooling 屬臨床異質，影響 item 11 與證據詮釋（與 GRADE 間接性分開記）。

‧ **輸出**：每篇 SR/MA 記 review／scope／trials_covered／amstar2_rating／amstar2_basis（滿足與未滿足之關鍵領域）／role，渲染為獨立「相關系統性回顧／統合分析特徵表」，不混入 RCT 特徵表。

## 16 題與適用範圍（v2 強化）
- AMSTAR 2 共 **16 題**，其中上列 **7 題為關鍵領域(critical domains)**（item 2,4,7,9,11,13,15），其餘為非關鍵弱點。
- AMSTAR 2 特別強化評估「**同時納入 RCT 與 NRSI**」之 SR 的能力——item 9（偏誤工具）對 RCT 應用 **RoB 2**、對 NRSI 應用 **ROBINS-I**（與本框架三路徑一致）。
- 逐題作答 `yes / partial_yes / no / no_meta_analysis`，記於 `amstar2.items[]`（透明表格資料）。

## 整體信心演算法（機器看守）
依**關鍵瑕疵數(critical_flaws)＋非關鍵弱點數(noncritical_weaknesses)**演算（與上「整體信心分級」一致）：
`>1 關鍵→critically_low｜1 關鍵→low｜0 關鍵且 >1 非關鍵→moderate｜0 關鍵且 ≤1 非關鍵→high`。
- **機器看守 `validate.py check_p2_rob_routing`（track A）**：`overall_confidence` 必與上式一致，否則 FAIL；
  若提供 `items[]`，關鍵題(2,4,7,9,11,13,15)答 `no` 的數量須等於 `critical_flaws`（透明表格與計數一致），否則 FAIL；缺 `basis` FAIL。
  schema 另強制 track A 必帶 `amstar2`＋`protocol_completeness`＋`rob_tool=amstar2`。

## 透明表格（Cochrane 規範）
報告須納入一張表：**每篇 SR 在各題的評分 ＋ 給該評估的具體理由 ＋ 最終整體評等**，以脈絡化證據基礎、讓讀者了解方法學瑕疵是否/如何影響結果完整性與可信度。資料來源＝`amstar2.items[]`＋`amstar2.basis`＋`amstar2.overall_confidence`。

## 模式 B（Overview）基底擇定連動
擇單一最佳基底時：高 AMSTAR 2 信心 ＋ 最新檢索(`search_recency`) ＋ 與目標 PICO 契合 ＋ CCA 重疊最低（連動 [overlap_indirect]）；`critically_low` 之 SR/MA 不宜作基底。
