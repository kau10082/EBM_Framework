# -*- coding: utf-8 -*-
"""
fulltext_title_audit.py — 分析端『本機全文內容 ↔ paper_id 標題』稽核（committed；補 EBM_Search ⑤a 的對稱缺口）。

2026-06 使用者糾正而立：EBM_Search ⑤a 有 `doi_title_audit`/`check_doi_title_audited` 守『DOI↔標題』；
但 **EBM_Analysis 這側（ingest/補全文→抽取）完全沒有「本機全文的實際內容是否就是該 paper_id 那篇」的稽核**。
實測：base #1（`10.23736_s0026-4806.21.07623-0`，標題「…an *updated* NMA」）的 inputs .txt/.pdf 其實是
另一篇 Edris「…a *systematic review and* NMA」的誤存（與 base #3 重複內容）——這種「內容放錯 paper_id」會
**靜默通過、直接進 GRADE 抽取**。本稽核就是要在補全文後、進抽取前把它抓出來。

判定（對每篇有本機全文的 base）：
  • own        = 該 paper 自己的標題（正規化後）最長連續片段在『本機全文前 8000 字』出現的比例(0..1)。
  • best_other = 其他 base 標題在『本機全文首頁/前 1500 字』出現的最高比例（只看開頭，避免被內文引用別篇誤判）。
  • own ≥ OK                         → ok（自己的標題明確出現在開頭，可信）
  • 否則 best_other ≥ STRONG 且 (best_other − own) ≥ MARGIN
                                      → **mismatch**（開頭是『別篇』的標題、不是自己的 → 內容八成放錯 paper_id）
  • 其餘                              → unverifiable（標題在本機全文裡找不到明確證據——多為 .txt 被截掉封面；只警示不阻擋）

用法：
  python tools/fulltext_title_audit.py                 # 讀 _corpus.json＋inputs/，印各 base 狀態
  python tools/fulltext_title_audit.py --json
  python tools/fulltext_title_audit.py --selftest
程式內：
  from fulltext_title_audit import audit, mismatches
  res = audit(papers, text_of)        # text_of(paper_id)->本機全文文字(None=無檔)；回逐篇狀態
  bad = mismatches(res)               # 只取 status=='mismatch'
"""
import sys, os, re, json, argparse, difflib
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
OK     = 0.62   # own ≥ 此 → 自己的標題明確出現，判 ok
STRONG = 0.65   # 別篇標題在開頭出現到此比例 → 算『明確出現』
MARGIN = 0.18   # 別篇比自己高出此幅度 → 判內容放錯
HEAD   = 1500   # best_other 只在前這麼多字（首頁標題區）找，避免被內文引用別篇標題誤判
BODY   = 8000   # own 在前這麼多字找（自己的標題可能不在最頂端，放寬）


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _lcs_frac(needle_norm, hay_norm):
    """needle 最長連續片段出現在 hay 的比例(0..1)。"""
    if not needle_norm or not hay_norm:
        return 0.0
    m = difflib.SequenceMatcher(None, needle_norm, hay_norm).find_longest_match(
        0, len(needle_norm), 0, len(hay_norm))
    return m.size / len(needle_norm)


def audit(papers, text_of):
    """papers: [{paper_id,title}]; text_of(paper_id)->本機全文文字 或 None。回逐篇狀態 dict。"""
    norm_titles = [(p["paper_id"], _norm(p.get("title"))) for p in papers]
    out = []
    for p in papers:
        pid = p["paper_id"]
        raw = text_of(pid)
        if not raw:
            out.append({"paper_id": pid, "status": "no_fulltext"})
            continue
        body = _norm(raw)[:BODY]
        head = body[:HEAD]
        own = _lcs_frac(_norm(p.get("title")), body)
        best_id, best = None, 0.0
        for qid, qt in norm_titles:
            if qid == pid or not qt:
                continue
            s = _lcs_frac(qt, head)
            if s > best:
                best, best_id = s, qid
        if own >= OK:
            st = "ok"
        elif best >= STRONG and (best - own) >= MARGIN:
            st = "mismatch"
        else:
            st = "unverifiable"
        out.append({"paper_id": pid, "status": st, "own": round(own, 2),
                    "best_other_id": best_id, "best_other": round(best, 2),
                    "title": (p.get("title") or "")[:120]})
    return out


def mismatches(results):
    return [r for r in results if r.get("status") == "mismatch"]


# ----- 真檔讀取（CLI 用；程式內可自帶 text_of） -----
def _pdf_text(path, maxchars=BODY):
    for mod in ("fitz", "pypdf"):
        try:
            if mod == "fitz":
                import fitz
                d = fitz.open(str(path)); buf = []
                for i in range(min(4, d.page_count)):
                    buf.append(d[i].get_text())
                    if sum(len(x) for x in buf) > maxchars:
                        break
                d.close()
                return " ".join(" ".join(buf).split())[:maxchars]
            else:
                import pypdf
                r = pypdf.PdfReader(str(path)); buf = []
                for pg in r.pages[:4]:
                    buf.append(pg.extract_text() or "")
                    if sum(len(x) for x in buf) > maxchars:
                        break
                return " ".join(" ".join(buf).split())[:maxchars]
        except Exception:
            continue
    return None


