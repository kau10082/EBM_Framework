# -*- coding: utf-8 -*-
"""無 API：把「我（Claude）產出的某階段 JSON」對照該階段 schema 驗證。
這就是「不漏護欄」的檢查點——schema 缺欄即報錯，由我修正後重存。

  python tools/validate.py p1 cache/paper1.p1.json
  python tools/validate.py p3 cache/paper1.p3.json
  phase 代號：p0 / p1 / p2 / p3 / per_paper / synthesis
"""
import sys
import json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema"

MAP = {
    "p0": ("phase0_corpus.json", None),
    "p1": ("phase1_extract.json", None),
    "p2": ("phase2_triage.json", None),
    "p3": ("phase3_grade.json", None),
    "per_paper": ("phase4_output.json", ("properties", "per_paper", "items")),
    "synthesis": ("phase4_output.json", ("properties", "synthesis")),
}


def _subschema(full, path):
    if not path:
        return full
    node = full
    for k in path:
        node = node[k]
    return node


_LEVELS = ["very_low", "low", "moderate", "high"]
_DOWN = {"not_serious": 0, "not_applicable": 0, "serious": 1, "very_serious": 2}
_UP = {"none": 0, "not_applicable": 0, "up_one": 1, "up_two": 2}


def check_p3_certainty(data):
    """重算每個 outcome 的 certainty_final＝起始 − 淨下調（封頂3、不低於極低）＋上調，
    與所填 certainty_final 比對。回傳不一致清單（GRADE 算術 gate）。"""
    errs = []
    for o in data.get("outcomes", []):
        name = o.get("outcome_name", "?")
        try:
            start = _LEVELS.index(o["certainty_start"])
        except (KeyError, ValueError):
            errs.append(f"{name}: certainty_start 缺/無效")
            continue
        down = sum(_DOWN.get(d.get("verdict"), 0) for d in o.get("downgrade_domains", {}).values())
        up = sum(_UP.get(u.get("verdict"), 0) for u in o.get("upgrade_domains", {}).values())
        # 不對 down/up 獨立提前封頂：標準 GRADE 算術＝start−down+up，再由末端 max(0,min(3,…)) 統一夾至
        # [very_low, high]。提前封頂會在極端組合(如 start=high,down=5,up=2)改變 net——把本應 very_low
        # 的研究誤算成 moderate「起死回生」，使此核對 gate 偏離標準而誤判。忠實重算優先。
        idx = max(0, min(3, start - down + up))   # 不低於極低、不高於高
        computed = _LEVELS[idx]
        stated = o.get("certainty_final")
        if computed != stated:
            errs.append(f"{name}: 重算={computed}（起始 {o['certainty_start']} −{down} +{up}）"
                        f" ≠ 所填 certainty_final={stated}")
    return errs


