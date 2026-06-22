# -*- coding: utf-8 -*-
"""
sr_division_check.py — Gate ①『SR filter 分工：DB 腿無過濾主檢不得灌進篩選語料庫』硬 gate
================================================================================
2026-06 使用者定版（取代先前『additive 聯集進池、不取代廣檢』寫法）：

當使用者決定套用 SR filter 時，分工為——
  • 原始 RCT       ← PubMed 腿（Cochrane RCT 過濾器）
  • SR/MA/NMA      ← 非 PubMed DB 腿的『SR 變體』（`<leg>-SR`，如 EuropePMC-SR/Consensus-SR/OpenAlex-SR）
  • 登錄試驗        ← ClinicalTrials.gov

凡『有 SR 變體』的非 PubMed DB 腿（Consensus／OpenAlex／EuropePMC），其**無過濾主檢**
（尤以 EuropePMC REST 預設全文檢索）會帶進大量全文泛提及噪音，**不得灌進篩選語料庫**
（g1_union.json）。無過濾主檢若有實跑，只作為廣蒐取盡/稽核紀錄寫進 manifest，不進語料庫。

判定：
  • 由 g0_strategy.json 判 SR filter 是否啟用：sr_filter_decision=="applied"，
    或 legs 內存在任一名稱以 -SR 結尾的子腿。
  • 未啟用 → 此關不適用（回 None）。
  • 啟用 → 取「有 SR 變體的非 PubMed DB 腿」的 base 名集合（由 -SR 子腿反推），
    g1_union.json 任一筆 provenance(legs) 若含這些腿的『主檢』（同 base、非 -SR）即 FAIL。
    PubMed（RCT 腿）/ CT.gov（登錄庫，無 SR 變體）天然不在該集合 → 不受限。

用法：python sr_division_check.py --strategy g0_strategy.json --union g1_union.json
程式內：import sr_division_check; fails = sr_division_check.check(strategy, union)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

SR_SUFFIXES = ("-sr", " sr", "_sr", "-systematic-review")

def _norm(s): return (s or "").strip().lower()

def _is_sr(name):
    n = _norm(name)
    return any(n.endswith(suf) for suf in SR_SUFFIXES)

def _base(name):
    n = _norm(name)
    for suf in SR_SUFFIXES:
        if n.endswith(suf):
            return n[: -len(suf)].strip()
    return n

def _sr_applied(strategy):
    if not isinstance(strategy, dict):
        return False
    if _norm(strategy.get("sr_filter_decision")) == "applied":
        return True
    legs = strategy.get("legs") or []
    return any(_is_sr(l.get("leg") or l.get("name")) for l in legs if isinstance(l, dict))

def check(strategy, union):
    """回傳 fails 清單（空＝通過）。strategy: dict; union: list[dict]（每筆含 legs/provenance）。"""
    if not _sr_applied(strategy):
        return []  # SR filter 未啟用：此關不適用
    legs = (strategy.get("legs") or []) if isinstance(strategy, dict) else []
    # 「有 SR 變體」的腿 base 集合（由策略內的 -SR 子腿反推）
    sr_bases = {_base(l.get("leg") or l.get("name")) for l in legs
                if isinstance(l, dict) and _is_sr(l.get("leg") or l.get("name"))}
    if not sr_bases:
        # sr_filter_decision=applied 但策略沒宣告任何 -SR 子腿 → 落地不完整
        return ["g0_strategy.json 標 sr_filter_decision=applied 但 legs 無任何 `<leg>-SR` 子腿："
                "SR 分工未落地（非 PubMed DB 腿須以 -SR 子腿表示其 SR 變體）"]
    if union is None:
        return []  # g1_union 尚未產出＝尚未到此關/暫不適用（與 gate_guard.check_sr_division 的 None 處理一致）
    if not isinstance(union, list):
        return ["g1_union.json 格式非 list：無法稽核 provenance"]
    offenders = {}  # leg -> count
    for r in union:
        for lg in (r.get("legs") or r.get("provenance") or []):
            if _is_sr(lg):
                continue  # SR 變體：合法
            if _base(lg) in sr_bases:
                offenders[lg] = offenders.get(lg, 0) + 1
    if offenders:
        detail = "；".join(f"{lg}: {c} 筆" for lg, c in sorted(offenders.items()))
        return [f"SR filter 啟用時，篩選語料庫(g1_union) 含『有 SR 變體之非 PubMed DB 腿的無過濾主檢』結果（{detail}）："
                f"這些 DB 腿只能以 `<leg>-SR` 結果進語料庫（主檢全文泛提及噪音不得進池）；"
                f"原始 RCT 走 PubMed 腿、SR/MA 走 -SR 腿、登錄試驗走 CT.gov"]
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="g0_strategy.json")
    ap.add_argument("--union", default="g1_union.json")
    a = ap.parse_args()
    sp, up = Path(a.strategy), Path(a.union)
    strategy = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    if strategy is None:
        print(f"⏭  找不到 {a.strategy}（尚未到此關）"); sys.exit(1)
    union = json.loads(up.read_text(encoding="utf-8")) if up.exists() else None
    fails = check(strategy, union)
    if fails:
        print("❌ SR 分工檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ SR 分工：DB 腿只以 SR 變體進語料庫（主檢噪音未灌入），或 SR filter 未啟用（不適用）。")

if __name__ == "__main__":
    main()
