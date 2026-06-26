# -*- coding: utf-8 -*-
"""
build_screening_flow.py — 自動組出報告第 0 段『文獻篩選流程』(PRISMA-style)，免手填、防漂移。

2026-06 Antigravity 第十輪 🟡(c) 而立：FINAL_REPORT 的 screening_flow 原本手填於 `_synthesis.json`，
易與真實檢索漏斗脫鉤。本工具改為**自權威來源衍生**：
  • 檢索漏斗：EBM_Search 的 `_search_report.json` 的 `flow`（識別→②b→③→④→⑤a→⑤b，含 start/excluded/remain）。
    位置同 prisma_audit：`run_state.paths.fulltext_dir/_search_report.json`，或 `--search` 指定。
  • 分析尾段：由 `cache/_corpus.json` 的 grade_track 計數推得（最終 GRADE base anchors＝full(＋targeted_harms)；
    其餘 light_summary＝降背景）。
找不到 _search_report.json 時優雅降級：只出分析尾段，並在 note 標明檢索漏斗未取得。

用法：
  python tools/build_screening_flow.py                 # 印出推得的 flow（dry）
  python tools/build_screening_flow.py --write          # 併寫進 cache/_synthesis.json 的 screening_flow（僅當其缺漏；--force 覆寫）
  python tools/build_screening_flow.py --write --force   # 強制以衍生值覆寫（手填讓位給自動）
  python tools/build_screening_flow.py --selftest
程式內：from build_screening_flow import build; flow = build(cache_dir, search_path=None)
"""
import sys, os, json, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass


def _load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None


def _find_search_report(search_path=None):
    """同 prisma_audit：優先 --search；否則 run_state.paths.fulltext_dir/_search_report.json；否則 cache/。"""
    if search_path and os.path.exists(search_path):
        return search_path
    try:
        import run_state
        ftd = (run_state.load() or {}).get("paths", {}).get("fulltext_dir")
        cand = os.path.join(ftd, "_search_report.json") if ftd else None
        if cand and os.path.exists(cand):
            return cand
    except Exception:
        pass
    try:
        import workdir
        cand = os.path.join(workdir.cache_dir(), "_search_report.json")
        if os.path.exists(cand):
            return cand
    except Exception:
        pass
    return None


def build(cache_dir, search_path=None, corpus=None):
    """回傳 screening_flow（list of {stage,start,excluded,remain,note}）。"""
    flow = []
    # 1) 檢索漏斗 ← _search_report.flow（權威）
    sp = _find_search_report(search_path)
    sr = _load(sp) if sp else None
    if sr and isinstance(sr.get("flow"), list):
        for s in sr["flow"]:
            flow.append({"stage": s.get("stage", ""), "start": s.get("start", "—"),
                         "excluded": s.get("excluded", "—"), "remain": s.get("remain", ""),
                         "note": s.get("note", "") or ""})
    else:
        flow.append({"stage": "EBM_Search 檢索漏斗", "start": "—", "excluded": "—", "remain": "—",
                     "note": "（未取得 _search_report.json，檢索漏斗從略；可 --search 指定）"})
    # 2) 分析尾段 ← corpus grade_track 計數
    if corpus is None:
        corpus = _load(os.path.join(cache_dir, "_corpus.json")) or {}
    ps = corpus.get("papers", []) if isinstance(corpus, dict) else []
    n_full = sum(1 for p in ps if p.get("grade_track") == "full")
    n_th = sum(1 for p in ps if p.get("grade_track") == "targeted_harms")
    n_bg = sum(1 for p in ps if p.get("grade_track") == "light_summary")
    anchors = [p.get("paper_id", "") for p in ps if p.get("grade_track") in ("full", "targeted_harms")]
    if ps:
        flow.append({"stage": "Phase 0 分流＋AMSTAR2/CCA 收斂 → GRADE base anchors",
                     "start": "核心 SR/MA 候選", "excluded": f"降佐證／背景 {n_bg}",
                     "remain": f"{n_full + n_th} anchors", "note": "、".join(a for a in anchors[:6] if a)})
    return flow


