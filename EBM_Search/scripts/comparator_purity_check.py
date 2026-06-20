# -*- coding: utf-8 -*-
"""
comparator_purity_check.py — Gate ⓪／①『檢索 query 只含 in_query 軸，不得摻入對照/排除軸』硬 gate
================================================================================
檢索階段（廣蒐）必須**最大 recall**：每腿 query **只能含 in_query=true 的軸**（一般＝P 疾病軸＋
I 介入軸）。**對照軸 C（in_query=false）等任何「不放進 query」的軸，其同義詞不得出現在任何腿的 query**——
否則會把『標題/摘要沒提到對照組』的研究整段砍掉、嚴重傷 recall（對照軸要留待 ③ 嚴格篩讀全文才比對）。

把使用者鐵律「檢索只含 P＋I、不得含 C」從靠記性變機器看守。
（2026-06 實測：triple vs dual COPD 案，Consensus／OpenAlex query 連兩版被擅自塞入
 「versus dual therapy LABA/LAMA」＝C 軸 → 會砍掉沒提對照組的研究。本守門即為此而立，
 之後任何把 in_query=false 軸塞進 query 的偏離都會被攔下。）

關鍵：比對前**先把所有 in_query=true 軸的同義詞從 query 遮蔽**，避免 I 軸長詞含 C 軸子字串造成誤判
（例：I 軸『ICS/LABA/LAMA』內含 C 軸『LABA/LAMA』；遮蔽 I 軸後 query 殘餘才拿去掃 C 軸）。

g0_strategy.json.axes 與 g1_legs_manifest.json 格式同 axis_coverage_check（每軸 synonyms/in_query；
每腿 query＝實際送出字串；skipped 腿免查）。

用法：python comparator_purity_check.py --manifest g1_legs_manifest.json --strategy g0_strategy.json
程式內：import comparator_purity_check; fails = comparator_purity_check.check(legs, strategy)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def check(legs, strategy):
    """回傳 fails 清單（空＝通過）。legs: list[dict]（manifest 或 g0.legs）；strategy: dict（含 axes）。"""
    fails = []
    if not legs:
        return ["legs 不存在或為空：無法稽核 query 是否摻入對照/排除軸"]
    if not strategy or not isinstance(strategy, dict):
        return ["g0_strategy.json 不存在或格式錯誤：無基準可比對"]
    axes = strategy.get("axes")
    if not axes or not isinstance(axes, dict):
        return ["g0_strategy.json 未宣告 axes：無法判 in_query 軸"]
    in_query_axes = {k: v for k, v in axes.items() if isinstance(v, dict) and v.get("in_query")}
    no_query_axes = {k: v for k, v in axes.items() if isinstance(v, dict) and not v.get("in_query")}
    if not no_query_axes:
        return []  # 沒有任何「不放進 query」的軸（無對照軸）＝無可違反，通過
    # 先收集所有 in_query 軸同義詞（長詞優先），用來遮蔽 query，避免子字串誤判
    mask_terms = []
    for spec in in_query_axes.values():
        mask_terms += [s for s in (spec.get("synonyms") or []) if s]
    mask_terms = sorted(set(mask_terms), key=len, reverse=True)
    for leg in legs:
        if leg.get("skipped"):
            continue
        name = leg.get("leg") or leg.get("name") or "?"
        q = leg.get("query") or ""
        if not q:
            continue  # 缺 query 由 axis_coverage 處理，不在本關重複報
        masked = q.lower()
        for t in mask_terms:
            masked = masked.replace(t.lower(), " ")
        for ax, spec in no_query_axes.items():
            hits = sorted({s for s in (spec.get("synonyms") or []) if s and s.lower() in masked})
            if hits:
                fails.append(
                    f"[{name}] query 摻入『{ax}』軸（in_query=false）同義詞 {hits}："
                    f"檢索階段只能含 in_query=true 軸（求最大 recall）；對照/排除軸不得進 query，"
                    f"須留待 ③ 嚴格篩讀全文才比對（如要改須先得使用者核准、改 g0_strategy.json 的 in_query）")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="g1_legs_manifest.json")
    ap.add_argument("--strategy", default="g0_strategy.json")
    a = ap.parse_args()
    mp, sp = Path(a.manifest), Path(a.strategy)
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    # manifest 優先；無 manifest 時退回 g0 的 legs（讓 ⓪ 策略階段就能被稽核）
    if mp.exists():
        legs = json.loads(mp.read_text(encoding="utf-8"))
    elif isinstance(strategy, dict) and strategy.get("legs"):
        legs = strategy["legs"]
    else:
        print(f"⏭  找不到 {a.manifest} 也無 g0.legs（尚未到此關）"); sys.exit(1)
    fails = check(legs, strategy)
    if fails:
        print("❌ 對照軸純度檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 對照軸純度：各腿 query 只含 in_query 軸，未摻入對照/排除軸（檢索最大 recall）。")

if __name__ == "__main__":
    main()
