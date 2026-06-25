# -*- coding: utf-8 -*-
"""
screen_tiers.py — ③『全文/摘要搜尋及嚴格離題篩選』可重用 harness（committed；與 public_legs.py 同精神：
把每輪手刻 tier 腳本反覆復發的低級錯誤，前移成「器內先天保證」shift-left，不再靠 gate 事後攔）。

2026-06 Antigravity 複審『強烈建議』新增本器。封裝三項先天保證（皆為實測復發 bug 轉化）：
  (G1) 軸判定『必須有內容』：無 abstract／全文者一律回 unknown（escalate），**嚴禁憑標題判 present→切題**
       （實測 bug：Tier 3 對 6 筆 title-only 憑標題同時含三軸即判切題）。
  (G2) axis_hits『鍵名＝g0 軸名』：直接讀 g0_strategy.json 的 axes key（P_disease/I_benralizumab/…），
       不用通用 P/I/C（實測 bug：strict_screen_check 因鍵名不符報「放水」）。
  (G3) 判定『必帶內容 provenance』：finalize_check 在寫 g3_FINAL_screen.json 前自驗——切題/離題須帶
       abstract／fulltext_excerpt／content_status∈{registry,ai_summary}（實測 bug：最終檔只存 axis_hits、
       來源證明 gate 報「741 筆無內容卻有判定」）。

判定規則對齊 SEARCH_SPEC ③：切題＝所有必含軸 present；離題＝有內容且≥1 軸 absent（離題只在實取全文後定案）；
其餘＝escalate（升下一 Tier）。本器只做『單筆內容→軸判定→verdict』與『最終自驗』；Tier 升級流程、內容抓取
（PMC/Unpaywall/AI 合成）仍由呼叫端用 pmc_fulltext.py／fulltext_exhaust.py／Consensus·OE 完成。

用法：
  import screen_tiers as ST
  hits, has_content = ST.judge_axes(title, content, strategy)   # content＝該筆摘要或全文（無內容傳 ''）
  verdict = ST.verdict(hits, strategy, has_content)             # 切題/離題/escalate
  problems = ST.finalize_check(records, strategy)               # 寫 g3_FINAL 前自驗，空＝可寫
  python screen_tiers.py --selftest
"""
import sys, re, json, argparse
from pathlib import Path

MIN_CONTENT = 1   # 有任何非空內容即可判 absent；無內容→unknown（不得判 present/absent）

def mandatory_axes(strategy):
    ax = (strategy or {}).get("axes") or {}
    return [k for k, v in ax.items() if isinstance(v, dict) and v.get("mandatory_screen")]

def _syn_core(s):
    # 去掉欄位標籤（Asthma[mh]→Asthma、benralizumab[tiab]→benralizumab）
    return re.split(r"[\[]", s, maxsplit=1)[0].strip()

def judge_axes(title, content, strategy):
    """回 (axis_hits, has_content)。axis_hits 鍵＝g0 軸名(G2)；無內容→全 unknown(G1)，嚴禁憑標題判定
    （『禁只憑標題』鐵律：無 abstract/全文者，連標題都不拿來判 present/absent，一律 unknown→escalate 去抓內容）。
    有內容時才以『標題＋內容』判：軸同義詞命中→{'status':'yes','evidence':片段}；未命中→{'status':'no'}。"""
    ax = (strategy or {}).get("axes") or {}
    content = (content or "").strip()
    has_content = len(content) >= MIN_CONTENT
    text = ((title or "") + " \n " + content) if has_content else ""   # (G1) 無內容＝不判（連標題都不看）
    hits = {}
    for name, spec in ax.items():
        if not (isinstance(spec, dict) and (spec.get("mandatory_screen") or spec.get("in_query"))):
            continue
        ev = None
        for s in (spec.get("synonyms") or []):
            core = _syn_core(s)
            if not core:
                continue
            m = re.search(re.escape(core), text, re.I)
            if m:
                ev = m.group(0); break
        if ev:
            hits[name] = {"status": "yes", "evidence": ev}
        elif has_content:
            hits[name] = {"status": "no"}
        else:
            hits[name] = {"status": "unknown"}   # (G1) title-only：不得判 present/absent
    return hits, has_content

def verdict(hits, strategy, has_content):
    """切題＝所有必含軸 present；離題＝有內容且≥1 軸 absent；否則 escalate（升 Tier，離題只在實取全文後定案）。
    無內容一律 escalate（切題/離題皆須內容；防 title-only 定案）。"""
    if not has_content:
        return "escalate"
    mand = mandatory_axes(strategy)
    states = [(hits or {}).get(a, {}).get("status") for a in mand]
    if mand and all(s == "yes" for s in states):
        return "切題"
    if has_content and any(s == "no" for s in states):
        return "離題"
    return "escalate"

