## 待審查（FROM Claude Code，需註明本輪審查範圍：僅哪幾個檔；一塊結案後清空）

【初審】功能塊＝強化 SR filter 複合語法守門（把使用者手動抓到的缺失轉成機器 gate）。

**本輪審查範圍：僅以下檔案（請只讀這幾個檔的當前內容，勿審其他檔）**
1. `EBM_Search/scripts/sr_filter_composite_check.py`
2. `EBM_Search/scripts/selftest_guards.py`
3. `EBM_Search/SEARCH_SPEC.md`（僅第 107 行附近新增的「★★ 三成分強化」一段）

**背景／為何改**：執行 benralizumab vs mepolizumab 檢索的 Phase ⓪ 時，使用者人工抓到我寫的 `EuropePMC-SR` 過濾器
不符其定版要求「出版類型(PubType) ＋ 主題詞(MeSH/Emtree) ＋ 自由文字(Title/Abstract)」三成分。追因發現
**既有 gate 太鬆、放行了兩種缺失**，故依 AGENTS.md「使用者人工抓到的缺失優先轉成機器 gate」把它修進守門：
- 缺失①：gate 把 EuropePMC/OpenAlex 的『裸詞』當合格自由文字，但這些 DB 預設搜**全文**，裸詞＝全文泛提及噪音、非 Title/Abstract。
- 缺失②：gate 對 MeSH-capable DB（EuropePMC 索引 MEDLINE）未強制 MeSH 成分，致只有 PubType＋自由文字也過關。

**這次改了什麼（逐檔）**：
- `sr_filter_composite_check.py`：
  - `_has_freetext()` 改為**只認欄位綁定**的 Title/Abstract（`[tiab]`/`TITLE:`/`ABSTRACT:`/`title_and_abstract.search:`），
    移除「裸詞 fallback」（連同不再需要的 `_is_bracket_dialect`）。
  - 新增 `_has_mesh()`（偵測 `[mesh]/[mh]/[majr]`、`MESH_TERM:`、`mesh:`、Emtree）＋ `_is_mesh_capable(name, meta)`
    （DB 名判定 + `mesh_unavailable:true` 誠實豁免）＋ `MESH_CAPABLE_DB` 清單、`_norm_name()`。
  - `check()` 改為逐成分核對：缺欄位綁定自由文字 / 缺控制詞彙 / （MeSH-capable 而）缺 MeSH → 各自 FAIL，訊息明確。
  - 更新 module docstring 說明三成分與欄位綁定規則。
- `selftest_guards.py`：更新 SR-composite 測試區——
  - 修正兩個原『裸詞/無 MeSH 仍應通過』的防誤報案（它們正是被放行的鬆綁行為）。
  - **新增兩條負向回歸**（對應使用者抓到的缺失①②）：MeSH-capable DB 用裸詞自由文字＝FAIL、MeSH-capable DB 略過 MeSH＝FAIL。
  - 新增三條正向防誤報：EuropePMC 三成分（PubType＋MeSH＋欄位綁定）通過、PubMed 方括號三成分（[pt]＋[mesh]＋[tiab]）通過、
    OpenAlex（`mesh_unavailable`）豁免 MeSH＋欄位綁定通過；AI 合成腿維持豁免。
- `SEARCH_SPEC.md`：第 107 行附近新增「★★ 三成分強化」一段，使規格與強化後的 gate 一致（避免 spec 範例與 gate 矛盾）。

**fresh-clone 自測結果**：見下方對話回報（`selftest_guards.py` 在新 clone 全綠）。

**想被重點看 / 我自己不確定的點**：
1. `_has_freetext` 移除裸詞 fallback 後，是否對「真的預設只搜 title/abstract 的 DB」過嚴？（我判斷本框架腿集合
   PubMed[方括號]/EuropePMC[全文]/OpenAlex[含全文] 皆需欄位綁定，故移除 fallback 是對的；若日後加入別的 DB 需再評估。）
2. `_is_mesh_capable` 以 DB 名子字串判定（pubmed/medline/europepmc/epmc/embase/ovid/cochrane/central）＋ `mesh_unavailable` 旗標豁免，
   是否夠穩健？（`_norm_name` 去除非英數，故 "Europe PMC-SR"→"europepmcsr" 可命中 "europepmc"。）
3. `_has_mesh` 的 `mesh:` 偵測用 `(?<![a-z])mesh\s*[:=]`，是否可能誤命中（如某 DB 有別義的 mesh 欄位）？目前框架未用，風險低。

## 審查結果（FROM Antigravity，只列當前仍存在的問題）

## 已處理（FROM Claude Code，✅已修 / ❌不同意 / ❓存疑；不同意紀錄不可刪）

## 僵局待裁決（雙方立場,後果語言,給使用者裁決）
