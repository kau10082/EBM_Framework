#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consensus-verify / zotero_import.py  (Phase 2, v0.2)
====================================================
把 consensus-verify 的最終結果(清單二 / verified.json)匯入 Zotero 指定 collection。

定位
----
- EBM 管線 **Phase 2(歸檔層)**,與「找文獻＋驗證」的 xref_verify.py 分離。
- 零相依:純 Python 3.8+ 標準庫(urllib / json / os / argparse)。
- 安全預設:**dry-run**(只印不寫);要實際寫入 Zotero 需明確加 --commit。
- 金鑰來源優先序:環境變數 ZOTERO_API_KEY > config/settings.yaml(zotero 區)。
  ⚠️ api_key 是真秘密 → 放 env 或本機 settings.yaml(已 .gitignore);切勿進範本/ZIP。

已實作
------
- (1) **Crossref 補 metadata**:以 `resolved_doi` 打 Crossref,自動補期刊/卷/期/頁/年/作者
      (verified.json 本身沒有這些)。可 --no-enrich 關閉。polite pool 用 settings 的 crossref.mailto。
- (4) **真實寫入**:--commit POST Zotero Web API(/{library_type}s/{library_id}/items)。

未做(依需求略過)
  - (2) itemType 依文獻型態分流 / tag 客製:目前一律 journalArticle、tag 僅 evidence/verdict。
  - (3) 對既有 collection 去重:目前不查重,直接寫入。

用法
----
  python zotero_import.py --in verified.json                 # 乾跑(補 metadata、只印不寫)
  python zotero_import.py --in verified.json --no-enrich      # 不打 Crossref
  python zotero_import.py --in verified.json --commit         # 真的寫入
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ZOTERO_API = "https://api.zotero.org"
ZOTERO_API_VERSION = "3"
CROSSREF_WORKS = "https://api.crossref.org/works"

# 沿用 xref_verify 的零相依 YAML 讀取器(同資料夾),維持單一設定機制。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from xref_verify import load_settings, default_settings_path   # noqa: E402
except Exception:                            # noqa: BLE001
    def load_settings(path):                 # 後備:讀不到就回空
        return {}

    def default_settings_path():
        return os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "settings.yaml"))


def _settings_path(args=None):
    if args is not None and getattr(args, "config", None):
        return args.config
    return default_settings_path()


def _mask(secret):
    """金鑰遮罩:只露前後各 3 碼(用於 log,絕不印全 key)。"""
    if not secret:
        return "(空)"
    s = str(secret)
    return s if len(s) <= 6 else "%s***%s" % (s[:3], s[-3:])


def resolve_zotero_config(args):
    """env > settings.yaml(zotero 區) > CLI 預設。api_key 不經型別轉換。"""
    cfg = {}
    if not args.no_config:
        path = _settings_path(args)
        if os.path.exists(path):
            cfg = (load_settings(path) or {}).get("zotero", {}) or {}
            sys.stderr.write("settings: loaded zotero section from %s\n" % os.path.normpath(path))
    env = os.environ
    return {
        "api_key": env.get("ZOTERO_API_KEY") or cfg.get("api_key") or "",
        "library_type": args.library_type or cfg.get("library_type") or "user",
        "library_id": args.library_id or str(cfg.get("library_id") or ""),
        "collection_key": args.collection or cfg.get("collection_key") or "",
    }


def _crossref_mailto(args):
    try:
        return (load_settings(_settings_path(args)) or {}).get("crossref", {}).get("mailto", "") or ""
    except Exception:                        # noqa: BLE001
        return ""


