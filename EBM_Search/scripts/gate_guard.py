# -*- coding: utf-8 -*-
"""
gate_guard.py — 檢索端『關卡守門』總 orchestrator（harness 可掛 Stop hook 自動跑）
================================================================================
依 cache 內已存在的產物，自動判斷目前在哪些關、逐關跑對應硬 gate：
  • g1_legs_manifest.json + g0_strategy.json → check_strategy_approved（Gate ⓪ 策略須先經使用者核准才可檢索，防搶跑）
  • g1_legs_manifest.json           → leg_exhaust_check（Gate ① 每腿取盡）
  • g2c_FINAL_content.json (+unpaywall)→ Unpaywall 覆蓋稽核（Gate ②c 必跑 Unpaywall）
  • _search_report.json             → funnel_check（流程數字閉合）
  • _corpus_seed.json               → fulltext_audit（交接前 Unpaywall 複查）

設計目標：把「取盡」「跑 Unpaywall」從靠 Claude 記得，變成**機器條件**。
任一檢查 FAIL → exit 1（Stop hook 收到非零碼即可 block 回灌）。
`--auto`：找不到任何 EBM cache 時**靜默 exit 0**（非 EBM 對話不打擾）。

用法：
  python gate_guard.py --cache <cache_dir>        # 明指 cache
  python gate_guard.py --auto                      # 自動從 run_state 找 cache；無則靜默放行
  python gate_guard.py --auto --quiet              # Stop hook 用：PASS 不輸出
"""
import sys, os, json, argparse, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "EBM_Analysis" / "tools"))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ACTIVE_FLAG = "_search_active.flag"  # Gate ① 開始時建、交接/結案時移除；不存在＝檢索非進行中→守門休眠

def _load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None

def _active(cache):
    """檢索是否進行中：唯有哨兵旗標存在才讓 Stop hook 生效（避免全域每回合打擾）。"""
    return cache is not None and (cache / ACTIVE_FLAG).exists()

def _find_cache(explicit=None):
    if explicit and Path(explicit).exists():
        return Path(explicit)
    # 從 EBM run_state 解析 cache_dir
    try:
        import run_state
        st = run_state.load() or {}
        cd = (st.get("paths") or {}).get("cache_dir")
        if cd and Path(cd).exists():
            return Path(cd)
    except Exception:
        pass
    # 退而求其次：env / 預設 OneDrive 文件
    for cand in [os.environ.get("EBM_CACHE_DIR"),
                 os.path.expanduser(r"~/OneDrive/文件/EBM_Framework/work/cache")]:
        if cand and Path(cand).exists():
            return Path(cand)
    return None

def _norm_doi(d):
    if not d: return None
    import re
    d = d.lower().strip(); d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d); return d or None

def check_unpaywall_coverage(cache):
    """Gate ②c：每筆『非全文且有 DOI』必須已過 Unpaywall（**只做覆蓋稽核**）。
    註：是否『其實有 OA 卻誤判取不到』屬全文取得性判定——OA 旗標 ≠ 抓得到（IMPACT/ETHOS 旗標 OA 卻 403）。
    本關在『內容階段』無從得知實抓結果（fetch_failed/fulltext_verified 是後段 verify_have_fetchable 才寫進
    seed.json 的欄位、g2c_FINAL_content.json 沒有），故不在此用 OA 旗標反推分類對錯——那是 check_have_verified
    /verify_have_fetchable 實抓蓋章的職責。②c 只查『Unpaywall 有沒有跑』，避免關責外溢、與 have 守門打架。"""
    content = _load(cache / "g2c_FINAL_content.json")
    if content is None:
        return None  # 此關尚未到
    up = _load(cache / "g2c_unpaywall.json") or {}
    fails = []
    not_checked = []
    for c in content:
        cls = c.get("class") or ""
        if cls.startswith("有全文"):
            continue
        doi = _norm_doi(c.get("doi"))
        if not doi:
            continue  # 無 DOI 無法 Unpaywall（非失敗）
        if up.get(doi) is None:
            not_checked.append(doi)
    if not_checked:
        fails.append(f"②c 有 {len(not_checked)} 筆『非全文且有 DOI』未過 Unpaywall（漏跑）：{not_checked[:5]}{'…' if len(not_checked)>5 else ''}")
    return fails

