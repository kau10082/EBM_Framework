# -*- coding: utf-8 -*-
"""
quote_verify.py — 逐字 quote 機器核對（反幻覺皇冠）
==================================================
把 Phase 1 cache（*.p1.json）的每筆 source_locators.quote，**回原始全文模糊比對**，
確認該 quote 真的出現在來源（非 Claude 杜撰）。對不上 → FAIL。

來源解析（依交接包 fulltext_channel / fulltext_url）：
  local        → 讀 inputs/<paper_id>.pdf
  online + .pdf→ 線上抓 PDF 取文字
  online + PMC → NCBI efetch db=pmc 取全文 XML
  ai_synthesis → 標『二手·無法對全文核對』（不算 FAIL，但列出供人工注意）

比對：正規化（小寫、去非英數、收合空白）後做子字串 + difflib 比值（門檻 0.85）。
用法：python tools/quote_verify.py [--seed <_corpus_seed.json>] [--threshold 0.85]
"""
import sys, os, re, json, io, argparse, urllib.request, difflib
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir
CACHE = Path(workdir.cache_dir()); INPUTS = Path(workdir.inputs_dir())
UA = {"User-Agent": "Mozilla/5.0 (EBM_Framework quote_verify; +https://github.com/kau10082/EBM_Framework)"}

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def _pdf_text(data):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)

def _fetch(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

_BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
def _unpaywall_text(doi):
    """有 DOI 就問 Unpaywall：找到 OA PDF→抓文字。回 text 或 None。（退 ai_synthesis 前的最後一搏）
    機構典藏(如 Dundee)常擋非瀏覽器 UA→用完整瀏覽器 UA 抓。"""
    if not doi:
        return None
    try:
        import unpaywall
        purl = unpaywall.oa_pdf(doi)
        if not purl or not purl.lower().endswith(".pdf"):
            return None
        raw = urllib.request.urlopen(urllib.request.Request(purl, headers=_BROWSER_UA), timeout=60).read()
        txt = _pdf_text(raw)
        return txt if txt and len(txt) > 1000 else None
    except Exception:
        return None

def source_text(paper_id, seed_map):
    """回 (text, note)；text=None 表無法取得來源。"""
    s = seed_map.get(paper_id, {})
    ch = s.get("fulltext_channel"); url = s.get("fulltext_url"); pdf = s.get("pdf_file")
    doi = s.get("doi")
    if ch == "ai_synthesis":
        t = _unpaywall_text(doi)  # 退二手前先問 Unpaywall 有沒有 OA 全文
        if t:
            return t, "unpaywall:oa（原標 ai_synthesis，實有開放全文）"
        return None, "ai_synthesis（二手·無全文可核對）"
    # local：先試 inputs/<paper_id>.pdf，再試 seed pdf_file
    if ch == "local":
        for cand in [INPUTS / (paper_id + ".pdf"), (INPUTS / pdf) if pdf else None]:
            if cand and cand.exists():
                return _pdf_text(cand.read_bytes()), f"local:{cand.name}"
        return None, "local PDF 不存在"
    if ch == "online" and url:
        try:
            if url.lower().endswith(".pdf"):
                return _pdf_text(_fetch(url)), "online:pdf"
            m = re.search(r"(PMC\d+)", url)
            if m:
                pmcid = m.group(1)
                # 先用 Europe PMC（容器內可達），失敗再退 NCBI efetch
                xml = None
                try:
                    xml = _fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid).decode("utf-8", "replace")
                    if len(xml) < 2000:
                        xml = None
                except Exception:
                    xml = None
                if not xml:
                    num = pmcid.replace("PMC", "")
                    xml = _fetch("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=%s&rettype=full&retmode=xml" % num).decode("utf-8", "replace")
                # 摘要與正文都算「可引用全文」：abstract 常含主要結果(HR/RR/N),只取 <body> 會漏抓
                parts = re.findall(r"<abstract\b.*?</abstract>", xml, re.S) + re.findall(r"<body\b.*?</body>", xml, re.S)
                src = " ".join(parts) if parts else xml
                return re.sub(r"<[^>]+>", " ", src), "online:pmc"
            return _pdf_text(_fetch(url)), "online:fetch"
        except Exception as e:
            t = _unpaywall_text(doi)
            if t:
                return t, "unpaywall:oa（online 主來源失敗後備援）"
            return None, "online 取得失敗:%s" % str(e)[:40]
    # 無 channel/url：仍嘗試 Unpaywall（有 DOI 就試）
    t = _unpaywall_text(doi)
    if t:
        return t, "unpaywall:oa"
    return None, "無 channel/url"

def _digits(s):
    """取數字串集合（分隔符不敏感）：'0.58'→{'0','58'}、'0·52'→{'0','52'}、'2,525'→{'2','525'}。"""
    return set(re.findall(r"\d+", s or ""))