def enrich_from_crossref(doi, mailto="", timeout=20):
    """(1) 以 DOI 取 Crossref metadata,回補欄 dict(publicationTitle/volume/issue/pages/date/creators)。
    失敗(無 DOI / 連不到 / 404)回 {} → 由呼叫端 fallback 到輸入既有值。"""
    if not doi:
        return {}
    ua = "consensus-verify-zotero/0.2 (mailto:%s)" % (mailto or "anon@example.com")
    url = "%s/%s" % (CROSSREF_WORKS, urllib.parse.quote(doi))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            msg = json.loads(r.read().decode("utf-8", "replace")).get("message", {})
    except Exception:                        # noqa: BLE001
        return {}
    out = {}
    ct = msg.get("container-title") or []
    if ct:
        out["publicationTitle"] = ct[0]
    for k_cr, k_z in (("volume", "volume"), ("issue", "issue"), ("page", "pages")):
        if msg.get(k_cr):
            out[k_z] = msg[k_cr]
    issued = (msg.get("issued") or {}).get("date-parts") or [[None]]
    if issued and issued[0] and issued[0][0]:
        out["date"] = str(issued[0][0])
    creators = []
    for a in (msg.get("author") or []):
        fam = a.get("family")
        if fam:
            creators.append({"creatorType": "author", "lastName": fam, "firstName": a.get("given", "")})
    if creators:
        out["creators"] = creators
    return out


def enrich_from_europepmc(doi, timeout=20):
    """(1-fallback) Crossref 查無內容的 DOI(中文期刊 CMA 10.3760/DataCite/會議摘要)改打 EuropePMC core。
    回同形 dict(publicationTitle/volume/issue/pages/date/creators/ISSN)。失敗回 {}。"""
    if not doi:
        return {}
    q = urllib.parse.quote('DOI:"%s"' % doi)
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%s"
           "&resultType=core&format=json&pageSize=1" % q)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "consensus-verify-zotero/0.2"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8", "replace")).get("resultList", {}).get("result", [])
    except Exception:                        # noqa: BLE001
        return {}
    if not res:
        return {}
    m = res[0]
    ji = m.get("journalInfo", {}) or {}
    jr = ji.get("journal", {}) or {}
    out = {}
    if jr.get("title") or m.get("journalTitle"):
        out["publicationTitle"] = jr.get("title") or m.get("journalTitle")
    if ji.get("volume"):
        out["volume"] = ji["volume"]
    if ji.get("issue"):
        out["issue"] = ji["issue"]
    if m.get("pageInfo"):
        out["pages"] = m["pageInfo"]
    if m.get("pubYear"):
        out["date"] = str(m["pubYear"])
    if jr.get("issn") or jr.get("essn"):
        out["ISSN"] = jr.get("issn") or jr.get("essn")
    creators = []
    for a in (m.get("authorList", {}) or {}).get("author", []):
        ln = a.get("lastName") or ""
        fn = a.get("firstName") or a.get("initials") or ""
        if ln or fn:
            creators.append({"creatorType": "author", "lastName": ln, "firstName": fn})
        elif a.get("fullName"):
            creators.append({"creatorType": "author", "lastName": a["fullName"], "firstName": ""})
    if creators:
        out["creators"] = creators
    return out


def enrich_from_pubmed(pmid, timeout=20):
    """以 PMID 走 PubMed efetch(medline)補 title/creators/publicationTitle/date。
    DOI 路徑(Crossref/EuropePMC)補不到時的後援——無 DOI/preprint/Crossref 查無者最常缺作者。失敗回 {}。"""
    if not pmid:
        return {}
    try:
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s"
               "&rettype=medline&retmode=text" % pmid)
        txt = urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8", "replace")
    except Exception:
        return {}
    f = {}
    cur = None
    for line in txt.split("\n"):
        m = re.match(r"^([A-Z]{2,4})\s*- (.*)$", line)
        if m:
            cur = m.group(1); f.setdefault(cur, []).append(m.group(2))
        elif line.startswith("      ") and cur:
            f[cur][-1] += " " + line.strip()
    out = {}
    ti = " ".join(f.get("TI", [])).strip()
    if ti:
        out["title"] = ti
    creators = []
    for fau in f.get("FAU", []):
        if "," in fau:
            ln, fn = fau.split(",", 1)
            creators.append({"creatorType": "author", "lastName": ln.strip(), "firstName": fn.strip()})
        else:
            creators.append({"creatorType": "author", "lastName": fau.strip(), "firstName": ""})
    if not creators:
        for au in f.get("AU", []):
            p = au.rsplit(" ", 1)
            creators.append({"creatorType": "author", "lastName": p[0], "firstName": (p[1] if len(p) > 1 else "")})
    if creators:
        out["creators"] = creators
    jt = (f.get("JT") or f.get("TA") or [""])[0]
    if jt:
        out["publicationTitle"] = jt
    dp = (f.get("DP") or [""])[0]
    if dp:
        out["date"] = dp[:4]
    return out


