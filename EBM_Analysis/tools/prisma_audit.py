# -*- coding: utf-8 -*-
"""
prisma_audit.py — PRISMA 2020『27 項報告完整度稽核 gate』
=========================================================
把 PRISMA 2020 checklist 的 27 個編號項，逐項對「檢索報告產物」(_search_report.json)
與「GRADE 統合產物」(_synthesis.json) 做機器可檢的完整度稽核——非靠模型自律。
與 selfcheck_consistency（內部矛盾硬 gate）互補：那檔查「寫出來的東西彼此矛盾」，
本檔查「該報告的維度有沒有齊」。

每一項給四種狀態之一：
  PASS    —— 自動可驗、且結構化產物中找得到對應資料。
  FAIL    —— 自動可驗、但產物缺該維度（阻擋定稿；退出碼非 0）。
  MANUAL  —— 本質無法由結構化資料判定（如回顧層註冊/資金/利益衝突/單一評讀者流程），
             須人工聲明；預設「不阻擋」但一律列出，避免靜默跳過（呼應 no_silent_caps）。
  ATTEST  —— MANUAL 項已在 synthesis.prisma_attest[<項號>] 提供書面聲明 → 視為已涵蓋。
  PENDING —— 對應產物該階段尚未產出（如只跑完檢索、評讀未做），中性、不阻擋。

『不靜默跳過』鐵律：27 項一律全列、各標狀態與依據；數字一律從 cache/檢索報告帶、不硬編。

用法：
  python tools/prisma_audit.py [--strict] [--search <_search_report.json>] [--synth <_synthesis.json>]
  不給路徑時：search 走 run_state（fulltext_dir/_search_report.json）、synth 走 cache/_synthesis.json。
  --strict：未提供聲明的 MANUAL 項也計為失敗（要求 24/25/26 等補 prisma_attest 才放行）。

程式內：import prisma_audit; rows = prisma_audit.audit(search, syn, per_paper, artifacts_present)
        fails = prisma_audit.fails_of(rows)
"""
import json, sys, os, re, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import workdir; CACHE = Path(workdir.cache_dir())
except Exception:
    CACHE = Path(__file__).resolve().parent.parent / "cache"

MARK = {"PASS": "✅", "FAIL": "❌", "MANUAL": "⚠️", "ATTEST": "📝", "PENDING": "…"}
_DIGIT = re.compile(r"\d")


# ── 小工具 ────────────────────────────────────────────────────────────────
def _ne(v):
    """非空：字串去空白後非空、list/dict 長度 > 0。"""
    if v is None: return False
    if isinstance(v, str): return bool(v.strip())
    if isinstance(v, (list, dict, tuple)): return len(v) > 0
    return bool(v)

def _txt(*vals):
    """把多個可能是 str / list / dict 的欄位攤平成一段可搜尋文字。"""
    out = []
    for v in vals:
        if v is None: continue
        if isinstance(v, str): out.append(v)
        elif isinstance(v, (list, tuple)):
            for x in v: out.append(_txt(x))
        elif isinstance(v, dict):
            for x in v.values(): out.append(_txt(x))
        else: out.append(str(v))
    return " ".join(out)

def _kw(text, pat):
    return bool(re.search(pat, text or "", re.I))


