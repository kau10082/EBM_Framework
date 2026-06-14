# -*- coding: utf-8 -*-
"""無 API：把 cache 內所有 p3 的同類 outcome 並排，檢查跨篇是否用同一把尺。
不是判錯誤，是「分歧提示」——同類 outcome 的 imprecision/indirectness 判定不同時提醒回看
（差異可能由 N/事件數合理解釋，也可能是判斷不一致）。

  python tools/audit_consistency.py
"""
import sys
import json
import re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

# outcome 名 → 類別（關鍵字）
# 順序＝優先（先具體後一般）：嚴重/無惡化須在「惡化率」之前；整體安全在專項 AESI 之前
CATS = [
    ("time_to_exacerbation", r"惡化.*時間|time to"),
    ("severe_exacerbation", r"嚴重惡化|severe exacerb"),
    ("exacerbation_free", r"無惡化|exacerbation.?free"),
    ("exacerbation_rate", r"惡化率|至少一次惡化|一次惡化|exacerbation rate"),
    ("FEV1", r"FEV"),
    ("QoL", r"生活品質|QoL|QOL"),
    ("biomarker_NE", r"彈性蛋白酶|痰|elastase|NE 活性"),
    ("adverse_events", r"不良事件與安全|嚴重不良|嚴重 AE|serious ae|any ae|整體.*AE"),
    ("dental_AESI", r"牙科|牙周|dental"),
    ("skin_AESI", r"皮膚|hyperkeratosis|skin"),
    ("adverse_events_other", r"不良事件|安全|adverse|AE"),
]


def categorize(name):
    for cat, pat in CATS:
        if re.search(pat, name, re.I):
            return cat
    return "other"


def main():
    rows = {}
    for p in sorted(CACHE.glob("*.p3.json")):
        pid = p.name[:-8]
        data = json.loads(p.read_text(encoding="utf-8"))
        for o in data.get("outcomes", []):
            cat = categorize(o.get("outcome_name", ""))
            dd = o.get("downgrade_domains", {})
            rows.setdefault(cat, []).append({
                "pid": pid,
                "name": o.get("outcome_name", ""),
                "final": o.get("certainty_final", "?"),
                "rob": dd.get("risk_of_bias", {}).get("verdict", "?"),
                "ind": dd.get("indirectness", {}).get("verdict", "?"),
                "imp": dd.get("imprecision", {}).get("verdict", "?"),
            })

    if not rows:
        print("cache 內無 p3 檔。")
        return

    print(f"=== 跨篇一致性稽核（{sum(len(v) for v in rows.values())} 個 outcome，{len(rows)} 類）===\n")
    for cat in sorted(rows):
        items = rows[cat]
        print(f"▌ {cat}")
        for r in items:
            print(f"    {r['pid']:<26} {r['final']:<9} rob={r['rob']:<13} ind={r['ind']:<13} imp={r['imp']}")
        # 分歧提示（同類 ≥2 篇且某領域判定不只一種）
        if len(items) >= 2:
            for dom, key in [("imprecision", "imp"), ("indirectness", "ind"), ("risk_of_bias", "rob")]:
                vals = {r[key] for r in items}
                if len(vals) > 1:
                    print(f"    ⚠️ {dom} 判定分歧：{sorted(vals)} — 確認是否由 N/事件數差異合理解釋")
        print()


if __name__ == "__main__":
    main()
