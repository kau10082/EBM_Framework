# -*- coding: utf-8 -*-
"""
gate_guard.py — 檢索端『關卡守門』總 orchestrator（harness 可掛 Stop hook 自動跑）
================================================================================
依 cache 內已存在的產物，自動判斷目前在哪些關、逐關跑對應硬 gate：
  • g1_legs_manifest.json + g0_strategy.json → check_strategy_approved（Gate ⓪ 策略須先經使用者核准才可檢索，防搶跑）
  • g1_legs_manifest.json + g0_strategy.json → check_sr_filter_decided（Gate ⓪ SR filter 須問過並決定，防忘了問）
  • g1_legs_manifest.json + g0_strategy.json → check_sr_filter_composite（Gate ① SR filter 須複合語法 PubType/MeSH＋Title/Abstract，MECIR C33）
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
import sys, os, json, argparse
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

def _find_active_cache_by_flag(roots=None):
    """掃描 repo 內 EBM_Search/cache/*/ 找帶哨兵旗標 _search_active.flag 的『進行中』檢索 cache。
    這是 Stop hook（無 --cache）最可攜、最可靠的發現方式：哨兵旗標本身就是『此 cache 有檢索進行中』
    的地真值，與 run_state／env／OneDrive 路徑無關（後三者在 fresh-clone／手機／非 Windows 常常解析不到，
    會讓 hook 找不到 cache → 靜默 exit 0 → 守門等同失效）。多個進行中時取最近修改者（最可能是當前這輪）。"""
    if roots is None:
        here = Path(__file__).resolve().parent          # EBM_Search/scripts
        roots = [here.parent / "cache"]                 # EBM_Search/cache
    cands = []
    for root in roots:
        try:
            if Path(root).is_dir():
                for f in Path(root).glob("*/" + ACTIVE_FLAG):
                    cands.append(f.parent)
        except Exception:
            pass
    if not cands:
        return None
    return max(cands, key=lambda d: (d / ACTIVE_FLAG).stat().st_mtime)

def _find_cache(explicit=None):
    if explicit and Path(explicit).exists():
        return Path(explicit)
    # 優先：掃哨兵旗標找『進行中』cache（可攜、不依賴 run_state/env/OneDrive；Stop hook 無 --cache 時的主幹）
    flagged = _find_active_cache_by_flag()
    if flagged is not None:
        return flagged
    # 其次：從 EBM run_state 解析 cache_dir
    try:
        import run_state
        st = run_state.load() or {}
        cd = (st.get("paths") or {}).get("cache_dir")
        if cd and Path(cd).exists():
            return Path(cd)
    except Exception:
        pass
    # 再退而求其次：env / 預設 OneDrive 文件
    for cand in [os.environ.get("EBM_CACHE_DIR"),
                 os.path.expanduser(r"~/OneDrive/文件/EBM_Framework/work/cache")]:
        if cand and Path(cand).exists():
            return Path(cand)
    return None

def _norm_doi(d):
    if not d: return None
    import re
    d = d.lower().strip(); d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d); return d or None

def check_excl_requires_fulltext(cache):
    """全文/摘要搜尋及嚴格離題篩選 鐵律：『離題』只能在 Tier 3（實取全文）後定案——只有『切題』可在
    Tier 1/2（摘要／CT.gov 登錄／AI 合成）早停。故每筆 verdict=離題 必須帶 tier==3 或
    fulltext_parse_attempted=true（證明已升級到實取全文才判離題），否則＝在薄摘要/登錄就把
    『可能切題』者誤殺 → FAIL（高 recall：拼到全文才可判離題；2026-06 使用者定版流程）。"""
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None
    bad = []
    for r in g3:
        if (r.get("verdict") or "") != "離題":
            continue
        if r.get("tier") in (3, 4) or r.get("fulltext_parse_attempted") or r.get("fulltext_checked"):
            continue
        # 例外：登錄試驗(CT.gov)／AI 合成腿——其 Condition+InterventionName／合成摘要即『終端結構化內容』，
        # 無對應全文可再取（結果論文常不存在）；以該內容判離題即定案，不適用 Tier3 全文升級要求。
        if str(r.get("content_status") or "") in ("registry", "ai_summary") or r.get("nct") \
           or str(r.get("fulltext_channel") or "") == "registry":
            continue
        bad.append((r.get("title") or r.get("uid") or "?")[:50])
    if bad:
        return [f"③ 有 {len(bad)} 筆判『離題』但未升級到 Tier3 實取全文(tier==3/fulltext_parse_attempted)："
                f"離題只能在實取全文後定案，不得在薄摘要早停判離題（登錄/AI 結構化內容例外）：{bad[:5]}"]
    return []

