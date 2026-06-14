# -*- coding: utf-8 -*-
"""
verify_all.py — 定稿前『一鍵跑完所有驗證』統一入口（防漏跑、降分心）
====================================================================
依序執行並彙總：
  1) schema 驗證       每個 cache 階段檔（phase0/p1/p2/p3/phase4）符合 schema＋GRADE 算術重算
  2) selfcheck_consistency  自我一致性硬 gate C1-C13
  3) absrisk --selftest     絕對效應公式黃金值
  4) quote_verify           逐字 quote 回原文機器核對（反幻覺；需網路，可 --no-quotes 略過）
任一失敗 → 退出碼非 0。定稿/渲染前一律先跑此檔。

用法：python tools/verify_all.py [--no-quotes]
"""
import sys, os, json, subprocess
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workdir
CACHE = Path(workdir.cache_dir())
PY = sys.executable
results = []

def _run(name, argv):
    env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PY] + argv, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    ok = r.returncode == 0
    results.append((name, ok, (r.stdout or "") + (r.stderr or "")))
    print(f"  {'✅' if ok else '❌'} {name}")
    return ok

def main():
    no_quotes = "--no-quotes" in sys.argv
    print("== verify_all：定稿前統一驗證 ==")
    # 1) schema + 算術（逐階段）
    phase_map = {"phase0_corpus.json": "p0?", "Chalmers2025_ASPEN.p1.json": "p1",
                 "SYNTHESIS_DPP1_bronchiectasis.p3.json": "p3", "_synthesis.json": "synthesis"}
    # 用 validate.py 對 p1/p2/p3（p3 含 GRADE 算術重算）
    for f in sorted(CACHE.glob("*.json")):
        nm = f.name
        phase = ("p1" if nm.endswith(".p1.json") else
                 "p2" if nm.endswith(".p2.json") else
                 "p3" if nm.endswith(".p3.json") else None)
        if phase:
            _run(f"schema:{nm}", [str(HERE / "validate.py"), phase, str(f)])
    # _synthesis.json 是完整 phase4 物件 → 直接對 phase4_output.json 全 schema 驗（非 synthesis 子模式）
    import jsonschema
    sp = CACHE / "_synthesis.json"
    if sp.exists():
        try:
            sch = json.loads((HERE.parent / "schema" / "phase4_output.json").read_text(encoding="utf-8"))
            jsonschema.validate(json.loads(sp.read_text(encoding="utf-8")), sch)
            results.append(("schema:_synthesis.json(phase4)", True, "")); print("  ✅ schema:_synthesis.json(phase4)")
        except Exception as e:
            results.append(("schema:_synthesis.json(phase4)", False, str(e)[:200])); print("  ❌ schema:_synthesis.json(phase4):", str(e)[:80])
    cp = CACHE / "_corpus.json"
    if cp.exists():
        try:
            import jsonschema as _j
            sch = json.loads((HERE.parent / "schema" / "phase0_corpus.json").read_text(encoding="utf-8"))
            _j.validate(json.loads(cp.read_text(encoding="utf-8")), sch)
            results.append(("schema:_corpus.json(phase0)", True, "")); print("  ✅ schema:_corpus.json(phase0)")
        except Exception as e:
            results.append(("schema:_corpus.json(phase0)", False, str(e)[:200])); print("  ❌ schema:_corpus.json(phase0):", str(e)[:80])
    # 2) 自我一致性 gate
    try:
        import selfcheck_consistency as sc
        fails = sc.check()
        ok = not fails
        results.append(("selfcheck C1-C13", ok, "\n".join(fails)))
        print(f"  {'✅' if ok else '❌'} selfcheck C1-C13" + ("" if ok else f"（{len(fails)} 失敗）"))
        for x in fails: print("      -", x)
    except Exception as e:
        results.append(("selfcheck", False, str(e))); print("  ❌ selfcheck 例外:", e)
    # 3) absrisk selftest
    _run("absrisk --selftest", [str(HERE / "absrisk.py"), "--selftest"])
    # 4) quote_verify（網路）
    if not no_quotes:
        _run("quote_verify（反幻覺）", [str(HERE / "quote_verify.py")])
    else:
        print("  ⏭  quote_verify 已略過（--no-quotes）")
    # 5) 跨報告一致性（search 報告 vs analysis）：Study 數須一致（防兩份報告飄移）
    try:
        import run_state
        ftd = run_state.load().get("paths", {}).get("fulltext_dir")
        srp = os.path.join(ftd, "_search_report.json") if ftd else None
        if srp and os.path.exists(srp):
            sr = json.loads(open(srp, encoding="utf-8").read())
            n_search = len(sr.get("studies", []))
            syn = json.loads((CACHE / "_synthesis.json").read_text(encoding="utf-8")).get("synthesis", {})
            n_analysis = len(syn.get("study_characteristics", []))
            ok = (n_search == n_analysis) or n_analysis == 0
            results.append(("跨報告 Study 數一致", ok, f"search={n_search} analysis={n_analysis}"))
            print(f"  {'✅' if ok else '❌'} 跨報告 Study 數一致（search={n_search} / analysis={n_analysis}）")
    except Exception as e:
        print("  ⏭  跨報告檢查略過:", str(e)[:40])
    # 彙總
    bad = [n for n, ok, _ in results if not ok]
    print("\n== 彙總 ==")
    if bad:
        print(f"❌ {len(bad)} 項未過：{bad}")
        print("（細節見上；定稿前須全綠）")
        sys.exit(1)
    print(f"✅ 全部 {len(results)} 項通過——可定稿渲染。")

if __name__ == "__main__":
    main()
