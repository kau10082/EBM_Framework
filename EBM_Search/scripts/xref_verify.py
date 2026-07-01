#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consensus-verify / xref_verify.py
==================================
對 Consensus 檢索結果做「來源獨立」的交叉驗證:每篇文獻分別查 Crossref 與
PubMed(E-utilities),依 verified_requires 規則綜合判定 verdict,並標記證據等級。

設計原則
--------
- 零相依:純 Python 3.8+ 標準庫(urllib / json / difflib / argparse)。
- 來源獨立:Crossref 與 PubMed 各自得出 match / soft / miss / retracted / skipped / error,
  再由 combiner 依規則合併。被略過(skipped)或出錯(error)的來源「不算數」,
  不會把另一個已 match 的來源拖下水。
- 預設規則 verified_requires = "any":PubMed 或 Crossref 任一 match 即判 VERIFIED。
  (先前的 "both" 已停用;仍可用 --verified-requires both 切回。)
- 反幻覺消歧:每個來源回傳多個候選時,取「標題相似度最高且 >= 門檻」者;
  若無人達標則判 miss,絕不硬抓同藥不同篇(例:腎功能 PK vs 肝功能 PK)。

verdict 階層(由高到低)
-----------------------
  RETRACTED    任一來源標記撤稿 → 一律最高優先
  VERIFIED     依規則達標(any:至少一個 match;both:兩個都 match)
  PARTIAL      找到接近候選但未達 match 門檻,或 both 規則下只一邊 match
  UNVERIFIED   所有「實際查詢過」的來源都 miss(查無此文)
  UNRESOLVED   沒有來源實際查到資料(全 skipped/error),或會議摘要 miss(未索引)→ 待補跑
  OFF_TOPIC    主旨不符,依政策僅做主旨剔除、未送驗證(P4)

每筆另附:
  evidence_note  次級分析/substudy 等級加註(P5)
  reason         非 VERIFIED 時的細分原因(P3:未索引/衍生性非原始/ahead-of-print/查無)

選填輸入欄位
  doc_type   conference_abstract|abstract|poster|proceedings(會議摘要,miss→UNRESOLVED)
             synopsis|comment|editorial|journal_club|letter(衍生性非原始)
  off_topic  true → 直接判 OFF_TOPIC,不查任何來源(省搜尋額度)

證據等級僅反映文獻「類型」,不代表對任何臨床主張的支持強度。

用法
----
  python xref_verify.py --in consensus.json --out verified.json --mailto you@example.com
  python xref_verify.py --in consensus.json --out verified.json --md verified.md
  python xref_verify.py --in consensus.json --no-crossref --out verified.json   # 只跑 PubMed
  python xref_verify.py --query "Phase 3 Trial of the DPP-1 Inhibitor Brensocatib in Bronchiectasis"

設定優先序(v0.5.1)
------------------
  CLI 旗標 > 環境變數 > config/settings.yaml > 內建預設。
  金鑰建議走環境變數:NCBI_API_KEY(PubMed E-utilities 提速)、CROSSREF_MAILTO(polite pool)。
  設定檔預設讀 <script>/../config/settings.yaml(存在才讀);--config 可指定路徑,--no-config 可略過。
  讀檔用內建極簡 YAML parser,維持零相依(不需 pyyaml)。

輸入欄位(每筆)
  必填:title
  選填:id, year, doi, first_author(或 authors=[...])
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

CROSSREF_WORKS = "https://api.crossref.org/works"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "with", "without", "and", "or",
    "to", "from", "by", "vs", "versus", "study", "trial", "trials", "analysis",
    "adults", "adult", "patients", "patient", "randomised", "randomized",
    "double", "blind", "placebo", "controlled", "phase", "data", "effects",
    "effect", "using", "their", "into", "via",
}

CURRENT_YEAR = datetime.date.today().year

# --- P5：次級分析／substudy 標記(標題語意)。命中時不改 evidence_level 本身,
#         只加 evidence_note 提醒「主療效證據力低於原始主試驗」。
_SUBSTUDY = re.compile(
    r"\b(post[\s-]?hoc|secondary analysis|sub[\s-]?study|exploratory analysis|"
    r"pooled analysis|subgroup analysis|biomarker|multi[\s-]?omics|"
    r"immunomodulatory|mechanistic|data from the .+trial|analysis of the .+trial)\b",
    re.I)