def check_nocontent_bucket(cache):
    """全文/摘要搜尋及嚴格離題篩選：『全文及摘要皆無』桶必須真的『Tier 3＋Tier 4』皆取不到可判內容——每筆須帶
    fulltext_parse_attempted=true ∧ channels_exhausted=true，且無 abstract/全文摘錄、非登錄(registry)、
    非 AI 合成內容（否則該筆其實有內容、應判切題/離題，不得丟此桶）。
    **且有 DOI 者須帶 unpaywall_checked=true（＝確有跑過 Tier 4 的 Unpaywall OA 探查）**：
    Unpaywall 是獨立 Tier 4，『皆無』只能在 Tier 4 也查過後定案，不可只試 PMC（Tier 3）就 punt。取代舊『待評估雙桶』。"""
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None
    bad = []
    no_unpaywall = []
    for r in g3:
        if (r.get("verdict") or "") != "全文及摘要皆無":
            continue
        has_content = bool((r.get("abstract") or "").strip()) or bool((r.get("fulltext_excerpt") or "").strip()) \
                      or str(r.get("content_status") or "") in ("registry", "ai_summary") \
                      or str(r.get("class") or "").startswith(("登錄", "有"))
        proven = r.get("fulltext_parse_attempted") and r.get("channels_exhausted")
        if has_content or not proven:
            bad.append((r.get("title") or r.get("uid") or "?")[:50])
            continue
        # 『channels_exhausted』必須真的查過 Unpaywall——有 DOI 卻無 unpaywall_checked＝
        # 只試了 PMC 就宣稱『三層皆失敗』（2026-06 使用者糾正：13/23『全文及摘要皆無』其實
        # 有 Crossref 摘要/OA 全文，因漏跑 Unpaywall/Crossref 而誤判）。
        if r.get("doi") and not r.get("unpaywall_checked"):
            no_unpaywall.append((r.get("title") or r.get("doi") or r.get("uid") or "?")[:50])
    out = []
    if bad:
        out.append(f"③ 有 {len(bad)} 筆判『全文及摘要皆無』但其實有內容、或未證明三層實取皆失敗"
                   f"(fulltext_parse_attempted∧channels_exhausted)：有內容者須判切題/離題：{bad[:5]}")
    if no_unpaywall:
        out.append(f"③ 有 {len(no_unpaywall)} 筆判『全文及摘要皆無』且有 DOI 卻無 unpaywall_checked（未跑 Tier 4）："
                   f"『皆無』只能在 Tier 4（Unpaywall 全部 oa_locations 探查）也失敗後定案，"
                   f"不可只試 PMC（Tier 3）就 punt（用 fulltext_exhaust.py 跑完 Tier 4 再判）：{no_unpaywall[:5]}")
    return out

def check_screen_partition(cache):
    """全文/摘要搜尋及嚴格離題篩選 反坍縮＋分割閉合（單一產物 g3_FINAL_screen.json）：
    g3 含全部 ②b 倖存者，每筆 verdict ∈ {切題, 離題, 全文及摘要皆無}。以 uid 獨立重算：
    uid 穩定唯一（防坍縮鍵污染）、verdict 合法、無重複；若有 g2b_screen.json 則與 ②b kept 對帳（恰覆蓋）。
    來源證明：切題/離題 無 abstract/全文摘錄且非登錄/AI 者，其 uid 須在 g3_fetched_by_uid 帶實抓解析證明。"""
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None
    from collections import Counter
    VERD = {"切題", "離題", "全文及摘要皆無"}
    fails = []
    uids = [r.get("uid") for r in g3]
    if any(u is None for u in uids):
        return ["g3_FINAL_screen.json 有紀錄缺 uid：無法以唯一鍵防坍縮（請先 uid 化）"]
    if len(uids) != len(set(uids)):
        dup = [u for u, n in Counter(uids).items() if n > 1]
        fails.append(f"g3 uid 不唯一（{len(uids)}→{len(set(uids))}）：坍縮鍵污染 dup={dup[:5]}")
    badv = [r.get("uid") for r in g3 if (r.get("verdict") or "") not in VERD]
    if badv:
        fails.append(f"g3 有 {len(badv)} 筆 verdict 不在 {{切題,離題,全文及摘要皆無}}：{badv[:5]}")
    g2b = _load(cache / "g2b_screen.json")
    if isinstance(g2b, dict) and g2b.get("kept") is not None:
        kept = {r.get("uid") for r in g2b["kept"]}
        sset = set(uids)
        miss = kept - sset; extra = sset - kept
        if miss: fails.append(f"②b kept 有 {len(miss)} 筆未進 ③ 分類（漏失）")
        if extra: fails.append(f"③ 有 {len(extra)} 個 uid 不在 ②b kept（憑空冒出）")
    # 來源證明：切題/離題 無 abstract/全文摘錄且非登錄/AI 者，uid 須在 fetched 表帶實抓解析證明
    fetched = _load(cache / "g3_fetched_by_uid.json") or {}
    MIN_PARSED = 1500
    no_content = []
    for r in g3:
        if (r.get("verdict") or "") not in ("切題", "離題"):
            continue
        if (r.get("abstract") or "").strip() or (r.get("fulltext_excerpt") or "").strip():
            continue
        if str(r.get("content_status") or "") in ("registry", "ai_summary") or str(r.get("class") or "").startswith(("登錄", "有")):
            continue
        f = fetched.get(r.get("uid"))
        ok = isinstance(f, dict) and ((isinstance(f.get("text_len"), int) and f["text_len"] >= MIN_PARSED)
              or f.get("verified") or f.get("fulltext_verified") or f.get("channel") == "registry")
        if not ok:
            no_content.append((r.get("title") or r.get("uid") or "?")[:45])
    if no_content:
        fails.append(f"③ 有 {len(no_content)} 筆切題/離題無 abstract 且無實抓解析證明：無內容卻拿到判定，"
                     f"應判『全文及摘要皆無』或補實抓：{no_content[:5]}")
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

