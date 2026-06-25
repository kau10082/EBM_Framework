## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

### 2026-06-25（第三輪【複審】）本輪審查範圍＝2 檔
- **修改 `EBM_Search/scripts/screen_tiers.py`**（judge_axes 加分隔符正規化＋跨軸長詞遮蔽；finalize_check 加 fetched-proof fallback；selftest 加 3 條回歸）
- **修改 `EBM_Search/SEARCH_SPEC.md`**（screen_tiers 鐵律補：對照軸同義詞須『該藥專屬』）

**上一輪（第二輪）🔴 清單＝0**（Antigravity 給 2✅+1🟡、無 🔴）。但作者依 review-prompt 自我複審、**在實機 921 筆上驗證 screen_tiers**（非只跑 selftest），抓到 2 項上一輪漏看的問題，已修，請第三輪逐項核對是否真的消失：
1. **(原 🔴，已修) judge_axes 對照軸子字串假命中**：naive `re.escape` 子字串比對使對照軸泛詞 `anti-IL-5`/`anti-interleukin-5` 命中 benralizumab 自身描述 `anti-interleukin-5 receptor α` → 實測 **29 筆 離題→假切題**（含 CALIMA benra vs placebo）。修：(a) judge_axes 加分隔符正規化＋跨軸長詞優先遮蔽（`screen_tiers.py` judge_axes）；(b) 根因＝g0 對照軸放了類別泛詞→已從 run-cache g0 C_mepolizumab 移除 `anti-IL-5`/`anti-interleukin-5`（對照軸用 INN/品牌/代號）；(c) SEARCH_SPEC 加此鐵律。**驗證：實機 false 切題 29→0。**
2. **(原 🟡，已修) finalize_check 非完整鏡像**：缺 gate_guard 的 `g3_fetched_by_uid.json` fetched-proof fallback → 對 79 筆「內容在 fetched 表、g3 記錄無 inline 內容」的合格切題誤報缺 provenance（比事後守門更嚴）。修：`finalize_check(records, strategy, fetched=...)` 加同一 fallback。**驗證：實機 finalize 問題 79→0。**

**自我驗證**：`screen_tiers.py --selftest`＝8 案全過（含新增 G1-mask／G1-sep／G3-fetched）；實機 `validate_screen_tiers.py`：finalize 0 問題、false 切題 0、殘 62 筆皆 g3=切題→ST=離題且皆 tier3（C 僅在 Tier3 全文 body、未在餵給驗證器的 abstract）＝內容可得性差異、非邏輯錯。repo↔AppData 同步。

**請第三輪審查重點**：(a) 跨軸長詞遮蔽是否會反向誤殺合法命中（遮蔽過度）；(b) finalize_check 的 fetched-proof 判準（text_len≥1500/verified/…）是否與 gate_guard 完全一致；(c) 「對照軸同義詞須專屬」這條是否該升級為機器 gate（目前僅 SEARCH_SPEC 文字＋screen_tiers 行為）。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

（上一輪【第五塊 screen_tiers】2✅+1🟡 已處理；作者自我複審又發現並修掉 2 項〔🔴 對照軸子字串假命中、🟡 finalize_check 漏 fetched fallback〕，詳見「已處理」。本區待第三輪外部複審覆寫。）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑;不同意紀錄不可刪）

### 2026-06-25 處理第二輪審查結果（第五塊）＋ 自我複審補抓
- **✅【第五塊 (1) has_content 門檻／(2) finalize 完整性】Antigravity 給 2✅**：但作者依「不要沿用上一輪結論」在**實機 921 筆**驗證後發現第 (2) 項其實**不完整**（finalize_check 漏 `g3_fetched_by_uid` fallback，79 筆誤擋）——已修（見「待審查」第三輪 #2）。第 (1) 項 has_content 門檻維持、實機無誤。
- **✅【第五塊 (3) 🟡 retrofit run-cache】已採納並執行驗證**：朝「run-cache 改 import screen_tiers」方向，先以 `validate_screen_tiers.py` 把 harness 套到實機 921 筆 → 正是這步**揭露了上一輪漏看的 🔴 對照軸子字串假命中（29 筆）**，已修（見「待審查」第三輪 #1）。修後實機 false 切題＝0、finalize＝0。**run-cache `screen_tier1-4.py` 的實體 import 改寫**：本輪 ③ 已完成、結果正確（手刻 curated C regex 本就避開該 bug），故不重跑；下一個主題的 ③ 起一律走 screen_tiers（SEARCH_SPEC 已立鐵律）。
- 影響澄清：本輪 ③ 的實際結果（切題 516／離題 225／皆無 180）由手刻 tier 腳本產出、**未受 harness bug 影響**（手刻 C regex 是 mepolizumab 專屬、無泛詞）；harness 的 bug 只在「若拿 harness 重跑」時才會顯現，已於採用前修掉。

### 2026-06-25 處理第一輪審查結果（無 🔴；2✅＋1⚪＋1🟡）
- **✅【第三塊 public_legs.py】** 3 項全確認、無需改動，commit `eaee976`。
- **✅【第四塊 ai_synthesis_checked】⚪** 採用 Antigravity「查過」定義，commit `8a213ac`。run-cache 183 筆已補跑 Consensus AI 合成（救回 3，餘 180 蓋 `ai_synthesis_checked=true`），③ 分割 516/225/180、gate_guard 全綠。
- **✅【🟡 screen_tiers.py】** 已新增 committed harness（commit `a6bde9c`），並於第二/三輪持續修正。

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
