# -*- coding: utf-8 -*-
"""
axis_expansion_check.py — Gate ⓪『四軸展開必須真的做（同義詞庫要展開，不得過度簡化）』硬 gate
================================================================================
四軸展開是鐵律（SEARCH_SPEC §1①(1)）：每個概念都要沿『縮寫↔全文／臨床慣稱↔生化別名／
藥類↔INN↔開發代號↔品牌／疾病縮寫↔全文』把別名寫法窮盡，才有最大 recall。

既有 `axis_coverage_check.py` 只檢查「每腿 query ≥1 同義詞命中（軸存在性）」——**攔不到**
「同義詞庫根本沒展開」這個失敗模式（例：P 只寫 COPD、I 只寫 triple therapy 也會通過 coverage）。
本守門補上：直接稽核 **g0_strategy.json 的 axes 同義詞庫本身是否真的展開**。

判定（對每條 in_query 或 mandatory_screen 的軸）：
  (1) 去重後同義詞數 ≥ MIN_SYNONYMS(=3) —— 證明有展開出別名，而非一個裸詞；
  (2) 至少有 1 個「全文／多詞形式」（含空白的展開寫法）—— 證明做了『縮寫↔全文』展開，
      不是只丟一串純縮寫。
兩者任一不滿足＝四軸展開未做/過度簡化 → FAIL。

採低門檻（≥3＋至少一個全文形式）：任何真的有展開的軸都輕鬆通過，但能擋掉「裸詞」稀疏策略；
不要求塞滿 N 個（與 axis_coverage 設計一致，避免 fail-closed 無法通關）。

用法：python axis_expansion_check.py --strategy g0_strategy.json
程式內：import axis_expansion_check; fails = axis_expansion_check.check(strategy)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

MIN_SYNONYMS = 3

def check(strategy):
    """回傳 fails 清單（空＝通過）。strategy: dict（含 axes）。"""
    fails = []
    if not strategy or not isinstance(strategy, dict):
        return ["g0_strategy.json 不存在或格式錯誤：無法稽核四軸展開"]
    axes = strategy.get("axes")
    if not axes or not isinstance(axes, dict):
        return ["g0_strategy.json 未宣告 axes（四軸同義詞）：⓪ 須先寫出 axes 才能稽核四軸展開"]
    checked = 0
    for ax, spec in axes.items():
        if not isinstance(spec, dict):
            continue
        # 只稽核「會進 query 求 recall」或「要用來篩選」的軸——這些才需要四軸展開
        if not (spec.get("in_query") or spec.get("mandatory_screen")):
            continue
        checked += 1
        syns = [s.strip() for s in (spec.get("synonyms") or []) if isinstance(s, str) and s.strip()]
        uniq = sorted({s.lower() for s in syns})
        if len(uniq) < MIN_SYNONYMS:
            fails.append(f"[{ax}] 同義詞僅 {len(uniq)} 個（<{MIN_SYNONYMS}）：四軸展開未做/過度簡化"
                         f"（每軸至少要展開縮寫↔全文＋別名/INN/開發代號/品牌）")
            continue
        if not any(" " in s for s in syns):
            fails.append(f"[{ax}] 同義詞無任何『全文/多詞形式』（疑似只有純縮寫/代號）："
                         f"四軸展開缺『縮寫↔全文』那一軸（須補上展開後的全名寫法）")
    if checked == 0:
        return ["g0_strategy.json axes 無任一 in_query/mandatory_screen 軸：至少疾病/介入軸須宣告並展開"]
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="g0_strategy.json")
    a = ap.parse_args()
    sp = Path(a.strategy)
    if not sp.exists():
        print(f"⏭  找不到 {a.strategy}（⓪ 尚未寫出策略）"); sys.exit(1)
    strategy = json.loads(sp.read_text(encoding="utf-8"))
    fails = check(strategy)
    if fails:
        print("❌ 四軸展開檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 四軸展開：各軸同義詞庫已實際展開（≥3 別名且含全文形式）。")

if __name__ == "__main__":
    main()