# SR filter 決策合法 token：須為「已套用 / 不套用」其一，不得停在未決（pending/空）。
SR_DECISION_DECIDED = {"applied", "declined", "not_applied", "none"}

def check_sr_filter_decided(cache):
    """防『忘了問 SR filter』（Gate ⓪→①，與 check_strategy_approved 對稱）：
    報告檢索策略時必須主動詢問『是否套用 Systematic Review Filter』（SEARCH_SPEC §★鐵律），
    此為使用者決策、不可預設替他決定。本守門把『有沒有問過並得到決定』從靠記性變機器看守——
    Stage A 廣蒐（g1_legs_manifest.json）產出時，g0_strategy.json 的 sr_filter_decision
    必須是已決定值（applied／declined／not_applied／none），不得缺漏或停在 pending → 否則 FAIL。
    （2026-06 使用者糾正：報告策略時漏問 SR filter；此 gate 即為此而立。）"""
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None  # 尚未廣蒐：此關不適用
    strat = _load(cache / "g0_strategy.json")
    if not strat:
        return ["g1_legs_manifest.json 已產出但無 g0_strategy.json：無法確認是否問過 SR filter"]
    dec = (strat.get("sr_filter_decision") or "").strip().lower()
    if dec not in SR_DECISION_DECIDED:
        return ["Stage A 廣蒐（g1_legs_manifest.json 已產出）但 g0_strategy.json 的 sr_filter_decision "
                f"未決（現值＝{strat.get('sr_filter_decision')!r}）：報告檢索策略時必須主動詢問使用者"
                "『是否套用 Systematic Review Filter』，得到決定後才設 sr_filter_decision＝"
                "applied／declined（不套用），不得停在 pending 就開始檢索（防『忘了問 SR filter』）"]
    return []

def check_2b_stop(cache):
    """②b→③ 停頓點（防 ③ 搶跑）：②b 高敏初篩完成（g2b_survivors.json 產出）後，
    必須停下報告 ②b 結果、等使用者點頭，才可進 ③。
    落地：使用者確認後在 g2b_checkpoint.json 設 approved_by_user=true。
    g3_FINAL_screen.json 已產出但 ②b 未經使用者確認＝③ 搶跑 → FAIL。
    （2026-06 使用者糾正：②b 完成後未停下報告即逕跑 ③；此 gate 即為此而立，
      與 check_strategy_approved「⓪→① 防搶跑」對稱。）"""
    g2b = _load(cache / "g2b_survivors.json")
    if g2b is None:
        return None  # 尚未到 ②b：此關不適用
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None  # 尚未進 ③（正常停在 ②b）：此關不適用
    ckpt = _load(cache / "g2b_checkpoint.json")
    if not ckpt or not ckpt.get("approved_by_user"):
        return ["g3_FINAL_screen.json 已產出，但 g2b_checkpoint.json 未標 approved_by_user=true："
                "②b 高敏初篩完成後必須先停下報告、經使用者點頭才可進 ③（防 ③ 搶跑；"
                "使用者確認 ②b 結果後才在 g2b_checkpoint.json 設 approved_by_user=true）"]
    return []


