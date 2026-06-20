# -*- coding: utf-8 -*-
"""
awaiting_channels_check.py — 鐵律『待評估＝三管道全失敗才成立』硬 gate（②c）
================================================================================
使用者鐵律（2026-06 再三強調）：一筆要被歸到「待評估」，必須是**三個取得管道全部失敗**：
  1. 無摘要（abstract）
  2. 全文無法線上閱讀（PMC／Europe PMC inEPMC/isOpenAccess/pmcid/hasPDF）
  3. 全文也無法經 Unpaywall 等 OA 機制線上取得
三者皆失敗才判待評估；其中有 ID（doi/pmid/pmcid/nct）者＝『待人工補全文』，完全無 ID 者＝『兩者皆無』。

本守門讀 g2c_awaiting_classification.json，逐筆要求：
  • 帶 ID 的待評估（待人工補全文）必須同時標記三管道都查過＋已窮盡：
    abstract_checked ∧ online_fulltext_checked ∧ (unpaywall_checked|oa_fetch_attempted) ∧ channels_exhausted。
  • 『兩者皆無』必須真的無任何 ID（doi/pmid/pmcid/nct/oa_url）且 abstract_checked。
缺旗標或自相矛盾＝FAIL（代表沒把三管道查盡就 punt 成待評估）。

用法：python awaiting_channels_check.py --in g2c_awaiting_classification.json
程式內：import awaiting_channels_check; fails = awaiting_channels_check.check(awaiting)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _t(v): return str(v if v is not None else "")

def check(awaiting):
    fails = []
    if not awaiting:
        return []
    if not isinstance(awaiting, list):
        return ["g2c_awaiting_classification.json 非清單：無法稽核待評估三管道"]
    for a in awaiting:
        if not isinstance(a, dict):
            continue
        pid = a.get("paper_id") or a.get("uid") or _t(a.get("title"))[:40] or "?"
        reason = _t(a.get("reason") or a.get("verdict"))
        has_id = bool(a.get("doi") or a.get("pmid") or a.get("pmcid") or a.get("nct"))
        abs_ck = a.get("abstract_checked")
        onl_ck = a.get("online_fulltext_checked")
        oa_ck  = a.get("unpaywall_checked") or a.get("oa_fetch_attempted")
        if "兩者皆無" in reason:
            if has_id or a.get("oa_url"):
                fails.append(f"[{pid}] 標『兩者皆無』卻帶 ID/OA 路徑：有路徑＝不可判兩者皆無"
                             f"（須續查線上全文／Unpaywall，取不到才改『待人工補全文』）")
            if not abs_ck:
                fails.append(f"[{pid}] 『兩者皆無』未標 abstract_checked：須先確認確無摘要")
            continue
        # 其餘待評估（有 ID＝待人工補全文）：三管道＋窮盡旗標缺一不可
        missing = [n for n, v in (("abstract_checked", abs_ck),
                                  ("online_fulltext_checked", onl_ck),
                                  ("unpaywall_checked/oa_fetch_attempted", oa_ck),
                                  ("channels_exhausted", a.get("channels_exhausted"))) if not v]
        if missing:
            fails.append(f"[{pid}] 待評估但未證明三管道全查盡，缺旗標 {missing}："
                         f"待評估只在『無摘要＋無線上全文(PMC/EPMC)＋Unpaywall 亦無』時才成立")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="g2c_awaiting_classification.json")
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}（②c 尚未產出待評估）"); sys.exit(1)
    aw = json.loads(p.read_text(encoding="utf-8"))
    fails = check(aw)
    if fails:
        print("❌ 待評估三管道檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 待評估三管道：每筆待評估皆已證明摘要／線上全文／Unpaywall 三管道全失敗。")

if __name__ == "__main__":
    main()