def match(quote, src_norm, threshold, src_digits=None):
    """模糊比對 ＋『數字守門』：difflib 對長句改一個數字仍 >0.85，故額外要求 quote 內**每個數字串都在原文出現**，
    否則一律不算 match（防『周圍文字對、數字被捏造』的假陽性；反幻覺皇冠的真守門）。"""
    qn = _norm(quote)
    if not qn:
        return False, 0.0
    # 數字守門：src_digits 提供時，quote 的數字必須全在原文（捏造數字→直接 False）
    if src_digits is not None:
        miss = _digits(quote) - src_digits
        if miss:
            return False, -1.0           # ratio=-1 標記『文字近似但有原文沒有的數字』
    if qn in src_norm:
        return True, 1.0
    # 取片段做最佳比值（quote 可能含 {CI} 等被正規化後仍有小差）
    best = 0.0; L = len(qn)
    for i in range(0, max(1, len(src_norm) - L), max(1, L // 3)):
        r = difflib.SequenceMatcher(None, qn, src_norm[i:i + L + 20]).ratio()
        if r > best: best = r
        if best >= threshold: break
    return best >= threshold, round(best, 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed"); ap.add_argument("--threshold", type=float, default=0.85)
    a = ap.parse_args()
    seed_path = a.seed
    if not seed_path:
        try:
            import run_state
            ftd = run_state.load().get("paths", {}).get("fulltext_dir")
            seed_path = os.path.join(ftd, "_corpus_seed.json") if ftd else None
        except Exception: pass
    seed_map = {}
    if seed_path and os.path.exists(seed_path):
        seed = json.load(open(seed_path, encoding="utf-8"))
        seed_map = {p["paper_id"]: p for p in seed.get("papers", [])}
    p1files = sorted(CACHE.glob("*.p1.json"))
    total = ok = fail = skip = 0; failures = []
    for f in p1files:
        d = json.loads(f.read_text(encoding="utf-8")); pid = d["paper_id"]
        locs = d.get("source_locators", [])
        text, note = source_text(pid, seed_map)
        if text is None:
            skip += len(locs)
            print(f"  ⚠ {pid}: 來源無法核對（{note}）— {len(locs)} quote 待人工")
            continue
        src_norm = _norm(text); src_digits = _digits(text)
        pv = pf = 0
        for loc in locs:
            total += 1
            good, ratio = match(loc.get("quote", ""), src_norm, a.threshold, src_digits)
            if good: ok += 1; pv += 1
            else:
                fail += 1; pf += 1
                failures.append(f"{pid} [{loc.get('claim','')[:30]}] ratio={ratio} quote={loc.get('quote','')[:60]}")
        print(f"  {'✅' if pf==0 else '❌'} {pid}: {pv}/{pv+pf} 核對通過（來源 {note}）")

    # ── 同時核對 synthesis SoF 的 provenance（直接建 synthesis、未走 p1.json 時的『數字溯源』）──
    synp = CACHE / "_synthesis.json"
    if synp.exists():
        syn = json.loads(synp.read_text(encoding="utf-8")).get("synthesis", {})
        by_doi = {}
        for pid_, p in seed_map.items():
            d = (p.get("doi") or "")
            if d:
                by_doi[d.lower()] = p; by_doi[d.lower().replace("/", "_")] = p
        _txtcache = {}
        def _src_text(source):
            if source in _txtcache: return _txtcache[source]
            # (a) 直接 inputs/<source>.pdf（doi-slug 命名）
            for cand in (INPUTS / (source + ".pdf"), INPUTS / (source.replace("/", "_") + ".pdf")):
                if cand.exists():
                    r = (_pdf_text(cand.read_bytes()), f"local:{cand.name}"); _txtcache[source] = r; return r
            # (b) 經交接包 paper_id/doi 解析管道
            sp = seed_map.get(source) or by_doi.get(source.lower()) or by_doi.get(source.lower().replace("/", "_"))
            r = source_text(sp["paper_id"], seed_map) if sp else (None, "source 未在交接包/ inputs")
            _txtcache[source] = r; return r
        sof_q = 0
        for o in syn.get("sof", []):
            for pvn in (o.get("provenance") or []):
                total += 1; sof_q += 1
                text, note = _src_text(pvn.get("source", ""))
                if text is None:
                    skip += 1; print(f"  ⚠ SoF「{o.get('outcome','')[:12]}」{pvn.get('value','')}: 來源無法核對（{note}）"); continue
                good, ratio = match(pvn.get("quote", ""), _norm(text), a.threshold, _digits(text))
                if good: ok += 1
                else:
                    fail += 1; failures.append(f"SoF「{o.get('outcome','')[:14]}」value={pvn.get('value')} ratio={ratio} quote={pvn.get('quote','')[:60]}")
                print(f"  {'✅' if good else '❌'} SoF/{pvn.get('value','')[:20]}（{note}）")
        if sof_q:
            print(f"  — SoF provenance 共核 {sof_q} 個數值")

    print(f"\n總計：{ok} 通過 / {fail} 失敗 / {skip} 無法核對（共 {total+skip} quote）")
    if failures:
        print("失敗清單："); [print("  -", x) for x in failures]
        sys.exit(1)
    print("✅ 所有可核對之逐字 quote 均在來源全文中找到（反幻覺核對通過）")

if __name__ == "__main__":
    main()
