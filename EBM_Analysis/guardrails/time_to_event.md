---
id: time_to_event
title: 時間事件結果（HR / 存活）查核與絕對風險再表達
applies_to: all
trigger: 核心結果為 time-to-event（HR、存活曲線、至首次事件時間）
handbook_ref: Cochrane Ch6 §6.8、Ch14 §14.1.5.2
feeds: effect_measure / imprecision / sof
---

存活/時間事件結果（腫瘤、心血管、至首次惡化時間常見）查核：

1. **HR ≠ RR/OR**：HR 是瞬時風險比、隱含整段追蹤；不可把 HR 當 RR 解讀，也不可把某時點的 RR 當 HR。核心結論須標明效應量為 HR。
2. **比例風險（PH）假設**：HR 假設兩組風險比隨時間恆定。看到 KM 曲線交叉或分離時點延遲 → PH 可能違反、單一 HR 可能誤導；註記並考慮分時段。
3. **HR 來源**：偏好 published HR＋CI 或 O−E 與 V（log-rank）導出；由 KM 曲線重建（Parmar/Tierney 法）為近似、列為較低品質資料來源。
4. **絕對風險再表達（SoF 必做，§14.1.5.2）**：HR 須換算為絕對效應呈現——給定對照組於某時點 t 的事件風險 p_c，介入組 p_i = 1−(1−p_c)^HR；用 `tools/absrisk.py hr <HR> <p_c> --ci lo hi`。三種等效呈現：某時段內無事件存活比例、某時段事件風險、中位事件時間。
5. **不精確**：HR 的 CI 是否跨 1（或跨 MID 對應之 HR 門檻）依 no_effect_interpretation 判讀。

輸出要求：time-to-event 核心結果之 SoF 列須有絕對欄（由 absrisk hr 換算），不得只留 HR。selfcheck C9 會擋「HR 結果缺絕對效應」。