def check_waiting_fulltext(cache):
    """Gate ③：判『待評估(無內容)』者，必須真的無任何全文路徑可取；
    若還有 PMCID / Unpaywall PDF / OA 旗標未抓就丟待評估 → FAIL（全文有無以實際抓取為準）。"""
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None  # 尚未到/未產最終 g3
    fails = []
    leaked = []
    for r in g3:
        v = r.get("verdict") or ""
        if not v.startswith("待評估"):
            continue
        # 仍有全文路徑卻判待評估＝漏抓
        if r.get("pmcid") or r.get("inPMC") or r.get("oa_pdf") or r.get("oa_url") or r.get("isOA") == "Y" \
           or str(r.get("class") or "").startswith("有全文"):
            # 唯一放行：已『窮盡所有管道』或『待人工補全文』的明確標記；
            # 單純一次『抓取失敗(404/逾時/403)』不算——有路徑就要重試(EuropePMC→NCBI→Unpaywall→人工)
            if r.get("channels_exhausted") or ("待人工補全文" in v) or ("已窮盡管道" in v):
                continue
            leaked.append((r.get("title") or r.get("pmid") or r.get("doi") or "?")[:50])
    if leaked:
        fails.append(f"③ 有 {len(leaked)} 筆有全文路徑(PMC/OA/Unpaywall)卻丟待評估、未窮盡抓取：{leaked[:5]}{'…' if len(leaked)>5 else ''}（單次抓取失敗≠無內容；須重試 EuropePMC→NCBI→Unpaywall→人工，或明標 channels_exhausted/待人工補全文）")
    return fails

def check_screen_awaiting_resolved(cache):
    """Gate ③『待評估須先核對全文、不得只憑摘要』（2026-06 使用者糾正）：
    進 ③ 的候選都已有內容（摘要，且多數有全文），③ 必須用全文/摘要做出『切題/離題』二元判定；
    僅當『實際抓過全文仍無法核對』才可掛 ③待評估。故 g2c_awaiting_classification.json 內每筆
    若有 doi/pmid/oa_url（有全文路徑）卻無 fulltext_checked／oa_fetch_attempted／channels_exhausted 證明
    → FAIL（代表只憑摘要就punt成待評估，沒去抓全文核對對照 C）。"""
    aw = _load(cache / "g2c_awaiting_classification.json")
    if aw is None:
        return None
    fails = []
    for a in aw:
        has_path = a.get("doi") or a.get("pmid") or a.get("oa_url") or a.get("pmcid")  # 全文路徑：ID/OA/PMC（審查 🔴🟡 補強）
        attempted = a.get("fulltext_checked") or a.get("oa_fetch_attempted") or a.get("channels_exhausted")
        if has_path and not attempted:
            fails.append("%s 列 ③待評估但有 doi/pmid/oa_url 卻無全文核對證明(fulltext_checked/oa_fetch_attempted)："
                         "③候選已有內容，須抓全文核對對照 C 後做出切題/離題，不得只憑摘要 punt 成待評估"
                         % (a.get("paper_id") or a.get("uid") or a.get("title")))
    return fails

def check_partition_provenance(cache):
    """Gate ③ 反坍縮：以 uid 獨立重算，抓 key-collision 造成的污染/漏失。
    (1) 分割閉合：screened ⊎ awaiting 的 uid 必須『無重複、互斥、恰覆蓋』base 全部 uid。
    (2) 已篩來源證明：每筆 screened 的 base 紀錄必須真的有 abstract 或其 uid 在 fetched 表中
        ——否則代表是被坍縮鍵污染進來的『無內容卻拿到判定』。"""
    base = _load(cache / "g2c_FINAL_content.json")
    scr = _load(cache / "g3_FINAL_screen.json")
    awa = _load(cache / "g2c_awaiting_classification.json")
    if base is None or scr is None or awa is None:
        return None
    fetched = _load(cache / "g3_fetched_by_uid.json") or {}
    fails = []
    base_by_uid = {b.get("uid"): b for b in base}
    if any(b.get("uid") is None for b in base):
        return ["g2c_FINAL_content.json 有紀錄缺 uid：無法以唯一鍵防坍縮（請先 uid 化）"]
    if len(base_by_uid) != len(base):
        fails.append(f"base uid 不唯一（{len(base)} 筆但只有 {len(base_by_uid)} 個 uid）：uid 必須穩定唯一")
    su = [s.get("uid") for s in scr]; au = [a.get("uid") for a in awa]
    sset, aset = set(su), set(au)
    if len(su) != len(sset): fails.append(f"screened uid 有重複（{len(su)}→{len(sset)}）")
    if len(au) != len(aset): fails.append(f"awaiting uid 有重複（{len(au)}→{len(aset)}）")
    overlap = sset & aset
    if overlap: fails.append(f"同一 uid 同時在 screened 與 awaiting（{len(overlap)} 筆）：分割不互斥")
    missing = set(base_by_uid) - sset - aset
    extra = (sset | aset) - set(base_by_uid)
    if missing: fails.append(f"有 {len(missing)} 筆 base uid 未被分類（漏失）")
    if extra: fails.append(f"有 {len(extra)} 個 uid 不在 base（憑空冒出）")
    # (2) provenance：screened 每筆必須有自己的內容
    no_content = []
    for s in scr:
        b = base_by_uid.get(s.get("uid"))
        if b is None: continue
        has_ab = bool((b.get("abstract") or "").strip())
        if not has_ab and s.get("uid") not in fetched:
            no_content.append((b.get("title") or b.get("uid") or "?")[:45])
    if no_content:
        fails.append(f"③ 有 {len(no_content)} 筆 screened 其 base 無 abstract 且 uid 不在 fetched 表（疑遭坍縮鍵污染、無內容卻拿到判定）：{no_content[:5]}")
    return fails

