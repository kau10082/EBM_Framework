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
    try:
        fails = check_pdf_at_finalize(state, cache, outputs)
    except Exception as e:
        fails = [f"analysis_gate 自身例外（fail-closed）：{str(e)[:80]}"]
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
        sys.exit(0 if (ok and ok2) else 1)
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