# --- P2/P3：會議摘要 / 衍生性非原始文獻的 doc_type 提示值(由呼叫端依 Consensus
#           的期刊/型態填入;script 也會用 Crossref type 做輔助偵測)。
_ABSTRACT_DOCTYPES = {"conference_abstract", "abstract", "poster", "proceedings"}
_DERIVATIVE_DOCTYPES = {"synopsis", "comment", "editorial", "journal_club", "letter"}
_ABSTRACT_CR_TYPES = {"proceedings-article", "posted-content"}

# ----------------------------------------------------------------------------- helpers

def _norm_title(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"&[a-z]+;", " ", s)            # html entities
    s = re.sub(r"[^a-z0-9 ]+", " ", s)          # drop punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sim(a, b):
    return SequenceMatcher(None, _norm_title(a), _norm_title(b)).ratio()


def _year_of(s):
    if s is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(s))
    return int(m.group(0)) if m else None


def _http_get(url, headers=None, retries=3, timeout=20):
    headers = headers or {}
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                        # noqa: BLE001
            last = e
            time.sleep(2 ** i)                         # exponential backoff
    raise last


# ----------------------------------------------------------------------------- 連線探測(preflight)

def crossref_available(mailto, timeout=6):
    """快速探測 Crossref 是否可用(已知 DOI heartbeat,單次嘗試)。"""
    headers = {"User-Agent": "consensus-verify/1.0 (mailto:%s)" % (mailto or "anon@example.com")}
    try:
        # 注意:單篇 /works/{DOI} endpoint 不支援 select 參數(會回 400);
        # select 僅用於列表 endpoint /works?query=...。心跳只查裸 DOI 即可。
        _http_get("%s/10.1056/NEJMoa2021713" % CROSSREF_WORKS,
                  headers, retries=1, timeout=timeout)
        return True
    except Exception:                                 # noqa: BLE001
        return False


def pubmed_available(api_key, timeout=6):
    """快速探測 PubMed E-utilities 是否可用(最小 esearch,單次嘗試)。"""
    params = _eutils_params({"term": "bronchiectasis", "retmax": "1"}, api_key)
    url = "%s/esearch.fcgi?%s" % (EUTILS, urllib.parse.urlencode(params))
    try:
        _http_get(url, retries=1, timeout=timeout)
        return True
    except Exception:                                 # noqa: BLE001
        return False


def resolve_sources(args):
    """依 --source-mode 與連線探測,決定本次跑哪些來源。
    回傳 (use_crossref, use_pubmed, info)。--no-* 為硬性覆蓋,優先於探測。"""
    info = {"mode": args.source_mode, "probe": None}
    # 硬性覆蓋:任一 --no-* 一出現,就不做 auto 探測,直接照旗標
    if args.no_crossref or args.no_pubmed:
        info["mode"] = "manual"
        return (not args.no_crossref), (not args.no_pubmed), info
    if args.source_mode == "both":
        return True, True, info
    if args.source_mode == "pubmed-only":
        return False, True, info
    if args.source_mode == "crossref-only":
        return True, False, info
    # ---- auto:先確認 Crossref 是否可用 ----
    cr_ok = crossref_available(args.mailto)
    pm_ok = pubmed_available(args.ncbi_api_key)
    info["probe"] = {"crossref": cr_ok, "pubmed": pm_ok}
    if cr_ok and pm_ok:
        info["resolved"] = "both"
        return True, True, info
    if (not cr_ok) and pm_ok:
        info["resolved"] = "pubmed-only (Crossref 不可用,自動退回單用 PubMed)"
        return False, True, info
    if cr_ok and (not pm_ok):
        info["resolved"] = "crossref-only (PubMed 不可用)"
        return True, False, info
    info["resolved"] = "none reachable (兩來源皆不可用 → 全部 UNRESOLVED)"
    return False, False, info


