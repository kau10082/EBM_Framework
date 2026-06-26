# -*- coding: utf-8 -*-
"""
analysis_scope.py — 算出『實際進入分析的文獻』＋『需人工補全文清單』（確定性、可重現）
================================================================================
因 2026-06 使用者要求而立：
  • Zotero 匯入範圍＝『實際進入分析的文獻』＝grade_track ∈ {full, targeted_harms}
    （背景 light_summary 留在 _corpus.json／報告／交接包，不進 Zotero，除非另指定 --include-background）。
  • 人工補全文範圍＝上述分析集中『全文尚未取得』者；補了才會增進分析結果。
    其餘（背景、已有全文者）不必補。
本工具只『讀』_corpus.json＋inputs/＋cache/*.p1.json 算出兩份清單，不改任何資料。

全文是否已取得 has_fulltext(paper) 判準（任一成立即 True；**只認實際本機證據，不認 notes 的『全文=…』marker**
——2026-06 使用者兩次糾正而定：notes 可能被上游樂觀標 have(online) 或被 8000 字線上摘錄誤標 have(manual)）：
  1. cache/<id>.p1.json 的 data_source 含 'full_text'，或 fulltext_attempts 有 result=fulltext_obtained；
  2. inputs/<id>.pdf 存在（人工補全文／交接複製進來的本機 PDF）；
  3. inputs/<id>.txt 存在且 ≥ MIN_FULLTEXT_BYTES（夠長＝實取全文；8000 字截斷摘錄不算）。

用法：
  python tools/analysis_scope.py                 # 印兩份清單（Zotero 範圍／需補全文）
  python tools/analysis_scope.py --json           # 另印機器可讀 JSON
  python tools/analysis_scope.py --write          # 寫 cache/_analysis_scope.json
  python tools/analysis_scope.py --include-background   # Zotero 範圍含 light_summary 背景
程式內：from analysis_scope import compute; scope = compute(corpus, cache_dir, inputs_dir)
"""
import sys, os, json, re, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
ANALYSIS_TRACKS = {"full", "targeted_harms"}