def _has_provenance(r):
    return bool((r.get("abstract") or "").strip()) or bool((r.get("fulltext_excerpt") or "").strip()) \
        or str(r.get("content_status") or "") in ("registry", "ai_summary") \
        or bool(r.get("nct"))

def finalize_check(records, strategy):
    """(G2)+(G3) 寫 g3_FINAL_screen.json 前自驗：回問題清單（空＝可寫）。鏡像 gate_guard 之 ③ 檢查、前移攔截。"""
    mand = set(mandatory_axes(strategy))
    problems, seen = [], set()
    VERD = {"切題", "離題", "全文及摘要皆無"}
    for r in records:
        uid = r.get("uid")
        if not uid:
            problems.append("有記錄缺 uid（無法防坍縮）"); continue
        if uid in seen:
            problems.append(f"uid 重複：{uid}")
        seen.add(uid)
        v = r.get("verdict") or ""
        if v not in VERD:
            problems.append(f"[{uid}] verdict 非法：{v!r}"); continue
        if v in ("切題", "離題"):
            ah = r.get("axis_hits")
            if not isinstance(ah, dict) or not mand.issubset(set(ah.keys())):
                problems.append(f"[{uid}] axis_hits 鍵名須含 g0 軸名 {sorted(mand)}（得 {sorted((ah or {}).keys())}）")  # (G2)
            if not _has_provenance(r):
                problems.append(f"[{uid}] {v} 卻無內容 provenance（須 abstract/fulltext_excerpt/registry/ai_summary）")  # (G3)
    return problems

# ───────────────────────── self-test ─────────────────────────
def selftest():
    strat = {"axes": {
        "P_disease": {"mandatory_screen": True, "synonyms": ["asthma", "Asthma[mh]", "eosinophilic asthma"]},
        "I_benralizumab": {"mandatory_screen": True, "synonyms": ["benralizumab", "Fasenra"]},
        "C_mepolizumab": {"mandatory_screen": True, "synonyms": ["mepolizumab", "Nucala"]},
    }}
    ok = True
    # (G1) title-only with all 3 axes in TITLE but NO content -> must NOT be 切題 (must escalate)
    h, hc = judge_axes("benralizumab vs mepolizumab in eosinophilic asthma", "", strat)
    v = verdict(h, strat, hc)
    g1 = (v == "escalate") and all(h[k]["status"] == "unknown" for k in h)
    print(("  ✅" if g1 else "  ❌") + f" (G1) title-only 三軸不得判切題（得 verdict={v}）")
    ok &= g1
    # (G1ب) with content -> proper 切題
    h2, hc2 = judge_axes("switch study", "benralizumab and mepolizumab in severe eosinophilic asthma cohort", strat)
    g1b = verdict(h2, strat, hc2) == "切題" and set(h2.keys()) == {"P_disease", "I_benralizumab", "C_mepolizumab"}
    print(("  ✅" if g1b else "  ❌") + " (G2) 有內容→切題且 axis_hits 用 g0 軸名")
    ok &= g1b
    # 離題 only with content + absent axis
    h3, hc3 = judge_axes("benralizumab placebo trial", "benralizumab versus placebo in severe asthma, no other biologic", strat)
    g1c = verdict(h3, strat, hc3) == "離題" and h3["C_mepolizumab"]["status"] == "no"
    print(("  ✅" if g1c else "  ❌") + " (離題) 有內容且缺 C→離題")
    ok &= g1c
    # (G3) finalize_check catches 切題 without provenance & wrong keys
    bad = [{"uid": "x1", "verdict": "切題", "axis_hits": {"P": {"status": "yes"}}},  # wrong keys + no provenance
           {"uid": "x2", "verdict": "離題", "axis_hits": {"P_disease": {"status": "no"}, "I_benralizumab": {"status": "yes"}, "C_mepolizumab": {"status": "yes"}}}]  # no provenance
    probs = finalize_check(bad, strat)
    g3 = len(probs) >= 2
    print(("  ✅" if g3 else "  ❌") + f" (G3) finalize_check 攔截缺鍵/缺 provenance（得 {len(probs)} 問題）")
    ok &= g3
    # finalize_check passes a clean record
    good = [{"uid": "g1", "verdict": "切題", "abstract": "benralizumab mepolizumab asthma",
             "axis_hits": {"P_disease": {"status": "yes"}, "I_benralizumab": {"status": "yes"}, "C_mepolizumab": {"status": "yes"}}}]
    g4 = not finalize_check(good, strat)
    print(("  ✅" if g4 else "  ❌") + " (G3) 乾淨記錄應通過（防誤報）")
    ok &= g4
    print("✅ screen_tiers selftest 全過" if ok else "❌ screen_tiers selftest 有失敗")
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    if a.selftest:
        sys.exit(selftest())
    ap.print_help()

if __name__ == "__main__":
    main()