def _first_author_last(rec):
    fa = rec.get("first_author")
    if fa:
        fa = fa.strip()
        if "," in fa:
            return fa.split(",")[0].strip()
        return fa.split()[0] if fa.split() else ""
    auth = rec.get("authors")
    if isinstance(auth, list) and auth:
        a0 = auth[0]
        if isinstance(a0, dict):
            return a0.get("last") or a0.get("last_name") or ""
        if isinstance(a0, str):
            return (a0.split(",")[0].split() or [""])[0]   # " "/"," 等髒值不可 IndexError 讓整批中止
    return ""


# ----------------------------------------------------------------------------- evidence level

_TITLE_L1 = re.compile(r"\b(systematic review|meta-?analysis|network meta-?analysis)\b", re.I)
_TITLE_L2 = re.compile(r"\b(randomi[sz]ed controlled trial|phase\s*[1-4iv]+\b.*trial|double-?blind.*randomi[sz]ed)\b", re.I)
_TITLE_L4 = re.compile(r"\b(cohort|case-?control|observational|cross-?sectional|registry)\b", re.I)
_TITLE_L5 = re.compile(r"\b(review|guideline|consensus statement|narrative)\b", re.I)


def evidence_level(pubtypes, title):
    """pubtype 優先;缺乏分型標籤時退回標題語意 fallback。
    回傳 (level, note):level 僅反映文獻「類型」;若偵測到次級分析/substudy,
    note 會提醒此為衍生分析、主療效證據力低於原始主試驗(P5)。"""
    pts = {p.lower() for p in (pubtypes or [])}
    level = None
    if "systematic review" in pts or "meta-analysis" in pts:
        level = "L1"
    elif "randomized controlled trial" in pts:
        level = "L2"
    elif any(("clinical trial, phase %s" % n) in pts for n in ("i", "ii", "iii", "iv")):
        level = "L2"
    elif "clinical trial" in pts:
        level = "L3"
    elif "observational study" in pts or "comparative study" in pts:
        level = "L4"
    elif "practice guideline" in pts or "guideline" in pts:
        level = "L5"
    elif "review" in pts:
        level = "L5"
    if level is None:
        # ---- title fallback ----
        t = title or ""
        if _TITLE_L1.search(t):
            level = "L1"
        elif _TITLE_L2.search(t):
            level = "L2"
        elif _TITLE_L4.search(t):
            level = "L4"
        elif _TITLE_L5.search(t):
            level = "L5"
        else:
            level = "未分類"
    # ---- P5：次級分析/substudy 加註(不改 level) ----
    note = None
    if level in ("L1", "L2", "L3") and _SUBSTUDY.search(title or ""):
        note = "次級分析/substudy:等級僅反映文獻類型,對主療效問題的證據力低於原始主試驗,引用時宜降階看待"
    return level, note


# ----------------------------------------------------------------------------- Crossref leg

def _crossref_candidate(msg):
    title = (msg.get("title") or [""])[0]
    year = None
    issued = msg.get("issued", {}).get("date-parts", [[None]])
    if issued and issued[0]:
        year = issued[0][0]
    retracted = (msg.get("type") == "retraction") or (msg.get("subtype") == "retraction")
    for u in (msg.get("update-to") or []):
        if "retract" in (u.get("type", "") + u.get("label", "")).lower():
            retracted = True
    return {"title": title, "year": year, "doi": msg.get("DOI"),
            "type": msg.get("type"), "retracted": retracted}


