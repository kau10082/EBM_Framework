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

判定：依序試 PMC fullTextXML → Unpaywall best/oa_locations PDF(瀏覽器 UA)；以 _is_real_fulltext
      （≥12000 字元＋≥3 個章節/統計特徵）判『真全文』——排除中繼資料著陸頁假通過。
      --min-chars 只是額外下限（低於 12000 時實質由 _is_real_fulltext 決定）。
      整體網路不可用時 fail-closed：exit 3、不回寫，**不得把整批 have 誤判為假 have**。

用法：python verify_have_fetchable.py --in <papers.json|corpus_seed> [--min-chars 3000] [--only-included]
程式內：import verify_have_fetchable as v; res = v.verify(papers)
"""
import sys, re, json, argparse, urllib.request, urllib.parse, time
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
    # 1) PMC fullTextXML -> NCBI efetch(db=pmc) via pmc_fulltext.NcbiClient
    if pmid:
        try:
            import pmc_fulltext
            mailto, api_key = pmc_fulltext.resolve_credentials()
            cli = pmc_fulltext.NcbiClient(mailto=mailto or "ebm_bot@example.com", api_key=api_key)
            pmcids = cli.idconv_pmcids([pmid])
            pmcid = pmcids.get(str(pmid))
            if not pmcid:
                u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:%s%%20AND%%20SRC:MED"
                     "&format=json&resultType=core&pageSize=1" % pmid)
                r = (json.loads(_get(u, 25).decode("utf-8", "replace"))["resultList"]["result"] or [{}])[0]
                pmcid = r.get("pmcid")
            if pmcid:
                t = cli.fetch_pmc_body(pmcid)
                if t and _is_real_fulltext(t): return len(t), "pmc"
        except Exception:
            pass
    # 2) Unpaywall best + 所有 oa_locations（PDF 抽文字 / HTML 取內文，皆過 _is_real_fulltext）
    doi = _norm_doi(doi)
    if doi:
        try:
            import pmc_fulltext
            mailto, _ = pmc_fulltext.resolve_credentials()
            email_param = urllib.parse.quote(mailto or "ebm_bot@example.com")
            d = json.loads(_get("https://api.unpaywall.org/v2/" + urllib.parse.quote(doi) + "?email=" + email_param, 25).decode("utf-8", "replace"))
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
    if isinstance(obj, list):          # 頂層 list 也是合法輸入（docstring 明示 papers.json|corpus_seed）
        return obj
    if isinstance(obj, dict):
        v = obj.get("papers")
        if isinstance(v, list):
            return v
    sys.exit("輸入檔沒有可辨識的 papers（預期頂層 list 或 papers 鍵）：%s" % path)


def _write_back(path, papers):
    """把 verify() 蓋好的 fulltext_verified（與降階 need_supplement）回寫原檔，保留外層 wrapper。
    （否則本器只在記憶體改 papers，gate_guard.check_have_verified 讀檔仍見不到 fulltext_verified→
    『跑了 verify 卻過不了守門』；2026-06 使用者實測缺失。可用 --no-write 關閉。）"""
    p = Path(path)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and isinstance(obj.get("papers"), list):
        obj["papers"] = papers
    else:
        obj = papers
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

def _network_ok(timeout=10):
    """整體連線探測：全斷網時不得開驗——否則整批 have(online) 會被抓不到而集體誤判假 have。"""
    try:
        _get("https://api.crossref.org/types", timeout)
        return True
    except urllib.error.HTTPError:
        return True    # 伺服器有回應＝網路可用
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--min-chars", type=int, default=3000,
                    help="額外字元下限；實際『真全文』判定以 _is_real_fulltext（≥12000＋章節特徵）為準")
    ap.add_argument("--only-included", action="store_true")
    ap.add_argument("--no-write", action="store_true", help="只驗不回寫（預設會把 fulltext_verified 回寫原檔）")
    a = ap.parse_args()
    papers = _load_papers(a.infile)
    if not _network_ok():
        sys.exit("❌ 網路不可用（Crossref 連線探測失敗）：不執行實抓驗證、不回寫——"
                 "斷網跑一次會把整批 have 誤判為假 have（fail-closed）")
    res = verify(papers, min_chars=a.min_chars, only_included=a.only_included)
    if not a.no_write:
        _write_back(a.infile, papers)   # 回寫 fulltext_verified，讓 gate_guard 讀得到（否則白驗）
    print("verify_have_fetchable：實抓驗證 %d 筆 have(online)；通過 %d、假 have %d%s"
          % (res["checked"], res["ok"], len(res["false_have"]), "" if a.no_write else "（已回寫原檔）"))
    for f in res["false_have"]:
        print("  ❌ 假 have（判有全文但實抓不到，應改 need-supplement）：%s | pmid=%s | doi=%s | 取回 %d 字元 | %s"
              % (f["paper_id"], f["pmid"], f["doi"], f["chars"], f["title"]))
    if res["false_have"]:
        sys.exit(1)
    print("✅ 所有 have(online) 均實抓得到全文（過 _is_real_fulltext 真全文判定）。")

if __name__ == "__main__":
    main()