def check_p2_rob_routing(data):
    """Phase 2 偏誤風險『工具↔設計』路由（三路徑：A→AMSTAR2、B→RoB2、C(NRSI)→ROBINS-I）。
    把使用者鐵律『回顧性/非隨機研究須用 ROBINS-I、不可用 RoB2；NRSI 判低偏誤極罕見須附理由』
    從靠記性變機器看守（Cochrane Handbook Ch.25）。schema 已強制 rob_tool 與 track 相符＋track C 須帶
    robins_i 七領域；本語意檢查再補『ROBINS-I overall=low 必附 low_justification、七領域不得留 no_information 充數』。"""
    errs = []
    track = data.get("track")
    tool = data.get("rob_tool")
    expect = {"A": "amstar2", "B": "rob2", "C": "robins_i", "low": "none"}.get(track)
    if track in ("A", "B", "C") and tool != expect:
        errs.append(f"track={track} 須用 rob_tool={expect}（實得 {tool!r}）："
                    f"偏誤工具不可拿錯——RCT→RoB2、NRSI(回顧性/世代/case-control/真實世界)→ROBINS-I、SR/MA→AMSTAR2")
    # 起始確定性↔軌道『防飄移』：A/B 起始 high、low(case report 等)起始 very_low、C(NRSI) 起始 low 或 high(用 ROBINS-I)
    gs = data.get("grade_start")
    gs_expect = {"A": {"high"}, "B": {"high"}, "C": {"low", "high"}, "low": {"very_low"}}.get(track)
    if gs_expect and gs not in gs_expect:
        errs.append(f"grade_start={gs!r} 與 track={track} 不符（防飄移）：A/B→high、C(NRSI)→low(或用 ROBINS-I 起 high)、"
                    f"low(case report 等)→very_low；起始確定性不得偏離軌道")
    if track == "B":
        rb = data.get("rob2") or {}
        doms = (rb.get("domains") or {})
        need = ["randomization", "deviations", "missing_outcome", "measurement", "selection_reported"]
        overall = rb.get("overall")
        if not doms:
            errs.append("track=B(RCT) 缺 rob2.domains 五領域評估（RoB 2）")
        else:
            miss = [d for d in need if d not in doms]
            if miss:
                errs.append(f"RoB 2 缺領域 {miss}（五領域須逐一判，防漏填）")
            RANK = {"low": 0, "some_concerns": 1, "high": 2}
            dranks = [RANK[(doms.get(d) or {}).get("judgement")] for d in need if (doms.get(d) or {}).get("judgement") in RANK]
            if dranks and overall in RANK and RANK[overall] < max(dranks):
                inv = {v: k for k, v in RANK.items()}
                worst = [d for d in need if RANK.get((doms.get(d) or {}).get("judgement"), -1) == max(dranks)]
                errs.append(f"RoB 2 整體違反木桶原則：overall={overall} 優於最不利領域={inv[max(dranks)]}（{worst}）"
                            f"（任一 high→high、任一 some_concerns→至少 some_concerns）")
    if track == "A":
        am = data.get("amstar2") or {}
        if not am:
            errs.append("track=A(SR/MA) 缺 amstar2 方法學品質評估（AMSTAR 2）")
        else:
            cf = am.get("critical_flaws")
            ncw = am.get("noncritical_weaknesses")
            rating = am.get("overall_confidence")
            if not str(am.get("basis") or "").strip():
                errs.append("AMSTAR 2 缺 basis（Cochrane 要求透明呈現每題評分＋理由＋整體評等）")
            if isinstance(cf, int) and isinstance(ncw, int) and rating:
                # 整體信心演算法（依關鍵瑕疵數→四級）：>1 關鍵=critically_low；1 關鍵=low；
                # 0 關鍵且 >1 非關鍵弱點=moderate；0 關鍵且 ≤1 非關鍵弱點=high
                expect_rating = ("critically_low" if cf > 1 else "low" if cf == 1
                                 else "moderate" if ncw > 1 else "high")
                if rating != expect_rating:
                    errs.append(f"AMSTAR 2 整體信心算法不一致：關鍵瑕疵={cf}、非關鍵弱點={ncw} 應為 "
                                f"'{expect_rating}'，實填 '{rating}'（>1關鍵→critically_low／1關鍵→low／"
                                f"0關鍵且>1非關鍵→moderate／0關鍵且≤1非關鍵→high）")
            # 若提供逐題 items，交叉核對關鍵瑕疵計數（關鍵領域＝2,4,7,9,11,13,15 答 no）
            items = am.get("items")
            if isinstance(items, list) and items and isinstance(cf, int):
                CRITICAL_ITEMS = {2, 4, 7, 9, 11, 13, 15}
                crit_no = sum(1 for it in items if it.get("item") in CRITICAL_ITEMS and it.get("answer") == "no")
                if crit_no != cf:
                    errs.append(f"AMSTAR 2 關鍵瑕疵計數與逐題不符：items 中關鍵題(2,4,7,9,11,13,15)答 no 有 {crit_no} 個，"
                                f"但 critical_flaws={cf}（透明表格須與計數一致）")
    if track == "C":
        ri = data.get("robins_i") or {}
        doms = (ri.get("domains") or {})
        need = ["confounding", "selection", "classification", "deviations", "missing_data", "measurement", "selection_reported"]
        overall = ri.get("overall")
        if not doms:
            errs.append("track=C(NRSI) 缺 robins_i.domains 七領域評估（ROBINS-I）")
        else:
            miss = [d for d in need if d not in doms]
            if miss:
                errs.append(f"ROBINS-I 缺領域 {miss}（七領域須逐一判）")
            ni = [d for d in need if (doms.get(d) or {}).get("judgement") == "no_information"]
            if len(ni) >= 4:
                errs.append(f"ROBINS-I 有 {len(ni)} 個領域填 no_information（{ni}）：疑以『無資訊』充數規避判定，請據實評或標 serious/critical")
            # 木桶原則：整體不得優於最不利領域（任一 serious→至少 serious；任一 critical→critical）
            RANK = {"low": 0, "moderate": 1, "serious": 2, "critical": 3}
            dom_ranks = [RANK[(doms.get(d) or {}).get("judgement")] for d in need
                         if (doms.get(d) or {}).get("judgement") in RANK]
            if dom_ranks and overall in RANK:
                worst = max(dom_ranks)
                if RANK[overall] < worst:
                    inv = {v: k for k, v in RANK.items()}
                    worst_doms = [d for d in need if RANK.get((doms.get(d) or {}).get("judgement"), -1) == worst]
                    errs.append(f"ROBINS-I 整體判定違反木桶原則：overall={overall} 優於最不利領域={inv[worst]}"
                                f"（{worst_doms}）。整體不得低於最不利領域（任一 serious→至少 serious、任一 critical→critical）")
        # 前置作業（評估前必備）
        if ri.get("effect_of_interest") not in ("assignment", "adherence"):
            errs.append("ROBINS-I 缺前置作業 effect_of_interest（assignment ITT-like／adherence PP-like）：影響領域4 判定")
        if not (ri.get("confounders_considered") or []):
            errs.append("ROBINS-I 缺前置作業 confounders_considered（預先指定的重要干擾因子，至少 1 個）：干擾為 NRSI 最致命領域")
        # NRSI 判 low 極罕見：須附理由
        if overall == "low" and not str(ri.get("low_justification") or "").strip():
            errs.append("ROBINS-I overall=low 但無 low_justification：NRSI 判低偏誤極罕見（殘餘干擾無法消除），"
                        "須明述為何殘餘干擾可忽略（Cochrane Ch.25 警語）")
        # critical → 該結果應直接排除於統合（Cochrane Ch.25）
        if overall == "critical" and ri.get("meta_analysis_action") != "exclude":
            errs.append("ROBINS-I overall=critical 但 meta_analysis_action≠exclude：被評 critical 的 NRSI 結果"
                        "無法提供有用效果證據，Cochrane Ch.25 規定應直接排除於統合（meta_analysis_action=exclude）")
    return errs


