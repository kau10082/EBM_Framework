# -*- coding: utf-8 -*-
"""
analysis_scope.py — 算出『實際進入分析的文獻』＋『需人工補全文清單』（確定性、可重現）
================================================================================
因 2026-06 使用者要求而立：
  • Zotero 匯入範圍＝『實際進入分析的文獻』＝grade_track ∈ {full, targeted_harms}
    （背景 light_summary 留在 _corpus.json／報告／交接包，不進 Zotero，除非另指定 --include-background）。
  • 人工補全文範圍＝上述分析集中『全文尚未取得』者；補了才會增進分析結果。
    其餘（背景、已有全文者）不必補。
本工具只『讀』_corpus.json＋inputs/＋cache/*.p1.json 算出兩份清單，不改任何資料。

全文是否已取得 has_fulltext(paper) 判準（任一成立即 True）：
  1. cache/<id>.p1.json 的 data_source 含 'full_text'，或 fulltext_attempts 有 result=fulltext_obtained；
  2. inputs/<id>.pdf 存在（人工補全文／交接複製進來的本機 PDF）；
  3. _corpus.json notes 標 '全文=full_text' 或 '全文=have'。

用法：
  python tools/analysis_scope.py                 # 印兩份清單（Zotero 範圍／需補全文）
  python tools/analysis_scope.py --json           # 另印機器可讀 JSON
  python tools/analysis_scope.py --write          # 寫 cache/_analysis_scope.json
  python tools/analysis_scope.py --include-background   # Zotero 範圍含 light_summary 背景
程式內：from analysis_scope import compute; scope = compute(corpus, cache_dir, inputs_dir)
"""
import sys, os, json, re, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
ANALYSIS_TRACKS = {"full", "targeted_harms"}


def _study_of(p):
    m = re.search(r'study=([A-Za-z0-9\-]+)', p.get("notes") or "")
    return m.group(1) if m else "—"


def _has_fulltext(p, cache_dir, inputs_dir):
    pid = p["paper_id"]
    # 1) p1 證據
    p1 = Path(cache_dir) / f"{pid}.p1.json"
    if p1.exists():
        try:
            obj = json.loads(p1.read_text(encoding="utf-8"))
            if "full_text" in (obj.get("data_source") or []):
                return True, "p1:data_source=full_text"
            for a in (obj.get("fulltext_attempts") or []):
                if a.get("result") == "fulltext_obtained":
                    return True, f"p1:fulltext_obtained({a.get('channel')})"
        except Exception:
            pass
    # 2) 本機 PDF
    if (Path(inputs_dir) / f"{pid}.pdf").exists():
        return True, "inputs/<id>.pdf"
    # 3) notes 標記
    notes = p.get("notes") or ""
    if re.search(r'全文=(full_text|have)\b', notes):
        return True, "notes:全文=have"
    return False, "全文尚未取得"


