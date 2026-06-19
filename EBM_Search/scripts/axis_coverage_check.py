# -*- coding: utf-8 -*-
"""
axis_coverage_check.py — Gate ①『四軸展開覆蓋』硬 gate（反 query 過度簡化／四軸沒展開）
================================================================================
讀 g1_legs_manifest.json（每腿實際 query）＋ g0_strategy.json（axes 宣告同義詞）。
對每條『須在 query 出現的軸』(in_query=true)，**每腿 query 至少要命中該軸 1 個同義詞/別名/代號**；
某 in_query 軸 0 命中＝四軸沒展開/過度簡化 → FAIL。

把使用者鐵律「⓪四軸展開要確實做」從靠記性變機器看守（2026-06 手機遠端實測：四軸聯集沒做）。
（採審查 🟡 建議：驗『軸存在性』≥1 即可，**不**要求塞滿 N 個——精準高階 MeSH term 或
 CT.gov 字數限制時不需塞滿，避免過嚴 fail-closed 無法通關。）

g0_strategy.json.axes 格式：
  {"P":{"synonyms":["COPD","chronic obstructive pulmonary disease",...],"in_query":true,"mandatory_screen":true},
   "I":{"synonyms":["triple therapy","ICS/LABA/LAMA","Trelegy",...],"in_query":true,"mandatory_screen":true},
   "C":{"synonyms":["LABA/LAMA","umeclidinium/vilanterol",...],"in_query":false,"mandatory_screen":true}}
（in_query=false 的軸＝搜尋階段不放入 query 求 recall、留待 ③ 嚴格篩；故此關只查 in_query 軸。）

用法：python axis_coverage_check.py --manifest g1_legs_manifest.json --strategy g0_strategy.json
程式內：import axis_coverage_check; fails = axis_coverage_check.check(manifest, strategy)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def check(manifest, strategy):
    fails = []
    if not manifest:
        return ["g1_legs_manifest.json 不存在或為空：無法稽核四軸覆蓋"]
    if not strategy or not isinstance(strategy, dict):
        return ["g0_strategy.json 不存在或格式錯誤：無基準可比對"]
    axes = strategy.get("axes")
    if not axes or not isinstance(axes, dict):
        return ["g0_strategy.json 未宣告 axes（四軸同義詞）：⓪ 須先寫出 axes 才能稽核四軸展開"]
    qaxes = {k: v for k, v in axes.items() if isinstance(v, dict) and v.get("in_query")}
    if not qaxes:
        return ["g0_strategy.json axes 無任一 in_query 軸：至少疾病/介入軸須在 query 出現"]
    for leg in manifest:
        if leg.get("skipped"):
            continue
        name = leg.get("leg") or leg.get("name") or "?"
        q = leg.get("query") or ""
        if not q:
            fails.append(f"[{name}] 未記錄 query：無法稽核四軸覆蓋（廣蒐須把實際 query 寫進 manifest）")
            continue
        ql = q.lower()
        for ax, spec in qaxes.items():
            syns = [s for s in (spec.get("synonyms") or []) if s]
            if not syns:
                fails.append(f"g0 axes[{ax}] 無 synonyms：無法判該軸覆蓋（請補同義詞清單）")
                continue
            if not any(s.lower() in ql for s in syns):
                fails.append(f"[{name}] query 缺『{ax}』軸（0 個同義詞命中）：四軸未展開/過度簡化"
                             f"（須 ≥1 個 {ax} 同義詞/別名/代號出現於 query）")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="g1_legs_manifest.json")
    ap.add_argument("--strategy", default="g0_strategy.json")
    a = ap.parse_args()
    mp, sp = Path(a.manifest), Path(a.strategy)
    if not mp.exists():
        print(f"⏭  找不到 {a.manifest}"); sys.exit(1)
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    fails = check(manifest, strategy)
    if fails:
        print("❌ 四軸覆蓋檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 四軸覆蓋：各腿 query 對每條 in_query 必含軸 ≥1 同義詞命中（四軸已展開）。")

if __name__ == "__main__":
    main()