def check_have_verified(cache):
    """『判 have 必須實抓驗證』守門（防 OA 旗標高估）。
    讀 seed.json／_corpus_seed.json：凡 verdict=included 且要評讀(grade_track∈full/targeted_harms)、
    fulltext_status=have(online，無本機 pdf_file)者，必須帶 `fulltext_verified=true`
    （由 verify_have_fetchable.py 實抓蓋章）。否則代表只信了 OA 旗標、沒實抓 → FAIL，強制跑驗證器。
    （2026-06 實測：IMPACT/ETHOS 憑 Unpaywall is_oa 判 have，實抓 403/假陽性，拖到評讀才爆。）"""
    seed = _load(cache / "seed.json") or _load(cache / "_corpus_seed.json")
    if seed is None:
        return None
    papers = seed.get("papers", []) if isinstance(seed, dict) else seed
    fails = []
    for p in papers:
        if p.get("verdict") != "included":
            continue
        gt = (p.get("suggested") or {}).get("grade_track") or p.get("grade_track")
        if gt not in ("full", "targeted_harms"):
            continue
        if p.get("fulltext_status") not in ("have", "have_manual"):
            continue
        if p.get("pdf_file"):           # 本機 PDF 直接信任
            continue
        ch = (p.get("fulltext_channel") or "").lower()
        if "online" not in ch and "pmc" not in ch and "unpaywall" not in ch and ch != "":
            continue
        if not p.get("fulltext_verified"):
            fails.append("%s 判 have(online) 但未經 verify_have_fetchable 實抓驗證(無 fulltext_verified)"
                         "——只信 OA 旗標易高估；請跑 `verify_have_fetchable.py --in seed.json --only-included`，"
                         "假 have 改 need-supplement" % (p.get("paper_id") or p.get("pmid")))
    return fails

def check_strategy_approved(cache):
    """防『搶跑』（Gate ⓪→①）：Stage A 廣蒐（g1_legs_manifest.json）只能在
    『檢索策略已向使用者報告並取得確認』後才執行。
    落地：使用者確認策略後，才在 g0_strategy.json 設 approved_by_user=true。
    g1 已產出但 g0 未核准＝在使用者確認策略前就動手檢索＝搶跑 → FAIL。
    （2026-06 使用者糾正：曾未報告策略、未等確認即執行檢索，且擅自縮放範圍；此 gate 即為此而立。）"""
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None  # 尚未廣蒐：此關不適用
    strat = _load(cache / "g0_strategy.json")
    if not strat:
        return ["g1_legs_manifest.json 已產出但無 g0_strategy.json：廣蒐前須先寫出檢索策略並經使用者確認（防搶跑）"]
    if not strat.get("approved_by_user"):
        return ["Stage A 廣蒐（g1_legs_manifest.json 已產出）但 g0_strategy.json 未標記 approved_by_user=true："
                "檢索策略必須先報告並經使用者確認後才可執行檢索（防『搶跑』、防擅自縮放範圍；"
                "使用者確認策略後才在 g0_strategy.json 設 approved_by_user=true）"]
    return []

