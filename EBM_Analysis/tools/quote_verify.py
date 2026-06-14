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
UA = {"User-Agent": "Mozilla/5.0 (EBM quote_verify; kau10082ai@gmail.com)"}

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def _pdf_text(data):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)

def _fetch(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def source_text(paper_id, seed_map):
    """回 (text, note)；text=None 表無法取得來源。"""
    s = seed_map.get(paper_id, {})
    ch = s.get("fulltext_channel"); url = s.get("fulltext_url"); pdf = s.get("pdf_file")
    if ch == "ai_synthesis":
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
                num = m.group(1).replace("PMC", "")
                xml = _fetch("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=%s&rettype=full&retmode=xml" % num).decode("utf-8", "replace")
                body = re.search(r"<body\b.*?</body>", xml, re.S)
                return re.sub(r"<[^>]+>", " ", body.group(0) if body else xml), "online:pmc"
            return _pdf_text(_fetch(url)), "online:fetch"
        except Exception as e:
            return None, "online 取得失敗:%s" % str(e)[:40]
    return None, "無 channel/url"

def match(quote, src_norm, threshold):
    qn = _norm(quote)
    if not qn:
        return False, 0.0
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
        src_norm = _norm(text)
        pv = pf = 0
        for loc in locs:
            total += 1
            good, ratio = match(loc.get("quote", ""), src_norm, a.threshold)
            if good: ok += 1; pv += 1
            else:
                fail += 1; pf += 1
                failures.append(f"{pid} [{loc.get('claim','')[:30]}] ratio={ratio} quote={loc.get('quote','')[:60]}")
        print(f"  {'✅' if pf==0 else '❌'} {pid}: {pv}/{pv+pf} 核對通過（來源 {note}）")
    print(f"\n總計：{ok} 通過 / {fail} 失敗 / {skip} 無法核對（共 {total+skip} quote）")
    if failures:
        print("失敗清單："); [print("  -", x) for x in failures]
        sys.exit(1)
    print("✅ 所有可核對之逐字 quote 均在來源全文中找到（反幻覺核對通過）")

if __name__ == "__main__":
    main()
