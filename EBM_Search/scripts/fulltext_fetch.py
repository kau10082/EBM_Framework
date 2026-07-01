#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consensus-verify / fulltext_fetch.py  (Phase 3 骨架, v0.1-scaffold)
==================================================================
依 verified.json 的 DOI/PMID,查「合法開放取用(OA)」全文並(可選)下載 PDF。
付費牆者只標記、不抓(走醫院 Zotero 桌面「Find Available PDF」)。

定位
----
- EBM 管線 **Phase 3(全文層)**,與引擎(xref_verify)、歸檔(zotero_import)分離。
- 零相依:純 Python 3.8+ 標準庫(urllib / json / os / argparse)。
- **只抓合法 OA**:Unpaywall(DOI→最佳 OA PDF)＋ PMC OA(PMID→PMCID 佐證)。
  **絕不碰盜版**(Sci-Hub 等);付費牆全文需機構授權 → 走醫院 Zotero。
- 安全預設:**dry-run**(只查不下載、只寫 manifest);要實際下載加 --download。
- email 來源:settings.yaml 的 crossref.mailto(Unpaywall 必填,非秘密)。

三類分流(寫進 manifest 與終端)
  ✅ oa_direct   :Unpaywall 有 url_for_pdf → 可全自動下載
  ⚠️ oa_landing  :is_oa 但只有 landing page(無直連 PDF)→ 需解析 host/手動
  🏥 closed      :無 OA → 付費牆,走醫院 Zotero(本腳本不處理)

用法
----
  python fulltext_fetch.py --in verified.json                 # 只查 OA 可得性、寫 manifest
  python fulltext_fetch.py --in verified.json --download      # 實際下載 oa_direct 的 PDF
  python fulltext_fetch.py --in verified.json --out-dir ../fulltext

狀態:**骨架**。Unpaywall 查詢/分類/下載/manifest 都已接好;PMC OA 套件解析、
      landing→PDF 解析、下載被 403 的退場策略等待強化(見 TODO)。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UNPAYWALL = "https://api.unpaywall.org/v2"
IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
UA = "consensus-verify-fulltext/0.1 (mailto:%s)"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from xref_verify import load_settings, default_settings_path   # noqa: E402
except Exception:                            # noqa: BLE001
    def load_settings(path):
        return {}

    def default_settings_path():
        return os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "settings.yaml"))


def _settings_path(args=None):
    if args is not None and getattr(args, "config", None):
        return args.config
    return default_settings_path()


def _mailto(args):
    if not args.no_config:
        m = (load_settings(_settings_path(args)) or {}).get("crossref", {}).get("mailto", "")
        if m:
            return m
    return os.environ.get("CROSSREF_MAILTO", "") or "anon@example.com"


