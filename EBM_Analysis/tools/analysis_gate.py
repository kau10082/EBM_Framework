# -*- coding: utf-8 -*-
"""
analysis_gate.py — 分析端『輕量 Stop-hook 守門』（Bug8：最終 PDF 不照規範/沒產出）
================================================================================
比照 search 端 gate_guard 的設計，但**刻意輕量**（不跑 quote_verify 網路、不跑渲染子程序）——
只做一件在 Stop hook 安全、不會 mid-analysis 誤擋的事：

  • 「宣稱完成卻無合規 PDF」：run_state.stage 標示已到 phase4/定稿、且 _synthesis.json 已存在，
    卻找不到合規 PDF（grade_pdf 或 outputs/FINAL_REPORT.pdf，存在且非過小）→ FAIL。
    「無合規 PDF 不算完成」。

> 為何輕量：完整評讀驗證（schema/selfcheck C1-C15/SoF/PRISMA 27 項/渲染煙霧測試）仍由
> `verify_all.py` 負責，且 SKILL 要求**定稿前自跑 verify_all 貼 PASS**。本 gate 只當「Stop 時的
> 最後一道便宜防線」，抓「手機/遠端宣稱做完卻沒有合規 PDF」這個 Bug8 主症狀，且 stage 沒到
> 定稿前一律放行（不干擾 mid-analysis）。

用法：
  python tools/analysis_gate.py --cache <cache_dir>   # 人工跑
  python tools/analysis_gate.py --auto                 # 自動找 work；非分析中→靜默 exit 0
  python tools/analysis_gate.py --auto --hook          # Stop hook：FAIL→stderr＋exit 2
  python tools/analysis_gate.py --selftest             # 證明守門會 FAIL
"""
import sys, json, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

MIN_PDF_BYTES = 10240  # 合規 PDF 至少 10KB（小於此視為佔位/失敗產物）
FINAL_MARKERS = ("phase4", "final", "render", "定稿")  # stage 含這些＝已到定稿（不含 'done' 以免誤判 phase3_done）

def _load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None

def check_pdf_at_finalize(state, cache_dir, outputs_dir):
    """stage 標示已定稿、_synthesis.json 已在，卻無合規 PDF → FAIL。其餘一律放行（不擾 mid-analysis）。"""
    state = state or {}
    stage = str(state.get("stage") or "").lower()
    if not any(m in stage for m in FINAL_MARKERS):
        return []  # 未到定稿階段
    if not (Path(cache_dir) / "_synthesis.json").exists():
        return []  # 還沒合成 phase4，不可能算完成
    paths = state.get("paths", {}) or {}; arts = state.get("artifacts", {}) or {}
    cands = [paths.get("grade_pdf"), arts.get("grade_pdf"),
             str(Path(outputs_dir) / "FINAL_REPORT.pdf")]
    for c in cands:
        if c and Path(c).exists() and Path(c).stat().st_size >= MIN_PDF_BYTES:
            return []
    return [f"run_state.stage='{stage}' 標示已到定稿、且 _synthesis.json 已存在，"
            f"卻找不到合規 PDF（grade_pdf / outputs/FINAL_REPORT.pdf 不存在或 < {MIN_PDF_BYTES} bytes）："
            "無合規 PDF 不算完成（且定稿前須自跑 verify_all.py 貼 PASS）"]