def compute(corpus, cache_dir, inputs_dir, include_background=False):
    papers = corpus["papers"]
    wanted = set(ANALYSIS_TRACKS) | ({"light_summary"} if include_background else set())
    analysis_set, must, optional = [], [], []
    for p in papers:
        if p.get("grade_track") not in wanted:
            continue
        has, why = _has_fulltext(p, cache_dir, inputs_dir)
        rec = {"paper_id": p["paper_id"], "study": _study_of(p), "grade_track": p.get("grade_track"),
               "role": p.get("role"), "relevance": p.get("relevance"),
               "is_primary_report": bool(p.get("is_primary_report")),
               "title": (p.get("title") or "")[:140], "has_fulltext": has, "fulltext_reason": why}
        analysis_set.append(rec)
        if p.get("grade_track") in ANALYSIS_TRACKS and not has:
            # ★ 需補全文最小集（must）＝『分析錨點』：每 Study 的主要報告（full∧is_primary_report）
            #   ＋ targeted_harms 的真害結果研究。其餘 full 次級報告（congress/cost/子分析）＝overlap，
            #   補了不額外增進核心 GRADE → 列 optional，不強求。
            if p.get("grade_track") == "full" and not p.get("is_primary_report"):
                optional.append(rec)
            else:
                must.append(rec)
    must.sort(key=lambda r: (0 if r["grade_track"] == "full" else 1, r["study"], r["paper_id"]))
    optional.sort(key=lambda r: (r["study"], r["paper_id"]))
    # ★ 防呆：full track 的 Study 若『無任一報告有全文』又『無任一主報告進 must』，
    #   多半是 Phase 0 漏標 is_primary_report → 該 Study 的全文需求會被靜默漏列（全掉 optional）。
    #   這裡主動警示，請回 Phase 0 為該 Study 標一篇主報告（is_primary_report=true）。
    must_full_studies = {r["study"] for r in must if r["grade_track"] == "full"}
    full_by_study = {}
    for r in analysis_set:
        if r["grade_track"] == "full" and r["study"] != "—":
            full_by_study.setdefault(r["study"], []).append(r)
    warnings = []
    for s, recs in full_by_study.items():
        if not any(r["has_fulltext"] for r in recs) and s not in must_full_studies:
            warnings.append(f"Study「{s}」：{len(recs)} 篇 full 報告皆無全文，且無任一標 is_primary_report"
                            f"→ 全文需求被漏列（全掉 optional）；請於 Phase 0 為此 Study 標一篇主報告(is_primary_report=true)")
    return {"analysis_set": analysis_set,
            "need_manual_fulltext": must,            # 補這些即可（增進分析的最小集）
            "optional_fulltext": optional,           # full 次級 overlap 報告，補了不增進核心 GRADE
            "warnings": warnings}                    # 防呆警示（需回 Phase 0 修；不阻擋）


def _print(scope):
    a = scope["analysis_set"]; nm = scope["need_manual_fulltext"]; opt = scope.get("optional_fulltext") or []
    byt = {}
    for r in a:
        byt.setdefault(r["grade_track"], []).append(r)
    studies = sorted({r["study"] for r in byt.get("full", []) if r["study"] != "—"})
    print(f"== 實際進入分析的文獻（Zotero 匯入範圍）：{len(a)} 報告 ==")
    print(f"   核心 full：{len(byt.get('full',[]))} 報告 → 收斂為 {len(studies)} 個分析 Study（{'、'.join(studies)}）")
    print(f"   targeted_harms（只評害）：{len(byt.get('targeted_harms',[]))} 報告")
    if byt.get("light_summary"):
        print(f"   （含背景 light_summary：{len(byt['light_summary'])}，--include-background 時才計入）")
    print(f"\n== ★ 需人工補全文（補了才增進分析；補這些即可）：{len(nm)} 報告 ==")
    if not nm:
        print("  （分析集應補全文皆已取得，無需補。）")
    for r in nm:
        tier = "①核心主報告" if r["grade_track"] == "full" else "②harms"
        print(f"  {tier}  {r['paper_id']:<34} {r['study']:<8} {r['title'][:60]}")
    print(f"\n== ○ 選補（full 次級/overlap 報告，補了不增進核心 GRADE）：{len(opt)} 報告 ==")
    print("   （同 Study 的 congress/cost/子分析；分析以主報告全文為錨點，這些當 overlap，不強求補。）")
    warns = scope.get("warnings") or []
    if warns:
        print(f"\n== ⚠️ 防呆警示（需回 Phase 0 修；不阻擋）：{len(warns)} 項 ==")
        for w in warns:
            print("  - " + w)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None); ap.add_argument("--inputs", default=None)
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--include-background", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.path.insert(0, str(HERE)); import workdir
        cache = a.cache or workdir.cache_dir()
        inputs = a.inputs or os.path.join(os.path.dirname(cache), "inputs")
    except Exception:
        cache = a.cache or str(HERE.parent / "cache")
        inputs = a.inputs or str(HERE.parent / "inputs")
    corpus_path = a.corpus or os.path.join(cache, "_corpus.json")
    corpus = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    scope = compute(corpus, cache, inputs, include_background=a.include_background)
    _print(scope)
    if a.json:
        print("\n--- JSON ---"); print(json.dumps(scope, ensure_ascii=False, indent=2))
    if a.write:
        out = Path(cache) / "_analysis_scope.json"
        out.write_text(json.dumps(scope, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 寫出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