def crossref_check(rec, mailto, title_threshold, soft_threshold, year_tol, rows):
    title = rec.get("title", "")
    want_year = _year_of(rec.get("year"))
    headers = {"User-Agent": "consensus-verify/1.0 (mailto:%s)" % (mailto or "anon@example.com")}
    try:
        doi = (rec.get("doi") or "").strip()
        if doi:
            url = "%s/%s" % (CROSSREF_WORKS, urllib.parse.quote(doi))
            msg = json.loads(_http_get(url, headers))["message"]
            cand = _crossref_candidate(msg)
        else:
            params = {
                "query.bibliographic": "%s %s" % (title, _first_author_last(rec)),
                "rows": str(rows),
                # 注意:/works 列表路由的 select 不支援 'subtype'(會回 400
                # validation-failure → 整個 Crossref leg 變 error)。撤稿改靠
                # 'type'=='retraction' 與 'update-to' 標籤偵測即可;subtype 僅在
                # 單篇 /works/{DOI} 裸 GET(上面 if doi 分支)才拿得到、不受此限。
                "select": "DOI,title,issued,type,update-to",
            }
            if mailto:
                params["mailto"] = mailto
            url = "%s?%s" % (CROSSREF_WORKS, urllib.parse.urlencode(params))
            items = json.loads(_http_get(url, headers))["message"].get("items", [])
            cands = [_crossref_candidate(it) for it in items]
            cand = _best(cands, title)
        return _grade(cand, title, want_year, title_threshold, soft_threshold, year_tol)
    except Exception as e:                            # noqa: BLE001
        return {"status": "error", "detail": str(e)[:120]}


# ----------------------------------------------------------------------------- PubMed leg

def _pm_formulations(rec):
    title = rec.get("title", "")
    fa = _first_author_last(rec)
    yr = _year_of(rec.get("year"))
    words = [w for w in _norm_title(title).split() if w not in STOPWORDS and len(w) > 2]
    title_words = " ".join(words[:8])
    forms = []
    if fa and yr and title_words:
        forms.append("%s[Author] AND %s[Title] AND %s[pdat]" % (fa, title_words, yr))
    if title_words:
        forms.append("%s[Title]" % title_words)
    if fa and yr:
        forms.append("%s[Author] AND %s[pdat]" % (fa, yr))
    return forms


def _eutils_params(extra, api_key):
    p = {"db": "pubmed", "retmode": "json"}
    p.update(extra)
    if api_key:
        p["api_key"] = api_key
    return p


def _esearch(term, retmax, api_key):
    params = _eutils_params({"term": term, "retmax": str(retmax), "sort": "relevance"}, api_key)
    url = "%s/esearch.fcgi?%s" % (EUTILS, urllib.parse.urlencode(params))
    data = json.loads(_http_get(url))
    return data.get("esearchresult", {}).get("idlist", [])


def _esummary(pmids, api_key):
    params = _eutils_params({"id": ",".join(pmids)}, api_key)
    url = "%s/esummary.fcgi?%s" % (EUTILS, urllib.parse.urlencode(params))
    data = json.loads(_http_get(url)).get("result", {})
    return {pid: data[pid] for pid in data.get("uids", [])}


def pubmed_check(rec, api_key, title_threshold, soft_threshold, year_tol, candidates):
    title = rec.get("title", "")
    want_year = _year_of(rec.get("year"))
    try:
        pmids = []
        for q in _pm_formulations(rec):
            pmids = _esearch(q, candidates, api_key)
            if pmids:
                break
        if not pmids:
            return {"status": "miss", "detail": "no esearch hit"}
        summaries = _esummary(pmids, api_key)
        cands = []
        for pid, s in summaries.items():
            cands.append({
                "title": s.get("title", ""),
                "year": _year_of(s.get("pubdate")),
                "pmid": pid,
                "pubtypes": s.get("pubtype", []),
                "retracted": any("retract" in str(pt).lower() for pt in s.get("pubtype", [])),
            })
        cand = _best(cands, title)
        graded = _grade(cand, title, want_year, title_threshold, soft_threshold, year_tol)
        if cand:
            graded["pmid"] = cand.get("pmid")
            graded["pubtypes"] = cand.get("pubtypes", [])
        return graded
    except Exception as e:                            # noqa: BLE001
        return {"status": "error", "detail": str(e)[:120]}


# ----------------------------------------------------------------------------- grading / combine

def _best(cands, title):
    """取標題相似度最高者;無候選回 None。門檻判定留給 _grade。"""
    cands = [c for c in cands if c and c.get("title")]
    if not cands:
        return None
    return sorted(cands, key=lambda c: _sim(title, c["title"]), reverse=True)[0]