def check_citation_stop(cache):
    """④ 引文追蹤完成後須停下報告、經使用者核准才可進 ⑤a 交叉驗證（防搶跑）。
    落地：使用者確認後在 g4_checkpoint.json 設 approved_by_user=true。
    ⑤a 產物 g6_verified.json 已產出但 ④ 未核准＝搶跑 → FAIL。
    （2026-06 使用者定版：④/⑤a/⑤b 三關各須停下報告、核准後續，與 ⓪→①、②b→③ 對稱。）"""
    down = _load(cache / "g6_verified.json")
    if down is None:
        return None
    ck = _load(cache / "g4_checkpoint.json")
    if not ck or not ck.get("approved_by_user"):
        return ["g6_verified.json(⑤a) 已產出，但 g4_checkpoint.json 未標 approved_by_user=true："
                "④ 引文追蹤完成後須先停下報告、經使用者核准才可進 ⑤a 交叉驗證（防搶跑）"]
    return []


def check_xref_stop(cache):
    """⑤a 交叉驗證＋撤稿完成後須停下報告、經使用者核准才可進 ⑤b 決定納入單位（防搶跑）。
    落地：g6_checkpoint.json approved_by_user=true。⑤b 產物 g7_units.json 已產出但 ⑤a 未核准 → FAIL。"""
    down = _load(cache / "g7_units.json")
    if down is None:
        return None
    ck = _load(cache / "g6_checkpoint.json")
    if not ck or not ck.get("approved_by_user"):
        return ["g7_units.json(⑤b) 已產出，但 g6_checkpoint.json 未標 approved_by_user=true："
                "⑤a 交叉驗證/撤稿完成後須先停下報告、經使用者核准才可進 ⑤b 決定納入單位（防搶跑）"]
    return []


def check_units_stop(cache):
    """⑤b 決定納入單位完成後須停下報告、經使用者核准才可進 ⑥ 三表/報告（防搶跑）。
    落地：g7_checkpoint.json approved_by_user=true。⑥ 產物 _search_report.json 已產出但 ⑤b 未核准 → FAIL。"""
    down = _load(cache / "_search_report.json")
    if down is None:
        return None
    ck = _load(cache / "g7_checkpoint.json")
    if not ck or not ck.get("approved_by_user"):
        return ["_search_report.json(⑥) 已產出，但 g7_checkpoint.json 未標 approved_by_user=true："
                "⑤b 決定納入單位完成後須先停下報告、經使用者核准才可進 ⑥ 三表/報告（防搶跑）"]
    return []

def check_units_no_nocontent(cache):
    """⑤b 決定納入單位：輸入全是『切題（已具內容）』候選（③ 三桶中的『切題』），故 g7_units.json
    **不得出現『全文及摘要皆無／無內容／兩者皆無』類**——那是第③關 Tier 4 的終端桶，已在 ③ 定案、
    不在 ⑤b 重新產生。允許『待評估:會議摘要』（會議摘要有摘要內容、屬 MECIR studies awaiting
    classification，非『無內容』）。（2026-06 使用者糾正：『⑤b 不應再有「待評估,無內容」』。）"""
    units = _load(cache / "g7_units.json")
    if units is None:
        return None
    recs = units.get("records") if isinstance(units, dict) else units
    if not isinstance(recs, list):
        return None
    BAD = ("全文及摘要皆無", "無內容", "兩者皆無")
    bad = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        blob = " ".join(str(r.get(k) or "") for k in ("unit", "design", "verdict", "core_basis", "class", "relevance"))
        if any(b in blob for b in BAD):
            bad.append((r.get("title") or r.get("uid") or "?")[:50])
    if bad:
        return [f"⑤b g7_units.json 有 {len(bad)} 筆標『全文及摘要皆無/無內容/兩者皆無』："
                f"⑤b 只消費『切題(已具內容)』候選，無內容桶＝③ Tier4 終端、不得在 ⑤b 重生"
                f"（會議摘要請標『待評估:會議摘要』＝有摘要內容）：{bad[:5]}"]
    return []

