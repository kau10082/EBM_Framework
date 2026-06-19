# -*- coding: utf-8 -*-
"""
strict_screen_check.py — Gate ③『嚴格篩逐軸核對、不放水』硬 gate
================================================================================
讀 g3_FINAL_screen.json ＋ g0_strategy.json（mandatory_screen 軸）。每筆判定須帶
`axis_hits`（逐軸證據）。把使用者鐵律「③須對 P∧I∧C 全部核對才算切題、不准放水」
從靠記性變機器看守（2026-06 手機遠端實測：③ 未確實逐軸核對、有放水）。

判定規則（必含軸＝g0 axes 中 mandatory_screen=true 者；比較型題含 C）：
 • 切題(included/切題)：**所有**必含軸必須命中（present）；缺任一 → FAIL（放水）。
   無 axis_hits 逐軸證據亦 FAIL（無從證明逐軸核對過）。
 • 離題(excluded/離題)：須**至少一**必含軸『確認缺(absent/no)』並標明缺哪軸；
   若無任何軸確認缺（例如 P∧I 命中、C 僅 unknown）→ FAIL（應移『待評估』而非離題）。
 • 待評估/awaiting：放行（Stage A 待全文）。

axis_hits 值判讀：present＝True/"yes"/任何非空證據字串；absent＝False/"no"；
unknown＝None/缺/"unknown"/"?"。

用法：python strict_screen_check.py --screen g3_FINAL_screen.json --strategy g0_strategy.json
程式內：import strict_screen_check; fails = strict_screen_check.check(screen, strategy)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

INCLUDE = {"切題", "included", "include", "納入候選", "候選"}
EXCLUDE = {"離題", "excluded", "exclude", "剔除"}

def _state(v):
    """present / absent / unknown。"""
    if v is True: return "present"
    if v is False: return "absent"
    if v is None: return "unknown"
    s = str(v).strip().lower()
    if s in ("yes", "y", "present", "命中", "現", "✓", "true"): return "present"
    if s in ("no", "n", "absent", "缺", "✗", "false"): return "absent"
    if s in ("", "unknown", "unk", "?", "？", "na", "n/a", "待確認"): return "unknown"
    return "present"  # 非空且非否定字串＝視為提供了證據（命中）

def check(screen, strategy):
    fails = []
    if screen is None:
        return ["g3_FINAL_screen.json 不存在：無法稽核嚴格篩"]
    if not strategy or not isinstance(strategy, dict) or not strategy.get("axes"):
        return ["g0_strategy.json 未宣告 axes：無 mandatory_screen 必含軸基準可比對"]
    mand = [k for k, v in strategy["axes"].items() if isinstance(v, dict) and v.get("mandatory_screen")]
    if not mand:
        return ["g0 axes 無任一 mandatory_screen 軸：③ 無必含軸可核對"]
    for i, r in enumerate(screen):
        tag = r.get("uid") or r.get("pmid") or r.get("title") or ("#%d" % i)
        v = str(r.get("verdict") or "").strip()
        hits = r.get("axis_hits")
        if v in INCLUDE:
            if not isinstance(hits, dict):
                fails.append(f"[{tag}] 切題卻無 axis_hits 逐軸證據：放水（須逐軸核對 {mand} 才可切題）")
                continue
            miss = [ax for ax in mand if _state(hits.get(ax)) != "present"]
            if miss:
                fails.append(f"[{tag}] 切題卻缺必含軸證據 {miss}（axis_hits={hits}）：放水，須所有必含軸命中才切題")
        elif v in EXCLUDE:
            states = {ax: _state((hits or {}).get(ax)) for ax in mand}
            if "absent" not in states.values():
                unknown = [a for a, s in states.items() if s == "unknown"]
                fails.append(f"[{tag}] 判離題卻無任何必含軸『確認缺(absent)』（{states}）：離題須標明缺哪軸；"
                             f"若僅 {unknown} 未確認（如短摘要看不出對照 C），應移『待評估』待看全文，不得逕判離題")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", default="g3_FINAL_screen.json")
    ap.add_argument("--strategy", default="g0_strategy.json")
    a = ap.parse_args()
    sc, sp = Path(a.screen), Path(a.strategy)
    if not sc.exists():
        print(f"⏭  找不到 {a.screen}"); sys.exit(1)
    screen = json.loads(sc.read_text(encoding="utf-8"))
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    fails = check(screen, strategy)
    if fails:
        print("❌ 嚴格篩逐軸核對未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 嚴格篩：切題者全必含軸命中、離題者標明缺軸（無放水）。")

if __name__ == "__main__":
    main()
