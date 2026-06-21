# -*- coding: utf-8 -*-
"""
fulltext_gate.py — 分析端『全文為準』機器守門（guardrail: fulltext_authoritative）
================================================================================
到了評讀階段一切以全文為準；摘要/登錄庫/AI 合成只有在『各種管道都無法閱讀全文』時才退用。
本 gate 逐 `cache/*.p1.json` 強制此規則（因 2026-06 使用者糾正而立）：

  凡 data_source 不含 "full_text" 卻用了 abstract/ai_synthesis/registry_results：
    • 必須附 fulltext_attempts，且涵蓋 local_pdf / pmc_fulltextxml / unpaywall_oa 三管道
      皆已實試（result≠skipped）；
    • 不得有任一 channel result=fulltext_obtained（若取得全文就該標 full_text 並以全文重抽）；
    • extraction_validation.status 須為 needs_review（非全文不得宣稱 ok 定稿）。
  反向：data_source 含 "full_text" 卻沒有任一 fulltext_attempts 標 fulltext_obtained → 不一致 FAIL。

不滿足 → FAIL（＝沒窮盡全文就退二手 / 全文標記與證據不符）。

用法：
  python tools/fulltext_gate.py                 # 掃 workdir cache
  python tools/fulltext_gate.py --cache <dir>   # 指定 cache 目錄
  python tools/fulltext_gate.py --selftest      # 證明守門會 FAIL
程式內：from fulltext_gate import check; fails = check(cache_dir)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FALLBACK_SOURCES = {"abstract", "ai_synthesis", "registry_results"}
REQUIRED_CHANNELS = {"local_pdf", "pmc_fulltextxml", "unpaywall_oa"}


def _check_one(name, obj):
    """回傳該檔的失敗訊息 list（空＝通過）。"""
    fails = []
    ds = set(obj.get("data_source") or [])
    attempts = obj.get("fulltext_attempts") or []
    tried = {a.get("channel") for a in attempts if a.get("result") not in (None, "skipped")}
    got = {a.get("channel") for a in attempts if a.get("result") == "fulltext_obtained"}
    has_full = "full_text" in ds
    used_fallback = bool(ds & FALLBACK_SOURCES)
    status = ((obj.get("extraction_validation") or {}).get("status") or "")

    if not has_full and used_fallback:
        # 退二手：須先窮盡全文管道
        missing = REQUIRED_CHANNELS - tried
        if missing:
            fails.append(f"{name}：data_source 退用 {sorted(ds & FALLBACK_SOURCES)} 卻未實試全文管道 "
                         f"{sorted(missing)}（fulltext_attempts 須涵蓋 local_pdf/pmc_fulltextxml/unpaywall_oa 且 result≠skipped）")
        if got:
            fails.append(f"{name}：fulltext_attempts 有 {sorted(got)} 取得全文(fulltext_obtained)，"
                         f"data_source 卻無 full_text、仍退二手——取得全文就須以全文重抽並標 full_text")
        if status != "needs_review":
            fails.append(f"{name}：非全文來源(extraction_validation.status='{status}')須為 needs_review（非全文不得宣稱 ok）")
    if has_full and not got:
        # 宣稱全文卻無任何 fulltext_obtained 證據
        fails.append(f"{name}：data_source 標 full_text 卻無任一 fulltext_attempts 標 fulltext_obtained（全文標記無證據）")
    return fails


def check(cache_dir=None):
    if cache_dir is None:
        try:
            import workdir
            cache_dir = workdir.cache_dir()
        except Exception:
            cache_dir = str(HERE.parent / "cache")
    cache = Path(cache_dir)
    fails = []
    for f in sorted(cache.glob("*.p1.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            fails.append(f"{f.name}：讀取/解析失敗 {e}")
            continue
        fails += _check_one(f.name, obj)
    return fails


def _selftest():
    bad = {
        "data_source": ["abstract"],
        "fulltext_attempts": [{"channel": "pmc_fulltextxml", "result": "not_found"}],  # 缺 local_pdf/unpaywall
        "extraction_validation": {"status": "ok"},  # 又錯標 ok
    }
    f1 = _check_one("BAD.p1.json", bad)
    assert f1, "selftest 失敗：壞例應被抓出"
    good = {
        "data_source": ["abstract", "registry_results"],
        "fulltext_attempts": [
            {"channel": "local_pdf", "result": "not_found"},
            {"channel": "pmc_fulltextxml", "result": "no_access"},
            {"channel": "unpaywall_oa", "result": "no_access"},
            {"channel": "manual_supplement", "result": "skipped"},
        ],
        "extraction_validation": {"status": "needs_review"},
    }
    f2 = _check_one("GOOD.p1.json", good)
    assert not f2, f"selftest 失敗：好例不應被抓出，但得到 {f2}"
    full = {  # 取得全文：須標 full_text 且有 fulltext_obtained
        "data_source": ["full_text"],
        "fulltext_attempts": [{"channel": "pmc_fulltextxml", "result": "fulltext_obtained"}],
        "extraction_validation": {"status": "ok"},
    }
    f3 = _check_one("FULL.p1.json", full)
    assert not f3, f"selftest 失敗：全文好例不應被抓出，但得到 {f3}"
    full_noproof = {"data_source": ["full_text"], "fulltext_attempts": [], "extraction_validation": {"status": "ok"}}
    assert _check_one("FULLNOPROOF.p1.json", full_noproof), "selftest 失敗：標 full_text 無證據應被抓出"
    print("✅ fulltext_gate selftest 通過（壞例被抓、好例放行、全文證據一致性檢查有效）")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest(); return 0
    fails = check(a.cache)
    if fails:
        print(f"❌ fulltext_gate FAIL（{len(fails)} 項）：")
        for x in fails:
            print("  -", x)
        return 1
    print("✅ fulltext_gate PASS（所有 p1：全文為準、退二手前已窮盡全文管道）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