def check_units_only_concordant(cache):
    """⑤b 只能消費 ③『切題』候選（＋④ 引文追蹤新切題）。『離題』(清單三排除) 與『全文及摘要皆無/待評估』
    **等同丟棄、不入後續分析**——嚴禁把它們餵進 g7_units（決定納入單位）當核心或背景。
    （2026-06 使用者糾正：曾把 ③ 的 274 筆『離題』誤當『背景』灌進 ⑤b，使 corpus 由 561 切題膨脹成 835；
      使用者定版：離題與待評估都不入分析。背景＝『切題中非核心』者，不是『離題』。）
    判定：g7_units 每筆 uid 必須是 ③ g3_FINAL_screen 中 verdict=='切題' 者，或 ④ g4 的新切題；
    出現 g3 中 verdict∈{離題,全文及摘要皆無} 的 uid → FAIL。"""
    units = _load(cache / "g7_units.json")
    if units is None:
        return None
    g3 = _load(cache / "g3_FINAL_screen.json")
    if g3 is None:
        return None
    concordant = {r.get("uid") for r in g3 if (r.get("verdict") or "") == "切題"}
    excluded = {r.get("uid"): (r.get("verdict") or "") for r in g3
                if (r.get("verdict") or "") in ("離題", "全文及摘要皆無")}
    g4 = _load(cache / "g4_citation_tracking.json") or {}
    for r in (g4.get("new_relevant") or []):
        if r.get("uid"):
            concordant.add(r.get("uid"))
    recs = units.get("records") if isinstance(units, dict) else units
    if not isinstance(recs, list):
        return None
    bad = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        uid = r.get("uid")
        if uid in concordant:
            continue
        why = excluded.get(uid)
        if why:
            bad.append(f"{(r.get('title') or uid or '?')[:45]}（③判={why}）")
        else:
            bad.append(f"{(r.get('title') or uid or '?')[:45]}（uid 不在 ③切題/④新切題）")
    if bad:
        return [f"⑤b g7_units.json 有 {len(bad)} 筆非『切題』候選被納入決定單位："
                f"『離題』與『全文及摘要皆無/待評估』等同丟棄、不入分析（背景＝切題中非核心，非離題）："
                f"{bad[:6]}"]
    return []

def check_search_report_format(cache):
    """⑥ 報告格式『強制執行』：_search_report.json 必須符合使用者 2026-06-24 定版『5 段核心』格式——
    1 檢索基本參數(params: pico/databases/limits)、2 完整檢索字串(search_strings 逐字)、3 PRISMA 流程(flow)、
    4 納入清單(included；只核心，欄位＝作者/年份/文獻類型｜標題｜DOI｜PMID｜驗證；byline 須『作者 年份／文獻類型』、
    不得退回截斷標題、文獻類型不得空)、5 進行中試驗(ongoing)。無 _search_report.json → N/A(尚未產⑥)。
    把『必須照使用者格式』從靠記憶/文件變**機器強制**；schema＝references/search_report_schema.json。"""
    import re as _re
    data = _load(cache / "_search_report.json")
    if data is None:
        return None
    if not isinstance(data, dict):
        return ["_search_report.json 非物件：無法驗 5 段格式"]
    f = []
    for k in ("title", "search_date", "params", "search_strings", "flow", "included"):
        if k not in data: f.append(f"缺必備鍵 `{k}`")
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("search_date", ""))):
        f.append("search_date 非 YYYY-MM-DD（第1段 檢索日期須精確到日）")
    pm = data.get("params") or {}
    if not pm.get("pico"): f.append("params.pico 缺（第1段 PICO 簡述）")
    if not (isinstance(pm.get("databases"), list) and pm.get("databases")): f.append("params.databases 缺/空（第1段 資料庫清單）")
    if not pm.get("limits"): f.append("params.limits 缺（第1段 限制條件須誠實交代）")
    ss = data.get("search_strings") or []
    if not ss: f.append("search_strings 空（第2段 須各腿逐字布林字串）")
    elif not any((s.get("query") or "").strip() for s in ss): f.append("search_strings 無任何非空 query（MECIR 可重製）")
    if len(data.get("flow") or []) < 3: f.append("flow < 3 階（第3段 PRISMA 流程須逐階段數字）")
    inc = data.get("included") or []
    if not inc:
        f.append("included 空（第4段 至少列核心）")
    bad_bl, bad_ty = [], []
    for it in inc:
        bl = it.get("byline", "") or ""
        head, sep, typ = bl.partition(" / ")
        head = head.replace("〔base〕", "").strip(); typ = typ.strip()
        if not sep or not _re.search(r"\b(19|20)\d\d\b", head):   # 須『作者 年份』、防退回截斷標題
            bad_bl.append(bl[:34])
        if not typ:
            bad_ty.append(bl[:34])
    if bad_bl: f.append(f"included 有 {len(bad_bl)} 筆 byline 非『作者 年份／文獻類型』(疑退回截斷標題/缺年份)：{bad_bl[:4]}")
    if bad_ty: f.append(f"included 有 {len(bad_ty)} 筆缺『文獻類型』：{bad_ty[:4]}")
    if inc and not all(("title" in it and ("pmid" in it or "doi" in it)) for it in inc):
        f.append("included 某筆缺 title/pmid/doi 欄")
    return f


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

