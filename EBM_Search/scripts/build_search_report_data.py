# -*- coding: utf-8 -*-
"""
build_search_report_data.py — 由 cache 確定性組出 5 段報告資料 JSON（_search_report.json）
================================================================================================
讀 v0.22 cache（g0_strategy / g1_legs_manifest / g1_union / g2b_screen / g3_FINAL_screen /
g4_citation / g6_verified / g7_units / g1_api_legs）＋可選 g7_base_srma.json（模式B base 候選），
**確定性**組出 build_search_report.py 要的 5 段資料 JSON。嚴禁手拼 _search_report.json——一律走本器。

5 段：① 檢索基本參數 ② 完整檢索字串(逐字) ③ PRISMA 流程數字 ④ 納入證據清單(只核心，欄位＝
作者/年份/文獻類型｜標題｜DOI｜PMID｜驗證) ⑤ 進行中試驗(NCT｜標題)。背景不列表。

用法：python build_search_report_data.py --cache <dir> --out <dir>/_search_report.json [--mailto x@y]
"""
import os, sys, json, argparse, re, time, urllib.request, urllib.parse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _http(url, mailto, pause=0.34, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EBM-Framework/0.22 (mailto:%s)" % mailto})
            with urllib.request.urlopen(req, timeout=60) as r:
                time.sleep(pause); return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1.0 + i)
    return None

def _load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

DESIGN2TYPE = [   # design 關鍵字 → 文獻類型標籤（順序敏感）
    ("SR/MA/NMA/ITC", "NMA/MA"), ("會議摘要", "會議摘要"), ("指引", "指引"),
    ("綜述", "綜述"), ("經濟", "經濟評估"), ("他病", "他病族群研究"),
    ("多生物製劑", "多藥真實世界世代"), ("直接比較", "真實世界直接對照"), ("原始研究", "原始研究"),
]
def doctype_of(design, override=None):
    if override: return override
    for k, v in DESIGN2TYPE:
        if k in (design or ""): return v
    return "研究"

