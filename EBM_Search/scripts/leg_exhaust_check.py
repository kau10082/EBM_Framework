# -*- coding: utf-8 -*-
"""
leg_exhaust_check.py — Gate ①『每腿務必取盡』硬 gate（反偷工）
==============================================================
讀 g1_legs_manifest.json（廣蒐時各腿記下 hitCount / fetched / exhaustible），
逐腿硬性斷言：**可窮盡腿（PubMed/OpenAlex/EuropePMC/ClinicalTrials.gov）的
`fetched` 必須 ≥ `hitCount`**，否則 FAIL。AI 合成腿（Consensus/OpenEvidence）
標 exhaustible=false（單次回應先天上限、無法窮盡），只需申報、不強制。

把使用者鐵律「Gate ① 每腿請務必取盡、不准用『量大是噪音/後面會篩』偷工」
從『靠我記得』變機器看守（本輪此錯復發：OpenAlex/EuropePMC 一度只取計數沒翻頁）。

manifest 格式（list[dict]）：
  [{"leg":"PubMed","hitCount":218,"fetched":218,"exhaustible":true}, ...]

用法：python leg_exhaust_check.py --in g1_legs_manifest.json
程式內：import leg_exhaust_check; fails = leg_exhaust_check.check(legs)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# 可窮盡腿（有 cursor/retstart/pageToken，必須翻到底）
EXHAUSTIBLE_DEFAULT = {"pubmed", "openalex", "europepmc", "europe pmc", "clinicaltrials.gov",
                       "clinicaltrials", "ctgov", "epistemonikos"}
# AI 合成腿（單次先天上限，無法窮盡——只能申報）
AI_CAPPED = {"consensus", "openevidence", "oe"}

def _norm(name): return (name or "").strip().lower()

def _base(name):
    """去掉 SR 子腿後綴（`<leg>-SR`／`<leg> sr`），讓 SR 子腿沿用母腿的窮盡分類。
    （SR 過濾器 additive 子腿命名見 SEARCH_SPEC「主動詢問 SR Filter」段：非 PubMed 腿用 `<leg>-SR`。）"""
    n = _norm(name)
    for suf in ("-sr", " sr", "_sr", "-systematic-review"):
        if n.endswith(suf):
            return n[: -len(suf)].strip()
    return n

def check(legs, min_legs=4):
    """回傳 fails 清單（空＝通過）。legs: list[dict]。"""
    fails = []
    if not legs:
        return ["g1_legs_manifest.json 不存在或為空：Gate ① 必須逐腿記 hitCount/fetched 才能證明取盡"]
    seen_exhaustible = 0
    for leg in legs:
        name = leg.get("leg") or leg.get("name") or "?"
        n = _base(name)
        hit = leg.get("hitCount"); fetched = leg.get("fetched")
        exhaustible = leg.get("exhaustible")
        # 跳過腿：唯一合法理由＝技術硬限制（MCP 未連/無金鑰/管轄封鎖）
        if leg.get("skipped"):
            if not leg.get("reason"):
                fails.append(f"[{name}] 標 skipped 但未附硬理由（須為 MCP 未連/無金鑰/管轄封鎖；嚴禁『價值低/重疊高』主觀略過）")
            continue
        if exhaustible is None:
            exhaustible = (n in EXHAUSTIBLE_DEFAULT) and (n not in AI_CAPPED)
        if not exhaustible:
            if n not in AI_CAPPED:
                fails.append(f"[{name}] 標 exhaustible=false 但非已知 AI 合成腿（Consensus/OE）；不可窮盡腿須附硬理由（MCP 未連/無金鑰/管轄封鎖）")
            continue
        seen_exhaustible += 1
        if hit is None or fetched is None:
            fails.append(f"[{name}] 缺 hitCount 或 fetched：無法證明取盡（取盡＝可稽核字面宣稱，須對帳）")
            continue
        if fetched < hit:
            fails.append(f"[{name}] 未取盡：fetched {fetched} < hitCount {hit}（差 {hit-fetched} 筆未翻頁）。量大正解是收緊 query，不是少抓固定 query")
    if seen_exhaustible < min_legs:
        fails.append(f"可窮盡腿只記到 {seen_exhaustible} 條（需 ≥{min_legs}）：六腿不可主觀省略，能跑而未跑＝本關未通關")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="g1_legs_manifest.json")
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}（Gate ① 尚未跑或未寫 manifest）"); sys.exit(1)
    legs = json.loads(p.read_text(encoding="utf-8"))
    fails = check(legs)
    if fails:
        print("❌ Gate ① 取盡檢查未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ Gate ① 每腿取盡（可窮盡腿 fetched≥hitCount，AI 合成腿已申報）。")

if __name__ == "__main__":
    main()
