# -*- coding: utf-8 -*-
"""
verify_have_fetchable.py — 『判 have 必須實抓得到全文』驗證器（防 OA 旗標高估）
================================================================================
與 fulltext_audit.py 對稱：後者查「判 not-have 的是否其實 OA」（防低估）；
本器查「判 fulltext_status=have/have_manual(online) 的是否『實際抓得到內容』」（防高估）。

實測（COPD 三聯案）：②c 憑 Unpaywall is_oa 旗標把 IMPACT/ETHOS 判 have，但 NEJM
出版商 OA URL 實抓 403、ETHOS 還因錯 DOI 假陽性 → 全文其實免費抓不到，卻沒列進需補清單，
拖到 Phase 1 評讀才爆。本器在 ②c/⑧ 就實抓每筆 have(online)、字元數 < 門檻即判『假 have』，
回傳應改 need-supplement 的清單，並蓋 `fulltext_verified` 真旗標供守門檢核。

判定：依序試 PMC fullTextXML → Unpaywall best/oa_locations PDF(瀏覽器 UA) → 取回正文字元數
      ≥ min_chars(預設 3000，遠大於摘要) 才算『實抓到』；否則 false-have。

用法：python verify_have_fetchable.py --in <papers.json|corpus_seed> [--min-chars 3000] [--only-included]
程式內：import verify_have_fetchable as v; res = v.verify(papers)
"""
import sys, os, re, json, argparse, urllib.request, urllib.parse, time
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
HAVE = {"have", "have_manual"}

def _get(url, timeout=45):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def _norm_doi(d):
    if not d: return None
    d = str(d).lower().strip(); d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d); return d or None

def _pdf_chars(data):
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        t = " ".join(p.get_text() for p in doc); doc.close()
        return len(t)
    except Exception:
        return 0

_FT_MARKERS = [r"\bmethods?\b", r"\bresults?\b", r"\b(discussion|conclusion)\b",
               r"randomi[sz]|randomly", r"95%\s*ci|p\s*[<=]\s*0", r"\b(intro|background)"]

def _is_real_fulltext(t):
    """真全文判定：足夠長 ＋ 含多個章節/統計特徵；藉此排除『中繼資料著陸頁』假通過
    （實測 IMPACT 的 Manchester landing >8000 字卻只是 metadata/abstract/refs）。"""
    if not t or len(t) < 12000:
        return False
    hits = sum(1 for m in _FT_MARKERS if re.search(m, t, re.I))
    return hits >= 3

def _fetch_text(pmid, doi, timeout=45):
    """回 (chars, channel)；只在『真全文』時回非零（PDF/PMC/HTML 皆可，靠 _is_real_fulltext 把關）。"""
    # 1) PMC fullTextXML（EuropePMC，以 pmid 找 pmcid）
    if pmid:
        try:
            u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:%s%%20AND%%20SRC:MED"
                 "&format=json&resultType=core&pageSize=1" % pmid)
            r = (json.loads(_get(u, 25).decode("utf-8", "replace"))["resultList"]["result"] or [{}])[0]
            pmcid = r.get("pmcid")
            if pmcid:
                xml = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid, timeout).decode("utf-8", "replace")
                t = re.sub(r"<[^>]+>", " ", xml)
                if _is_real_fulltext(t): return len(t), "pmc"
        except Exception:
            pass
    # 2) Unpaywall best + 所有 oa_locations（PDF 抽文字 / HTML 取內文，皆過 _is_real_fulltext）
    doi = _norm_doi(doi)
    if doi:
        try:
            d = json.loads(_get("https://api.unpaywall.org/v2/" + urllib.parse.quote(doi) + "?email=kau10082@gmail.com", 25).decode("utf-8", "replace"))
            locs = ([d.get("best_oa_location")] if d.get("best_oa_location") else []) + (d.get("oa_locations") or [])
            for loc in locs:
                for url in [(loc or {}).get("url_for_pdf"), (loc or {}).get("url")]:
                    if not url: continue
                    try:
                        data = _get(url, timeout)
                        if data[:4] == b"%PDF":
                            d2 = None
                            try:
                                import fitz
                                d2 = fitz.open(stream=data, filetype="pdf")
                                t = " ".join(p.get_text() for p in d2); d2.close()
                            except Exception:
                                t = ""
                            if _is_real_fulltext(t): return len(t), "unpaywall_pdf:" + (loc.get("host_type") or "")
                        else:
                            t = re.sub(r"<[^>]+>", " ", data.decode("utf-8", "replace"))
                            if _is_real_fulltext(t): return len(t), "unpaywall_html:" + (loc.get("host_type") or "")
                    except Exception:
                        continue
        except Exception:
            pass
    return 0, ""

def verify(papers, min_chars=3000, only_included=False, sleep=0.2):
    """回 {checked, ok, false_have:[...], records:[{paper_id, verified, chars, channel}]}。"""
    out = {"checked": 0, "ok": 0, "false_have": [], "records": []}
    for p in papers:
        st = p.get("fulltext_status")
        ch = (p.get("fulltext_channel") or "").lower()
        if st not in HAVE:
            continue
        if only_included and p.get("verdict") != "included":
            continue
        # 本機 PDF（have_manual + pdf_file）：信任，不需網路抓
        if p.get("pdf_file"):
            p["fulltext_verified"] = True
            out["records"].append({"paper_id": p.get("paper_id") or p.get("pmid"), "verified": True, "chars": None, "channel": "local_pdf"})
            out["checked"] += 1; out["ok"] += 1
            continue
        if ch and "online" not in ch and "pmc" not in ch and "unpaywall" not in ch:
            continue
        pid = p.get("paper_id") or p.get("pmid")
        chars, channel = _fetch_text(str(p.get("pmid") or ""), p.get("doi"))
        time.sleep(sleep)
        verified = chars >= min_chars
        p["fulltext_verified"] = bool(verified)
        out["records"].append({"paper_id": pid, "verified": verified, "chars": chars, "channel": channel})
        out["checked"] += 1
        if verified:
            out["ok"] += 1
        else:
            out["false_have"].append({"paper_id": pid, "pmid": p.get("pmid"), "doi": p.get("doi"),
                                       "title": (p.get("title") or "")[:60], "chars": chars,
                                       "verdict": p.get("verdict")})
    return out

def _load_papers(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return obj.get("papers", obj if isinstance(obj, list) else [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--min-chars", type=int, default=3000)
    ap.add_argument("--only-included", action="store_true")
    a = ap.parse_args()
    papers = _load_papers(a.infile)
    res = verify(papers, min_chars=a.min_chars, only_included=a.only_included)
    print("verify_have_fetchable：實抓驗證 %d 筆 have(online)；通過 %d、假 have %d"
          % (res["checked"], res["ok"], len(res["false_have"])))
    for f in res["false_have"]:
        print("  ❌ 假 have（判有全文但實抓不到，應改 need-supplement）：%s | pmid=%s | doi=%s | 取回 %d 字元 | %s"
              % (f["paper_id"], f["pmid"], f["doi"], f["chars"], f["title"]))
    if res["false_have"]:
        sys.exit(1)
    print("✅ 所有 have(online) 均實抓得到全文（≥%d 字元）。" % a.min_chars)

if __name__ == "__main__":
    main()