def enrich_metadata(doi, mailto=""):
    """補書目:先 Crossref,查無內容(非 Crossref 註冊的 DOI)再 fallback EuropePMC。"""
    out = enrich_from_crossref(doi, mailto)
    if not out or not (out.get("creators") or out.get("publicationTitle")):
        ep = enrich_from_europepmc(doi)
        if ep:
            # 以 EuropePMC 補滿缺欄(保留 Crossref 已有者)
            for k, v in ep.items():
                out.setdefault(k, v)
    return out


def _authors_to_creators(rec):
    """fallback:輸入只有 first_author 時的 creators(無 Crossref 時用)。"""
    inp = rec.get("input", rec)
    fa = inp.get("first_author") or rec.get("first_author")
    if not fa:
        return []
    parts = fa.replace(",", " ").split()
    last = parts[0] if parts else fa
    first = " ".join(parts[1:]) if len(parts) > 1 else ""
    return [{"creatorType": "author", "lastName": last, "firstName": first}]


def map_to_zotero(rec, collection_key, enrich=None):
    """一筆 verified 結果 → Zotero journalArticle item。enrich(Crossref)優先,輸入值 fallback。"""
    enrich = enrich or {}
    inp = rec.get("input", rec)
    title = inp.get("title") or rec.get("title") or enrich.get("title") or ""
    doi = rec.get("resolved_doi") or inp.get("doi") or rec.get("doi") or ""
    pmid = rec.get("resolved_pmid") or rec.get("pmid") or ""
    year = enrich.get("date") or inp.get("year") or rec.get("year") or ""
    creators = enrich.get("creators") or _authors_to_creators(rec)
    item = {
        "itemType": "journalArticle",
        "title": title,
        "creators": creators,
        "date": str(year) if year else "",
        "DOI": doi or "",
        "publicationTitle": enrich.get("publicationTitle", "") or rec.get("journal", ""),
        "volume": enrich.get("volume", "") or rec.get("volume", ""),
        "issue": enrich.get("issue", "") or rec.get("issue", ""),
        "pages": enrich.get("pages", "") or rec.get("pages", ""),
        "extra": ("PMID: %s" % pmid) if pmid else "",
    }
    tags = []
    if rec.get("evidence_level"):
        tags.append({"tag": "evidence:%s" % rec["evidence_level"]})
    if rec.get("verdict"):
        tags.append({"tag": "verdict:%s" % rec["verdict"]})
    if rec.get("study"):
        tags.append({"tag": "study:%s" % rec["study"]})
    if rec.get("role"):
        tags.append({"tag": "role:%s" % rec["role"]})
    if tags:
        item["tags"] = tags
    if collection_key:
        item["collections"] = [collection_key]
    return item


def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("results") or data.get("items") or []
    return data


