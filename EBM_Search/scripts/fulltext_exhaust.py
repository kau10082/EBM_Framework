# -*- coding: utf-8 -*-
"""
fulltext_exhaust.py — ②c 的『完整實抓解析』工具（移到「待評估」前的最後一道盡力）
================================================================================
鐵律（2026-06 使用者糾正）：②c 一筆「找不到摘要/全文」者，**移到『待評估』之前
必須先真的『完整實抓解析』全文**——不是只看 Unpaywall `is_oa` 旗標就 punt。
只有「真的盡全力實抓解析仍失敗」者，才能列為待評估。

本工具是該動作的單一真實來源（任何主題的 ②c 都呼叫它）。對每筆缺內容記錄，
依序窮盡管道、**實際下載並解析**，命中可篩內容（≥ min_chars）即升回 have：
  (1) 既有 abstract（已有就直接 have）
  (2) Crossref 摘要欄（abstract，JATS→去標籤）
  (3) PMC fullTextXML（EuropePMC 以 pmid/doi 找 pmcid → 取 XML 去標籤）
  (4) Unpaywall 全部 oa_locations（url_for_pdf / url）**實際下載**：
        PDF → pypdf/fitz 抽文字；HTML → 去標籤取內文
全部失敗 → 標 content_status=awaiting，並寫滿『可稽核的實抓證明』供 gate_guard 核對：
  abstract_checked / online_fulltext_checked / unpaywall_checked / oa_fetch_attempted /
  fulltext_parse_attempted=True / oa_urls_tried=[...實際試過的URL] / channels_exhausted=True，
  並標 doc_type（correspondence/editorial＝來源本無摘要；unresolved＝抓取失敗）。

force=True（全文/摘要搜尋及嚴格離題篩選 Tier 3 用）：即使已有 abstract 也不早停，強制實取全文以取得『比摘要更多
的內容』——因『離題』只能在實取全文後定案；取得更長正文則升級 fulltext_excerpt，否則保留 abstract
並照樣蓋 fulltext_parse_attempted（證明已試到全文）。

用法（CLI）：
  python fulltext_exhaust.py --in g2c_need_content.json --out g2c_resolved.json [--min-chars 250]
程式內：
  import fulltext_exhaust as fx
  fx.resolve(records, min_chars=250)   # 原地更新每筆 records（dict）
"""
import sys, os, re, io, json, time, argparse, urllib.parse, urllib.request
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from xref_verify import load_settings, default_settings_path  # noqa: E402
except Exception:  # noqa: BLE001
    def load_settings(_p): return {}
    def default_settings_path(): return ""

DEFAULT_MAIL = "noreply@example.org"

def _mail():
    try:
        s = load_settings(default_settings_path()) or {}
        m = ((s.get("crossref") or {}).get("mailto")
             or (s.get("report") or {}).get("mailto"))
        if m: return m
    except Exception:
        pass
    return os.environ.get("CROSSREF_MAILTO", DEFAULT_MAIL)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 EBM_Search/0.21"

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get_content_type()

def _norm_doi(d):
    if not d: return None
    d = str(d).lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None

def _strip_tags(s):
    s = re.sub(r"(?is)<(script|style|head|nav|footer).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = re.sub(r"&[a-z#0-9]+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# 真內容特徵（防呆）：OA 下載的 HTML/PDF 若只是 cookie 同意書／登入提示／paywall 版權宣告，
# 純文字也可能 >min_chars。要求命中 ≥2 個科學/方法學特徵才算真內容（landing/wall 頁幾乎 0 命中）。
# 只套在『Unpaywall OA 下載』分支——Crossref 摘要欄、PMC fullTextXML 為結構化來源，已是真內容。
_CONTENT_MARKERS = [
    r"\bmethods?\b", r"\bresults?\b", r"\bconclusions?\b", r"\bbackground\b",
    r"\bintroduction\b", r"\bdiscussion\b", r"\bobjective", r"randomi[sz]",
    r"\bpatients?\b", r"\bparticipants?\b", r"\bplacebo\b", r"\befficacy\b",
    r"\bexacerbat", r"95%\s*c", r"\bp\s*[<=]\s*0", r"double[\s\-]*blind", r"\boutcome",
]
def _looks_like_content(t, min_chars):
    if not t or len(t) < min_chars:
        return False
    hits = sum(1 for m in _CONTENT_MARKERS if re.search(m, t, re.I))
    return hits >= 2

def _pdf_text(data):
    # 優先 pypdf；無則試 pymupdf(fitz)
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(data))
        return re.sub(r"\s+", " ", " ".join((pg.extract_text() or "") for pg in rd.pages[:6])).strip()
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        t = " ".join(p.get_text() for p in doc); doc.close()
        return re.sub(r"\s+", " ", t).strip()
    except Exception:
        return ""

def _crossref_abstract(doi, mail):
    try:
        raw, _ = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi)
                      + "?mailto=" + urllib.parse.quote(mail), 45)
        msg = json.loads(raw.decode("utf-8", "replace")).get("message", {})
    except Exception:
        return None, None
    ab = msg.get("abstract")
    dt = msg.get("type")
    return (_strip_tags(ab) if ab else None), dt