def check_axis_coverage(cache):
    """Gate ①：每腿 query 對每條 in_query 必含軸 ≥1 同義詞命中（反四軸沒展開/過度簡化）。"""
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None
    strat = _load(cache / "g0_strategy.json")
    try:
        import axis_coverage_check
        return axis_coverage_check.check(man, strat)
    except Exception as e:
        return [f"axis_coverage_check 載入失敗：{str(e)[:80]}"]

def check_comparator_purity(cache):
    """Gate ⓪／①：檢索 query 只含 in_query 軸，不得摻入對照/排除軸（in_query=false）——反『C 軸進 query 砍 recall』。
    manifest 優先；無 manifest 時退回 g0.legs，讓 ⓪ 策略階段就能被稽核。"""
    strat = _load(cache / "g0_strategy.json")
    man = _load(cache / "g1_legs_manifest.json")
    legs = man if man is not None else (strat.get("legs") if isinstance(strat, dict) else None)
    if legs is None:
        return None
    try:
        import comparator_purity_check
        return comparator_purity_check.check(legs, strat)
    except Exception as e:
        return [f"comparator_purity_check 載入失敗：{str(e)[:80]}"]

def check_strict_screen(cache):
    """Gate ③：嚴格篩逐軸核對——切題須全必含軸命中、離題須標明缺軸（反放水）。"""
    scr = _load(cache / "g3_FINAL_screen.json")
    if scr is None:
        return None
    strat = _load(cache / "g0_strategy.json")
    try:
        import strict_screen_check
        return strict_screen_check.check(scr, strat)
    except Exception as e:
        return [f"strict_screen_check 載入失敗：{str(e)[:80]}"]

def check_screen_order(cache):
    """Bug3：③嚴格篩(g3)不得早於②c全文取得(g2c)與 Stage A 交接(_stage1_corpus)。
    見 g3_FINAL_screen.json 卻缺前置產物＝順序顛倒。"""
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None
    fails = []
    if _load(cache / "g2c_FINAL_content.json") is None:
        fails.append("③嚴格篩產物存在，但②c全文取得產物 g2c_FINAL_content.json 不存在：③不得早於②c（順序顛倒）")
    if _load(cache / "_stage1_corpus.json") is None:
        fails.append("③嚴格篩產物存在，但 Stage A 交接 _stage1_corpus.json 不存在：須先過 Stage A→B 邊界才可③")
    return fails

def check_verification_coverage(cache):
    """Bug6：⑦交接/報告前，included＋background 每筆都必須過⑥交叉驗證（在 g6_verified.json 有紀錄）。"""
    seed = _load(cache / "seed.json") or _load(cache / "_corpus_seed.json")
    if seed is None:
        return None
    ver = _load(cache / "g6_verified.json")
    if ver is None:
        return ["交接包存在但 g6_verified.json 不存在：included/background 未經⑥ Crossref+PubMed 交叉驗證"
                "（未驗證不得進交接/Zotero/報告表二三）"]
    vids = set()
    for v in ver:
        if v.get("pmid"): vids.add(("pmid", str(v.get("pmid"))))
        if v.get("doi"): vids.add(("doi", _norm_doi(v.get("doi"))))
    papers = seed.get("papers", []) if isinstance(seed, dict) else seed
    fails = []
    for p in papers:
        if p.get("verdict") not in ("included", "background"):
            continue
        pid = p.get("pmid"); doi = _norm_doi(p.get("doi"))
        if not pid and not doi:
            continue  # 無 PMID 也無 DOI（如 CT.gov NCT 登錄紀錄）：依 SPEC 以註冊號為憑、不走 Crossref/PubMed → 不在此關稽核
        ok = (pid and ("pmid", str(pid)) in vids) or (doi and ("doi", doi) in vids)
        if not ok:
            fails.append(f"{p.get('paper_id') or pid or doi}（verdict={p.get('verdict')}）未在 g6_verified.json："
                         "⑥交叉驗證未覆蓋（每筆 included/background 必須經 Crossref+PubMed 驗證）")
    return fails

def check_pdf_emitted(cache):
    """Bug7：宣稱 Phase1 完成（_search_report.json 存在）前，報告 PDF 須實際產出且非空。
    路徑不寫死——由報告產生器以 settings 解析後寫入 _search_report.json 的 `pdf_path`；本守門只驗該檔存在。"""
    rep = _load(cache / "_search_report.json")
    if rep is None:
        return None
    pdf = rep.get("pdf_path")
    if not pdf:
        return ["_search_report.json 無 pdf_path：Phase1 PDF 未產出/未登記（無 PDF 不算 Phase1 完成；"
                "路徑須由產生器以 settings.report.pdf_output_dir 解析後登記，勿寫死）"]
    p = Path(pdf)
    if not p.exists() or p.stat().st_size < 1024:
        return [f"登記的 Phase1 PDF 不存在或過小(<1KB)：{pdf}"]
    return []

