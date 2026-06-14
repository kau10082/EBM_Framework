#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consensus-verify / journal_quartile.py  (Phase 1 v0.11 — Q1+Q2 期刊品質閘)
=========================================================================
查期刊 SJR 分位(Q1–Q4),並對 verified.json 做「保留 ≤Qn」過濾(**預設只 Q1**,求最強公信力;
`--max-quartile 2` 改 Q1+Q2)。被剔除者(Q2 及以下)應進清單三並標分位,供人工自挑,勿丟棄。
用於 §1①(3′):PM／OE 無原生分位 → 事後對 SCImago 表過濾。C 腿請直接用 sjr_max=1。

資料來源:SCImago Journal Rank(免費)。**scimagojr 有 bot 牆**,須帶瀏覽器標頭才下得到
(本腳本已內建)。下載一次後建快取 references/scimago_quartiles.json,之後離線可用。

零相依:純 Python 3.8+ 標準庫(csv / json / urllib)。

用法
----
  python journal_quartile.py --build                         # 下載 SCImago、建快取(首次必跑)
  python journal_quartile.py --journal "New England Journal of Medicine"
  python journal_quartile.py --issn 0028-4793
  python journal_quartile.py --in verified.json --max-quartile 2   # 過濾,保留 Q1+Q2,印剔除清單
  python journal_quartile.py --in verified.json --max-quartile 2 --out verified_q12.json

分位來源欄＝SCImago「SJR Best Quartile」(跨類最佳,最不誤砍)。期刊以 ISSN 優先、標題 fallback。
無分位者(新刊/未收錄/會議摘要)→ 標 'unranked',**預設保留**(不誤殺;--drop-unranked 可改)。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

SCIMAGO_URL = "https://www.scimagojr.com/journalrank.php?out=xls"
CROSSREF_WORKS = "https://api.crossref.org/works"
BROWSER_H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,application/vnd.ms-excel,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.scimagojr.com/journalrank.php",
}
_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(_HERE, "..", "references", "scimago_quartiles.json")
_Q = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

sys.path.insert(0, _HERE)
try:
    from xref_verify import load_settings, default_settings_path   # noqa: E402  (拿 crossref.mailto)
except Exception:                            # noqa: BLE001
    def load_settings(path):
        return {}

    def default_settings_path():
        return os.path.normpath(os.path.join(_HERE, "..", "..", "config", "settings.yaml"))


def _norm_issn(s):
    return re.sub(r"[^0-9xX]", "", s or "").upper()