def check_fulltext_content_audited(state, cache_dir):
    """定稿階段：base 文獻『本機全文內容↔paper_id 標題』稽核須做過且無 mismatch（Antigravity 第九輪 🟡c 升 gate）。
    比照 search 端 `gate_guard.check_doi_title_audited`：離線讀稽核產物 `_fulltext_audit.json`（由
    `fulltext_title_audit.py --out cache/_fulltext_audit.json` 產），缺檔或有 mismatch 即 FAIL——
    『內容放錯 paper_id』(實測 updated-NMA 的全文其實是 Edris) 不可靜默進 GRADE。輕量、不連網、不跑子程序。"""
    state = state or {}
    cache = Path(cache_dir)
    corpus = _load(cache / "_corpus.json")
    base = [p for p in (corpus or {}).get("papers", []) if p.get("grade_track") in ("full", "targeted_harms")] if corpus else []
    if not base:
        return []  # 無 base 可稽核
    # 兩個觸發點（R12b pre-check）：(1) 定稿(FINAL_MARKERS)＋_synthesis 已在；(2) Phase 1 抽取已開始
    #   ——cache 出現任何 <pid>.p1.json。後者把『漏稽核』提前到抽取一開始就攔下，免白費 Phase 1–3。
    stage = str(state.get("stage") or "").lower()
    at_final = any(m in stage for m in FINAL_MARKERS) and (cache / "_synthesis.json").exists()
    extraction_started = any((cache / f"{p['paper_id']}.p1.json").exists() for p in base)
    if not (at_final or extraction_started):
        return []  # Phase 0 中、尚未抽取也未定稿 → 放行（不擾 mid-analysis）
    audit = _load(cache / "_fulltext_audit.json")
    if audit is None:
        when = "已定稿" if at_final else "已開始 Phase 1 抽取(出現 *.p1.json)"
        return [f"{when}卻無 _fulltext_audit.json：Phase 0 須先跑 "
                "`fulltext_title_audit.py --out cache/_fulltext_audit.json`（本機全文內容↔標題稽核），"
                "確認無『內容放錯 paper_id』才可進抽取/定稿（否則恐白費 Phase 1–3）"]
    mm = audit.get("mismatch")
    if isinstance(mm, int) and mm > 0:
        ids = [m.get("paper_id") for m in (audit.get("mismatches") or [])][:5]
        return [f"_fulltext_audit.json 有 {mm} 筆內容↔標題 mismatch 未解決（內容放錯 paper_id）：{ids}"
                "；須換正確全文或修正 paper_id 後重跑稽核"]
    return []


def _resolve():
    """回傳 (work_root, cache_dir, outputs_dir, state) 或 None（無法解析）。不建立資料夾。"""
    try:
        import workdir, run_state
        cache = workdir.cache_dir(create=False)
        outs = workdir.outputs_dir(create=False)
        st = run_state.load()
        return cache, outs, st
    except Exception:
        return None

def _active(cache):
    """分析是否已到『可能完成』：_synthesis.json 存在才需本 gate（否則靜默放行）。"""
    return cache and (Path(cache) / "_synthesis.json").exists()