def _grade(cand, title, want_year, title_threshold, soft_threshold, year_tol):
    if not cand:
        return {"status": "miss", "detail": "no candidate"}
    if cand.get("retracted"):
        return {"status": "retracted", "title": cand.get("title"),
                "doi": cand.get("doi"), "pmid": cand.get("pmid")}
    sim = _sim(title, cand.get("title", ""))
    year_ok = True
    if want_year and cand.get("year"):
        year_ok = abs(int(cand["year"]) - want_year) <= year_tol
    out = {"title": cand.get("title"), "year": cand.get("year"),
           "doi": cand.get("doi"), "similarity": round(sim, 3)}
    if cand.get("type"):
        out["type"] = cand.get("type")
    if sim >= title_threshold and year_ok:
        out["status"] = "match"
    elif sim >= soft_threshold:
        out["status"] = "soft"
        if not year_ok:
            out["detail"] = "year mismatch"
    else:
        out["status"] = "miss"
    return out


def combine(sources, verified_requires):
    """sources: {'crossref': {...}, 'pubmed': {...}} → verdict 字串。"""
    statuses = {k: v.get("status") for k, v in sources.items()}
    if "retracted" in statuses.values():
        return "RETRACTED"
    attempted = {k: s for k, s in statuses.items() if s in ("match", "soft", "miss")}
    matches = [k for k, s in attempted.items() if s == "match"]
    softs = [k for k, s in attempted.items() if s == "soft"]

    if not attempted:
        return "UNRESOLVED"                 # 全 skipped / error → 待補跑
    if verified_requires == "both":
        if len(matches) >= 2:
            return "VERIFIED"
        if matches or softs:
            return "PARTIAL"
        return "UNVERIFIED"
    # default: any
    if matches:
        return "VERIFIED"
    if softs:
        return "PARTIAL"
    return "UNVERIFIED"


def classify_reason(rec, sources, verdict):
    """P2+P3:為非 VERIFIED 的結果標 reason,並把『會議摘要的 PubMed miss』
    由 UNVERIFIED 轉判 UNRESOLVED(待 Crossref 定案,而非『查無此文』)。
    回傳 (new_verdict, reason)。doc_type 由呼叫端提供;另用 Crossref type 輔助偵測。"""
    doc_type = (rec.get("doc_type") or "").strip().lower()
    cr_type = (sources.get("crossref", {}) or {}).get("type", "")
    is_abstract = (doc_type in _ABSTRACT_DOCTYPES) or (cr_type in _ABSTRACT_CR_TYPES)
    is_derivative = doc_type in _DERIVATIVE_DOCTYPES

    if verdict == "UNRESOLVED":
        # 全 skipped/error:沒有任何來源實際查到
        return verdict, "no_source_queried:全 skipped/error,待補跑"

    if verdict != "UNVERIFIED":
        return verdict, None

    # ---- 以下處理 UNVERIFIED(實際查過但 miss)的細分 ----
    if is_abstract:
        # 會議摘要 PubMed 多無索引 → 不是『不存在』,是『未索引』。改判 UNRESOLVED 待 Crossref。
        return "UNRESOLVED", "not_indexed:conference_abstract(PubMed未索引,待Crossref定案)"
    if is_derivative:
        return verdict, "derivative_non_original:衍生性文獻(摘要評論/評論/社論等),非原始研究"
    yr = _year_of(rec.get("year"))
    if yr and yr >= CURRENT_YEAR:
        return verdict, "ahead_of_print/not_indexed?:出版年為當年度,疑尚未被索引,建議Crossref/本機複查"
    return verdict, "not_found:已實際查詢仍無相符文獻(疑幻覺引用或書目有誤)"


# ----------------------------------------------------------------------------- driver

