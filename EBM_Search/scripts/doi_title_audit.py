# -*- coding: utf-8 -*-
"""
doi_title_audit.py — ⑤a 交叉驗證的『DOI↔標題一致性』稽核器（committed；補強純存在性驗證的漏洞）。

2026-06 使用者糾正而立：Consensus／OE 腿不回 DOI，Claude 手填 DOI 易錯（實測 13 篇 base NMA 有
3 篇 DOI 指向完全不相干的論文：Campylobacter/Omalizumab/Phase-2 trial）。若 ⑤a 只查『DOI 存在
與否』(存在性)，錯 DOI 因『指向的論文真的存在』而被判 VERIFIED → 漏網，後段才爆（重複/抓錯全文）。
**鐵律：⑤a 對每筆有 DOI 的納入候選，必須再查 Crossref 該 DOI 的『實際標題』與我記錄的標題比對**——
similarity 低於門檻＝DOI↔title 不符＝該 DOI 可能填錯，須標 UNVERIFIED/待修，不得當 VERIFIED 放行。
（committed `xref_verify.py` 本就做標題比對；本器是『只給 DOI+title 清單即可獨立稽核』的輕量版，
 並供 gate_guard 的 `check_doi_title_audited` 確認 ⑤a 確實做過標題比對、非只查存在性。）

用法：
  python doi_title_audit.py --in records.json        # records=[{doi,title,pmid?}, ...]→印不符清單
  python doi_title_audit.py --selftest
程式內：
  import doi_title_audit as A
  mism = A.audit(records, mailto="x@y")              # 回 [{doi,recorded,crossref,sim}, ...]（空=全符）
  sim  = A.title_sim(a, b)                            # 0..1（離線，純字串）
"""
import sys, json, re, time, argparse, difflib, urllib.request, urllib.parse, urllib.error

MIN_SIM = 0.55   # 標題相似度門檻；低於此＝DOI↔title 不符（保守，避免標點/排版差異誤殺）

def _norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()

def title_sim(a, b):
    """離線標題相似度（正規化後 difflib ratio，比前 90 字元）。"""
    na, nb = _norm(a)[:90], _norm(b)[:90]
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()

def crossref_title(doi, mailto, timeout=30):
    """回 (status, title)：status ∈ ok／not_found（404＝DOI 不存在，最典型的幻覺 DOI）／error（網路等暫時失敗）。
    三態不可混：not_found 是『來源真的沒有』＝稽核 FAIL；error 是『抓取失敗』＝不可當已比對放行（fail-closed）。"""
    try:
        u = "https://api.crossref.org/works/" + urllib.parse.quote(doi) + "?mailto=" + mailto
        req = urllib.request.Request(u, headers={"User-Agent": "EBM-Framework/0.22 (mailto:%s)" % mailto})
        m = json.loads(urllib.request.urlopen(req, timeout=timeout).read())["message"]
        return "ok", (m.get("title") or [""])[0]
    except urllib.error.HTTPError as e:
        return ("not_found", "") if e.code == 404 else ("error", "HTTP %s" % e.code)
    except Exception as e:
        return "error", str(e)[:60]

def audit(records, mailto="ebm@example.com", sleep=0.2):
    """回 {"checked": 實際完成比對數, "mismatches": [...], "not_found": [...], "errors": [...]}。
    records: [{doi,title,...}]。**斷網/404 不得靜默放行**：曾經任何查不到都 continue，
    斷網跑一次＝mismatches 0、宣稱 checked=n → gate 誤認 ⑤a 已誠實比對（fail-open）。"""
    mism, not_found, errors = [], [], []
    checked = 0
    for r in records:
        doi = (r.get("doi") or "").strip()
        rec_t = r.get("title") or ""
        if not doi or not rec_t:
            continue
        status, ct = crossref_title(doi, mailto); time.sleep(sleep)
        if status == "not_found":
            not_found.append({"doi": doi, "recorded": rec_t[:64]})   # DOI 不存在＝疑幻覺 DOI，稽核 FAIL
            continue
        if status == "error":
            errors.append({"doi": doi, "detail": ct})                # 抓取失敗＝未比對，不可計入 checked
            continue
        checked += 1
        sim = title_sim(rec_t, ct)
        if sim < MIN_SIM:
            mism.append({"doi": doi, "recorded": rec_t, "crossref": ct, "sim": round(sim, 2)})
    return {"checked": checked, "mismatches": mism, "not_found": not_found, "errors": errors}

def _selftest():
    ok = True
    g = title_sim("Comparative efficacy of mepolizumab, benralizumab, and dupilumab in eosinophilic asthma",
                  "Comparative efficacy of mepolizumab, benralizumab, and dupilumab in eosinophilic asthma: a NMA")
    print(("  ✅" if g >= MIN_SIM else "  ❌") + f" 同題高相似（{g:.2f}≥{MIN_SIM}）")
    ok &= g >= MIN_SIM
    b = title_sim("Efficacy and Safety of Biologics for Oral Corticosteroid-Dependent Asthma",
                  "So How Should I Treat It? Campylobacter Infection in CVID")
    print(("  ✅" if b < MIN_SIM else "  ❌") + f" 異題低相似（{b:.2f}<{MIN_SIM}）→ 會被判 DOI↔title 不符")
    ok &= b < MIN_SIM
    e = title_sim("", "anything")
    print(("  ✅" if e == 0.0 else "  ❌") + " 空標題→0")
    ok &= e == 0.0
    print("✅ doi_title_audit selftest 全過" if ok else "❌ 有失敗")
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile"); ap.add_argument("--mailto", default="ebm@example.com")
    ap.add_argument("--out", dest="outfile", help="寫出稽核結果 JSON（如 cache/g6_title_audit.json，供 gate_guard 確認 ⑤a 做過比對）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    if a.selftest:
        sys.exit(_selftest())
    if not a.infile:
        ap.print_help(); return
    recs = json.loads(open(a.infile, encoding="utf-8").read())
    recs = recs if isinstance(recs, list) else recs.get("papers") or recs.get("records") or []
    res = audit(recs, a.mailto)
    mism, not_found, errors = res["mismatches"], res["not_found"], res["errors"]
    n_doi = sum(1 for r in recs if (r.get("doi") or "").strip())
    if a.outfile:
        with open(a.outfile, "w", encoding="utf-8") as f:
            json.dump({"checked": res["checked"], "n_doi": n_doi, "min_sim": MIN_SIM,
                       "mismatches": mism, "not_found": not_found, "errors": errors},
                      f, ensure_ascii=False, indent=1)
        print(f"wrote {a.outfile} (checked={res['checked']}/{n_doi}, mismatches={len(mism)}, "
              f"not_found={len(not_found)}, errors={len(errors)})")
    print(f"DOI↔title MISMATCHES: {len(mism)}")
    for m in mism:
        print(f"  sim={m['sim']} | DOI {m['doi']}\n     recorded: {m['recorded'][:64]}\n     crossref: {m['crossref'][:64]}")
    if not_found:
        print(f"DOI NOT FOUND (404，疑幻覺 DOI)：{len(not_found)}")
        for m in not_found: print(f"  DOI {m['doi']} | {m['recorded']}")
    if errors:
        print(f"查詢失敗（≠已比對，請恢復網路重跑）：{len(errors)}")
    sys.exit(2 if (mism or not_found or errors) else 0)

if __name__ == "__main__":
    main()
