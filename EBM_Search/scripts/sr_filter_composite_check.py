# -*- coding: utf-8 -*-
"""
sr_filter_composite_check.py — Gate ①『SR filter 須為複合語法（PubType/MeSH ＋ Title/Abstract 自由文字）』硬 gate
================================================================================
2026-06 使用者定版（補正先前『SR filter 只靠出版類型過濾』之缺失）：

正確的 SR（系統性回顧/統合分析）檢索過濾器**不可只依出版類型（Publication Type）**，
必須是 **「控制詞彙（出版類型 PubType／主題詞 MeSH/Emtree）＋ 自由文字詞（Title/Abstract）」的複合組合**。
理由（Cochrane MECIR C33）：
  • 索引時間差（indexing lag）：資料庫人工貼 PubType/MeSH 需數天～數月；只用 PubType 會漏掉
    剛發表、尚未被索引的最新 SR/MA。
  • 索引不一致：作者用語與索引者認知可能不同；故任何方法學過濾策略都須**並用**控制詞彙與自由文字詞。
標準 SR 邏輯範例（PubMed）：
  ((systematic review[pt] OR meta-analysis[pt] OR systematic review[tiab] OR meta-analysis[tiab]))

本守門對每條『SR 子腿（`<leg>-SR`，或 g0 role=SR_MA_NMA）且使用 Boolean query』的腿，
斷言其實際 query **同時含**：
  (1) 控制詞彙成分：SR 詞綁定 [pt]/[ptyp]/[mesh]/[mh]/[sb] 或 `pub_type:`；以及
  (2) 自由文字成分：SR 詞綁定 [tiab]/[ti]/[tw]/[ab]/[title]，或 title/abstract 欄位語法，
      或『裸詞』（無欄位標籤＝在多數 DB 預設搜 title/abstract）。
缺任一成分 → FAIL（只靠 PubType＝會漏未索引最新 SR；只靠自由文字＝召回雜訊、非標準過濾）。

AI 合成腿（Consensus/OpenEvidence，role=ai_synthesis 或 exhaustible=false）以結構化參數
（如 study_types）限定設計、無 [tiab] 欄位語法 → **豁免**本複合語法要求。

用法：python sr_filter_composite_check.py --manifest g1_legs_manifest.json --strategy g0_strategy.json
程式內：import sr_filter_composite_check; fails = sr_filter_composite_check.check(manifest, strategy)
"""
import sys, re, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

SR_SUFFIXES = ("-sr", " sr", "_sr", "-systematic-review")
# SR 方法學詞（自由文字／詞幹；分隔符寬鬆：meta-analysis / meta analysis / metaanalysis）
SR_TERM = r"(?:systematic\s+(?:literature\s+)?review|systematic\s+overview|meta[\s\-]?analy(?:sis|ses)|network\s+meta[\s\-]?analy(?:sis|ses))"
# 控制詞彙欄位標籤（出版類型 / 主題詞）
CONTROLLED_TAGS = r"(?:pt|ptyp|mesh|mh|mh:noexp|majr|sb)"
# 自由文字欄位標籤（標題/摘要）
FREETEXT_TAGS = r"(?:tiab|ti|tw|ab|title|titl|tw:noexp)"

def _norm(s): return (s or "").strip().lower()

def _is_sr(name):
    n = _norm(name)
    return any(n.endswith(suf) for suf in SR_SUFFIXES)

def _leg_meta(strategy, name):
    """從 g0.legs 取該腿 role/exhaustible（判 AI 合成腿豁免）。"""
    legs = (strategy.get("legs") or []) if isinstance(strategy, dict) else []
    n = _norm(name)
    for l in legs:
        if isinstance(l, dict) and _norm(l.get("leg") or l.get("name")) == n:
            return l
    return {}

def _is_ai_synthesis(meta):
    return _norm(meta.get("role")) == "ai_synthesis" or meta.get("exhaustible") is False