def post_to_zotero(items, conf, timeout=30):
    """(4) POST 一批 item(Zotero 單批上限 50)。回傳解析後 JSON。"""
    lib_seg = "%ss" % conf["library_type"]            # users / groups
    url = "%s/%s/%s/items" % (ZOTERO_API, lib_seg, conf["library_id"])
    body = json.dumps(items, ensure_ascii=False).encode("utf-8")
    headers = {
        "Zotero-API-Key": conf["api_key"],
        "Zotero-API-Version": ZOTERO_API_VERSION,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def existing_dois(conf, timeout=30):
    """(去重) 取目標 collection 既有 item 的 DOI 集合(小寫)。失敗回空集合(不擋匯入)。"""
    lib_seg = "%ss" % conf["library_type"]
    coll = conf.get("collection_key")
    base = ("%s/%s/%s/collections/%s/items" % (ZOTERO_API, lib_seg, conf["library_id"], coll)) if coll \
           else ("%s/%s/%s/items" % (ZOTERO_API, lib_seg, conf["library_id"]))
    headers = {"Zotero-API-Key": conf["api_key"], "Zotero-API-Version": ZOTERO_API_VERSION}
    out = set(); start = 0
    try:
        while True:
            url = "%s?format=json&limit=100&start=%d" % (base, start)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                batch = json.loads(r.read().decode("utf-8", "replace"))
            if not batch:
                break
            for it in batch:
                doi = (it.get("data", {}).get("DOI") or "").strip().lower()
                if doi:
                    out.add(doi)
            if len(batch) < 100:
                break
            start += 100
    except Exception as e:
        sys.stderr.write("dedup: 取既有 DOI 失敗(%s) → 本次不去重\n" % str(e)[:60])
    return out


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="把 consensus-verify 結果匯入 Zotero collection(Phase 2)")
    ap.add_argument("--in", dest="infile", required=True, help="輸入 JSON(verified.json / 清單二)")
    ap.add_argument("--config", dest="config", help="設定檔路徑(預設 <script>/../config/settings.yaml)")
    ap.add_argument("--no-config", action="store_true", help="略過設定檔,只用 env 與 CLI")
    ap.add_argument("--library-type", choices=["user", "group"], default=None)
    ap.add_argument("--library-id", default=None)
    ap.add_argument("--collection", default=None, help="覆蓋目標 collection key")
    ap.add_argument("--no-enrich", action="store_true", help="不打 Crossref 補 metadata")
    ap.add_argument("--no-dedup", action="store_true", help="不對既有 collection 做 DOI 去重")
    ap.add_argument("--commit", action="store_true", help="實際寫入 Zotero(預設 dry-run)")
    args = ap.parse_args(argv)

    conf = resolve_zotero_config(args)
    records = load_items(args.infile)
    mailto = "" if args.no_enrich else _crossref_mailto(args)

    # (去重) 取既有 DOI；dry-run 也先查,讓 payload 反映實際會寫入者
    seen = set()
    if not args.no_dedup and conf.get("api_key") and conf.get("library_id"):
        seen = existing_dois(conf)
        if seen:
            sys.stderr.write("dedup: collection 既有 %d 個 DOI,將跳過重複\n" % len(seen))

    items, enriched, skipped = [], 0, 0
    for r in records:
        doi = r.get("resolved_doi") or r.get("input", {}).get("doi") or r.get("doi") or ""
        if doi and doi.strip().lower() in seen:
            skipped += 1
            continue
        e = {} if args.no_enrich else enrich_metadata(doi, mailto)
        # PubMed 後援：Crossref/EuropePMC(DOI 路徑)補不到作者/標題時，以 PMID efetch 補齊
        # （無 DOI、preprint、Crossref 查無者最常缺作者；避免匯入後書目缺標題/作者）
        pmid = r.get("resolved_pmid") or r.get("pmid") or r.get("input", {}).get("pmid") or ""
        if not args.no_enrich and pmid and (not e.get("creators") or not (r.get("title") or r.get("input", {}).get("title"))):
            pm = enrich_from_pubmed(str(pmid))
            for k, v in (pm or {}).items():
                if v and not e.get(k):
                    e[k] = v
        if e:
            enriched += 1
        items.append(map_to_zotero(r, conf["collection_key"], e))
    if skipped:
        sys.stderr.write("dedup: 跳過 %d 筆(DOI 已在 collection),實際待匯 %d 筆\n" % (skipped, len(items)))

    sys.stderr.write("zotero: library=%s/%s collection=%s api_key=%s | %d 筆(Crossref 補 %d)\n" % (
        conf["library_type"], conf["library_id"] or "(未設)", conf["collection_key"] or "(未設)",
        _mask(conf["api_key"]), len(items), enriched))

    if not args.commit:
        sys.stderr.write("DRY-RUN(未寫入)。下方為將送進 Zotero 的 payload;確認無誤後加 --commit。\n")
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    missing = [k for k in ("api_key", "library_id", "collection_key") if not conf[k]]
    if missing:
        ap.error("缺少必要設定:%s(env ZOTERO_API_KEY 或 settings.yaml 的 zotero 區)" % ", ".join(missing))
    if len(items) > 50:
        ap.error("單批上限 50 筆,本次 %d 筆;請分批(之後可加自動分批)。" % len(items))
    resp = post_to_zotero(items, conf)
    print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
