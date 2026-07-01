# -*- coding: utf-8 -*-
"""
citation_screen_check.py — 鐵律『引文追蹤新候選須以標題＋摘要高敏初篩，嚴禁只憑標題丟』硬 gate
================================================================================
使用者鐵律（2026-06，Cochrane 高敏感紅線）：④ 引文追蹤（滾雪球）滾出的新候選，**必須批次抓回摘要、
以『標題＋摘要』做高敏初篩**；**嚴禁「標題沒中 P/I 就直接丟、不抓摘要」**——因為許多 RCT 標題用成分名／
縮寫／廣義詞（chronic lung disease／airflow obstruction／inhaled therapy），只看標題會漏殺隱藏 RCT，
正好抵銷滾雪球的目的。技術正解＝Batch API（efetch 200/批、OpenAlex 50/批），不是犧牲敏感度。
唯一例外：完全無摘要可抓者，可用「負向排除法」（只在標題明顯他題 cancer/pregnancy/animal 時丟、其餘從寬放行）。

讀 g4_citation_tracking.json，逐輪斷言：
  • screened_on 必含 'title+abstract'（每輪都以標題＋摘要篩）；
  • title_only_dropped == 0（沒有任何新候選被『只憑標題』丟棄）；
  • 有 ID 的新候選 > 0 時 abstracts_fetched > 0（確實有批次抓摘要，而非跳過）。

用法：python citation_screen_check.py --in g4_citation_tracking.json
程式內：import citation_screen_check; fails = citation_screen_check.check(g4)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def check(g4):
    fails = []
    if not g4:
        return []  # ④ 尚未跑
    if not isinstance(g4, dict):
        return ["g4_citation_tracking.json 非物件：無法稽核引文追蹤篩選方式"]
    rounds = g4.get("rounds") or []
    method = str(g4.get("screening_method") or "")
    # fail-closed：④ 已有新增候選（new_relevant/hits）卻無 rounds 結構、也未聲明 title+abstract →
    # 篩選方式完全不可稽核（曾因 rounds 空 → 迴圈不跑 → 紅線 gate 靜默通過）
    if not rounds and "title+abstract" not in method and (g4.get("new_relevant") or g4.get("hits")):
        fails.append("④ 有新增候選（new_relevant/hits）但無 rounds 結構、screening_method 也未聲明"
                     " 'title+abstract'：引文追蹤的篩選方式不可稽核——請補 rounds（每輪 screened_on/"
                     "abstracts_fetched/title_only_dropped）或聲明 screening_method")
    if rounds and "title+abstract" not in method and not any("title+abstract" in str(r.get("screened_on","")) for r in rounds):
        fails.append("④ 未聲明以『標題＋摘要』篩（screening_method/screened_on 皆無 title+abstract）："
                     "疑只憑標題篩＝Cochrane 高敏感紅線")
    for r in rounds:
        rn = r.get("round")
        if "title+abstract" not in str(r.get("screened_on", "")):
            fails.append(f"第{rn}輪 screened_on 非『title+abstract』（實得 {r.get('screened_on')!r}）：須以標題＋摘要高敏初篩")
        if r.get("title_only_dropped", 0):
            fails.append(f"第{rn}輪 title_only_dropped={r.get('title_only_dropped')}>0："
                         f"嚴禁只憑標題丟棄滾雪球新候選（Cochrane 紅線；應批次抓摘要後以標題＋摘要篩）")
        if r.get("new_with_id", 0) > 0 and not r.get("abstracts_fetched", 0):
            fails.append(f"第{rn}輪 有 {r.get('new_with_id')} 筆有 ID 新候選卻 abstracts_fetched=0："
                         f"未批次抓摘要（應 efetch/OpenAlex 批次取回再以標題＋摘要篩）")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="g4_citation_tracking.json")
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}（④ 尚未跑）"); sys.exit(0)
    g4 = json.loads(p.read_text(encoding="utf-8"))
    fails = check(g4)
    if fails:
        print("❌ 引文追蹤篩選方式檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 引文追蹤：每輪以『標題＋摘要』高敏初篩、批次抓摘要、無只憑標題丟棄。")

if __name__ == "__main__":
    main()