def check_axis_expansion(cache):
    """Gate ⓪：四軸展開必須真的做——g0.axes 每條 in_query/mandatory_screen 軸的同義詞庫須實際展開
    （≥3 別名且含全文形式），反『裸詞稀疏策略也通過』。g0 存在即稽核（策略階段就生效）。"""
    strat = _load(cache / "g0_strategy.json")
    if strat is None:
        return None
    try:
        import axis_expansion_check
        return axis_expansion_check.check(strat)
    except Exception as e:
        return [f"axis_expansion_check 載入失敗：{str(e)[:80]}"]

def check_sr_division(cache):
    """Gate ①：SR filter 分工——啟用 SR filter 時，有 SR 變體的非 PubMed DB 腿（EuropePMC/Consensus/OpenAlex）
    只能以 `<leg>-SR` 結果進篩選語料庫 g1_union；其無過濾主檢（全文泛提及噪音）不得灌進池。
    g0 未啟用 SR filter 或 g1_union 未產出 → 此關不適用。"""
    strat = _load(cache / "g0_strategy.json")
    if strat is None:
        return None
    union = _load(cache / "g1_union.json")
    try:
        import sr_division_check
        # 未啟用 SR filter → check 回 []（通過/不適用）；但 union 尚未產出時，
        # 若已啟用仍應提醒。以 union 是否存在區分『尚未到此關』與『已到、須稽核』。
        if not sr_division_check._sr_applied(strat):
            return None
        if union is None:
            return None  # SR 已啟用但語料庫尚未組（Gate ① 收尾才產），暫不適用
        return sr_division_check.check(strat, union)
    except Exception as e:
        return [f"sr_division_check 載入/執行失敗：{e}"]


def check_sr_filter_composite(cache):
    """Gate ①：SR filter 須為複合語法——每條 SR 子腿（`<leg>-SR`／role=SR_MA_NMA）的 Boolean query
    須同時含『控制詞彙(PubType/MeSH)＋自由文字(Title/Abstract)』（MECIR C33；只靠 PubType 會因索引時間差漏最新 SR）。
    AI 合成腿（Consensus/OE）以 study_types 等結構化參數限定 → 豁免。manifest 未產出 → 不適用。"""
    man = _load(cache / "g1_legs_manifest.json")
    if man is None:
        return None
    strat = _load(cache / "g0_strategy.json")
    try:
        import sr_filter_composite_check
        return sr_filter_composite_check.check(man, strat)
    except Exception as e:
        return [f"sr_filter_composite_check 載入失敗：{str(e)[:80]}"]

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

def check_screen_tier_stops(cache):
    """③ 內部分層『逐 Tier 停頓報告』（鐵律，2026-06 使用者定版）：③ 嚴格篩的 Tier 1（摘要）→
    Tier 2（登錄/AI 合成）→ Tier 3（實取全文）→ Tier 4（Unpaywall→g3_FINAL）每一層之間都必須
    停下報告該層結果、經使用者核准後才可跑下一層；不可一口氣把 T2→T3→T4 連跑。
    落地：每層完成寫 g3_tierN.json，使用者核准後在 g3_tierN_checkpoint.json 設 approved_by_user=true；
    下一層產物存在但本層 checkpoint 未核准＝跨層搶跑 → FAIL（與 check_2b_stop 等停頓 gate 同構）。"""
    stages = [
        ("g3_tier1.json", "g3_tier1_checkpoint.json"),
        ("g3_tier2.json", "g3_tier2_checkpoint.json"),
        ("g3_tier3.json", "g3_tier3_checkpoint.json"),
        ("g3_FINAL_screen.json", None),  # Tier 4 收斂＝最終篩選產物
    ]
    fails = []
    for i in range(len(stages) - 1):
        up_prod, up_ckpt = stages[i]
        down_prod, _ = stages[i + 1]
        if _load(cache / down_prod) is None:
            continue  # 下一層尚未產出：此轉換不適用
        ck = _load(cache / up_ckpt) if up_ckpt else None
        if not ck or not ck.get("approved_by_user"):
            fails.append(f"{down_prod} 已產出，但上一層 {up_ckpt} 未標 approved_by_user=true："
                         f"③ 每個 Tier 之間必須停下報告、經使用者核准才可進下一層（防跨 Tier 搶跑；"
                         f"使用者核准 {up_prod} 結果後才在 {up_ckpt} 設 approved_by_user=true）")
    return fails

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

