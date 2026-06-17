# -*- coding: utf-8 -*-
"""
verify_all.py — 定稿前『一鍵跑完所有驗證』統一入口（防漏跑、降分心）
====================================================================
依序執行並彙總：
  1) schema 驗證       每個 cache 階段檔（phase0/p1/p2/p3/phase4）符合 schema＋GRADE 算術重算
  2) selfcheck_consistency  自我一致性硬 gate C1-C15（C15＝SoF 受試者數一致性，防 N 飄移）
  3) absrisk --selftest     絕對效應公式黃金值
  4) quote_verify           逐字 quote ＋ SoF provenance 回原文機器核對（反幻覺；可 --no-quotes 略過）
  5) 跨報告 Study 數一致、流程圖數字逐關閉合（funnel_check）、全文取得 Unpaywall 複查（fulltext_audit）
  6) prisma_audit           PRISMA 2020 27 項報告完整度稽核（維度齊不齊；MANUAL 項不阻擋）
  7) 渲染煙霧測試           V1 磚塊／V2 跳號／V3 空表／V4 SoF 死亡+SAE／V5 列數／V6 渲染器一致性
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
    if not ok:   # 失敗時印出子程序細節(末 20 行)，免去使用者手動重跑單獨指令排查
        detail = ((r.stdout or "") + (r.stderr or "")).strip()
        for ln in detail.splitlines()[-20:]:
            print("      │ " + ln)
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
        results.append(("selfcheck C1-C15", ok, "\n".join(fails)))
        print(f"  {'✅' if ok else '❌'} selfcheck C1-C15" + ("" if ok else f"（{len(fails)} 失敗）"))
        for x in fails: print("      -", x)
        for w in (sc.warnings() or []):           # 非阻擋提醒（如缺 plain_summary）
            print("      ⚠️ " + w)
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
            # 只數「試驗 Study 單位」：檢索報告 studies 表常含 SR/MA 顯示群(非 Study)，排除之
            # (與 analysis 的 study_characteristics＝試驗單位 對齊；SR/MA 屬合併效應來源、非分析單位)
            n_search = len([g for g in sr.get("studies", [])
                            if not str(g.get("study", "")).replace("\n", " ").strip().upper().startswith("SR/MA")])
            syn = json.loads((CACHE / "_synthesis.json").read_text(encoding="utf-8")).get("synthesis", {})
            n_analysis = len(syn.get("study_characteristics", []))
            ok = (n_search == n_analysis) or n_analysis == 0
            results.append(("跨報告 Study 數一致", ok, f"search={n_search} analysis={n_analysis}"))
            print(f"  {'✅' if ok else '❌'} 跨報告 Study 數一致（search={n_search} / analysis={n_analysis}）")
    except Exception as e:
        results.append(("跨報告 Study 數一致", False, str(e)[:200])); print("  ❌ 跨報告檢查失敗（gate 自身出錯，fail-closed）:", str(e)[:40])

    # 5a-i) 檢索流程圖數字逐關閉合（funnel_check；反飄移）
    try:
        import run_state
        ftd = (run_state.load() or {}).get("paths", {}).get("fulltext_dir")
        srj = os.path.join(ftd, "_search_report.json") if ftd else None
        if srj and os.path.exists(srj):
            sys.path.insert(0, str(HERE.parent.parent / "EBM_Search" / "scripts"))
            import funnel_check
            ff = funnel_check.check(json.loads(open(srj, encoding="utf-8").read()))
            results.append(("流程圖數字閉合", not ff, "\n".join(ff)))
            print(f"  {'✅' if not ff else '❌'} 流程圖數字逐關閉合" + ("" if not ff else f"（{len(ff)}）"))
            for x in ff: print("      -", x)
        else:
            print("  ⏭  流程圖數字閉合略過（無 _search_report.json）")
    except Exception as e:
        results.append(("流程圖數字閉合", False, str(e)[:200])); print("  ❌ 流程圖數字閉合失敗（gate 自身出錯，fail-closed）:", str(e)[:50])

    # 5a-ii) 全文取得『不可跳過 Unpaywall』複查（fulltext_audit；反幻覺/便宜行事）
    try:
        import run_state
        ftd = (run_state.load() or {}).get("paths", {}).get("fulltext_dir")
        seedj = os.path.join(ftd, "_corpus_seed.json") if ftd else None
        if seedj and os.path.exists(seedj):
            sys.path.insert(0, str(HERE.parent.parent / "EBM_Search" / "scripts"))
            import fulltext_audit
            papers = fulltext_audit._load_papers(seedj)
            fa, _missed = fulltext_audit.audit(papers)
            results.append(("全文取得Unpaywall複查", not fa, "\n".join(fa)))
            print(f"  {'✅' if not fa else '❌'} 全文取得 Unpaywall 複查" + ("" if not fa else f"（{len(fa)} 筆漏跑/漏判）"))
            for x in fa: print("      -", x)
        else:
            print("  ⏭  全文 Unpaywall 複查略過（無交接包）")
    except Exception as e:
        results.append(("全文取得Unpaywall複查", False, str(e)[:200])); print("  ❌ 全文 Unpaywall 複查失敗（gate 自身出錯，fail-closed）:", str(e)[:50])

    # 5b) PRISMA 2020 27 項報告完整度稽核（與 selfcheck 互補：那查矛盾、這查維度齊不齊）
    try:
        import prisma_audit
        rows, pfails = prisma_audit.check()
        ok = not pfails
        from collections import Counter as _C
        c = _C(r["status"] for r in rows)
        results.append(("PRISMA 2020 27 項稽核", ok,
                        f"PASS {c['PASS']}/FAIL {c['FAIL']}/MANUAL {c['MANUAL']}/ATTEST {c['ATTEST']}/PENDING {c['PENDING']}\n" + "\n".join(pfails)))
        print(f"  {'✅' if ok else '❌'} PRISMA 2020 27 項稽核"
              + f"（PASS {c['PASS']} / FAIL {c['FAIL']} / 待人工聲明 {c['MANUAL']} / 已聲明 {c['ATTEST']} / 待產出 {c['PENDING']}）")
        for x in pfails: print("      -", x)
        if c["MANUAL"]:
            print(f"      ⚠️ {c['MANUAL']} 項需人工聲明（不阻擋；於 synthesis.prisma_attest 補齊或報告明列）")
    except Exception as e:
        results.append(("PRISMA 2020 27 項稽核", False, str(e)[:200])); print("  ❌ PRISMA 稽核失敗（gate 自身出錯，fail-closed）:", str(e)[:60])

    # 6) 渲染煙霧測試（視覺/完整性：磚塊/章節跳號/空表/SoF 必要結局）——若 GRADE PDF 已產
    try:
        pdf = None
        try:
            import run_state
            pdf = (run_state.load() or {}).get("paths", {}).get("grade_pdf")
        except Exception:
            pass
        for c in (pdf, os.path.join(workdir.outputs_dir(), "FINAL_REPORT.pdf")):
            if c and os.path.exists(c):
                rr = subprocess.run([sys.executable, str(HERE / "render_smoketest.py"), c],
                                    capture_output=True, text=True, encoding="utf-8")
                ok = rr.returncode == 0
                results.append(("渲染煙霧測試", ok, rr.stdout[-200:]))
                print(f"  {'✅' if ok else '❌'} 渲染煙霧測試" + ("" if ok else "（見下）"))
                if not ok:
                    for ln in rr.stdout.splitlines():
                        if "❌" in ln: print("    " + ln.strip())
                break
        else:
            print("  ⏭  渲染煙霧測試略過（GRADE PDF 未產）")
    except Exception as e:
        results.append(("渲染煙霧測試", False, str(e)[:200])); print("  ❌ 渲染煙霧測試失敗（gate 自身出錯，fail-closed）:", str(e)[:40])

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