def build_data(cache, mailto):
    cache = Path(cache)
    g0 = _load(cache / "g0_strategy.json") or {}
    legs = _load(cache / "g1_legs_manifest.json") or []
    union = _load(cache / "g1_union.json") or {}
    g2b = _load(cache / "g2b_screen.json") or {}
    g3 = _load(cache / "g3_FINAL_screen.json") or []
    g4 = _load(cache / "g4_citation.json") or {}
    g6 = _load(cache / "g6_verified.json") or {}
    g7 = _load(cache / "g7_units.json") or {}
    api = _load(cache / "g1_api_legs.json") or {}
    base_srma = _load(cache / "g7_base_srma.json") or []   # 模式B base 候選（run 寫；無則空）

    # g7 一律經 classify_units.records_of 讀（相容產出端 rows/unit 與舊 records/role 形狀；防契約飄移使核心清單靜默歸零）
    from classify_units import records_of
    g7recs = records_of(g7)
    if (isinstance(g7, dict) and g7 and "rows" not in g7 and "records" not in g7):
        raise ValueError("g7_units.json 形狀無法辨識（無 rows/records 鍵）：請用 classify_units.py 重產，"
                         "不可讓報告在核心 0＋背景 0 的空清單上靜默產出")
    core = [r for r in g7recs if r.get("role") == "core"]
    bg = [r for r in g7recs if r.get("role") == "background"]
    aw = [r for r in g7recs if r.get("role") == "awaiting"]
    g6recs = g6.get("records", []) if isinstance(g6, dict) else (g6 or [])
    def _nd(d):
        d = (d or "").lower().strip()
        return re.sub(r"^https?://(dx\.)?doi\.org/", "", d) or None
    ver_by_pmid = {str(r.get("pmid")): r for r in g6recs if r.get("pmid")}
    ver_by_doi = {_nd(r.get("doi")): r for r in g6recs if _nd(r.get("doi"))}
    # ⑤a 驗證判定鍵相容兩種寫法：⑤a 落檔多用 verdict、報告器舊版用 verify（與 gate_guard 同樣 _vv 相容）。
    def _vv(r): return r.get("verify") or r.get("verdict")
    retracted = sum(1 for r in g6recs if _vv(r) == "RETRACTED")
    # 無法驗證＝UNVERIFIED 與 UNRESOLVED（無 PMID/DOI 可驗）皆計入，兩者都不入 ⑤b/交接（與 gate 一致）。
    unverified = sum(1 for r in g6recs if _vv(r) in ("UNVERIFIED", "UNRESOLVED"))

    # ── 精確判『文獻類型/研究設計』：讀每篇 pubtype＋摘要，逐篇判實際設計，
    #    嚴禁用 ⑤b 的 design 桶一概標「真實世界」(那只是『核心 vs 背景』分流，非研究設計)。
    g2bs = _load(cache / "g2b_survivors.json") or {}
    ab_by_uid = {r.get("uid"): (r.get("abstract") or "") for r in (g2bs.get("records") or [])}
    pt_by_uid = {r.get("uid"): (r.get("pubtype") or []) for r in g6recs}
    from study_type_classifier import classify_study_type
    def study_type(uid, title):
        pt_list = pt_by_uid.get(uid, []) or []
        abstract = ab_by_uid.get(uid, "") or ""
        return classify_study_type(pt_list, title, abstract)

    # ---- metadata (esummary) for included pmids ----
    # 硬規則：「抓取失敗」與「來源真的沒有」須可區分——批次失敗記 fetch_fails 並警示，
    # 單筆解析失敗只丟該筆（不可讓一筆髒資料丟掉整個 200 筆 batch 的 metadata）。
    inc_pmids = sorted({str(b.get("pmid")) for b in base_srma if b.get("pmid")} |
                       {str(r.get("pmid")) for r in core if r.get("pmid")})
    meta = {}
    fetch_fails = []
    for i in range(0, len(inc_pmids), 200):
        d = _http("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" +
                  ",".join(inc_pmids[i:i+200]), mailto)
        if not d:
            fetch_fails.append("esummary batch %d–%d（%d 筆 PMID）" % (i, i + 200, len(inc_pmids[i:i+200])))
            continue
        try:
            res = json.loads(d).get("result", {})
        except Exception as e:
            fetch_fails.append("esummary batch %d 回應非 JSON（%s）" % (i, str(e)[:40])); continue
        for pid in res.get("uids", []):
            try:
                x = res[pid]; au = x.get("authors") or []
                a1 = ((au[0].get("name") or "").split() or [""])[0] if au else ""
                doi = ""
                for aid in x.get("articleids", []):
                    if aid.get("idtype") == "doi": doi = aid.get("value", "")
                meta[pid] = {"a1": a1, "year": (x.get("pubdate", "") or "")[:4], "doi": doi, "title": x.get("title", "")}
            except Exception as e:
                fetch_fails.append("PMID %s esummary 解析失敗（%s）" % (pid, str(e)[:40]))
    if fetch_fails:
        sys.stderr.write("⚠ PubMed metadata 抓取有 %d 項失敗（≠來源沒有；byline 將退化，報告 gate 可能因此擋下）：\n%s\n"
                         % (len(fetch_fails), "\n".join("  - " + f for f in fetch_fails[:8])))

    def verify_str(pid, doi):
        r = ver_by_pmid.get(str(pid)) if pid else (ver_by_doi.get(_nd(doi)) if _nd(doi) else None)
        if not r: return "—"
        # ⑤a 落檔鍵為 verdict（gate_guard.py 同註）；舊報告器鍵為 verify——單讀 verify 曾使整欄靜默變「—」
        v = _vv(r) or "—"; via = r.get("verify_via") or []
        if v == "VERIFIED":
            tag = "+".join([s for s in (("PubMed" if "pubmed" in via else ""), ("Crossref" if "crossref" in via else "")) if s])
            return "VERIFIED (%s)" % (tag or "ok")
        return v

    # PubMed 缺 author/year 時(尤 DOI-only 會議摘要/protocol)以 Crossref 補，確保『作者／年份／文獻類型』忠實呈現
    def _datacite(doi):
        d = _http("https://api.datacite.org/dois/" + urllib.parse.quote(doi), mailto, pause=0.05)
        if not d: return {}
        try: a = json.loads(d)["data"]["attributes"]
        except Exception: return {}
        cre = a.get("creators") or []
        a1 = ""
        if cre:
            c0 = cre[0]; a1 = c0.get("familyName") or ((c0.get("name", "") or "").split(",")[0])
        return {"a1": a1 or "", "year": str(a.get("publicationYear") or ""),
                "type": ((a.get("types") or {}).get("resourceTypeGeneral", "") or ""), "container": ""}

    def _crossref(doi):
        if not doi or doi == "—": return {}
        d = _http("https://api.crossref.org/works/" + urllib.parse.quote(doi) + "?mailto=" + mailto, mailto, pause=0.05)
        if not d: return _datacite(doi)          # Crossref 不收(如 registry/DataCite DOI)→ 退 DataCite
        try: m = json.loads(d)["message"]
        except Exception: return _datacite(doi)
        au = m.get("author") or []
        a1 = (au[0].get("family", "") if au else "") or ""
        yr = ""
        for k in ("published-print", "published-online", "published", "issued"):
            dp = (m.get(k) or {}).get("date-parts") or []
            if dp and dp[0] and dp[0][0]: yr = str(dp[0][0]); break
        out = {"a1": a1, "year": yr, "type": m.get("type", ""), "container": " ".join(m.get("container-title") or [])}
        if not a1 and not yr:                     # Crossref 有條目但缺作者/年→ 再試 DataCite
            dc = _datacite(doi)
            if dc.get("a1") or dc.get("year"): return {**out, **{k: v for k, v in dc.items() if v}}
        return out

    def _refine_dtype(doi, cr, base_dtype):
        s = "%s %s %s" % (doi or "", cr.get("type", "") or "", cr.get("container", "") or "")
        if re.search(r"congress|conference|proceedings|poster|abstract", s, re.I): return "會議摘要"
        if re.search(r"protocol|registration|posted-content|preprint|/pr0", s, re.I): return "研究計畫書/preprint"
        return base_dtype

    def resolve(pid, doi, title, base_dtype, is_base=False):
        m = meta.get(str(pid), {}) if pid else {}
        a1 = m.get("a1", ""); yr = m.get("year", ""); cr = {}
        if not a1 or not yr:                       # PubMed 缺 → Crossref 補
            cr = _crossref(doi)
            a1 = a1 or cr.get("a1", ""); yr = yr or cr.get("year", "")
        dtype = base_dtype if is_base else _refine_dtype(doi, cr, base_dtype)
        head = ("%s %s" % (a1, yr)).strip() if (a1 or yr) else (title or "")[:24]
        return "%s / %s" % (head, dtype)

    included = []
    for b in base_srma:
        pid = str(b.get("pmid")) if b.get("pmid") else None
        m = meta.get(pid, {}) if pid else {}
        doi = b.get("doi") or m.get("doi", "") or "—"
        title = b.get("title") or m.get("title", "")
        dtype = doctype_of("SR/MA/NMA/ITC", b.get("doctype"))
        included.append({"byline": "〔base〕" + resolve(pid, doi, title, dtype, is_base=True), "title": title,
                         "doi": doi, "pmid": pid or "—", "verify": verify_str(pid, doi)})
    for r in core:
        pid = str(r.get("pmid")) if r.get("pmid") else None
        m = meta.get(pid, {}) if pid else {}
        doi = r.get("doi") or m.get("doi", "") or "—"
        title = r.get("title") or m.get("title", "")
        dtype = study_type(r.get("uid"), title)   # 逐篇判實際設計(非用 design 桶)
        included.append({"byline": resolve(pid, doi, title, dtype), "title": title,
                         "doi": doi, "pmid": pid or "—", "verify": verify_str(pid, doi)})

    # ---- search strings (verbatim) ----
    strings = [{"leg": l.get("leg"), "query": l.get("query", "")} for l in legs if not l.get("skipped")]

    # ---- flow numbers ----
    nU = (union.get("count", "") if isinstance(union, dict) else len(union))
    # ②b 保留/剔除數：優先由 records 的 verdict 實算（最可靠），缺 records 才退回數值型計數鍵。
    # （相容各 run 的 g2b_screen 鍵名差異；不可直接取 kept/survivors——它們可能是『清單』而非計數，
    #  直接 str() 會把整個 list 印進 PRISMA 格子。故只接受『可轉成數字』的計數鍵。）
    _g2b_recs = g2b.get("records") or []
    def _g2b_count(verdict, *count_keys):
        if _g2b_recs:
            return sum(1 for r in _g2b_recs if r.get("verdict") == verdict)
        for k in count_keys:
            v = g2b.get(k)
            if isinstance(v, int):
                return v
            if isinstance(v, list):
                return len(v)
        return ""
    surv = _g2b_count("kept", "kept_count", "survivors", "kept")
    drop = _g2b_count("removed", "removed_count", "dropped", "removed")
    from collections import Counter
    vc = Counter(r.get("verdict") for r in g3)
    n_hit = vc.get("切題", 0); n_off = vc.get("離題", 0); n_no = vc.get("全文及摘要皆無", 0)
    # ④ 引文追蹤新增切題數：相容鍵名，缺則由 g4_citation_tracking.json 的 new_relevant 或 g4 的 hits 實算。
    g4track = _load(cache / "g4_citation_tracking.json") or {}
    n_new = (g4.get("n_new_concordant") or g4.get("new_切題")
             or len(g4track.get("new_relevant") or [])
             or len(g4.get("hits") or []) or 0)
    # 自驗（防本輪 bug 復發）：PRISMA 每個流程數字都必須是整數。本輪根因＝讀 cache 用了不符的鍵名
    # （survivors/dropped/verify/n_new_concordant）→ 讀到空字串 "" → 格子留空、流程不對帳，卻無人擋。
    # 故在組 flow 前硬擋：任一數字非 int（疑似鍵名不符讀到空值）即 raise，讓產生器『大聲失敗』而非靜默出空格。
    _flow_nums = {"union(nU)": nU, "②b保留(surv)": surv, "②b剔除(drop)": drop,
                  "③切題(n_hit)": n_hit, "③離題(n_off)": n_off, "③皆無(n_no)": n_no,
                  "④新增(n_new)": n_new, "撤稿(retracted)": retracted, "無法驗證(unverified)": unverified}
    _bad = [k for k, v in _flow_nums.items() if not isinstance(v, int)]
    if _bad:
        raise ValueError("PRISMA 流程數字缺失/非整數（疑似 cache 鍵名與產生器不符→讀到空值）：%s。"
                         "請確認 g2b_screen.json（kept/removed 由 records 實算）、g6_verified.json（verdict）、"
                         "g4_citation*.json（new_relevant/hits）的鍵名與本產生器一致。" % ", ".join(_bad))
    flow = [
        {"stage": "識別 Identification：六腿廣蒐→跨腿去重", "start": "—", "excluded": "—", "remain": "%s（文獻聯集）" % nU},
        {"stage": "②b 高敏初篩（標題＋摘要）", "start": str(nU), "excluded": "剔除明顯離題 %s" % drop, "remain": str(surv)},
        {"stage": "③ 嚴格離題篩 Tier1–4（全文）", "start": str(surv), "excluded": "離題 %d、全文及摘要皆無 %d" % (n_off, n_no), "remain": "切題 %d" % n_hit},
        {"stage": "④ 引文追蹤（聚焦種子，收斂）", "start": str(n_hit), "excluded": "—（新增 +%d）" % n_new, "remain": str(n_hit + n_new)},
        {"stage": "⑤a 交叉驗證（Crossref＋PubMed）", "start": str(n_hit + n_new), "excluded": "撤稿 −%d、無法驗證 −%d（皆剔除，不入分析）" % (retracted, unverified), "remain": str(n_hit + n_new - retracted - unverified)},
        {"stage": "⑤b 決定納入單位", "start": str(n_hit + n_new - retracted - unverified), "excluded": "背景 %d、待評估會議摘要 %d" % (len(bg), len(aw)), "remain": "核心 %d（＋base SR/MA %d）" % (len(core), len(base_srma))},
    ]
    reconcile = "對帳：核心 %d ＋ 背景 %d ＋ 待評估 %d ＝ %d。" % (len(core), len(bg), len(aw), len(core) + len(bg) + len(aw))

    # ---- ongoing trials ----
    ct = (api.get("clinicaltrials", {}) or {}).get("records", [])
    ONG = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "AVAILABLE", "SUSPENDED"}
    ongoing = []
    for t in ct:
        st = (t.get("status") or "").upper()
        if st in ONG or (not t.get("hasResults") and st not in {"COMPLETED", "TERMINATED", "WITHDRAWN", "UNKNOWN"}):
            ongoing.append({"nct": t.get("nct") or "—", "title": t.get("title") or "—", "status": st or "—"})

    axes = g0.get("axes", {})
    def ax(k): return (axes.get(k, {}) or {}).get("label", "")
    sr = g0.get("sr_filter_decision", "")
    data = {
        "title": "EBM Phase 1 系統性檢索報告",
        "topic": g0.get("topic", ""),
        "search_date": g0.get("search_date", ""),   # 缺值不得偽造：留空讓 validate/gate 擋下，逼補 g0.search_date
        "params": {
            "pico": "P＝%s；I＝%s；C＝%s（O 待 Phase 0 補定）" % (ax("P"), ax("I"), ax("C")),
            "databases": [l.get("leg") for l in legs],
            "limits": "未套用 RCT filter；SR filter＝%s；無語言限制；無年份限制；敏感度優先、各腿翻頁取盡" %
                      ({"declined": "未加掛", "applied": "已加掛", "not_applied": "未加掛"}.get(sr, sr or "—")),
        },
        "search_strings": strings,
        "flow": flow,
        "flow_reconcile": reconcile,
        "included": included,
        "included_note": "〔base〕＝模式B 分析基底候選 NMA/ITC（Phase 0 以 AMSTAR2/ROBIS/CCA 終選）；其餘為核心真實世界直接對照（佐證）。背景與待評估依規定不列入本表。",
        "ongoing": ongoing,
    }
    return data

