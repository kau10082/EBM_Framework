# -*- coding: utf-8 -*-
"""
strategy_adherence_check.py — Gate ①『實際 query 不得偏離核准策略』硬 gate（反擅自加過濾）
================================================================================
比對 g1_legs_manifest.json 每腿『實際送出的 query』與 g0_strategy.json 的核准策略：
被核准為 design_filter_allowed=false 的腿，其 query **不得**出現設計／品質過濾特徵
（[pt]/[ptyp]、systematic[sb]、PUB_TYPE:、randomi*、placebo[tiab]、meta-analysis、
 systematic review、controlled clinical trial、sjr/quartile…）。

把使用者鐵律「不得擅自在檢索腿加未核准的過濾器」從靠記性變機器看守。
（2026-06 實測：OpenAlex/EuropePMC 被擅自加設計過濾、PubMed RCT 過濾器被私自擴成 RCT∨SR，
  當時無任何關卡比對『實際 query vs 核准策略』→ 偏離無人攔。本守門即為此而立。）

落地約定（由 ⓪ 核准與 Stage A 廣蒐寫出）：
  • g0_strategy.json：{"legs":[{"leg":"PubMed","design_filter_allowed":true},
                                {"leg":"OpenAlex","design_filter_allowed":false}, …]}
    —— 逐腿宣告該腿是否獲核准使用設計／品質過濾（PubMed 套 Cochrane RCT 過濾器＝true；
       其餘文獻腿求 recall＝false）。要改某腿的過濾政策，須先得使用者核准、改此檔。
  • g1_legs_manifest.json：每腿（skipped 者免）須含 "query"＝該腿『實際送出的字串』。

用法：python strategy_adherence_check.py --manifest g1_legs_manifest.json --strategy g0_strategy.json
程式內：import strategy_adherence_check; fails = strategy_adherence_check.check(manifest, strategy)
"""
import sys, json, re, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# 設計／品質過濾特徵（regex, 不分大小寫）。出現在「不准過濾」的腿＝未核准偏離。
# 僅列『設計/品質過濾』專屬語彙——疾病軸/介入軸詞（COPD、fluticasone… Trelegy 等）不會誤觸。
DESIGN_FILTER_PATTERNS = [
    r"\[pt\]", r"\[ptyp\]", r"systematic\[sb\]", r"pub_type\s*:",
    r"randomi[sz]", r"placebo\[tiab\]", r"\brandomly\b",
    r"meta-?analysis", r"systematic review", r"controlled clinical trial",
    r"\bsjr\b", r"\bsjr_max\b", r"\bquartile\b",
]

def _norm(s): return (s or "").strip().lower()

def check(manifest, strategy):
    """回傳 fails 清單（空＝通過）。manifest: list[dict]; strategy: dict（含 legs）或 list。"""
    fails = []
    if not manifest:
        return ["g1_legs_manifest.json 不存在或為空：無法稽核策略遵從"]
    if not strategy:
        return ["g0_strategy.json 不存在或為空：⓪ 核准策略未落地，無基準可比對"
                "（請於 ⓪ 核准時寫出 g0_strategy.json：逐腿 leg + design_filter_allowed）"]
    legs_strat = strategy.get("legs", strategy) if isinstance(strategy, dict) else strategy
    allow = {}
    for s in legs_strat:
        if isinstance(s, dict):
            allow[_norm(s.get("leg") or s.get("name"))] = bool(s.get("design_filter_allowed"))
    pats = [re.compile(p, re.I) for p in DESIGN_FILTER_PATTERNS]
    for leg in manifest:
        name = leg.get("leg") or leg.get("name") or "?"
        n = _norm(name)
        if leg.get("skipped"):
            continue
        if n not in allow:
            fails.append(f"[{name}] 不在核准策略 g0_strategy.json（無基準可比對；策略外的腿不得擅自新增）")
            continue
        q = leg.get("query")
        if not q:
            fails.append(f"[{name}] manifest 未記錄實際 query：無法稽核是否偏離核准策略"
                         "（廣蒐須把每腿實際送出的 query 寫進 manifest）")
            continue
        if allow[n]:
            continue  # 該腿經核准可用設計／品質過濾（如 PubMed 的 Cochrane RCT 過濾器）
        hit = sorted({p.pattern for p in pats if p.search(q)})
        if hit:
            fails.append(f"[{name}] 被核准為『不得加設計/品質過濾』，但實際 query 出現未核准過濾特徵 "
                         f"{hit}：擅自偏離核准策略（SR 敏感度優先；要加過濾須先得使用者核准、改 g0_strategy.json）")
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
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    fails = check(manifest, strategy)
    if fails:
        print("❌ 策略遵從檢查未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 策略遵從：各腿實際 query 未偏離核准策略（不得加未核准設計/品質過濾）。")

if __name__ == "__main__":
    main()