def make_text_of(inputs_dir):
    def text_of(pid):
        pdf = Path(inputs_dir) / f"{pid}.pdf"
        txt = Path(inputs_dir) / f"{pid}.txt"
        if pdf.exists():
            t = _pdf_text(pdf)
            if t:
                return t
        if txt.exists():
            return txt.read_text(encoding="utf-8", errors="replace")[:BODY]
        return None
    return text_of


def _selftest():
    ok = True
    # 真實 #1 情境：A 的 paper_id 標題是「updated NMA」，但本機全文其實是 B「systematic review NMA」(Edris)
    A = "Monoclonal antibodies in type 2 asthma: an updated network meta-analysis"
    B = "Monoclonal antibodies in type 2 asthma: a systematic review and network meta-analysis"
    edris_text = ("REVIEW Open Access " + B + " Ahmed Edris, Silke De Feyter, Tania Maes, Guy Joos and "
                  "Lies Lahousse Abstract Since novel treatments to target eosinophilic inflammation ...")
    papers = [{"paper_id": "A_updated", "title": A}, {"paper_id": "B_sr", "title": B},
              {"paper_id": "C_other", "title": "Comparative efficacy of tezepelumab to mepolizumab benralizumab dupilumab"}]
    texts = {
        "A_updated": edris_text,                                   # 內容放錯（是 B 的文）→ 應 mismatch
        "B_sr": edris_text,                                        # 自己的文 → ok
        "C_other": "INTRODUCTION Patients with moderate to severe asthma ... tezepelumab to mepolizumab benralizumab dupilumab ...",  # 自己標題在文中 → ok
    }
    res = {r["paper_id"]: r for r in audit(papers, lambda pid: texts.get(pid))}
    c1 = res["A_updated"]["status"] == "mismatch" and res["A_updated"]["best_other_id"] == "B_sr"
    print(("  ✅" if c1 else "  ❌") + f" 內容放錯 paper_id（A 實為 B 的文）→ mismatch（best_other=B）：{res['A_updated']}")
    ok &= c1
    c2 = res["B_sr"]["status"] == "ok"
    print(("  ✅" if c2 else "  ❌") + f" 正確全文 → ok：{res['B_sr']['status']}")
    ok &= c2
    c3 = res["C_other"]["status"] == "ok"
    print(("  ✅" if c3 else "  ❌") + f" 自己標題在內文 → ok：{res['C_other']['status']}")
    ok &= c3
    # 封面被截、標題缺如的 .txt → 不可誤判 mismatch（只能 unverifiable）
    papers2 = [{"paper_id": "X", "title": "Some Unique Distinct Title Alpha Beta"},
               {"paper_id": "Y", "title": "Totally Different Other Heading Gamma Delta"}]
    res2 = {r["paper_id"]: r for r in audit(papers2, lambda pid: "Introduction Methods Results Discussion conclusions references" if pid == "X" else None)}
    c4 = res2["X"]["status"] == "unverifiable"
    print(("  ✅" if c4 else "  ❌") + f" 標題缺如(.txt 截掉封面) → unverifiable 不誤殺：{res2['X']['status']}")
    ok &= c4
    c5 = res2["Y"]["status"] == "no_fulltext"
    print(("  ✅" if c5 else "  ❌") + f" 無本機全文 → no_fulltext：{res2['Y']['status']}")
    ok &= c5
    print("✅ fulltext_title_audit selftest 全過" if ok else "❌ 有失敗")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None); ap.add_argument("--inputs", default=None)
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    try:
        sys.path.insert(0, str(HERE)); import workdir
        cache = a.cache or workdir.cache_dir()
        inputs = a.inputs or os.path.join(os.path.dirname(cache), "inputs")
    except Exception:
        cache = a.cache or str(HERE.parent / "cache")
        inputs = a.inputs or str(HERE.parent / "inputs")
    corpus_path = a.corpus or os.path.join(cache, "_corpus.json")
    corpus = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    base = [p for p in corpus["papers"] if p.get("grade_track") in ("full", "targeted_harms")]
    res = audit(base, make_text_of(inputs))
    bad = mismatches(res)
    unv = [r for r in res if r["status"] == "unverifiable"]
    nf = [r for r in res if r["status"] == "no_fulltext"]
    print(f"== 本機全文內容↔標題稽核：base {len(base)} 篇 ==")
    for r in res:
        mark = {"ok": "✅", "mismatch": "🔴", "unverifiable": "🟡", "no_fulltext": "⚪"}[r["status"]]
        line = f"  {mark} {r['status']:<12} {r['paper_id']}"
        if r["status"] in ("ok", "mismatch", "unverifiable"):
            line += f"  (own={r['own']} best_other={r['best_other']}→{r.get('best_other_id')})"
        print(line)
    print(f"\n小結：ok={len(res)-len(bad)-len(unv)-len(nf)} / 🔴mismatch={len(bad)} / 🟡unverifiable={len(unv)} / ⚪no_fulltext={len(nf)}")
    if bad:
        print("🔴 內容放錯 paper_id（須換成正確全文或修正 paper_id，不可進抽取）：")
        for r in bad:
            print(f"   - {r['paper_id']}：本機全文開頭其實是『{r.get('best_other_id')}』那篇（own={r['own']}<{r['best_other']}）")
    if a.json:
        print("\n--- JSON ---"); print(json.dumps(res, ensure_ascii=False, indent=2))
    return 2 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