def _norm_title(s):
    s = (s or "").lower()
    s = re.sub(r"&[a-z]+;", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def build_cache(timeout=60):
    """下載 SCImago CSV(分號分隔),建 {by_issn, by_title} → 寫快取 JSON。"""
    req = urllib.request.Request(SCIMAGO_URL, headers=BROWSER_H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    rd = csv.DictReader(io.StringIO(raw), delimiter=";")
    by_issn, by_title = {}, {}
    n = 0
    for row in rd:
        q = (row.get("SJR Best Quartile") or "").strip()
        if q not in _Q:
            continue
        title = _norm_title(row.get("Title"))
        if title:
            by_title.setdefault(title, q)
        for issn in (row.get("Issn") or "").split(","):
            iss = _norm_issn(issn)
            if len(iss) == 8:
                by_issn.setdefault(iss, q)
        n += 1
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump({"by_issn": by_issn, "by_title": by_title}, f, ensure_ascii=False)
    sys.stderr.write("built cache: %d ranked journals → %s (issn=%d, title=%d)\n" % (
        n, os.path.normpath(CACHE), len(by_issn), len(by_title)))
    return {"by_issn": by_issn, "by_title": by_title}


def load_cache(auto_build=True):
    if os.path.exists(CACHE):
        with open(CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    if auto_build:
        sys.stderr.write("快取不存在,下載 SCImago 建立中…\n")
        return build_cache()
    return {"by_issn": {}, "by_title": {}}


def quartile_of(cache, journal=None, issns=None):
    """回 'Q1'..'Q4' 或 None(未收錄)。ISSN 優先,標題 fallback。"""
    for iss in (issns or []):
        q = cache["by_issn"].get(_norm_issn(iss))
        if q:
            return q
    if journal:
        return cache["by_title"].get(_norm_title(journal))
    return None


def crossref_journal(doi, mailto, timeout=20):
    """以 DOI 取 Crossref → (container-title, [issn...])。失敗回 (None, [])。"""
    if not doi:
        return None, []
    # 注意:單篇 /works/{DOI} 不支援 select(會回 400,同 v0.8.2 教訓)→ 裸 GET 取全 message。
    url = "%s/%s" % (CROSSREF_WORKS, urllib.parse.quote(doi))
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "consensus-verify-quartile/1.0 (mailto:%s)" % (mailto or "anon@example.com")})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            msg = json.loads(r.read().decode("utf-8", "replace")).get("message", {})
        ct = (msg.get("container-title") or [None])[0]
        return ct, (msg.get("ISSN") or [])
    except Exception:                        # noqa: BLE001
        return None, []


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="期刊 SJR 分位查詢/過濾(Q1+Q2 品質閘, §1①(3′))")
    ap.add_argument("--build", action="store_true", help="下載 SCImago、(重)建快取")
    ap.add_argument("--journal", help="查單一期刊名的分位")
    ap.add_argument("--issn", help="查單一 ISSN 的分位")
    ap.add_argument("--in", dest="infile", help="verified.json:逐筆查分位並過濾")
    ap.add_argument("--out", help="過濾後輸出 JSON(預設只印報告不寫檔)")
    ap.add_argument("--max-quartile", type=int, default=1,
                    help="保留 ≤Qn(預設 1=只 Q1,求最強公信力;2=Q1+Q2)")
    ap.add_argument("--drop-unranked", action="store_true", help="把未收錄者也剔除(預設保留,不誤殺)")
    ap.add_argument("--config", dest="config", help="settings.yaml 路徑(取 crossref.mailto)")
    args = ap.parse_args(argv)

    if args.build:
        build_cache()
        if not (args.journal or args.issn or args.infile):
            return

    cache = load_cache()

    if args.journal or args.issn:
        q = quartile_of(cache, journal=args.journal, issns=[args.issn] if args.issn else None)
        print("%s → %s" % (args.journal or args.issn, q or "未收錄(unranked)"))
        return

    if not args.infile:
        ap.error("需 --build、--journal/--issn 或 --in 其一")

    path = args.config or default_settings_path()
    mailto = (load_settings(path) or {}).get("crossref", {}).get("mailto", "") if os.path.exists(path) else ""

    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("results") or data.get("items") or data if isinstance(data, dict) else data

    keep, dropped, rows = [], [], []
    for rec in records:
        inp = rec.get("input", rec)
        doi = rec.get("resolved_doi") or inp.get("doi") or rec.get("doi") or ""
        journal = rec.get("journal") or inp.get("journal") or ""
        issns = rec.get("issns") or []
        if not journal and doi:
            journal, issns = crossref_journal(doi, mailto)
        q = quartile_of(cache, journal=journal, issns=issns)
        rank = _Q.get(q)
        if q is None:
            in_keep = not args.drop_unranked
            tag = "unranked(%s)" % ("剔除" if args.drop_unranked else "保留")
        else:
            in_keep = rank <= args.max_quartile
            tag = "%s(%s)" % (q, "保留" if in_keep else "剔除")
        (keep if in_keep else dropped).append(rec)
        rows.append((tag, journal or "(無期刊)", (inp.get("title") or "")[:46]))

    sys.stderr.write("品質閘 ≤Q%d:總 %d → 保留 %d／剔除 %d(未收錄%s)\n" % (
        args.max_quartile, len(records), len(keep), len(dropped),
        "剔除" if args.drop_unranked else "保留"))
    for tag, j, t in rows:
        mark = "✅" if "保留" in tag else "✂️"
        print("%s %-14s %-34s %s" % (mark, tag, j[:34], t))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"results": keep}, f, ensure_ascii=False, indent=1)
        sys.stderr.write("wrote %s(%d 筆)\n" % (args.out, len(keep)))


if __name__ == "__main__":
    main()
