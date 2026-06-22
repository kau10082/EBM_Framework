# -*- coding: utf-8 -*-
"""
build_report_data.py — SR 報告資料『制式欄位＋務實填滿』確定性產生器
====================================================================
取代「每次手拼 _search_report.json」(欄位飄、常缺格)。從 cache 既有產物確定性組裝，
**固定欄位、每格務實填滿（缺就自動回填）、撤稿排除**，並在寫出前自我驗證無缺格。

制式欄位（canonical，勿自創）：
  核心 Study 表 reports = [標題, PMID, DOI, 全文狀態, 交叉檢核]   （5 欄，全必填）
  背景表  background     = [標題, PMID, DOI, 型態, 全文狀態, 檢核] （6 欄，全必填）
  進行中  ongoing_trials = [登錄號, 內容, 狀態]                    （3 欄，登錄號必填）
列舉值：全文狀態∈{線上,僅摘要,需補}；檢核∈{VERIFIED,UNVERIFIED,PARTIAL,UNRESOLVED}
        （xref_verify 實際詞彙；RETRACTED 與 OFF_TOPIC 不應入表，混入即 validate 失敗）；
        DOI 缺→「缺」(顯式)；PMID 必有(無→以登錄號/「—」+理由，不留空)。

讀：g6_verified / g7_final_decision / g8_fulltext_audit / g1_ctgov（皆 cache）。
缺 title/全文狀態/登錄號 → 以 EuropePMC core 回填（自我修復、不留空）。

用法：python build_report_data.py --cache <dir> --out <_search_report.json>
"""
import sys, json, argparse, urllib.request, urllib.parse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

CORE_COLS = ["標題", "PMID", "DOI", "全文狀態", "交叉檢核"]
BG_COLS = ["標題", "PMID", "DOI", "型態", "全文狀態", "檢核"]
ONGOING_COLS = ["登錄號", "內容", "狀態"]
FT_ENUM = {"線上", "僅摘要", "需補"}
# 交叉檢核欄合法值＝xref_verify 實際詞彙（去掉 RETRACTED/OFF_TOPIC——它們不該出現在納入/背景表）。
# 缺這個 enum 守門時，PARTIAL/UNRESOLVED 等會被靜默放行進報告表（外部審查指出的契約漂移）。
XREF_ENUM = {"VERIFIED", "UNVERIFIED", "PARTIAL", "UNRESOLVED"}

def _load(cache, f):
    p = Path(cache) / f
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None

def _epmc_core(pmid):
    try:
        u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:%s%%20AND%%20SRC:MED"
             "&format=json&resultType=core&pageSize=1" % pmid)
        r = (json.load(urllib.request.urlopen(u, timeout=25))["resultList"]["result"] or [{}])[0]
        return r
    except Exception:
        return {}

def _ft_status(pmid, r=None):
    """線上/僅摘要/需補——以實際 OA 旗標＋Unpaywall 判，不留 '?'。"""
    r = r or _epmc_core(pmid)
    if r.get("isOpenAccess") == "Y" or r.get("pmcid"):
        return "線上"
    doi = r.get("doi")
    if doi:
        try:
            d = json.load(urllib.request.urlopen(
                "https://api.unpaywall.org/v2/" + urllib.parse.quote(doi) + "?email=kau10082@gmail.com", timeout=20))
            if d.get("is_oa"):
                return "線上"
        except Exception as e:
            # 區分「抓取失敗」與「來源真的非 OA」：網路/403/逾時不可靜默當「僅摘要」，
            # 否則暫時性錯誤會把可得全文誤標。發 stderr 警告留痕，供操作者複查。
            sys.stderr.write(f"⚠️ _ft_status: Unpaywall 查詢失敗（doi={doi}：{str(e)[:60]}），暫記『僅摘要』待複查\n")
    return "僅摘要"

def _doctype(v):
    """背景表型態：優先用明確 doctype；缺則從 pubtypes/標題**程式化回推**，
    避免依賴 LLM 在 g6_verified 手填 doctype 而恆空、SR/MA/指引靜默漏件（外部審查指出的契約破口）。"""
    dt = v.get("doctype")
    if dt in ("Meta-Analysis", "Systematic Review", "Guideline"):
        return dt
    pts = ((v.get("sources") or {}).get("pubmed") or {}).get("pubtypes") or []
    blob = (" ".join(str(p) for p in pts) + " " + str((v.get("input") or {}).get("title") or v.get("title") or "")).lower()
    if "meta-analysis" in blob or "meta analysis" in blob or "統合分析" in blob:
        return "Meta-Analysis"
    if "systematic review" in blob or ("系統" in blob and "回顧" in blob):
        return "Systematic Review"
    if "guideline" in blob or "指引" in blob:
        return "Guideline"
    return dt  # 其餘原樣（None 或原始醫學型態）