def verify_record(rec, args):
    # ---- P4:主旨不符者免全驗,直接短路(不查任何來源,省搜尋額度) ----
    if rec.get("off_topic"):
        return {
            "id": rec.get("id"),
            "input": {"title": rec.get("title"), "year": _year_of(rec.get("year")),
                      "doi": rec.get("doi"), "first_author": _first_author_last(rec)},
            "verdict": "OFF_TOPIC",
            "evidence_level": "未分類",
            "evidence_note": None,
            "reason": "off_topic:主旨不符,依政策僅做主旨剔除、未送驗證",
            "resolved_doi": rec.get("doi"),
            "resolved_pmid": None,
            "sources": {},
        }

    sources = {}
    if args.no_crossref:
        sources["crossref"] = {"status": "skipped"}
    else:
        sources["crossref"] = crossref_check(
            rec, args.mailto, args.title_threshold, args.soft_threshold,
            args.year_tolerance, args.pm_candidates)
    if args.no_pubmed:
        sources["pubmed"] = {"status": "skipped"}
    else:
        sources["pubmed"] = pubmed_check(
            rec, args.ncbi_api_key, args.title_threshold, args.soft_threshold,
            args.year_tolerance, args.pm_candidates)

    verdict = combine(sources, args.verified_requires)
    verdict, reason = classify_reason(rec, sources, verdict)   # P2/P3
    pub = sources.get("pubmed", {})
    lvl, lvl_note = evidence_level(pub.get("pubtypes"), rec.get("title"))   # P5
    # resolved_doi/pmid 只採信「確實匹配上」的來源（match/retracted）。soft/miss 是未達門檻的候選，
    # _grade 仍會帶其 doi/pmid（行 394 先填、405 miss 不清），若採信會把『同藥不同篇』的錯誤 ID
    # 當定案外洩給下游抓全文/去重/匯入。輸入自帶 doi（rec）仍保留（那是被驗證的引用本身）。
    def _confirmed(src, key):
        return src.get(key) if isinstance(src, dict) and src.get("status") in ("match", "retracted") else None
    _cr = sources.get("crossref", {})
    # 輸入自帶 DOI 若被 Crossref『以該 DOI 直查』判 miss（指向論文的標題與記錄不符）＝疑手填錯 DOI：
    # 不可原樣冠上 verdict 外洩（下游 fulltext_fetch 優先用 resolved_doi 會抓到不相干論文的全文）。
    # 此時優先採「確實匹配上」來源解析出的 DOI；無則保留但標 doi_suspect 供 ⑤a 稽核/人工修正。
    rec_doi = rec.get("doi")
    doi_suspect = bool(rec_doi and isinstance(_cr, dict) and _cr.get("status") == "miss"
                       and str(_cr.get("doi") or "").lower().strip() == str(rec_doi).lower().strip())
    if doi_suspect:
        resolved_doi = _confirmed(_cr, "doi") or _confirmed(pub, "doi") or rec_doi
    else:
        resolved_doi = rec_doi or _confirmed(_cr, "doi") or _confirmed(pub, "doi")
    return {
        **({"doi_suspect": True} if doi_suspect else {}),
        "id": rec.get("id"),
        "input": {"title": rec.get("title"), "year": _year_of(rec.get("year")),
                  "doi": rec.get("doi"), "first_author": _first_author_last(rec)},
        "verdict": verdict,
        "evidence_level": lvl,
        "evidence_note": lvl_note,
        "reason": reason,
        "resolved_doi": resolved_doi,
        "resolved_pmid": _confirmed(pub, "pmid"),
        "sources": sources,
    }


def load_input(args):
    if args.query:
        return [{"title": args.query}]
    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("items") or data.get("results")
        if not isinstance(data, list):
            sys.exit("輸入檔沒有可辨識的紀錄清單（預期頂層 list 或 items/results 鍵）：%s"
                     "——餵錯檔不可靜默空跑寫出空 verified.json" % args.infile)
    return data


def to_markdown(results):
    head = ("| # | 標題 | 年 | verdict | 證據等級 | resolved DOI | PMID | reason/note |\n"
            "|---|---|---|---|---|---|---|---|\n")
    rows = []
    for i, r in enumerate(results, 1):
        note = r.get("reason") or r.get("evidence_note") or ""
        rows.append("| %d | %s | %s | %s | %s | %s | %s | %s |" % (
            i, (r["input"]["title"] or "")[:70], r["input"]["year"] or "",
            r["verdict"], r["evidence_level"], r["resolved_doi"] or "",
            r["resolved_pmid"] or "", note[:80]))
    return head + "\n".join(rows) + "\n"