def check_2b_abstract_screen(cache):
    """鐵律：②b 高敏初篩須以『標題＋摘要』篩，嚴禁只憑標題（Cochrane/MECIR 紅線；與 ④ citation_screen 對稱）。
    g2b_screen.json 須結構化宣告 screening_method=title+abstract、批次抓摘要、無 title-only 剔除。"""
    g2b = _load(cache / "g2b_screen.json")
    if g2b is None:
        return None
    try:
        import screen_2b_abstract_check
        return screen_2b_abstract_check.check(g2b)
    except Exception as e:
        return [f"screen_2b_abstract_check 載入失敗：{str(e)[:80]}"]

def check_citation_screen(cache):
    """鐵律：④ 引文追蹤新候選須批次抓摘要、以『標題＋摘要』高敏初篩，嚴禁只憑標題丟（Cochrane 紅線）。"""
    g4 = _load(cache / "g4_citation_tracking.json")
    if g4 is None:
        return None
    try:
        import citation_screen_check
        return citation_screen_check.check(g4)
    except Exception as e:
        return [f"citation_screen_check 載入失敗：{str(e)[:80]}"]

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

def check_no_retracted(cache):
    """撤稿管控：⑥交叉驗證標 RETRACTED 者，嚴禁出現在 納入/背景/報告表/Zotero payload/交接包。
    （2026-06 實測撤稿 SR 被當背景匯入 Zotero；撤稿須統一在交叉驗證查〔PubMed PT + Crossref is-retracted〕，
     並由本守門確保下游不殘留。）"""
    ver = _load(cache / "g6_verified.json")
    if ver is None:
        return None
    def _vv(v): return v.get("verdict") or v.get("verify")   # 相容兩種鍵名（⑤a 寫 verdict／報告器寫 verify）
    retr = {str(v.get("pmid")) for v in ver if _vv(v) == "RETRACTED" and v.get("pmid")}
    # Crossref is-retracted 多以 DOI 為憑——撤稿文獻可能無 PMID，須一併以 DOI 比對（審查 🔴 補強）
    retr_dois = {_norm_doi(v.get("doi")) for v in ver if _vv(v) == "RETRACTED" and v.get("doi")}
    retr_dois.discard(None)
    if not retr and not retr_dois:
        return []
    def _hp(x): return bool(x) and str(x) in retr                 # pmid 命中
    def _hd(x): return bool(_norm_doi(x)) and _norm_doi(x) in retr_dois  # doi 命中
    fails = []
    rep = _load(cache / "_search_report.json")
    if rep:
        for grp in (rep.get("included_studies") or rep.get("studies") or []):  # 正式報告鍵為 included_studies（相容舊 studies）
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