def run(cache, outputs, state, quiet=False):
    fails = []
    for _fn in (lambda: check_pdf_at_finalize(state, cache, outputs),
                lambda: check_fulltext_content_audited(state, cache)):
        try:
            fails += _fn() or []
        except Exception as e:
            fails.append(f"analysis_gate 自身例外（fail-closed）：{str(e)[:80]}")
    if fails:
        print("❌ analysis_gate 攔截："); [print("  -", f) for f in fails]; return 1
    if not quiet:
        print("✅ analysis_gate：通過（合規 PDF 已產出，或尚未到定稿階段）。")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache"); ap.add_argument("--auto", action="store_true")
    ap.add_argument("--hook", action="store_true"); ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        import tempfile
        d = Path(tempfile.mkdtemp()); (d / "_synthesis.json").write_text("{}", encoding="utf-8")
        fails = check_pdf_at_finalize({"stage": "phase4_complete", "paths": {}}, str(d), str(d))
        ok = bool(fails)
        print(("✅" if ok else "❌") + " selftest：定稿無合規 PDF 應 FAIL — " + ("會 FAIL（有效）" if ok else "未 FAIL（失效！）"))
        # 反向：未到定稿應放行
        none_fail = check_pdf_at_finalize({"stage": "phase3_done"}, str(d), str(d))
        ok2 = not none_fail
        print(("✅" if ok2 else "❌") + " selftest：未到定稿應放行 — " + ("放行（正確）" if ok2 else "誤擋！"))
        # 內容稽核 gate：定稿＋有 base 卻無 _fulltext_audit.json → FAIL
        d2 = Path(tempfile.mkdtemp()); (d2 / "_synthesis.json").write_text("{}", encoding="utf-8")
        (d2 / "_corpus.json").write_text(json.dumps({"papers": [{"paper_id": "A", "grade_track": "full"}]}), encoding="utf-8")
        f1 = check_fulltext_content_audited({"stage": "phase4_final"}, str(d2))
        ok3 = bool(f1)
        print(("✅" if ok3 else "❌") + " selftest：定稿有 base 卻未跑內容稽核應 FAIL — " + ("會 FAIL（有效）" if ok3 else "未 FAIL（失效！）"))
        # 有稽核產物但 mismatch>0 → FAIL
        (d2 / "_fulltext_audit.json").write_text(json.dumps({"mismatch": 1, "mismatches": [{"paper_id": "A"}]}), encoding="utf-8")
        f2 = check_fulltext_content_audited({"stage": "phase4_final"}, str(d2))
        ok4 = bool(f2)
        print(("✅" if ok4 else "❌") + " selftest：內容稽核有 mismatch 應 FAIL — " + ("會 FAIL（有效）" if ok4 else "未 FAIL！"))
        # 稽核乾淨(mismatch=0) → 放行
        (d2 / "_fulltext_audit.json").write_text(json.dumps({"mismatch": 0, "mismatches": []}), encoding="utf-8")
        f3 = check_fulltext_content_audited({"stage": "phase4_final"}, str(d2))
        ok5 = not f3
        print(("✅" if ok5 else "❌") + " selftest：內容稽核乾淨應放行 — " + ("放行（正確）" if ok5 else "誤擋！"))
        # R12b pre-check：未定稿但抽取已開始(出現 *.p1.json)＋無稽核產物 → 提前 FAIL
        d3 = Path(tempfile.mkdtemp())
        (d3 / "_corpus.json").write_text(json.dumps({"papers": [{"paper_id": "A", "grade_track": "full"}]}), encoding="utf-8")
        (d3 / "A.p1.json").write_text("{}", encoding="utf-8")   # 抽取已開始
        f4 = check_fulltext_content_audited({"stage": "phase1_extract"}, str(d3))
        ok6 = bool(f4)
        print(("✅" if ok6 else "❌") + " selftest：抽取已開始卻未稽核應提前 FAIL（pre-check）— " + ("會 FAIL（有效）" if ok6 else "未 FAIL！"))
        # 反向：Phase 0 中(未抽取未定稿)＋無稽核 → 放行（不擾）
        d4 = Path(tempfile.mkdtemp())
        (d4 / "_corpus.json").write_text(json.dumps({"papers": [{"paper_id": "A", "grade_track": "full"}]}), encoding="utf-8")
        f5 = check_fulltext_content_audited({"stage": "phase0_triage"}, str(d4))
        ok7 = not f5
        print(("✅" if ok7 else "❌") + " selftest：Phase 0 中(未抽取)應放行 — " + ("放行（正確）" if ok7 else "誤擋！"))
        sys.exit(0 if (ok and ok2 and ok3 and ok4 and ok5 and ok6 and ok7) else 1)
    # 解析 work
    if a.cache:
        cache = a.cache
        try:
            import workdir, run_state; outputs = workdir.outputs_dir(create=False); state = run_state.load()
        except Exception:
            outputs = str(Path(cache).parent / "outputs"); state = _load(Path(cache).parent / "run_state.json") or {}
    else:
        res = _resolve()
        if res is None:
            if a.auto: sys.exit(0)  # 無法解析 work（非 EBM 分析環境）→ 靜默放行
            print("⏭  找不到分析 work（--cache 指定，或非分析中）"); sys.exit(0)
        cache, outputs, state = res
    if (a.auto or a.hook) and not _active(cache):
        sys.exit(0)  # 尚無 _synthesis.json＝分析非『可能完成』→ 全域靜默零打擾
    rc = run(cache, outputs, state, quiet=a.quiet or a.hook)
    if a.hook and rc != 0:
        sys.stderr.write("analysis_gate 攔截：宣稱完成評讀卻無合規 PDF（見上）。\n"); sys.exit(2)
    sys.exit(rc)

if __name__ == "__main__":
    main()