def _coerce(v):
    """把設定檔/環境變數的字串值轉成 bool/int/float/str(金鑰類請勿經此函式)。"""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _strip_inline_comment(line):
    """移除「不在引號內」的 # 之後內容。"""
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def default_settings_path():
    """決定 settings.yaml 路徑(整個 EBM_Framework 共用)。順序:
      1) 環境變數 EBM_CONFIG(絕對路徑);
      2) 根 config:  <script>/../../config/settings.yaml  ＝ EBM_Framework/config(平常用這個);
      3) 本地回退:    <script>/../config/settings.yaml      ＝ EBM_Search/config(打包安裝、看不到根 config 時)。
    回傳第一個存在者;皆不存在則回根路徑(讓上層自行判 not exists)。"""
    env = os.environ.get("EBM_CONFIG")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, "..", "..", "config", "settings.yaml"))   # EBM_Framework/config
    local = os.path.normpath(os.path.join(here, "..", "config", "settings.yaml"))         # EBM_Search/config(legacy)
    if os.path.exists(root):
        return root
    if os.path.exists(local):
        return local
    return root


def load_settings(path):
    """零相依極簡 YAML 讀取器:僅支援本專案 settings.yaml 的兩層 'key: value' 結構。
    不支援清單/多行字串/錨點;無法解析者略過。回傳 {section: {key: value}} 巢狀 dict。"""
    data, section = {}, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return data
    for raw in lines:
        line = _strip_inline_comment(raw.rstrip("\n"))
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if ":" not in body:
            continue
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if indent == 0:
            if val == "":
                section = key
                data.setdefault(section, {})
            else:
                data[key] = _coerce(val)
                section = None
        else:
            if section is None:
                continue
            data[section][key] = _coerce(val)
    return data


def resolve_config(args):
    """以「CLI 旗標 > 環境變數 > settings.yaml > 內建預設」決定最終參數,就地寫回 args。
    僅在對應 CLI 旗標未明確給定(None)時,才回退 env / 設定檔。"""
    builtin = {
        "mailto": "", "ncbi_api_key": "", "source_mode": "auto",
        "title_threshold": 0.85, "soft_threshold": 0.65, "year_tolerance": 1,
        "pm_candidates": 5, "verified_requires": "any", "drop_unverified": False,
    }
    cfg = {}
    if not getattr(args, "no_config", False):
        path = args.config or default_settings_path()
        if os.path.exists(path):
            cfg = load_settings(path)
            sys.stderr.write("settings: loaded %s\n" % os.path.normpath(path))

    def fromfile(section, key):
        sec = cfg.get(section)
        if isinstance(sec, dict) and key in sec:
            return sec[key]
        return None

    env = os.environ
    # arg 名 -> (環境變數名 or None, (設定檔 section, key))
    spec = {
        "mailto": ("CROSSREF_MAILTO", ("crossref", "mailto")),
        "ncbi_api_key": ("NCBI_API_KEY", ("pubmed", "ncbi_api_key")),
        "source_mode": (None, ("source", "mode")),
        "title_threshold": (None, ("matching", "title_threshold")),
        "soft_threshold": (None, ("matching", "soft_threshold")),
        "year_tolerance": (None, ("matching", "year_tolerance")),
        "pm_candidates": (None, ("pubmed", "candidates")),
        "verified_requires": (None, ("verdict", "verified_requires")),
        "drop_unverified": (None, ("verdict", "drop_unverified")),
    }
    for name, (envvar, (sec, key)) in spec.items():
        if getattr(args, name, None) is not None:
            continue                                  # CLI 明確給定 → 最優先
        val = None
        if envvar and env.get(envvar):                # 其次:環境變數(放金鑰最佳;不經 _coerce)
            val = env[envvar]
        if val is None:
            val = fromfile(sec, key)                  # 再其次:設定檔
        if val is None or val == "":
            val = builtin[name]                       # 最後:內建預設(空字串視同未設)
        setattr(args, name, val)

    if args.source_mode not in ("auto", "both", "pubmed-only", "crossref-only"):
        args.source_mode = "auto"
    return args