def _pmc_fulltext(pmid, doi, mail):
    """EuropePMC：以 pmid 或 doi 找 pmcid → 取 fullTextXML 去標籤。"""
    q = None
    if pmid: q = "EXT_ID:%s AND SRC:MED" % pmid
    elif doi: q = 'DOI:"%s"' % doi
    if not q: return ""
    try:
        u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
             + urllib.parse.urlencode({"query": q, "format": "json",
                                       "resultType": "core", "pageSize": 1}))
        raw, _ = _get(u, 30)
        res = (json.loads(raw.decode("utf-8", "replace")).get("resultList", {}).get("result") or [{}])[0]
        # 順手撿摘要
        ab = res.get("abstractText")
        pmcid = res.get("pmcid")
        if pmcid:
            xml, _ = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid, 60)
            t = _strip_tags(xml.decode("utf-8", "replace"))
            if t: return t
        if ab: return _strip_tags(ab)
    except Exception:
        pass
    return ""

def _unpaywall_locations(doi, mail):
    try:
        raw, _ = _get("https://api.unpaywall.org/v2/%s?email=%s"
                      % (urllib.parse.quote(doi), urllib.parse.quote(mail)), 30)
        d = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None, []
    is_oa = bool(d.get("is_oa"))
    locs = ([d.get("best_oa_location")] if d.get("best_oa_location") else []) + (d.get("oa_locations") or [])
    urls = []
    for L in locs:
        if not L: continue
        for k in ("url_for_pdf", "url"):
            if L.get(k) and L[k] not in urls:
                urls.append(L[k])
    return is_oa, urls

_CORR = ("point:", "counterpoint", "letter", "reply", "response to", "editorial",
         "comment on", "correspondence", "author's reply", "in response")

def _doc_type(rec):
    t = (rec.get("title") or "").lower()
    pt = " ".join(str(x).lower() for x in (rec.get("ptypes") or []))
    if any(k in t for k in _CORR) or "letter" in pt or "editorial" in pt or "comment" in pt:
        return "correspondence/editorial(來源本無摘要)"
    return "unresolved"