def _min_fulltext_bytes():
    """.txt 視為『有完整全文』的最小位元組數。集中於 settings.yaml(analysis.min_fulltext_bytes)，
    使其與『線上摘錄上限(~8000字)』的耦合可在一處調整（Antigravity 第八輪 🟡）；讀不到則退回 9000。
    設在摘錄上限之上，使被截斷的摘錄落入 need_manual（真全文 PDF/PMC body 普遍 >20k 字，遠超此門檻）。"""
    try:
        import yaml
        cfg = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        v = ((yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("analysis") or {}).get("min_fulltext_bytes")
        if isinstance(v, int) and v > 0:
            return v
    except Exception:
        pass
    return 9000

MIN_FULLTEXT_BYTES = _min_fulltext_bytes()


def _study_of(p):
    m = re.search(r'study=([A-Za-z0-9\-]+)', p.get("notes") or "")
    return m.group(1) if m else "—"


def _supplement_dir(inputs_dir):
    """『需補全文清單.txt』與使用者補件 PDF 的資料夾，依序解析（2026-06 使用者要求 honor config——
    修正『設定 report.fulltext_dir 有值、但本工具卻寫死 <inputs>/_fulltext_supplement』的不一致）：
      1) `run_state.paths.fulltext_dir`：EBM_Search→Analysis 交接包(_corpus_seed.json)所在的 per-topic 夾，
         補件與交接包同處（最可靠；其值本身即由 config report.fulltext_dir 衍生）。
      2) config `report.fulltext_dir` 有設值：用 `<fulltext_dir>/<run_state.slug>`（取不到 slug 則用根，
         避免跨主題覆蓋）。
      3) 回退 `<inputs>/_fulltext_supplement/`（fulltext_dir 留空時的原行為）。"""
    st = {}
    try:
        sys.path.insert(0, str(HERE)); import run_state
        st = run_state.load() or {}
        ftd = (st.get("paths") or {}).get("fulltext_dir")
        if ftd and str(ftd).strip():
            return Path(str(ftd).strip())
    except Exception:
        pass
    try:
        import yaml
        cfg = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        conf = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        # 兩個 config 鍵（見 settings.example.yaml）：`analysis.fulltext_dir`＝Phase 0 補全文專用鍵（優先）；
        #   `report.fulltext_dir`＝「人工補全文＋交接包」根（相容；使用者多半只設這個，補件即與交接包同根）。
        #   2026-06 修：原僅讀 analysis.* 卻拿到 None（使用者未設）→ 永遠落回退分支；改為 analysis→report 皆認。
        fd = ((conf.get("analysis") or {}).get("fulltext_dir")
              or (conf.get("report") or {}).get("fulltext_dir") or "").strip()
        if fd:
            slug = (st.get("slug") or "").strip() if isinstance(st, dict) else ""
            return Path(fd) / slug if slug else Path(fd)
    except Exception:
        pass
    return Path(inputs_dir) / "_fulltext_supplement"


def _has_fulltext(p, cache_dir, inputs_dir, sup_dir=None):
    pid = p["paper_id"]
    # 1) p1 證據
    p1 = Path(cache_dir) / f"{pid}.p1.json"
    if p1.exists():
        try:
            obj = json.loads(p1.read_text(encoding="utf-8"))
            if "full_text" in (obj.get("data_source") or []):
                return True, "p1:data_source=full_text"
            for a in (obj.get("fulltext_attempts") or []):
                if a.get("result") == "fulltext_obtained":
                    return True, f"p1:fulltext_obtained({a.get('channel')})"
        except Exception:
            pass
    # 2) 本機 PDF＝完整全文；或實取全文 .txt（但須『夠長』——線上摘錄常被截在 ~8000 字上限，
    #    那只是摘錄、不足以抽完整結果表，不算『有全文』。門檻 MIN_FULLTEXT_BYTES 設在摘錄上限之上，
    #    使 8000 字截斷摘錄落入 need_manual（2026-06 使用者糾正：3 篇 base 只有 8000 字摘錄卻被當有全文）。）
    #    ★ 同時掃 inputs/ 與『補全文夾』(sup_dir)——使用者直接把 PDF 丟進補全文夾即被偵測，免再手動搬進 inputs。
    for base, tag in ((Path(inputs_dir), "inputs"), (Path(sup_dir) if sup_dir else None, "補全文夾")):
        if base is None:
            continue
        if (base / f"{pid}.pdf").exists():
            return True, f"{tag}/<id>.pdf"
        txtp = base / f"{pid}.txt"
        if txtp.exists() and txtp.stat().st_size >= MIN_FULLTEXT_BYTES:
            return True, f"{tag}/<id>.txt"
    # 3) **只信實際本機檔案／p1 證據，不信 notes 的『全文=…』marker**（2026-06 使用者糾正兩次而立）：
    #    notes 可能被上游樂觀標 have(online) 或被『8000 字線上摘錄』誤標 have(manual)——兩者都不是可抽取的
    #    完整全文。真正取得完整全文者必有本機 PDF 或夠長 .txt（上面已涵蓋）；故此處不再以 notes 判 have，
    #    避免 need_manual 被少報（excerpt 充當 full）。
    return False, "全文尚未取得"


def compute(corpus, cache_dir, inputs_dir, include_background=False):
    papers = corpus["papers"]
    sup_dir = _supplement_dir(inputs_dir)   # 補全文夾（honor config；一次解析、全程共用）
    wanted = set(ANALYSIS_TRACKS) | ({"light_summary"} if include_background else set())
    analysis_set, must, optional = [], [], []
    for p in papers:
        if p.get("grade_track") not in wanted:
            continue
        has, why = _has_fulltext(p, cache_dir, inputs_dir, sup_dir)
        rec = {"paper_id": p["paper_id"], "study": _study_of(p), "grade_track": p.get("grade_track"),
               "role": p.get("role"), "relevance": p.get("relevance"),
               "is_primary_report": bool(p.get("is_primary_report")),
               "doi": (p.get("doi") or "").strip(),    # 供『需補全文清單.txt』列 DOI（Antigravity 第八輪 c；ingest_seed 帶入）
               "title": (p.get("title") or "")[:140], "has_fulltext": has, "fulltext_reason": why}
        analysis_set.append(rec)
        if p.get("grade_track") in ANALYSIS_TRACKS and not has:
            # ★ 需補全文最小集（must）＝『分析錨點』：每 Study 的主要報告（full∧is_primary_report）
            #   ＋ targeted_harms 的真害結果研究。其餘 full 次級報告（congress/cost/子分析）＝overlap，
            #   補了不額外增進核心 GRADE → 列 optional，不強求。
            if p.get("grade_track") == "full" and not p.get("is_primary_report"):
                optional.append(rec)
            else:
                must.append(rec)
    must.sort(key=lambda r: (0 if r["grade_track"] == "full" else 1, r["study"], r["paper_id"]))
    optional.sort(key=lambda r: (r["study"], r["paper_id"]))
    # ★ 防呆：full track 的 Study 若『無任一報告有全文』又『無任一主報告進 must』，
    #   多半是 Phase 0 漏標 is_primary_report → 該 Study 的全文需求會被靜默漏列（全掉 optional）。
    #   這裡主動警示，請回 Phase 0 為該 Study 標一篇主報告（is_primary_report=true）。
    must_full_studies = {r["study"] for r in must if r["grade_track"] == "full"}
    full_by_study = {}
    for r in analysis_set:
        if r["grade_track"] == "full" and r["study"] != "—":
            full_by_study.setdefault(r["study"], []).append(r)
    warnings = []
    for s, recs in full_by_study.items():
        if not any(r["has_fulltext"] for r in recs) and s not in must_full_studies:
            warnings.append(f"Study「{s}」：{len(recs)} 篇 full 報告皆無全文，且無任一標 is_primary_report"
                            f"→ 全文需求被漏列（全掉 optional）；請於 Phase 0 為此 Study 標一篇主報告(is_primary_report=true)")
    return {"analysis_set": analysis_set,
            "need_manual_fulltext": must,            # 補這些即可（增進分析的最小集）
            "optional_fulltext": optional,           # full 次級 overlap 報告，補了不增進核心 GRADE
            "supplement_dir": str(sup_dir),          # 補全文夾（honor config；need-list 寫此、亦掃此偵測 PDF）
            "warnings": warnings}                    # 防呆警示（需回 Phase 0 修；不阻擋）


def _print(scope):
    a = scope["analysis_set"]; nm = scope["need_manual_fulltext"]; opt = scope.get("optional_fulltext") or []
    byt = {}
    for r in a:
        byt.setdefault(r["grade_track"], []).append(r)
    studies = sorted({r["study"] for r in byt.get("full", []) if r["study"] != "—"})
    print(f"== 實際進入分析的文獻（Zotero 匯入範圍）：{len(a)} 報告 ==")
    print(f"   核心 full：{len(byt.get('full',[]))} 報告 → 收斂為 {len(studies)} 個分析 Study（{'、'.join(studies)}）")
    print(f"   targeted_harms（只評害）：{len(byt.get('targeted_harms',[]))} 報告")
    if byt.get("light_summary"):
        print(f"   （含背景 light_summary：{len(byt['light_summary'])}，--include-background 時才計入）")
    print(f"\n== ★ 需人工補全文（補了才增進分析；補這些即可）：{len(nm)} 報告 ==")
    if not nm:
        print("  （分析集應補全文皆已取得，無需補。）")
    for r in nm:
        tier = "①核心主報告" if r["grade_track"] == "full" else "②harms"
        print(f"  {tier}  {r['paper_id']:<34} {r['study']:<8} {r['title'][:60]}")
    print(f"\n== ○ 選補（full 次級/overlap 報告，補了不增進核心 GRADE）：{len(opt)} 報告 ==")
    print("   （同 Study 的 congress/cost/子分析；分析以主報告全文為錨點，這些當 overlap，不強求補。）")
    warns = scope.get("warnings") or []
    if warns:
        print(f"\n== ⚠️ 防呆警示（需回 Phase 0 修；不阻擋）：{len(warns)} 項 ==")
        for w in warns:
            print("  - " + w)


def write_need_manual_list(scope, inputs_dir):
    """確定性寫出 `需補全文清單.txt` 到『補全文夾』（honor config analysis.fulltext_dir，見 `_supplement_dir`；
    每次算 scope 都重寫，與 need_manual_fulltext 永遠同步、不會像手寫版那樣過時）。回傳寫出的路徑。
    2026-06 使用者糾正而立：此清單『一定要給』，故改由本工具確定性產出，不靠 Claude 手寫。"""
    sup = Path(scope.get("supplement_dir") or _supplement_dir(inputs_dir))
    sup.mkdir(parents=True, exist_ok=True)
    nm = scope.get("need_manual_fulltext") or []
    lines = ["需補全文清單（EBM Phase 0；analysis_scope.py 確定性產出，每次重算即更新）",
             "=" * 72,
             f"補全文夾：{sup}",
             "說明：以下為『分析錨點且全文尚未取得』者（每核心 Study 主報告＋真 harms）。",
             "      請把 PDF 放進本資料夾（即上方路徑），檔名＝下方『建議檔名』(＝paper_id.pdf；多為 DOI 去斜線)。",
             ""]
    if not nm:
        lines.append("（目前分析集全文皆已取得，無需補。）")
    for r in nm:
        tier = "核心主報告(full)" if r.get("grade_track") == "full" else "harms(targeted_harms)"
        lines.append(f"- [{tier}] {r.get('title','')}")
        doi = (r.get("doi") or "").strip()
        doi_bit = f"   | DOI：{doi}" if doi else "   | DOI：（交接包未帶；可用標題檢索）"
        lines.append(f"    建議檔名：{r.get('paper_id','')}.pdf   | Study：{r.get('study','—')}{doi_bit}")
    out = sup / "需補全文清單.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _selftest():
    import tempfile, shutil
    ok = True
    tmp = Path(tempfile.mkdtemp())
    try:
        inp = tmp / "inputs"; sup = tmp / "sup"; cache = tmp / "cache"
        for d in (inp, sup, cache):
            d.mkdir()
        (sup / "P1.pdf").write_bytes(b"%PDF-1.4 dummy")                       # 補全文夾的 PDF
        has, why = _has_fulltext({"paper_id": "P1"}, cache, inp, sup)
        c1 = has and "補全文夾" in why
        print(("  ✅" if c1 else "  ❌") + f" 補全文夾的 PDF 被偵測為有全文（免再搬進 inputs）：{why}"); ok &= c1
        (sup / "P2.txt").write_text("x" * (MIN_FULLTEXT_BYTES + 10), encoding="utf-8")
        (sup / "P3.txt").write_text("x" * 100, encoding="utf-8")
        h2, _2 = _has_fulltext({"paper_id": "P2"}, cache, inp, sup)
        h3, _3 = _has_fulltext({"paper_id": "P3"}, cache, inp, sup)
        c2 = h2 and not h3
        print(("  ✅" if c2 else "  ❌") + f" 補全文夾 .txt 夠長判有、過短(摘錄)判無：P2={h2} P3={h3}"); ok &= c2
        h4, _4 = _has_fulltext({"paper_id": "P9"}, cache, inp, sup)
        print(("  ✅" if not h4 else "  ❌") + " 兩處皆無檔→無全文"); ok &= (not h4)
        c4 = isinstance(_supplement_dir(str(inp)), Path)
        print(("  ✅" if c4 else "  ❌") + f" _supplement_dir 回傳 Path：{_supplement_dir(str(inp))}"); ok &= c4
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("✅ analysis_scope selftest 全過" if ok else "❌ 有失敗")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None); ap.add_argument("--inputs", default=None)
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--include-background", action="store_true")
    ap.add_argument("--selftest", action="store_true")
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
    scope = compute(corpus, cache, inputs, include_background=a.include_background)
    _print(scope)
    txt = write_need_manual_list(scope, inputs)   # 一律寫出『需補全文清單.txt』(確定性、永不過時)
    print(f"\n📄 需補全文清單已寫出：{txt}（{len(scope.get('need_manual_fulltext') or [])} 篇）")
    if a.json:
        print("\n--- JSON ---"); print(json.dumps(scope, ensure_ascii=False, indent=2))
    if a.write:
        out = Path(cache) / "_analysis_scope.json"
        out.write_text(json.dumps(scope, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 寫出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