# ── 核心：逐項稽核 ──────────────────────────────────────────────────────────
def audit(search, syn, per_paper=None, artifacts_present=False):
    """回傳 27 個 dict（PRISMA 順序）：{id, section, item, status, evidence}。純函式、好測。"""
    search = search or {}
    syn = syn or {}
    per_paper = per_paper or []
    attest = (syn.get("prisma_attest") or {}) if isinstance(syn.get("prisma_attest"), dict) else {}
    have_search = _ne(search)
    have_synth = _ne(syn)
    rows = []

    def add(num, section, item, status, evidence):
        rows.append({"id": str(num), "section": section, "item": item,
                     "status": status, "evidence": evidence})

    def auto(num, section, item, ok, ev_ok, ev_no, needs="synth"):
        """自動項：產物在→PASS/FAIL；產物不在→PENDING（中性）。"""
        if needs == "search" and not have_search:
            return add(num, section, item, "PENDING", "檢索報告尚未產出（該階段不適用）")
        if needs == "synth" and not have_synth:
            return add(num, section, item, "PENDING", "GRADE 統合尚未產出（評讀階段未做）")
        add(num, section, item, "PASS" if ok else "FAIL", ev_ok if ok else ev_no)

    def manual(num, section, item, default_note):
        """人工項：有 prisma_attest[num] → ATTEST，否則 MANUAL。"""
        st = str(num)
        if _ne(attest.get(st)):
            add(num, section, item, "ATTEST", "聲明：" + str(attest[st]).strip())
        else:
            add(num, section, item, "MANUAL", default_note)

    # 來源欄位
    s_method = _txt(search.get("method_notes"), search.get("method_summary"), search.get("narrative"))
    funnel = search.get("funnel") or []
    funnel_txt = _txt(funnel, search.get("funnel_closure"))
    sof = syn.get("sof") or []
    rob = syn.get("rob_summary") or []
    sc = syn.get("study_characteristics") or []
    limitations_txt = _txt(syn.get("limitations"))
    discuss_interp = _txt(syn.get("bottom_line"), syn.get("clinical_one_liner"))

    # ── TITLE & ABSTRACT ──
    title = _txt(syn.get("report_title"), search.get("title"), search.get("topic"))
    if not (have_search or have_synth):
        add(1, "標題", "1 標題標明為系統性回顧", "PENDING", "尚無任何產物")
    elif _ne(title):
        st = "PASS" if _kw(title, r"系統|回顧|實證|檢索|systematic|review|\bSR\b|meta") else "MANUAL"
        add(1, "標題", "1 標題標明為系統性回顧", st,
            ("標題：" + title[:60]) if st == "PASS" else f"標題未含『系統性回顧』字樣，請確認：{title[:40]}")
    else:
        add(1, "標題", "1 標題標明為系統性回顧", "FAIL", "無標題（檢索報告 title/topic 與 synthesis.report_title 皆空）")

    abstract_ok = _ne(syn.get("bottom_line")) and (_ne(syn.get("clinical_one_liner")) or _ne(per_paper))
    auto(2, "摘要", "2 結構式摘要（PRISMA-for-Abstracts）", abstract_ok,
         "bottom_line＋臨床一句話/逐篇結論齊備", "缺結構式摘要：synthesis.bottom_line / clinical_one_liner 為空")

    # ── INTRODUCTION ──
    auto(3, "前言", "3 背景與理由（rationale）", _ne(s_method) or _ne(search.get("background")) or _ne(search.get("narrative")),
         "檢索報告含方法/背景敘述", "缺背景理由敘述（method_summary/narrative/background 皆空）", needs="search")
    auto(4, "前言", "4 目的（PICO/必含連言軸）", _ne(search.get("conjunction_axes")),
         "必含連言軸＝PICO 雛形已定義", "缺目的/PICO：檢索報告 conjunction_axes 為空", needs="search")

    # ── METHODS ──
    auto(5, "方法", "5 合格條件（納入/排除）", _ne(search.get("conjunction_axes")) and _ne(search.get("axes")),
         "必含軸＋四軸展開已列＝合格條件", "缺合格條件：conjunction_axes / axes 不全", needs="search")
    src_ok = _ne(search.get("search_date")) and (
        _kw(s_method + funnel_txt, r"pubmed|crossref|consensus|clinicaltrial|europe\s*pmc|openalex|openevidence|embase|cochrane|cinahl"))
    auto(6, "方法", "6 資訊來源（資料庫＋檢索日）", src_ok,
         "已列資料庫名＋檢索日", "缺資訊來源：須列具名資料庫與檢索日（search_date / method_notes）", needs="search")
    auto(7, "方法", "7 完整檢索策略字串", _ne(search.get("axes")),
         "四軸實際 query 字串已列（axes）", "缺完整檢索策略：檢索報告 axes 為空", needs="search")
    auto(8, "方法", "8 選擇流程（篩選）", len(funnel) >= 2,
         f"PRISMA 漏斗 {len(funnel)} 階段", "缺選擇流程：funnel 階段 < 2", needs="search")
    manual(9, "方法", "9 資料蒐集流程",
           "預設由單一評讀者（Claude）抽取、逐篇二次重讀降幻覺；請於報告聲明流程（或設 prisma_attest['9']）")
    auto(10, "方法", "10 資料項目（結局＋變項）", _ne(sc) and _ne(sof),
         "納入研究特徵表＋SoF 結局清單齊備", "缺資料項目：study_characteristics / sof 為空")
    auto(11, "方法", "11 研究偏誤評估方法（RoB 2）", _ne(rob),
         "已用 RoB 2 逐領域評估", "缺 RoB 評估方法：rob_summary 為空")
    em_ok = any(_kw(_txt(o.get("relative_effect"), o.get("absolute_effect")), r"\b(RR|OR|HR|MD|SMD|NNT)\b|風險差|率差|平均差") for o in sof)
    auto(12, "方法", "12 效應量測度（RR/OR/HR/MD…）", em_ok,
         "SoF 已具名效應量測度", "缺效應量測度：SoF relative/absolute_effect 未見 RR/OR/HR/MD")
    syn_ok = _ne(syn.get("vote_counting_check")) and _ne(syn.get("consistency")) and _ne(syn.get("weight_adjudication"))
    auto(13, "方法", "13 統合方法", syn_ok,
         "vote_counting／一致性／權重裁量齊備", "缺統合方法：vote_counting_check / consistency / weight_adjudication 不全")
    auto(14, "方法", "14 報告偏誤評估方法", _ne(syn.get("publication_bias")) or _ne(syn.get("missing_evidence_sensitivity")),
         "已聲明發表偏誤/缺失證據評估", "缺報告偏誤評估方法：publication_bias / missing_evidence_sensitivity 皆空")
    auto(15, "方法", "15 確定性評估方法（GRADE）", _ne(syn.get("body_of_evidence")) or any(_ne(o.get("certainty")) for o in sof),
         "已用 GRADE 評確定性", "缺確定性評估方法：sof.certainty / body_of_evidence 皆空")

    # ── RESULTS ──
    flow_num = bool(funnel) and any(_DIGIT.search(_txt(s.get("remain"), s.get("change"))) for s in funnel)
    excl_reason = _kw(funnel_txt, r"排除|剔除|exclud") and _kw(funnel_txt, r"理由|原因|reason|缺")
    if not have_search:
        add(16, "結果", "16 研究選擇（流程圖＋排除理由）", "PENDING", "檢索報告尚未產出（該階段不適用）")
    elif not flow_num:
        add(16, "結果", "16 研究選擇（流程圖＋排除理由）", "FAIL", "缺 16a：流程圖各階段數字（funnel remain/change 無數字）")
    elif not excl_reason:
        add(16, "結果", "16 研究選擇（流程圖＋排除理由）", "MANUAL", "16a 數字齊；16b 排除理由未自動偵測，請確認流程圖各階段已標排除數＋理由")
    else:
        add(16, "結果", "16 研究選擇（流程圖＋排除理由）", "PASS", "16a 數字＋16b 排除理由齊備")

    auto(17, "結果", "17 納入研究特徵", _ne(sc), "納入研究特徵表齊備", "缺納入研究特徵：study_characteristics 為空")
    auto(18, "結果", "18 研究內偏誤（結果）", _ne(rob), "RoB 2 逐領域摘要已列", "缺 RoB 結果：rob_summary 為空")
    if not have_synth:
        add(19, "結果", "19 個別研究結果", "PENDING", "GRADE 統合尚未產出")
    else:
        ok19 = _ne(per_paper)
        add(19, "結果", "19 個別研究結果", "PASS" if ok19 else "MANUAL",
            "逐篇報告（per_paper）齊備" if ok19 else "per_paper 為空：請確認逐篇結果已於報告呈現（效應＋CI）")
    syn_res_ok = _ne(sof) and _ne(syn.get("consistency"))
    sens_note = "" if (_ne(syn.get("subgroup_implications")) or _ne(syn.get("missing_evidence_sensitivity"))) else "（提醒：20d 敏感度/次群組 subgroup_implications/missing_evidence_sensitivity 為空）"
    auto(20, "結果", "20 統合結果（效應＋CI＋異質性）", syn_res_ok,
         "SoF 效應＋一致性已呈現" + sens_note, "缺統合結果：sof / consistency 不全")
    auto(21, "結果", "21 報告偏誤評估結果", _ne(syn.get("publication_bias")),
         "已陳述發表偏誤評估結果", "缺報告偏誤結果：publication_bias 為空")
    auto(22, "結果", "22 證據確定性（結果）", _ne(syn.get("body_of_evidence")) or any(_ne(o.get("certainty")) for o in sof),
         "逐 outcome 確定性已列", "缺確定性結果：body_of_evidence / sof.certainty 皆空")

    # ── DISCUSSION（23：a 詮釋／b 證據限制／c 流程限制／d 意涵） ──
    if not have_synth:
        add(23, "討論", "23 討論（詮釋／限制／意涵）", "PENDING", "GRADE 統合尚未產出")
    else:
        vague_only = _kw(limitations_txt + discuss_interp, r"需要更多研究|more research") and not _kw(
            limitations_txt + _txt(syn.get("subgroup_implications")), r"族群|比較|對照|結局|設計|劑量|頭對頭|未來試驗|gap|缺口|specific")
        if not _ne(discuss_interp):
            add(23, "討論", "23 討論（詮釋／限制／意涵）", "FAIL", "缺 23a 結果詮釋：bottom_line / clinical_one_liner 為空")
        elif not _ne(limitations_txt):
            add(23, "討論", "23 討論（詮釋／限制／意涵）", "FAIL", "缺 23b 證據限制：limitations 為空")
        elif vague_only:
            add(23, "討論", "23 討論（詮釋／限制／意涵）", "FAIL", "23d 意涵僅籠統『需要更多研究』；須具體指明缺口（族群/比較/結局/設計）")
        else:
            add(23, "討論", "23 討論（詮釋／限制／意涵）", "PASS", "詮釋＋證據限制＋具體研究意涵齊備")

    # ── OTHER INFORMATION（24–27；多為回顧層人工聲明） ──
    manual(24, "其他", "24 註冊與計畫書（protocol）",
           "回顧層註冊（如 PROSPERO）/protocol/偏離須人工聲明；若未事前註冊請明述（設 prisma_attest['24']）")
    manual(25, "其他", "25 經費支持（funding）",
           "本回顧之經費來源須人工聲明（設 prisma_attest['25']）")
    manual(26, "其他", "26 利益衝突（competing interests）",
           "評讀者利益衝突須人工聲明（設 prisma_attest['26']）")
    if str(27) in attest and _ne(attest.get("27")):
        add(27, "其他", "27 資料／程式／材料可得性", "ATTEST", "聲明：" + str(attest["27"]).strip())
    elif artifacts_present:
        add(27, "其他", "27 資料／程式／材料可得性", "PASS",
            "本框架產出結構化 cache JSON＋PRISMA checklist＋報告，資料可得")
    else:
        add(27, "其他", "27 資料／程式／材料可得性", "MANUAL",
            "請聲明資料/程式/材料可得性（本框架之 cache JSON＋checklist 可作載體；設 prisma_attest['27']）")

    return rows


