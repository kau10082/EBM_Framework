---
id: rare_events
title: 罕見事件統合方法查核（安全性/罕見不良事件）
applies_to: sr_ma
trigger: outcome 為罕見事件（高比例研究有 0 事件）或罕見 harms
handbook_ref: Cochrane Ch10 §10.4.4
feeds: risk_of_bias / inconsistency / imprecision
---

評讀罕見事件（如嚴重不良事件、死亡）之 MA 時查核所用方法是否適當（§10.4.4）：

1. **雙臂零事件研究應自 MA 略去**（不提供方向資訊）；只報「納入但無事件」即可。
2. **固定 0.5 連續性校正會引偏誤**，尤其臂大小不均時——看到固定 0.5 校正→紅旗。
3. **反變異數法與 DerSimonian-Laird 隨機效應在罕見事件下表現差、應避免**；事件率 <1% 時 **Peto OR 表現最佳**（但臂嚴重不均或效應極大時 Peto 亦偏誤）。
4. **風險差（RD）法不適合罕見事件**（CI 過窄、跨研究合併不穩）。
5. **Mantel-Haenszel 不校正**或精確法為較佳選擇。

輸出要求：評讀罕見 harms MA 時，若用了上述不適當方法（DL 隨機效應/固定 0.5 校正/RD），於該 outcome 註記方法學限制、對其效應估計保守解讀；與 harms 護欄交叉引用（被動 vs 系統性收集）。