def check_stage1(cache):
    """Stage A→B 邊界守門：對 _stage1_corpus.json 跑 stage1_check（全文狀態resolved/待評估不混入候選/取盡/互斥）。"""
    data = _load(cache / "_stage1_corpus.json")
    if data is None:
        return None
    try:
        import stage1_check
        return stage1_check.check(data)
    except Exception as e:
        return [f"stage1_check 載入失敗：{str(e)[:80]}"]

def check_no_retracted(cache):
    """撤稿管控：⑥交叉驗證標 RETRACTED 者，嚴禁出現在 納入/背景/報告表/Zotero payload/交接包。
    （2026-06 實測撤稿 SR 被當背景匯入 Zotero；撤稿須統一在交叉驗證查〔PubMed PT + Crossref is-retracted〕，
     並由本守門確保下游不殘留。）"""
    ver = _load(cache / "g6_verified.json")
    if ver is None:
        return None
    retr = {str(v.get("pmid")) for v in ver if v.get("verdict") == "RETRACTED" and v.get("pmid")}
    # Crossref is-retracted 多以 DOI 為憑——撤稿文獻可能無 PMID，須一併以 DOI 比對（審查 🔴 補強）
    retr_dois = {_norm_doi(v.get("doi")) for v in ver if v.get("verdict") == "RETRACTED" and v.get("doi")}
    retr_dois.discard(None)
    if not retr and not retr_dois:
        return []
    def _hp(x): return bool(x) and str(x) in retr                 # pmid 命中
    def _hd(x): return bool(_norm_doi(x)) and _norm_doi(x) in retr_dois  # doi 命中
    fails = []
    rep = _load(cache / "_search_report.json")
    if rep:
        for grp in rep.get("studies", []):
            for r in grp.get("reports", []):  # 元組 [title, pmid, doi, ft, xref]
                if (len(r) >= 2 and _hp(r[1])) or (len(r) >= 3 and _hd(r[2])):
                    fails.append(f"撤稿 {r[1] if len(r)>1 and _hp(r[1]) else (r[2] if len(r)>2 else '?')} 出現在核心 Study 表（{grp.get('study')}）：須剔除、改列待評估/排除")
        for r in rep.get("background", []):  # 元組 [title, pmid, doi, type, ft, xref]
            if (len(r) >= 2 and _hp(r[1])) or (len(r) >= 3 and _hd(r[2])):
                fails.append(f"撤稿 {r[1] if len(r)>1 and _hp(r[1]) else (r[2] if len(r)>2 else '?')} 出現在背景表：須剔除")
    pay = _load(cache / "g8_zotero_payload.json")
    if pay:
        for p in pay:
            if _hp(p.get("pmid")) or _hd(p.get("doi")):
                fails.append(f"撤稿 {p.get('pmid') or p.get('doi')} 在 Zotero payload：禁匯入（須先剔除再 commit）")
    seed = _load(cache / "seed.json") or _load(cache / "_corpus_seed.json")
    if seed:
        for p in (seed.get("papers", []) if isinstance(seed, dict) else seed):  # seed 可能是 bare list（同 check_have_verified）
            if _hp(p.get("pmid")) or _hd(p.get("doi")):
                fails.append(f"撤稿 {p.get('pmid') or p.get('doi')} 在交接包 papers：禁進 GRADE 證據體")
    return fails

def check_report(cache):
    """報告版型/內容硬 gate：對 _search_report.json 跑 report_check（③二分/PMID欄/無佔位/背景檢核/進行中表）。"""
    data = _load(cache / "_search_report.json")
    if data is None:
        return None
    try:
        import report_check
        return report_check.check(data)
    except Exception as e:
        return [f"report_check 載入失敗：{str(e)[:80]}"]

def check_exhaust(cache):
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None
    try:
        import leg_exhaust_check
        return leg_exhaust_check.check(man)
    except Exception as e:
        return [f"leg_exhaust_check 載入失敗：{str(e)[:80]}"]

def check_strategy_adherence(cache):
    """Gate ①：每腿『實際送出的 query』不得偏離 ⓪ 核准策略（反擅自加未核准的設計/品質過濾）。"""
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None
    strat = _load(cache / "g0_strategy.json")
    try:
        import strategy_adherence_check
        return strategy_adherence_check.check(man, strat)
    except Exception as e:
        return [f"strategy_adherence_check 載入失敗：{str(e)[:80]}"]