def build(cache):
    ver = _load(cache, "g6_verified.json") or []
    dec = _load(cache, "g7_final_decision.json") or {}
    aud = _load(cache, "g8_fulltext_audit.json") or {"have": [], "need": []}
    ctg = _load(cache, "g1_ctgov.json") or []
    vmap = {str(v.get("pmid")): v for v in ver if v.get("pmid")}
    retr = {str(v.get("pmid")) for v in ver if v.get("verdict") == "RETRACTED"}
    ftmap = {}
    for r in aud.get("have", []):
        if r.get("pmid") is None:
            continue
        st = str(r.get("status") or "")
        if "有全文" in st:                       # substring：相容「有全文 (PDF)」等措辭，不因尾綴被誤降
            ftmap[str(r["pmid"])] = "線上"
        else:
            if st and st not in ("僅摘要", "摘要", "AI合成摘要", "ai_summary_only"):
                sys.stderr.write(f"⚠️ g8 have 段 status『{st}』非預期（pmid={r['pmid']}），暫當『僅摘要』——請確認是否其實有全文\n")
            ftmap[str(r["pmid"])] = "僅摘要"
    for r in aud.get("need", []):
        if r.get("pmid") is not None: ftmap[str(r["pmid"])] = "需補"

    def xref(pm):
        v = vmap.get(pm, {})
        return "VERIFIED" if v.get("verdict") == "VERIFIED" else (v.get("verdict") or "UNVERIFIED")

    def fill_row5(pm):
        v = vmap.get(pm, {}); core = None
        title = (v.get("title") or "").strip()
        if not title or len(title) < 5:
            core = _epmc_core(pm); title = (core.get("title") or "").strip() or ("(PMID %s)" % pm)
        ft = ftmap.get(pm) or _ft_status(pm, core)
        if ft not in FT_ENUM: ft = "僅摘要"
        doi = (v.get("doi") or (core or {}).get("doi") or "缺")
        return [title[:95], str(pm), doi, ft, xref(pm)]

    # 1. 核心 Study 表（排除撤稿；保持 g7 的 study 分組與順序）
    # 主報告置頂：**資料驅動**——優先讀 g7 提供的 main_reports（study名→主報告 PMID），
    # 否則以該 study 列表首篇為主報告。不再硬編特定主題的 PMID（曾殘留前案 COPD 試驗表，
    # 換主題即全 miss → 主報告排序保護失效、可能漏樞紐主報告）。
    # main_reports 的 key 與 study_reports 一樣先正規化（砍括號/NCT），否則 g7 兩處 key 形不一致時
    # MAIN.get(name) 靜默 miss → 退回「首篇」（g7 不保證首位＝主報告）→ 主報告置頂保護失效。
    MAIN = {str(k).split("(")[0].strip(): str(v) for k, v in (dec.get("main_reports") or {}).items()}
    studies = []
    for tr, pmids in dec.get("study_reports", {}).items():
        if "PENDING" in tr: continue
        name = tr.split("(")[0].strip()   # 與 MAIN key 同正規化（砍括號＋strip），確保對得上
        pmids = [str(p) for p in pmids if str(p) not in retr]
        main = MAIN.get(name)
        if not main and pmids:
            main = pmids[0]  # fallback：列表首篇；但 g7 未保證首位＝主報告，故出警告供複查
            sys.stderr.write(f"⚠️ study「{name}」未在 g7.main_reports 指定主報告，暫取列表首篇 {main} 置頂——請確認是否為主報告\n")
        if main and main in pmids: pmids = [main] + [p for p in pmids if p != main]
        if pmids:
            studies.append({"study": name, "reports": [fill_row5(p) for p in pmids]})

    # 2. 背景表（SR/MA＋指引；排除撤稿）
    background = []
    prim = {str(p) for g in studies for p in [r[1] for r in g["reports"]]}
    for v in ver:
        pm = str(v.get("pmid") or "")
        if pm and (pm in retr or pm in prim): continue
        dt = _doctype(v)   # 程式化回推（不單靠手填 doctype）
        if dt in ("Meta-Analysis", "Systematic Review", "Guideline"):
            if pm:
                row = fill_row5(pm)  # [title,pmid,doi,ft,xref]
                background.append([row[0][:78], row[1], row[2], dt, row[3], row[4]])
            else:
                # 無 PMID（preprint/DOI-only）：依 spec『不留空，以登錄號/DOI＋理由』→ 以 DOI 當識別、標 preprint。
                doi = (v.get("doi") or "缺")
                ident = ("DOI:" + doi) if doi != "缺" else "—(preprint,無PMID)"
                title = ((v.get("title") or "").strip()[:78]) or "(無標題)"
                xr = v.get("verdict") if v.get("verdict") in XREF_ENUM else "UNVERIFIED"
                background.append([title, ident, doi, dt, "需補", xr])
    # 背景空表但仍有非主研究的 verified 記錄 → 警告（surface doctype 缺失致漏件，不靜默）
    if not background and any(str(v.get("pmid")) not in retr and str(v.get("pmid")) not in prim for v in ver if v.get("pmid")):
        sys.stderr.write("⚠️ 背景表空，但尚有非主研究的 verified 記錄——確認 g6_verified 是否含可辨識型態（SR/MA/指引可能漏件）\n")

    # 3. 進行中試驗（CT.gov 招募中/未招募 + 已發表 protocol；登錄號必填）
    ONG = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}
    ongoing = []
    for s in ctg:
        # 主題無關：g1_ctgov 已是本主題 CT.gov 檢索腿的結果（已被搜尋字串範圍化），此處只按狀態收，
        # 不再硬編特定藥物正則（曾寫死 COPD triple/dual 字串，換主題即全 miss→空表→下游驗證 crash）。
        if s.get("status") in ONG and str(s.get("nct") or "").strip():
            intr = ", ".join((s.get("intr") or [])[:3]); t = s.get("title") or ""
            ongoing.append([s["nct"], (t[:70] + " ｜ " + intr[:40]), s.get("status")])
    # 額外進行中（已發表 protocol/他庫登錄，如 TRACK；登錄號必填）— 讀 cache 的 g_extra_ongoing.json
    extra = _load(cache, "g_extra_ongoing.json") or []
    for e in extra:
        if e and str(e[0]).strip():
            ongoing.append([e[0], e[1], e[2] if len(e) > 2 else "protocol/待結果"])
    return {"studies": studies, "background": background, "ongoing_trials": ongoing}