def resolve_one(rec, min_chars=250, mail=None, sleep=0.0, force=False):
    """原地更新單筆 rec。回傳 True=有可篩內容(have)、False=awaiting。
    force=True：即使已有 abstract 也不早停，強制實取全文（Tier 3：離題定案前須試到全文）。"""
    mail = mail or _mail()
    if not force and rec.get("abstract") and len(rec["abstract"]) >= min_chars:
        rec["content_status"] = "have"
        rec.setdefault("content_via", "abstract")
        return True
    had_abstract = bool(rec.get("abstract") and len(rec["abstract"]) >= min_chars)
    rec["abstract_checked"] = True
    doi = _norm_doi(rec.get("doi"))
    pmid = str(rec.get("pmid")) if rec.get("pmid") else None
    tried = []

    # (2) Crossref 摘要欄
    if doi:
        ab, dt = _crossref_abstract(doi, mail)
        if dt and not rec.get("ptypes"): rec["ptypes"] = [dt]
        if ab and len(ab) >= min_chars:
            rec["abstract"] = ab; rec["content_status"] = "have"; rec["content_via"] = "crossref-abstract"
            return True

    # (3) PMC fullTextXML（線上全文管道）——已進入『實抓解析全文』階段，補齊證明旗標。
    # oa_fetch_attempted 設在此（不限有 DOI）：對 PMID-only 記錄，PMC 即為其 OA 取得管道，
    # Unpaywall(DOI-based)不適用時，PMC 嘗試本身就代表已試 OA → 避免無 DOI 待評估卡守門。
    rec["online_fulltext_checked"] = True
    rec["fulltext_parse_attempted"] = True
    rec["oa_fetch_attempted"] = True
    ft = _pmc_fulltext(pmid, doi, mail)
    if ft and len(ft) >= min_chars:
        rec["fulltext_excerpt"] = ft[:8000]; rec["content_status"] = "have"; rec["content_via"] = "pmc-fulltext"
        return True

    # (4) Unpaywall 全部 oa_locations 實際下載+解析（DOI-based；無 DOI 時此管道不適用，
    #     OA 嘗試已由 (3) PMC 涵蓋）
    if doi:
        rec["unpaywall_checked"] = True
        is_oa, urls = _unpaywall_locations(doi, mail)
        rec["oa"] = is_oa
        for url in urls:
            tried.append(url)
            try:
                data, ct = _get(url, 60)
            except Exception:
                continue
            if data[:4] == b"%PDF" or (ct and "pdf" in (ct or "")):
                t = _pdf_text(data)
            else:
                try: t = _strip_tags(data.decode("utf-8", "replace"))
                except Exception: t = ""
            # 防呆：須像『真內容』(≥2 科學/方法學特徵)，否則視為 landing/cookie/paywall 牆頁、不算取得
            if _looks_like_content(t, min_chars):
                rec["fulltext_excerpt"] = t[:8000]; rec["content_status"] = "have"
                rec["content_via"] = "oa:" + (url[:80])
                rec["oa_urls_tried"] = tried
                if sleep: time.sleep(sleep)
                return True
    rec["oa_urls_tried"] = tried
    rec["channels_exhausted"] = True
    if force and had_abstract:
        # Tier 3 強制實取但取不到更長正文：保留既有 abstract 當可篩內容（已蓋實抓證明旗標）
        rec["content_status"] = "have"
        rec.setdefault("content_via", "abstract")
        if sleep: time.sleep(sleep)
        return True
    # 全部管道失敗且無既有摘要 → awaiting（已留可稽核的實抓證明）
    rec["content_status"] = "awaiting"
    rec["doc_type"] = _doc_type(rec)
    if sleep: time.sleep(sleep)
    return False

def resolve(records, min_chars=250, sleep=0.0):
    """對 records 中『尚無可篩內容』者逐筆完整實抓解析。回傳統計 dict。"""
    mail = _mail()
    have = aw = 0
    for r in records:
        # 已有內容（registry/ai_summary/have）者跳過——本工具只處理缺內容者
        if r.get("content_status") in ("registry", "ai_summary"):
            continue
        if r.get("content_status") == "have" and r.get("abstract") and len(r["abstract"]) >= min_chars:
            have += 1; continue
        ok = resolve_one(r, min_chars=min_chars, mail=mail, sleep=sleep)
        have += 1 if ok else 0
        aw += 0 if ok else 1
    return {"have": have, "awaiting": aw, "min_chars": min_chars, "mail": mail}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile")
    ap.add_argument("--min-chars", type=int, default=250)
    ap.add_argument("--sleep", type=float, default=0.0)
    a = ap.parse_args()
    recs = json.loads(Path(a.infile).read_text(encoding="utf-8"))
    if isinstance(recs, dict): recs = recs.get("records") or recs.get("papers") or []
    res = resolve(recs, min_chars=a.min_chars, sleep=a.sleep)
    out = a.outfile or a.infile
    Path(out).write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    print("fulltext_exhaust：完整實抓解析完成 → have %d、awaiting %d（min_chars=%d, mail=%s）"
          % (res["have"], res["awaiting"], res["min_chars"], res["mail"]))
    print("  awaiting 者已標 fulltext_parse_attempted/channels_exhausted/oa_urls_tried 供守門核對。")

if __name__ == "__main__":
    main()