def fails_of(rows, strict=False):
    """回傳阻擋清單字串。預設只擋 FAIL；strict 時 MANUAL（未聲明）也算失敗。"""
    out = []
    for r in rows:
        if r["status"] == "FAIL":
            out.append(f"項{r['id']} {r['item']}：{r['evidence']}")
        elif strict and r["status"] == "MANUAL":
            out.append(f"項{r['id']} {r['item']}（strict：缺人工聲明）：{r['evidence']}")
    return out


def check(strict=False):
    """供 verify_all 等以程式呼叫：載入產物→稽核→回 (rows, fails)。"""
    search, syn, per_paper, art = _load()
    rows = audit(search, syn, per_paper, artifacts_present=art)
    return rows, fails_of(rows, strict)


# ── 載入產物 ────────────────────────────────────────────────────────────────
def _load(search_path=None, synth_path=None):
    search = {}
    if search_path is None:
        try:
            import run_state
            ftd = (run_state.load() or {}).get("paths", {}).get("fulltext_dir")
            cand = os.path.join(ftd, "_search_report.json") if ftd else None
            search_path = cand if cand and os.path.exists(cand) else None
        except Exception:
            search_path = None
    if search_path and os.path.exists(search_path):
        try: search = json.loads(Path(search_path).read_text(encoding="utf-8"))
        except Exception: search = {}

    synth_path = synth_path or str(CACHE / "_synthesis.json")
    obj = {}
    if os.path.exists(synth_path):
        try: obj = json.loads(Path(synth_path).read_text(encoding="utf-8"))
        except Exception: obj = {}
    syn = obj.get("synthesis", obj) if isinstance(obj, dict) else {}
    per_paper = obj.get("per_paper") if isinstance(obj, dict) else None

    # 27 資料可得性：報告/輸出產物是否存在
    art = False
    try:
        for d in (workdir.outputs_dir(),):
            if d and os.path.isdir(d) and any(Path(d).glob("*")):
                art = True; break
        if not art:
            import run_state
            paths = (run_state.load() or {}).get("paths", {})
            art = any(paths.get(k) and os.path.exists(paths[k]) for k in ("grade_pdf", "search_report_pdf", "reports_dir"))
    except Exception:
        pass
    return search, syn, per_paper, art


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--search"); ap.add_argument("--synth")
    a = ap.parse_args()
    search, syn, per_paper, art = _load(a.search, a.synth)
    rows = audit(search, syn, per_paper, artifacts_present=art)

    # 印 27 項表
    print("== PRISMA 2020 — 27 項報告完整度稽核 ==")
    cur = None
    for r in rows:
        if r["section"] != cur:
            cur = r["section"]; print(f"\n【{cur}】")
        print(f"  {MARK.get(r['status'],'?')} {r['item']}  — {r['evidence']}")

    # 寫 checklist 產物（供報告附錄／item 27 可得性載體）
    try:
        out = CACHE / "_prisma_checklist.json"
        out.write_text(json.dumps({"standard": "PRISMA 2020", "items": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n→ 已寫 checklist：{out}")
    except Exception as e:
        print("（checklist 未寫出：", str(e)[:60], "）")

    # 彙總
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print(f"\n== 彙總 ==  PASS {c['PASS']} / FAIL {c['FAIL']} / MANUAL {c['MANUAL']} / ATTEST {c['ATTEST']} / PENDING {c['PENDING']}（共 {len(rows)} 項）")
    fails = fails_of(rows, a.strict)
    if c["MANUAL"]:
        print(f"⚠️  {c['MANUAL']} 項需人工聲明（{'strict→已計失敗' if a.strict else '未阻擋，但須於報告補齊；可設 synthesis.prisma_attest'}）")
    if c["PENDING"]:
        print(f"…  {c['PENDING']} 項對應產物尚未產出（中性、不阻擋）")
    if fails:
        print(f"\n❌ {len(fails)} 項未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("\n✅ 自動可驗的 PRISMA 項全數齊備——可定稿。" + ("" if not c["MANUAL"] else "（人工聲明項請另確認）"))


if __name__ == "__main__":
    main()
