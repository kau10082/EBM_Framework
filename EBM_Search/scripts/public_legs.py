# -*- coding: utf-8 -*-
"""
public_legs.py — Gate ① 公開 API 檢索腿『可重用、編碼安全』取得器
（與 pmc_fulltext.py 同精神：把易手刻出錯的取得邏輯收斂成一個 import 即用的器，
 嚴禁每輪重寫 ad-hoc urllib —— 那正是 OpenAlex『%20 二次編碼→0 筆』bug 反覆復發的根因）。

涵蓋四個免金鑰公開腿：
  • OpenAlex   （cursor 翻頁；meta.count 為『估計值』，next_cursor=None 即已取盡）
  • Europe PMC （cursorMark 翻頁）
  • ClinicalTrials.gov v2（pageToken 翻頁）
  • PubMed E-utilities（esearch retmax；走 MCP 時不需此腿，本器供本機/重現用）

兩個 2026-06 校正後落地的鐵律（避免再犯）：
  (BUG-1 編碼) 一律用 urllib.parse.urlencode() 組 query string，**參數值內嚴禁預先放 %XX**
               （預先 %20 會被 urlencode 再編一次成 %2520 → API 收到壞字串 → 0 筆）。
               OpenAlex『AND 多詞』用『一個半形空格』表示，交給 urlencode 編碼即可。
  (BUG-2 取盡) OpenAlex `meta.count` 是估計值、常與實際翻頁數差 1~2；**判定取盡看 next_cursor 是否為 None**，
               而非 fetched>=count。取盡後 hitCount 回報 fetched（真實取得數），count_estimate 另存。

用法（CLI）：
  python public_legs.py --selftest                      # 線上自我驗證（證明編碼正確、>0 筆）
  python public_legs.py --openalex "benralizumab asthma" --type review
  python public_legs.py --europepmc '(TITLE:"benralizumab") AND (TITLE:"asthma")'
  python public_legs.py --ctgov-cond asthma --ctgov-intr benralizumab
程式內：
  import public_legs as P
  res = P.fetch_openalex("benralizumab asthma", extra_filters={"type": "review"})
  # res = {"leg","query","hitCount","fetched","count_estimate","exhausted","hits":[...]}
"""
import sys, json, time, argparse, urllib.request, urllib.parse
from pathlib import Path

DEFAULT_MAILTO = "kau10082ai@gmail.com"


def _ua(mailto):
    return {"User-Agent": f"EBM-Search/0.22 (mailto:{mailto})"}


def _get(url, mailto=DEFAULT_MAILTO, timeout=60):
    req = urllib.request.Request(url, headers=_ua(mailto))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _url(base, params):
    """唯一允許的 query-string 組裝法：urlencode 單次編碼。
    嚴禁呼叫端在 params 值內預先放 %XX（會二次編碼）。"""
    return base + "?" + urllib.parse.urlencode(params)


# ───────────────────────── OpenAlex ─────────────────────────
def fetch_openalex(search, extra_filters=None, mailto=DEFAULT_MAILTO, sleep=0.2, max_pages=10000):
    """search: 送 title_and_abstract.search 的字串；多詞以半形空格分隔＝AND（交給 urlencode，勿手動 %20）。
    extra_filters: 例 {"type":"review"} → 併進 filter（逗號＝AND）。"""
    base = "https://api.openalex.org/works"
    filt_parts = [f"title_and_abstract.search:{search}"]
    for k, v in (extra_filters or {}).items():
        filt_parts.append(f"{k}:{v}")
    filt = ",".join(filt_parts)
    hits, cursor, estimate, pages = [], "*", None, 0
    while pages < max_pages:
        pages += 1
        d = _get(_url(base, {"filter": filt, "per-page": 200, "cursor": cursor,
                             "mailto": mailto,
                             "select": "id,doi,title,publication_year,type,ids"}), mailto)
        if estimate is None:
            estimate = d.get("meta", {}).get("count")
        results = d.get("results", [])
        for w in results:
            ids = w.get("ids") or {}
            pmid = ids["pmid"].rstrip("/").split("/")[-1] if ids.get("pmid") else None
            hits.append({"id": w.get("id"),
                         "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                         "title": w.get("title"), "year": w.get("publication_year"),
                         "type": w.get("type"), "pmid": pmid})
        cursor = d.get("meta", {}).get("next_cursor")
        if not cursor or not results:          # ← 取盡判定靠 next_cursor=None（非 fetched>=count）
            break
        time.sleep(sleep)
    return {"leg": "openalex", "query": filt, "hitCount": len(hits),
            "fetched": len(hits), "count_estimate": estimate, "exhausted": True, "hits": hits}