def validate(data):
    """完整性守門：每張表所有必填格非空、非佔位、非 '?'，列舉值合法。回 fails。"""
    fails = []
    for grp in data.get("studies", []):
        for r in grp.get("reports", []):
            if len(r) != 5: fails.append(f"[{grp.get('study')}] 核心列非 5 欄"); continue
            for col, val in zip(CORE_COLS, r):
                if val in (None, "", "?", "？", "(無標題)"): fails.append(f"[{grp.get('study')}] 核心『{col}』空/佔位（pmid={r[1]}）")
            if r[3] not in FT_ENUM: fails.append(f"[{grp.get('study')}] 全文狀態非法『{r[3]}』")
            if r[4] not in XREF_ENUM: fails.append(f"[{grp.get('study')}] 交叉檢核非法『{r[4]}』（須∈{sorted(XREF_ENUM)}；pmid={r[1]}）")
    for r in data.get("background", []):
        if len(r) != 6: fails.append("背景列非 6 欄"); continue
        for col, val in zip(BG_COLS, r):
            if val in (None, "", "?", "？"): fails.append(f"背景『{col}』空（pmid={r[1]}）")
        if r[4] not in FT_ENUM: fails.append(f"背景全文狀態非法『{r[4]}』（pmid={r[1]}）")
        if r[5] not in XREF_ENUM: fails.append(f"背景檢核非法『{r[5]}』（須∈{sorted(XREF_ENUM)}；pmid={r[1]}）")
    if not data.get("ongoing_trials"):
        # 空表降為警告（非阻擋）：有些主題 CT.gov 確實無招募中/進行中試驗，不該讓整個驗證 crash
        sys.stderr.write("⚠️ 進行中試驗表空——該主題 CT.gov 無招募中/進行中試驗，或未檢索到；請確認是否合理\n")
    for o in data.get("ongoing_trials", []):
        if not str(o[0]).strip() or str(o[0]) in ("—", "-"): fails.append(f"進行中缺登錄號：{str(o[1])[:40]}")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--merge-into", default=None, help="把三表併入既有 _search_report.json（保留其餘欄位）")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    tables = build(a.cache)
    fails = validate(tables)
    if fails:
        print("❌ 報告資料完整性未過（有缺格/佔位）：")
        for f in fails: print("  -", f)
        sys.exit(1)
    target = a.merge_into or a.out
    if a.merge_into and Path(a.merge_into).exists():
        data = json.loads(Path(a.merge_into).read_text(encoding="utf-8"))
        data.update(tables)
    else:
        data = tables
    if target:
        Path(target).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✅ 制式三表已寫出（核心 {sum(len(s['reports']) for s in tables['studies'])} 報告／背景 {len(tables['background'])}／進行中 {len(tables['ongoing_trials'])}）→ {target}")
    else:
        print("✅ 完整性通過（未指定 --out/--merge-into，僅驗證）")

if __name__ == "__main__":
    main()
