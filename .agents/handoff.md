## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【本輪性質】**非功能塊**；設定檔引號樣式調整 ＋ 對「這到底是不是真 bug」的**更正紀錄**。

**本輪審查範圍：**
- `config/settings.yaml` —— ⚠️ gitignored、不在版控，審查端 clone 看不到。
- `EBM_Search/scripts/xref_verify.py`（`load_settings`／`_coerce`／`default_settings_path`）—— 版控內，本輪未改動，僅供查證「設定實際怎麼被讀取」。
- `config/settings.example.yaml` —— 版控內，本輪未改動，僅對照。

**⚠️ 更正（重要，repo 為唯一真相、以實跑為證）：**
先前我把這件事描述成「會讓 `yaml.safe_load` 的 helper crash、整條管線無法啟動的 bug」——**這個描述不正確**。
- 實跑查證：全 repo **無任何 `.py` 以 `yaml.safe_load`／`yaml.load` 讀 settings**（grep 0 命中）。
- settings 一律由 `xref_verify.load_settings`（自製零相依解析器）讀取；`_coerce` 會剝除單／雙引號、且**保留反斜線字面值**。
- 實測：`load_settings(default_settings_path())` 正確讀回 `'C:\Users\kau10\OneDrive\…\reports'`；`_coerce` 對雙引號版與單引號版回傳**完全相同**字串。
- 結論：settings.yaml 用雙引號包 Windows 路徑，**對本 repo 的實際讀取器不是 bug、不會 crash**。我先前看到的 crash 來自我自己臨時用 PyYAML 寫的診斷腳本，並非 repo 的程式路徑。

**本輪實際改動：**
- `config/settings.yaml` 5 個路徑值由雙引號改單引號 —— **功能中立**（自製解析器兩者讀法相同、路徑內容不變），純樣式、非修復性、非載入必要。保留即可，亦可還原，無差。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

- ❓ **存疑**：審查 🟡「範本反斜線路徑易誘使用者用雙引號填入而 crash → 建議預防①範本加註、預防②解析處 try/except 友善錯誤」。
  **存疑理由（已實跑查證，非臆測）：** 本 repo 設定**從不經 PyYAML 解析**（全 repo `yaml.safe_load`／`load` 0 命中），而是走 `xref_verify.load_settings` 自製解析器；`_coerce` 對單／雙引號處理相同並保留反斜線 → 雙引號 Windows 路徑**不會 crash**（已用真實 `load_settings` 實讀證明）。因此：
  - 預防②「在 YAML 解析失敗處 try/except 給友善錯誤」**無對應程式點可加**：repo 沒有 settings 的 yaml 解析；自製 `load_settings` 讀不到檔回 `{}`、對無法解析的行靜默 `continue`，本就不丟例外 → 硬加即死碼／過度工程（違反核心原則）。
  - 預防①「範本加註：Windows 路徑要用單引號否則 crash」基於同一錯誤前提；若照此措辭加註，等於在版控範本寫進一句**不正確**的警告。
  此 🟡 的根因是我上一輪交班把影響**誤述**為「yaml.safe_load 會 crash 管線」，誤導了審查端；已於本輪「待審查」區更正。
  **我的建議：①②皆不納入**（對應 repo 不存在該失效模式、且 ② 無落點）。若使用者仍想要文件防呆，最多加一句**正確**版註解（如「本檔由自製解析器讀取，單／雙引號皆可、反斜線會原樣保留」）。**交使用者裁決。**

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