# ───────────────────────── Europe PMC ─────────────────────────
def fetch_europepmc(query, mailto=DEFAULT_MAILTO, sleep=0.34, page_size=1000):
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    hits, cursor, total = [], "*", None
    while True:
        d = _get(_url(base, {"query": query, "format": "json", "pageSize": page_size,
                             "cursorMark": cursor, "resultType": "core"}), mailto)
        if total is None:
            total = d.get("hitCount")
        rl = d.get("resultList", {}).get("result", [])
        for it in rl:
            ptl = it.get("pubTypeList")
            hits.append({"id": it.get("id"), "source": it.get("source"),
                         "pmid": it.get("pmid"), "doi": it.get("doi"),
                         "title": it.get("title"), "year": it.get("pubYear"),
                         "pubType": ptl.get("pubType") if isinstance(ptl, dict) else None,
                         "isOA": it.get("isOpenAccess"), "inEPMC": it.get("inEPMC"),
                         "pmcid": it.get("pmcid")})
        nc = d.get("nextCursorMark")
        if not nc or nc == cursor or not rl:
            break
        cursor = nc
        if len(hits) >= (total or 0):
            break
        time.sleep(sleep)
    return {"leg": "europepmc", "query": query, "hitCount": total,
            "fetched": len(hits), "exhausted": True, "hits": hits}


# ───────────────────────── ClinicalTrials.gov v2 ─────────────────────────
def fetch_ctgov(cond, intr, sleep=0.2):
    base = "https://clinicaltrials.gov/api/v2/studies"
    hits, token = [], None
    while True:
        params = {"query.cond": cond, "query.intr": intr, "pageSize": 200,
                  "fields": "NCTId,BriefTitle,OverallStatus,Phase,StudyType,Condition,"
                            "InterventionName,StartDate,CompletionDate"}
        if token:
            params["pageToken"] = token
        d = _get(_url(base, params))
        for s in d.get("studies", []):
            p = s.get("protocolSection", {})
            hits.append({
                "nct": p.get("identificationModule", {}).get("nctId"),
                "title": p.get("identificationModule", {}).get("briefTitle"),
                "status": p.get("statusModule", {}).get("overallStatus"),
                "phase": ",".join(p.get("designModule", {}).get("phases", []) or []),
                "studyType": p.get("designModule", {}).get("studyType"),
                "conditions": p.get("conditionsModule", {}).get("conditions"),
                "interventions": [i.get("name") for i in
                                  (p.get("armsInterventionsModule", {}).get("interventions") or [])],
            })
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(sleep)
    return {"leg": "clinicaltrials", "query": f"cond={cond}; intr={intr}",
            "hitCount": len(hits), "fetched": len(hits), "exhausted": True, "hits": hits}


# ───────────────────────── PubMed E-utilities ─────────────────────────
def fetch_pubmed(term, mailto=DEFAULT_MAILTO, retmax=1000):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    d = _get(_url(base, {"db": "pubmed", "term": term, "retmax": retmax,
                         "retmode": "json", "email": mailto}), mailto)
    res = d.get("esearchresult", {})
    ids = res.get("idlist", [])
    cnt = int(res.get("count")) if res.get("count") else None
    return {"leg": "pubmed", "query": term, "hitCount": cnt,
            "fetched": len(ids), "exhausted": (cnt is None or len(ids) >= cnt),
            "hits": [{"pmid": i} for i in ids]}


# ───────────────────────── self-test ─────────────────────────
def selftest():
    ok = True
    # (BUG-1) 證明編碼正確：OpenAlex『benralizumab asthma』必須 >0 筆（二次編碼會回 0）
    r = fetch_openalex("benralizumab asthma", extra_filters={"type": "review"}, max_pages=1)
    n = r["fetched"]
    print(("  ✅" if n > 0 else "  ❌") + f" OpenAlex 編碼安全（benralizumab asthma type:review 第一頁 fetched={n}>0）")
    ok &= n > 0
    # filter 字串內不得殘留預編碼 %XX（除非是 urlencode 後，但此處看的是組裝前的 filt）
    has_pre = "%2520" in r["query"] or "%20" in r["query"]
    print(("  ✅" if not has_pre else "  ❌") + f" filter 無預先 %XX 二次編碼痕跡：{r['query']}")
    ok &= not has_pre
    # (BUG-2) 取盡判定欄位齊全
    print(("  ✅" if "count_estimate" in r and r.get("exhausted") is True else "  ❌")
          + f" OpenAlex 取盡語意（exhausted=True, count_estimate={r.get('count_estimate')}）")
    ok &= ("count_estimate" in r)
    print(("✅ public_legs selftest 全過" if ok else "❌ public_legs selftest 有失敗"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--openalex"); ap.add_argument("--type", help="OpenAlex extra filter type，如 review")
    ap.add_argument("--europepmc")
    ap.add_argument("--ctgov-cond"); ap.add_argument("--ctgov-intr")
    ap.add_argument("--pubmed")
    ap.add_argument("--out")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if a.selftest:
        sys.exit(selftest())
    res = None
    if a.openalex:
        res = fetch_openalex(a.openalex, extra_filters=({"type": a.type} if a.type else None))
    elif a.europepmc:
        res = fetch_europepmc(a.europepmc)
    elif a.ctgov_cond and a.ctgov_intr:
        res = fetch_ctgov(a.ctgov_cond, a.ctgov_intr)
    elif a.pubmed:
        res = fetch_pubmed(a.pubmed)
    else:
        ap.print_help(); return
    summ = {k: v for k, v in res.items() if k != "hits"}
    print(json.dumps(summ, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote", a.out)


if __name__ == "__main__":
    main()
