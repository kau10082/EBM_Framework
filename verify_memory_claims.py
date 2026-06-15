# -*- coding: utf-8 -*-
"""
verify_memory_claims.py — 「長期記憶 vs 程式現況」漂移檢查（根治記憶過時）
==========================================================================
背景：長期記憶會斷言程式狀態（「plain_summary 已加進 schema/renderer」），但程式會漂移、
記憶不會自動更新——曾因此誤信不存在的機制。此檔把記憶裡**對程式狀態的具體聲明**編成
可重跑斷言：任一不符即 FAIL，提醒去修『記憶或程式』其一。

原則：記憶該存「為什麼/決定」，不存「程式裡有什麼」（後者由 code＋測試＋本檔當真相）。
新增記憶若指名 檔案/函式/旗標/gate/schema 欄位，請在此補一條斷言。

用法：python verify_memory_claims.py
"""
import os, re, sys, subprocess
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
ROOT = Path(__file__).resolve().parent

def _has(rel, pat):
    p = ROOT / rel
    return bool(p.exists() and re.search(pat, p.read_text(encoding="utf-8", errors="replace")))

def _absrisk_named_ok():
    r = subprocess.run([sys.executable, str(ROOT / "EBM_Analysis/tools/absrisk.py"), "rr", "--rr", "1.33", "--control", "0.403"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0

# (記憶條目, 斷言)  ── 與各 memory 的「程式狀態聲明」對齊
CLAIMS = [
    ("grade-self-consistency-gate / cochrane-v65 / anti-drift：selfcheck 硬 gate C1–C15",
     lambda: all(_has("EBM_Analysis/tools/selfcheck_consistency.py", rf"\b{n}\b") for n in
                 ("C1", "C2", "C3", "C8", "C9", "C10", "C13", "C14", "C15"))),
    ("verify-before-act / anti-drift / prisma：verify_all 串接 render_smoketest+quote_verify+prisma_audit+funnel_check+fulltext_audit",
     lambda: all(_has("EBM_Analysis/tools/verify_all.py", g) for g in
                 ("render_smoketest", "quote_verify", "prisma_audit", "funnel_check", "fulltext_audit"))),
    ("grade-report-pdf-render-rules：_build_pdf 走 workdir、單一真相讀 _synthesis.json",
     lambda: _has("EBM_Analysis/_build_pdf.py", r"workdir") and _has("EBM_Analysis/_build_pdf.py", r"_synthesis")),
    ("ebm-report-readability：plain_summary 機制（schema＋兩 renderer）",
     lambda: _has("EBM_Analysis/schema/phase4_output.json", r"plain_summary")
             and _has("EBM_Analysis/tools/build_reports.py", r"plain_summary")
             and _has("EBM_Analysis/_build_pdf.py", r"plain_summary")),
    ("verify-before-act：absrisk 具名旗標 rr --rr X --control Y 可用", _absrisk_named_ok),
    ("zotero-import-scope-options：zotero_import 有 study/role tag＋DOI 去重＋EuropePMC fallback",
     lambda: _has("EBM_Search/scripts/zotero_import.py", r"study:%s")
             and _has("EBM_Search/scripts/zotero_import.py", r"existing_dois")
             and _has("EBM_Search/scripts/zotero_import.py", r"enrich_from_europepmc")),
    ("fulltext-supplement / verify-before-act：fulltext_audit + quote_verify 之 Unpaywall fallback",
     lambda: (ROOT / "EBM_Search/scripts/fulltext_audit.py").exists()
             and _has("EBM_Analysis/tools/quote_verify.py", r"_unpaywall_text")),
    ("sr-report-pdf-canonical-format：build_search_report safe() 字形淨化＋funnel_check",
     lambda: _has("EBM_Search/scripts/build_search_report.py", r"_SAFE_TR")
             and (ROOT / "EBM_Search/scripts/funnel_check.py").exists()),
    ("pubmed-mcp-pagination-retstart：SEARCH_SPEC 載明翻頁 retstart",
     lambda: _has("EBM_Search/SEARCH_SPEC.md", r"retstart")),
    ("ebm-framework-single-entry：/ebm 已移除（無 .claude/skills/ebm）",
     lambda: not (ROOT / ".claude/skills/ebm").exists()),
    ("ebm-run-state-pointer：run_state.py 指標檔機制存在",
     lambda: _has("EBM_Analysis/tools/run_state.py", r"run_state\.json|def load")),
    ("核心工具齊備：ingest_seed/end_run/archive_run/prisma_audit/quote_verify",
     lambda: all((ROOT / f"EBM_Analysis/tools/{t}.py").exists() for t in
                 ("ingest_seed", "end_run", "archive_run", "prisma_audit", "quote_verify"))),
]

def main():
    bad = []
    print("== 記憶 vs 程式 漂移檢查 ==")
    for desc, fn in CLAIMS:
        try:
            ok = bool(fn())
        except Exception as e:
            ok = False; desc += f"（檢查例外：{str(e)[:40]}）"
        print(("  ✅ " if ok else "  ❌ ") + desc)
        if not ok: bad.append(desc)
    print()
    if bad:
        print(f"❌ {len(bad)} 項記憶與程式不符 → 修『記憶或程式』其一（記憶存 why、程式為真相）：")
        for b in bad: print("  -", b)
        sys.exit(1)
    print(f"✅ 全部 {len(CLAIMS)} 項記憶聲明與程式一致——無漂移。")

if __name__ == "__main__":
    main()