def check_p0_completeness(data):
    """Phase 0 納入完整性（防樞紐試驗主報告被靜默漏掉）。
    以 overlap_with 連通分量分群（同一 Study 的主報告＋子報告）；
    任何『含 direct 相關文獻的多報告 Study 群』必須至少有 1 篇 grade_track=full（主報告），
    否則代表主報告漏了或未設 full——樞紐試驗主報告標題常不含試驗縮寫，最易被分組漏掉。
    回 fails 清單（空＝通過）。"""
    papers = data.get("papers", []) or []
    by_id = {p.get("paper_id"): p for p in papers}
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    for p in papers:
        pid = p.get("paper_id"); find(pid)
        for o in (p.get("overlap_with") or []):
            if o in by_id:
                union(pid, o)
    clusters = {}
    for p in papers:
        clusters.setdefault(find(p.get("paper_id")), []).append(p)
    fails = []
    for members in clusters.values():
        directs = [m for m in members if m.get("relevance") == "direct"]
        if not directs:
            continue
        has_full = any(m.get("grade_track") == "full" for m in members)
        if len(members) >= 2 and not has_full:
            ids = [m.get("paper_id") for m in members]
            fails.append("Study 群（%d 報告：%s%s）含 direct 文獻但無 full-track 主報告"
                         "——疑漏主報告/主報告未設 full（樞紐試驗主報告標題常不含縮寫，易被分組漏掉，請核對該試驗 primary publication 是否在 corpus）"
                         % (len(members), ids[:5], "…" if len(ids) > 5 else ""))
    return fails