def _safe(name, fn, cache):
    """呼叫單一守門：例外一律視為未通過(fail-closed)。
    避免某個 check 自身拋例外（型態異常的 cache 等）讓 run_hook 以未捕捉例外退出 exit 1——
    Stop hook 只有 exit 2 才會 block，exit 1 會被當成『hook 出錯但放行』→ 守門靜默失效。"""
    try:
        return (name, fn(cache))
    except Exception as e:
        return (name, [f"守門 {fn.__name__} 自身拋例外（{str(e)[:80]}）：視為未通過(fail-closed)，請修 cache 或守門"])


def _all_checks(cache):
    return [_safe("Gate⓪ 策略經使用者核准才可檢索(防搶跑)", check_strategy_approved, cache),
            _safe("有全文須實抓驗證", check_have_verified, cache),
            _safe("Stage A→B 邊界", check_stage1, cache),
            _safe("Gate① 取盡", check_exhaust, cache),
            _safe("Gate① 策略遵從(實際query vs 核准)", check_strategy_adherence, cache),
            _safe("Gate① 四軸覆蓋(query 展開)", check_axis_coverage, cache),
            _safe("Gate⓪／① 對照軸純度(query 只含 P＋I，C 不進 query)", check_comparator_purity, cache),
            _safe("Gate③ 嚴格篩逐軸核對(不放水)", check_strict_screen, cache),
            _safe("②c→③ 順序(③不得早於②c)", check_screen_order, cache),
            _safe("⑥驗證覆蓋(included/background 全驗)", check_verification_coverage, cache),
            _safe("Phase1 PDF 實體產出", check_pdf_emitted, cache),
            _safe("Gate②c Unpaywall 覆蓋", check_unpaywall_coverage, cache),
            _safe("Gate③ 待評估未漏抓全文", check_waiting_fulltext, cache),
            _safe("Gate③ 分割閉合＋已篩來源(反坍縮)", check_partition_provenance, cache),
            _safe("Gate③ 待評估須先核對全文(不得只憑摘要punt)", check_screen_awaiting_resolved, cache),
            _safe("報告版型/內容", check_report, cache),
            _safe("撤稿不得殘留納入/背景/Zotero", check_no_retracted, cache)]


def run(cache, quiet=False):
    checks = _all_checks(cache)
    all_fails = []
    lines = []
    for name, res in checks:
        if res is None:
            lines.append(f"  ⏭  {name}：尚未到此關（產物不存在）")
        elif res:
            lines.append(f"  ❌ {name}：")
            for f in res: lines.append(f"       - {f}"); all_fails.append(f)
        else:
            lines.append(f"  ✅ {name}：通過")
    if all_fails:
        print("❌ gate_guard 攔截到未通關項目：")
        print("\n".join(lines))
        return 1
    if not quiet:
        print("✅ gate_guard：所有已抵達關卡通過")
        print("\n".join(lines))
    return 0

def run_hook(cache):
    """Stop hook 模式：FAIL 時把原因寫 stderr 並 exit 2（Claude Code Stop hook 以 exit 2 阻擋停止、回灌 stderr 給模型）。"""
    if not _active(cache):
        sys.exit(0)  # 檢索非進行中（無哨兵旗標）：靜默放行，全域零打擾
    checks = _all_checks(cache)  # 每個 check 以 _safe 兜底：例外→fail-closed，不讓 hook 退 1 放行
    fails = []
    for name, res in checks:
        if res:
            for f in res: fails.append(f"[{name}] {f}")
    if fails:
        sys.stderr.write("gate_guard 攔截：本輪檢索關卡有未通關項目，請修正後再結束：\n"
                         + "\n".join("  - " + f for f in fails) + "\n")
        sys.exit(2)
    sys.exit(0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--hook", action="store_true", help="Stop hook 模式：FAIL→stderr＋exit 2")
    a = ap.parse_args()
    cache = _find_cache(a.cache)
    if a.hook:
        run_hook(cache)
        return
    if cache is None:
        if a.auto:
            sys.exit(0)  # 非 EBM 對話：靜默放行
        print("⏭  找不到 EBM cache（--cache 指定，或先跑 Gate ①）"); sys.exit(0)
    sys.exit(run(cache, quiet=a.quiet))

if __name__ == "__main__":
    main()