def merge_into_synthesis(cache_dir, flow, force=False):
    """把 flow 併入 cache/_synthesis.json 的 screening_flow（預設僅當缺漏；--force 覆寫）。回傳 (written, reason)。"""
    sp = os.path.join(cache_dir, "_synthesis.json")
    obj = _load(sp)
    if obj is None:
        return False, "無 _synthesis.json"
    syn = obj.get("synthesis", obj) if isinstance(obj, dict) else obj
    if syn.get("screening_flow") and not force:
        return False, "已有 screening_flow（未 --force，保留手填）"
    syn["screening_flow"] = flow
    Path(sp).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, f"已寫入 {len(flow)} 階段"


def _selftest():
    import tempfile, shutil
    ok = True
    tmp = Path(tempfile.mkdtemp())
    try:
        # 假 _search_report.flow ＋ 假 corpus
        sr = {"flow": [{"stage": "識別", "start": "—", "excluded": "—", "remain": "1000"},
                       {"stage": "②b 初篩", "start": "1000", "excluded": "離題 50", "remain": "950"}]}
        (tmp / "_search_report.json").write_text(json.dumps(sr), encoding="utf-8")
        corpus = {"papers": [{"paper_id": "A", "grade_track": "full"},
                             {"paper_id": "B", "grade_track": "full"},
                             {"paper_id": "C", "grade_track": "light_summary"}]}
        (tmp / "_corpus.json").write_text(json.dumps(corpus), encoding="utf-8")
        flow = build(str(tmp), search_path=str(tmp / "_search_report.json"))
        c1 = len(flow) == 3 and flow[0]["remain"] == "1000" and flow[-1]["remain"] == "2 anchors"
        print(("  ✅" if c1 else "  ❌") + f" 檢索漏斗(2)＋分析尾段(1)、anchors=2、降背景=1：{[f['remain'] for f in flow]}"); ok &= c1
        c2 = "A" in flow[-1]["note"] and "降佐證／背景 1" in flow[-1]["excluded"]
        print(("  ✅" if c2 else "  ❌") + " 尾段標 anchor id ＋降背景數"); ok &= c2
        # 找不到 search_report → 優雅降級（只剩分析尾段＋占位）
        flow2 = build(str(tmp), search_path=str(tmp / "nope.json"))
        c3 = any("未取得 _search_report" in (f.get("note") or "") for f in flow2)
        print(("  ✅" if c3 else "  ❌") + " 無檢索報告→優雅降級占位"); ok &= c3
        # merge：缺漏才寫、有則保留（除非 force）
        (tmp / "_synthesis.json").write_text(json.dumps({"synthesis": {}}), encoding="utf-8")
        w1, _r1 = merge_into_synthesis(str(tmp), flow)
        (tmp / "_synthesis.json").write_text(json.dumps({"synthesis": {"screening_flow": [{"stage": "手填"}]}}), encoding="utf-8")
        w2, _r2 = merge_into_synthesis(str(tmp), flow)              # 已有→不覆寫
        w3, _r3 = merge_into_synthesis(str(tmp), flow, force=True)  # force→覆寫
        c4 = w1 and (not w2) and w3
        print(("  ✅" if c4 else "  ❌") + f" merge：缺漏寫({w1})／有則保留({not w2})／force 覆寫({w3})"); ok &= c4
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("✅ build_screening_flow selftest 全過" if ok else "❌ 有失敗")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None); ap.add_argument("--search", default=None)
    ap.add_argument("--write", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    try:
        import workdir
        cache = a.cache or workdir.cache_dir()
    except Exception:
        cache = a.cache or str(HERE.parent / "cache")
    flow = build(cache, search_path=a.search)
    print(json.dumps(flow, ensure_ascii=False, indent=2))
    if a.write:
        w, r = merge_into_synthesis(cache, flow, force=a.force)
        print(("✅ " if w else "· ") + r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