def _has_controlled(q):
    """SR 詞綁定控制詞彙欄位，或 pub_type: 前綴。"""
    if re.search(SR_TERM + r"\s*\[\s*" + CONTROLLED_TAGS + r"\s*\]", q, re.I):
        return True
    if re.search(r"systematic\s*\[\s*sb\s*\]", q, re.I):  # systematic[sb] 子集策略
        return True
    if re.search(r"pub_?type\s*:\s*\"?\s*(?:review|systematic|meta)", q, re.I):
        return True
    # 文獻/著作型態控制欄位（OpenAlex `type:review`、EuropePMC/Embase doctype 等＝控制詞彙的一種）
    if re.search(r"(?:doctype|document[_\-]?type|publication[_\-]?types?|\btype)\s*[:=]\s*\"?\s*(?:review|systematic|meta)", q, re.I):
        return True
    # MeSH 引號式：\"meta-analysis as topic\"[mesh]
    if re.search(r"\"\s*" + SR_TERM + r"(?:\s+as\s+topic)?\s*\"\s*\[\s*" + CONTROLLED_TAGS + r"\s*\]", q, re.I):
        return True
    return False

def _has_freetext(q):
    """SR 詞綁定自由文字欄位 / title:abstract: 語法 / 裸詞（無欄位標籤＝預設搜文字）。"""
    if re.search(SR_TERM + r"\s*\[\s*" + FREETEXT_TAGS + r"\s*\]", q, re.I):
        return True
    # 欄位前綴語法（OpenAlex/EuropePMC）：title:"systematic review" / abstract.search:meta-analysis / ti:(...)
    if re.search(r"(?:title|abstract|ti|ab|tiab)[\w.\s]*:\s*[\"(]?\s*" + SR_TERM, q, re.I):
        return True
    # 裸詞（SR 詞之後沒有任何 [欄位] 標籤）＝多數 DB 預設搜 title/abstract（含 EuropePMC 預設）
    for m in re.finditer(SR_TERM, q, re.I):
        tail = q[m.end(): m.end() + 12]
        if not re.match(r"\s*\[", tail):
            return True
    return False

def check(manifest, strategy):
    """回傳 fails 清單（空＝通過/不適用）。manifest: list[dict]; strategy: dict。"""
    if not manifest:
        return []  # 尚未廣蒐：不適用（取盡/遵從等其他 gate 負責）
    if not isinstance(strategy, dict):
        return ["g0_strategy.json 不存在或格式錯誤：無法稽核 SR filter 複合語法"]
    fails = []
    checked = 0
    for leg in manifest:
        name = leg.get("leg") or leg.get("name") or "?"
        if leg.get("skipped"):
            continue
        meta = _leg_meta(strategy, name)
        is_sr_leg = _is_sr(name) or _norm(meta.get("role")) == "sr_ma_nma"
        if not is_sr_leg:
            continue
        if _is_ai_synthesis(meta):
            continue  # AI 合成腿以 study_types 等結構化參數限定，豁免 Boolean 複合語法
        q = leg.get("query")
        if not q:
            continue  # 缺 query 由 strategy_adherence_check 負責報，不重複
        checked += 1
        ctrl = _has_controlled(q)
        free = _has_freetext(q)
        if ctrl and free:
            continue
        if ctrl and not free:
            fails.append(f"[{name}] SR filter 只用控制詞彙（出版類型/MeSH），缺自由文字（Title/Abstract）成分："
                         "只靠 PubType/MeSH 會因索引時間差漏掉最新未索引 SR/MA（MECIR C33 須並用自由文字詞）。"
                         "請補 `systematic review[tiab] OR meta-analysis[tiab]` 之類自由文字成分")
        elif free and not ctrl:
            fails.append(f"[{name}] SR filter 只用自由文字（Title/Abstract），缺控制詞彙（出版類型/MeSH）成分："
                         "標準 SR 過濾器須並用控制詞彙（如 systematic review[pt] OR \"meta-analysis\"[mesh]）以提精準")
        else:
            fails.append(f"[{name}] 標為 SR 子腿但 query 未見任何 SR 方法學過濾成分（既無 PubType/MeSH 亦無 Title/Abstract）："
                         "SR 子腿必須以複合語法限定 systematic review/meta-analysis")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="g1_legs_manifest.json")
    ap.add_argument("--strategy", default="g0_strategy.json")
    a = ap.parse_args()
    mp, sp = Path(a.manifest), Path(a.strategy)
    if not mp.exists():
        print(f"⏭  找不到 {a.manifest}（Gate ① 尚未跑或未寫 manifest）"); sys.exit(1)
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    fails = check(manifest, strategy)
    if fails:
        print("❌ SR filter 複合語法檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ SR filter 複合語法：各 SR 子腿並用控制詞彙＋自由文字（符合 MECIR C33）。")

if __name__ == "__main__":
    main()