def check_synthesis_tracks(data):
    """多軌並行整合『防混池/防遺失/防飄移』（Phase 4 synthesis）。
    使用者鐵則（Cochrane）：RCT(RoB2)／NRSI(ROBINS-I)／SR/MA(AMSTAR2) 三軌絕不混進同一統計模型或同一 GRADE；
    NRSI=critical 必排除於合成；既有 SR/MA 非 Overview 時不得作數據源池化（防 double-counting）。
    本檢查作用於 synthesis.tracks（存在才查；自洽層級，跨階段 track 歸屬另由 selfcheck 補）。"""
    errs = []
    tr = (data or {}).get("tracks")
    if not isinstance(tr, dict):
        return errs  # 未用多軌容器：不適用（單軌報告）
    rct = tr.get("rct") or {}
    nrsi = tr.get("nrsi") or {}
    srma = tr.get("srma_context") or {}
    rct_inc = set(rct.get("included_paper_ids") or [])
    nrsi_inc = set(nrsi.get("included_paper_ids") or [])
    nrsi_crit = set(nrsi.get("excluded_critical_ids") or [])
    # 1) 跨軌混池：同一 paper 不得同時在 RCT 與 NRSI 池
    both = rct_inc & nrsi_inc
    if both:
        errs.append(f"跨軌混池：paper {sorted(both)[:5]} 同時在 RCT 與 NRSI 池——三軌絕不可合併於同一統計模型/森林圖")
    # 2) NRSI critical 必排除、且不得同時在 included
    dup = nrsi_inc & nrsi_crit
    if dup:
        errs.append(f"NRSI critical 矛盾：paper {sorted(dup)[:5]} 同時列 included 與 excluded_critical（critical 必剔除於合成，Cochrane Ch.25）")
    # 3) SR/MA 不得作數據源池化（非 Overview）
    if srma:
        if srma.get("used_as_data_source") is True and not srma.get("is_overview"):
            errs.append("SR/MA 軌 used_as_data_source=true 但非 Overview：既有 SR/MA 不可作數據提取/池化來源（防 double-counting），僅作討論對照")
        if srma.get("role") not in (None, "discussion_context") and not srma.get("is_overview"):
            errs.append(f"SR/MA 軌 role={srma.get('role')!r} 非 discussion_context：一般 SR 中既有 SR/MA 僅作討論對照")
    # 4) 池化了卻無 GRADE 輸出（防遺失）：synthesis_mode=meta_analysis 且 included 非空 → 須有 sof 或 certainty_summary
    for nm, blk, inc in (("RCT", rct, rct_inc), ("NRSI", nrsi, nrsi_inc)):
        if blk.get("synthesis_mode") == "meta_analysis":
            if not inc:
                errs.append(f"{nm} 軌標 meta_analysis 但 included_paper_ids 空（無池化對象）")
            elif not (blk.get("sof") or str(blk.get("certainty_summary") or "").strip()):
                errs.append(f"{nm} 軌已池化(meta_analysis) 但缺 sof／certainty_summary（GRADE 輸出遺失——每軌須獨立 SoF/確定性）")
    return errs


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    phase, jf = argv[0], argv[1]
    if phase not in MAP:
        print(f"unknown phase '{phase}'（可選：{', '.join(MAP)}）")
        return 2
    import jsonschema
    fname, sub = MAP[phase]
    full = json.loads((SCHEMA / fname).read_text(encoding="utf-8"))
    schema = _subschema(full, sub)
    data = json.loads(Path(jf).read_text(encoding="utf-8"))
    v = jsonschema.Draft7Validator(schema)
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs:
        print(f"❌ {jf} 不符 {phase} schema（{len(errs)} 處）：")
        for e in errs[:30]:
            print(f"  - /{'/'.join(map(str, e.path))}: {e.message}")
        return 1
    # p0：額外做納入完整性檢查（防樞紐主報告漏掉）
    if phase == "p0":
        comp_errs = check_p0_completeness(data)
        if comp_errs:
            print(f"❌ {jf} 結構合格、但納入完整性有疑（{len(comp_errs)} 處）：")
            for e in comp_errs:
                print(f"  - {e}")
            return 1
        print(f"✅ {jf} 符合 {phase} schema ＋ 納入完整性（每 Study 群有 full 主報告）")
        return 0
    # p2：額外做『偏誤工具↔設計』路由檢查（A→AMSTAR2 / B→RoB2 / C(NRSI)→ROBINS-I）
    if phase == "p2":
        rob_errs = check_p2_rob_routing(data)
        if rob_errs:
            print(f"❌ {jf} 結構合格、但偏誤風險工具路由有疑（{len(rob_errs)} 處）：")
            for e in rob_errs:
                print(f"  - {e}")
            return 1
        print(f"✅ {jf} 符合 {phase} schema ＋ 偏誤工具↔設計路由（NRSI 用 ROBINS-I）")
        return 0
    # p3：額外做 GRADE 確定性算術檢查
    if phase == "p3":
        cert_errs = check_p3_certainty(data)
        if cert_errs:
            print(f"❌ {jf} 結構合格、但 GRADE 確定性算術不一致（{len(cert_errs)} 處）：")
            for e in cert_errs:
                print(f"  - {e}")
            return 1
        print(f"✅ {jf} 符合 {phase} schema ＋ 確定性算術一致")
        return 0
    # synthesis：額外做多軌並行『防混池/防遺失/防飄移』檢查
    if phase == "synthesis":
        tr_errs = check_synthesis_tracks(data)
        if tr_errs:
            print(f"❌ {jf} 結構合格、但多軌整合有疑（{len(tr_errs)} 處）：")
            for e in tr_errs:
                print(f"  - {e}")
            return 1
        print(f"✅ {jf} 符合 {phase} schema ＋ 多軌並行整合（三軌不混池）")
        return 0
    print(f"✅ {jf} 符合 {phase} schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