# 交叉檢核欄合法值（⑤a 產出枚舉的子集）：撤稿/離題者在 ⑤a→⑤b 已剔除，嚴禁混入報告表。
XREF_LEGAL_PREFIX = ("VERIFIED", "PARTIAL", "UNVERIFIED", "UNRESOLVED", "—")

def validate(data):
    """寫檔前 shape/內容驗證（fail loud，不靜默寫出）。回傳缺失清單（空＝通過）。
    外部審查曾指出的契約：報告表的驗證欄只能出現 VERIFIED/PARTIAL/UNVERIFIED/UNRESOLVED，
    OFF_TOPIC/RETRACTED 混入須被攔下——此守門曾在 2026-06 重寫時遺失，現釘回並由 tests/ 回歸測試釘住。"""
    fails = []
    for k in ("title", "search_date", "params", "search_strings", "flow", "included"):
        if k not in data:
            fails.append("缺必備鍵 `%s`" % k)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("search_date", ""))):
        fails.append("search_date 非 YYYY-MM-DD（g0_strategy.json 須帶精確到日的 search_date）")
    for it in data.get("included", []) or []:
        v = str(it.get("verify", "") or "")
        if not v.startswith(XREF_LEGAL_PREFIX):
            fails.append("included 交叉檢核非法值 %r（%s）：報告表只允許 %s——OFF_TOPIC/RETRACTED 應在 ⑤a/⑤b 剔除，不得入表"
                         % (v, (it.get("title") or "")[:30], "/".join(XREF_LEGAL_PREFIX[:4])))
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mailto", default=os.environ.get("CROSSREF_MAILTO", "anon@example.com"))
    a = ap.parse_args()
    data = build_data(a.cache, a.mailto)
    fails = validate(data)
    if fails:
        sys.stderr.write("❌ _search_report 資料驗證未過（不寫檔）：\n" + "\n".join("  - " + f for f in fails) + "\n")
        sys.exit(2)
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE:", a.out, "| included", len(data["included"]), "| ongoing", len(data["ongoing"]))

if __name__ == "__main__":
    main()