def check_no_unverified(cache):
    """無法驗證（UNVERIFIED）管控：⑤a 交叉驗證查不到存在性者（Crossref／PubMed 皆無、或完全無 ID 可查證）
    **與撤稿一視同仁——嚴禁進下一關**（⑤b g7_units／交接包 corpus_seed／報告納入背景表／Zotero payload）。
    （2026-06 使用者定版：『無法驗證跟撤稿一樣剔除，不可入下一關』；與 check_no_retracted 對稱。）
    判定：g6_verified 標 UNVERIFIED 者，以 pmid／doi／uid 比對下游；命中即 FAIL（須剔除，不得當背景保留）。
    註：以註冊號（NCT）為憑的登錄紀錄屬『registry-verified』，⑤a 不應標其 UNVERIFIED，故不在此誤殺。"""
    ver = _load(cache / "g6_verified.json")
    if ver is None:
        return None
    def _vv(v): return v.get("verdict") or v.get("verify")
    unv_pmid = {str(v.get("pmid")) for v in ver if _vv(v) == "UNVERIFIED" and v.get("pmid")}
    unv_doi = {_norm_doi(v.get("doi")) for v in ver if _vv(v) == "UNVERIFIED" and v.get("doi")}
    unv_doi.discard(None)
    unv_uid = {v.get("uid") for v in ver if _vv(v) == "UNVERIFIED" and v.get("uid")}
    unv_uid.discard(None)
    if not (unv_pmid or unv_doi or unv_uid):
        return []
    def _hit(uid, pmid, doi):
        return (uid in unv_uid) or (pmid and str(pmid) in unv_pmid) or (_norm_doi(doi) in unv_doi)
    fails = []
    g7 = _load(cache / "g7_units.json")
    recs = g7.get("records") if isinstance(g7, dict) else g7
    if isinstance(recs, list):
        for r in recs:
            if _hit(r.get("uid"), r.get("pmid"), r.get("doi")):
                fails.append(f"UNVERIFIED {r.get('pmid') or r.get('doi') or r.get('uid')} 在 ⑤b g7_units（{r.get('role')}）："
                             "無法驗證須與撤稿一樣剔除、不得當核心/背景保留")
    seed = _load(cache / "seed.json") or _load(cache / "_corpus_seed.json")
    if seed:
        for p in (seed.get("papers", []) if isinstance(seed, dict) else seed):
            if _hit(p.get("uid") or p.get("paper_id"), p.get("pmid"), p.get("doi")):
                fails.append(f"UNVERIFIED {p.get('pmid') or p.get('doi')} 在交接包 papers：禁進 GRADE 證據體（須剔除）")
    pay = _load(cache / "g8_zotero_payload.json")
    if pay:
        for p in pay:
            if _hit(p.get("uid"), p.get("pmid"), p.get("doi")):
                fails.append(f"UNVERIFIED {p.get('pmid') or p.get('doi')} 在 Zotero payload：禁匯入（須先剔除）")
    return fails


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
            _safe("Gate⓪ SR filter 須問過並決定(防忘了問)", check_sr_filter_decided, cache),
            _safe("有全文須實抓驗證", check_have_verified, cache),
            _safe("Gate① 取盡", check_exhaust, cache),
            _safe("Gate① 策略遵從(實際query vs 核准)", check_strategy_adherence, cache),
            _safe("Gate① 四軸覆蓋(query 展開)", check_axis_coverage, cache),
            _safe("Gate⓪ 四軸展開(同義詞庫真的展開)", check_axis_expansion, cache),
            _safe("Gate⓪／① 對照軸純度(query 只含 P＋I，C 不進 query)", check_comparator_purity, cache),
            _safe("Gate① SR分工(DB腿主檢噪音不得進語料庫)", check_sr_division, cache),
            _safe("Gate① SR filter 複合語法(PubType/MeSH＋Title/Abstract,MECIR C33)", check_sr_filter_composite, cache),
            _safe("②b→③ 停頓點(②b須經使用者確認才可進③，防搶跑)", check_2b_stop, cache),
            _safe("②b 須以標題＋摘要高敏初篩(禁只憑標題)", check_2b_abstract_screen, cache),
            _safe("④→⑤a 停頓點(引文追蹤後須核准才可交叉驗證)", check_citation_stop, cache),
            _safe("⑤a→⑤b 停頓點(交叉驗證/撤稿後須核准才可決定納入單位)", check_xref_stop, cache),
            _safe("⑤b→⑥ 停頓點(決定納入單位後須核准才可產三表/報告)", check_units_stop, cache),
            _safe("⑤b 不得有『待評估,無內容』(③Tier4終端桶不在⑤b重生)", check_units_no_nocontent, cache),
            _safe("⑤b 只消費切題(離題/待評估等同丟棄、不入分析)", check_units_only_concordant, cache),
            _safe("⑥ 報告須照使用者 5 段格式(作者/年份/文獻類型 byline 等)", check_search_report_format, cache),
            _safe("③ 逐 Tier 停頓報告(T1→T2→T3→T4 不得跨層搶跑)", check_screen_tier_stops, cache),
            _safe("Gate③ 嚴格篩逐軸核對(不放水)", check_strict_screen, cache),
            _safe("④引文追蹤須標題+摘要批次篩(禁只憑標題丟)", check_citation_screen, cache),
            _safe("⑥驗證覆蓋(included/background 全驗)", check_verification_coverage, cache),
            _safe("Phase1 PDF 實體產出", check_pdf_emitted, cache),
            _safe("③ 融合分層篩 分割閉合＋反坍縮", check_screen_partition, cache),
            _safe("③ 離題只在實取全文後定案(Tier3)", check_excl_requires_fulltext, cache),
            _safe("③『全文及摘要皆無』須證明三層實取皆失敗", check_nocontent_bucket, cache),
            _safe("撤稿不得殘留納入/背景/Zotero", check_no_retracted, cache),
            _safe("無法驗證(UNVERIFIED)須剔除(同撤稿,不得入⑤b/交接/Zotero)", check_no_unverified, cache)]


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