def _force_utf8_console():
    """Windows 主控台預設 cp950，印中文 reason/log 會亂碼;強制 UTF-8。
    stdout/stderr 非 TextIOWrapper(被重導向/管線)時 reconfigure 不存在 → 安全略過。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _force_utf8_console()
    ap = argparse.ArgumentParser(description="Consensus 結果交叉驗證(Crossref + PubMed)")
    ap.add_argument("--in", dest="infile", help="輸入 JSON(list 或 {items:[...]})")
    ap.add_argument("--query", help="臨時驗證單筆標題(免檔案)")
    ap.add_argument("--out", help="輸出 JSON 路徑(預設 stdout)")
    ap.add_argument("--md", help="另存 markdown 表格路徑")
    ap.add_argument("--config", dest="config",
                    help="設定檔路徑(YAML);預設 <script>/../config/settings.yaml(存在才讀)")
    ap.add_argument("--no-config", dest="no_config", action="store_true",
                    help="略過設定檔,只用 CLI 旗標與內建預設")
    ap.add_argument("--mailto", default=None, help="Crossref polite pool 用 email(亦可 env CROSSREF_MAILTO)")
    ap.add_argument("--ncbi-api-key", dest="ncbi_api_key", default=None,
                    help="NCBI API key(可選,亦可 env NCBI_API_KEY)")
    ap.add_argument("--source-mode", dest="source_mode",
                    choices=["auto", "both", "pubmed-only", "crossref-only"], default=None,
                    help="來源選擇:auto=先探測 Crossref,通則雙源、不通則自動退回單用 PubMed(預設 auto)")
    ap.add_argument("--no-pubmed", action="store_true", help="硬性略過 PubMed leg(覆蓋 source-mode)")
    ap.add_argument("--no-crossref", action="store_true", help="硬性略過 Crossref leg(覆蓋 source-mode)")
    ap.add_argument("--title-threshold", dest="title_threshold", type=float, default=None,
                    help="判定 match 的標題相似度門檻(預設 0.85)")
    ap.add_argument("--soft-threshold", dest="soft_threshold", type=float, default=None,
                    help="判定 soft(PARTIAL)的相似度下限(預設 0.65)")
    ap.add_argument("--year-tolerance", dest="year_tolerance", type=int, default=None,
                    help="年份容差(預設 ±1)")
    ap.add_argument("--pm-candidates", dest="pm_candidates", type=int, default=None,
                    help="每來源取回候選數,用於消歧(預設 5)")
    ap.add_argument("--verified-requires", dest="verified_requires",
                    choices=["any", "both"], default=None,
                    help="VERIFIED 條件:any=任一來源(預設)/ both=兩來源皆需")
    ap.add_argument("--drop-unverified", dest="drop_unverified",
                    action="store_const", const=True, default=None,
                    help="輸出時濾除 UNVERIFIED / UNRESOLVED")
    args = ap.parse_args(argv)

    if not args.infile and not args.query:
        ap.error("需指定 --in 檔案或 --query 單筆")

    # --- 設定解析:CLI 旗標 > 環境變數 > settings.yaml > 內建預設 ---
    resolve_config(args)

    # --- 前置:連線探測,決定本次來源 ---
    use_cr, use_pm, mode_info = resolve_sources(args)
    args.no_crossref = not use_cr
    args.no_pubmed = not use_pm
    sys.stderr.write("source-mode: %s | crossref=%s pubmed=%s%s\n" % (
        mode_info["mode"], use_cr, use_pm,
        (" | " + mode_info["resolved"]) if mode_info.get("resolved") else ""))

    records = load_input(args)
    results = []
    for rec in records:
        if isinstance(rec, str):
            rec = {"title": rec}
        results.append(verify_record(rec, args))

    if args.drop_unverified:
        results = [r for r in results if r["verdict"] not in ("UNVERIFIED", "UNRESOLVED")]

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"verified_requires": args.verified_requires,
               "run_mode": {"crossref": use_cr, "pubmed": use_pm, **mode_info},
               "summary": counts, "results": results}

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write("wrote %s (%s)\n" % (args.out, counts))
    else:
        print(text)

    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(to_markdown(results))
        sys.stderr.write("wrote %s\n" % args.md)


if __name__ == "__main__":
    main()