def _get_json(url, ua, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def unpaywall_lookup(doi, mailto, timeout=20):
    """DOI → Unpaywall。回 {is_oa, oa_status, pdf_url, landing_url, host_type}。
    無 DOI 回 {}；**查詢失敗回 None**——「抓取失敗」與「來源真的無 OA」必須可區分（硬規則），
    失敗不得被 classify 靜默當成 closed（付費牆）。"""
    if not doi:
        return {}
    url = "%s/%s?email=%s" % (UNPAYWALL, urllib.parse.quote(doi), urllib.parse.quote(mailto))
    try:
        d = _get_json(url, UA % mailto, timeout)
    except Exception:                        # noqa: BLE001
        return None
    loc = d.get("best_oa_location") or {}
    return {
        "is_oa": bool(d.get("is_oa")),
        "oa_status": d.get("oa_status", ""),
        "pdf_url": loc.get("url_for_pdf") or "",
        "landing_url": loc.get("url") or "",
        "host_type": loc.get("host_type", ""),
    }


def pmcid_of(pmid, mailto, timeout=20):
    """PMID → PMCID(佐證 PMC 有免費版;TODO:接 PMC OA 套件取真正 PDF)。
    無 PMC 版回 ''；**查詢失敗回 None**（與「真的無 PMC 版」區分）。"""
    if not pmid:
        return ""
    url = "%s?ids=%s&format=json&tool=consensus-verify&email=%s" % (
        IDCONV, urllib.parse.quote(str(pmid)), urllib.parse.quote(mailto))
    try:
        d = _get_json(url, UA % mailto, timeout)
        recs = d.get("records") or []
        return recs[0].get("pmcid", "") if recs else ""
    except Exception:                        # noqa: BLE001
        return None


def classify(up):
    if up is None:                            # Unpaywall 查詢失敗 ≠ 付費牆：獨立分類，不得混入 closed
        return "lookup_failed"
    if up.get("pdf_url"):
        return "oa_direct"
    if up.get("is_oa"):
        return "oa_landing"
    return "closed"


def _doi_slug(doi):
    return (doi or "no-doi").replace("/", "_").replace(":", "_")


def download_pdf(url, dest, mailto, timeout=60):
    """下載 PDF 到 dest。回 (ok, detail)。零相依;部分出版商會擋 scripted UA(403)→ 標記待醫院。
    TODO:對 landing-only / 403 加 host 專屬解析或交回 Zotero。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA % mailto, "Accept": "application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
        if b"%PDF" not in data[:1024] and "pdf" not in ct.lower():
            return False, "非 PDF(可能是 landing/HTML;Content-Type=%s)" % ct
        with open(dest, "wb") as f:
            f.write(data)
        return True, "%d KB" % (len(data) // 1024)
    except urllib.error.HTTPError as e:
        return False, "HTTP %s(出版商擋 scripted 下載?走醫院)" % e.code
    except Exception as e:                    # noqa: BLE001
        return False, str(e)[:60]


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="依 verified.json 查/抓合法 OA 全文(Phase 3 骨架)")
    ap.add_argument("--in", dest="infile", required=True, help="輸入 JSON(verified.json / 清單二)")
    ap.add_argument("--config", dest="config", help="設定檔路徑(預設 <script>/../config/settings.yaml)")
    ap.add_argument("--no-config", action="store_true")
    ap.add_argument("--out-dir", default=None, help="PDF 下載資料夾(預設 <script>/../fulltext)")
    ap.add_argument("--download", action="store_true", help="實際下載 oa_direct 的 PDF(預設只查不抓)")
    ap.add_argument("--manifest", default=None, help="manifest 輸出路徑(預設 out-dir/fulltext_manifest.json)")
    ap.add_argument("--no-pmc", action="store_true", help="不查 PMCID 佐證(省一次請求)")
    args = ap.parse_args(argv)

    mailto = _mailto(args)
    out_dir = args.out_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "fulltext")
    manifest_path = args.manifest or os.path.join(out_dir, "fulltext_manifest.json")
    if args.download:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        records = data.get("results") or data.get("items") or data.get("records") or data.get("papers")
        if not isinstance(records, list):
            sys.exit("輸入檔沒有可辨識的紀錄清單（預期頂層 list 或 results/items/records/papers 鍵）：%s"
                     "——餵錯檔不可靜默空跑當成功" % args.infile)
    else:
        records = data

    rows, cats = [], {"oa_direct": 0, "oa_landing": 0, "closed": 0, "lookup_failed": 0}
    for rec in records:
        inp = rec.get("input", rec)
        doi = rec.get("resolved_doi") or inp.get("doi") or rec.get("doi") or ""
        pmid = rec.get("resolved_pmid") or rec.get("pmid") or ""
        title = (inp.get("title") or rec.get("title") or "")[:50]
        up = unpaywall_lookup(doi, mailto)
        cat = classify(up)
        up = up or {}
        pmcid = "" if (args.no_pmc or not pmid) else pmcid_of(pmid, mailto)
        row = {"pmid": pmid, "doi": doi, "title": title, "category": cat,
               "oa_status": up.get("oa_status", ""), "pdf_url": up.get("pdf_url", ""),
               "landing_url": up.get("landing_url", ""), "pmcid": pmcid if pmcid is not None else "",
               "downloaded": None, "detail": "Unpaywall 查詢失敗（≠無 OA，請重跑）" if cat == "lookup_failed" else ""}
        if pmcid is None:
            row["detail"] = (row["detail"] + "；" if row["detail"] else "") + "PMCID 查詢失敗（≠無 PMC 版）"
        if args.download and cat == "oa_direct":
            dest = os.path.join(out_dir, "%s.pdf" % (pmid or _doi_slug(doi)))
            ok, detail = download_pdf(up["pdf_url"], dest, mailto)
            row["downloaded"] = ok
            row["detail"] = detail if ok else "下載失敗:%s" % detail
        cats[cat] += 1
        rows.append(row)
        time.sleep(0.3)                       # 對 Unpaywall 客氣

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"mailto": mailto, "summary": cats, "items": rows}, f, ensure_ascii=False, indent=2)

    icon = {"oa_direct": "✅", "oa_landing": "⚠️", "closed": "🏥", "lookup_failed": "❓"}
    sys.stderr.write("fulltext: %d 筆 | ✅oa_direct %d ／ ⚠️oa_landing %d ／ 🏥closed %d ／ ❓lookup_failed %d ｜ manifest→%s\n" % (
        len(rows), cats["oa_direct"], cats["oa_landing"], cats["closed"], cats["lookup_failed"],
        os.path.normpath(manifest_path)))
    if cats["lookup_failed"]:
        sys.stderr.write("⚠ 有 %d 筆 Unpaywall 查詢失敗：這些**不是**付費牆判定，請恢復網路後重跑，"
                         "不得直接當 closed 走醫院清單。\n" % cats["lookup_failed"])
    for r in rows:
        dl = "" if r["downloaded"] is None else ("｜下載 %s" % ("OK " + r["detail"] if r["downloaded"] else r["detail"]))
        print("%s %-9s %-14s %s%s" % (icon[r["category"]], r["category"], r["oa_status"] or "-", r["title"], dl))
    if not args.download:
        sys.stderr.write("DRY-RUN(只查未下載)。加 --download 抓 ✅oa_direct 的 PDF;🏥closed 走醫院 Zotero。\n")


if __name__ == "__main__":
    main()
