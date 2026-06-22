# -*- coding: utf-8 -*-
"""
selftest_guards.py — 守門自我驗證（裝完/clone 後跑一次，證明硬 gate 真的會 FAIL）
================================================================================
不依賴任何 run 的真實資料：對每個守門餵「故意壞」的 fixture，斷言它回非空 fails。
讓任何使用者（含 repo 上的別人）安裝後可一鍵確認守門有效，而非只是擺著。

用法：python selftest_guards.py   # 全綠＝守門可用；任一未 FAIL＝守門失效
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _assert_fires(name, fails):
    ok = bool(fails)
    print(("  ✅" if ok else "  ❌") + f" {name}：" + ("會 FAIL（守門有效）" if ok else "未 FAIL（守門失效！）"))
    return ok

def _assert_true(name, cond):
    print(("  ✅" if cond else "  ❌") + f" {name}：" + ("通過" if cond else "FAIL"))
    return bool(cond)

def main():
    allok = True
    print("守門自我驗證（餵壞資料，應全部 FAIL）：")

    import gate_guard as _gg_strat, tempfile as _tf_s, json as _js_s, io as _io_s, shutil as _sh_s
    # Gate ⓪ 防搶跑：g1 已產出但 g0 未核准 → 必須 FAIL
    _tmps = Path(_tf_s.mkdtemp())
    _js_s.dump([{"leg":"PubMed","query":"COPD AND triple therapy","hitCount":1,"fetched":1,"exhaustible":True}],
               _io_s.open(_tmps/"g1_legs_manifest.json","w",encoding="utf-8"))
    _js_s.dump({"topic":"x","axes":{}}, _io_s.open(_tmps/"g0_strategy.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate⓪ 搶跑（g1 已產出但策略未經使用者核准）",
        _gg_strat.check_strategy_approved(_tmps))
    # 正向：g0 標 approved_by_user=true → 應通過（防誤報）
    _js_s.dump({"topic":"x","axes":{},"approved_by_user":True}, _io_s.open(_tmps/"g0_strategy.json","w",encoding="utf-8"))
    _sok = _gg_strat.check_strategy_approved(_tmps)
    print(("  ✅" if not _sok else "  ❌") + " 策略已核准應通過（防誤報）：" + ("通過" if not _sok else str(_sok)))
    allok &= (not _sok)
    _sh_s.rmtree(_tmps, ignore_errors=True)

    import leg_exhaust_check
    allok &= _assert_fires("Gate① 取盡（OpenAlex 600/1216）",
        leg_exhaust_check.check([{"leg":"PubMed","hitCount":218,"fetched":218,"exhaustible":True},
                                 {"leg":"OpenAlex","hitCount":1216,"fetched":600,"exhaustible":True},
                                 {"leg":"EuropePMC","hitCount":6252,"fetched":6252,"exhaustible":True},
                                 {"leg":"ClinicalTrials.gov","hitCount":137,"fetched":137,"exhaustible":True}]))

    import strategy_adherence_check
    # 不准加過濾的腿（OpenAlex）卻在 query 出現設計過濾特徵 → 必須 FAIL
    allok &= _assert_fires("Gate① 策略遵從（OpenAlex 擅自加 RCT/meta-analysis 過濾）",
        strategy_adherence_check.check(
            [{"leg":"PubMed","query":"COPD AND triple therapy AND randomized[tiab]","hitCount":1,"fetched":1,"exhaustible":True},
             {"leg":"OpenAlex","query":'"triple therapy" AND COPD AND (randomized OR "meta-analysis")',"hitCount":1,"fetched":1,"exhaustible":True}],
            {"legs":[{"leg":"PubMed","design_filter_allowed":True},
                     {"leg":"OpenAlex","design_filter_allowed":False}]}))

    import axis_coverage_check
    _ax_strat = {"axes":{"P":{"synonyms":["COPD","chronic obstructive pulmonary disease"],"in_query":True,"mandatory_screen":True},
                         "I":{"synonyms":["triple therapy","ICS/LABA/LAMA","Trelegy"],"in_query":True,"mandatory_screen":True},
                         "C":{"synonyms":["LABA/LAMA","umeclidinium/vilanterol"],"in_query":False,"mandatory_screen":True}}}
    # 某腿 query 缺 P 軸同義詞 → 四軸沒展開 → FAIL
    allok &= _assert_fires("Gate① 四軸覆蓋（OpenAlex query 缺疾病軸）",
        axis_coverage_check.check([{"leg":"OpenAlex","query":"triple therapy single inhaler"}], _ax_strat))
    _axok = axis_coverage_check.check([{"leg":"PubMed","query":'COPD AND "triple therapy"'}], _ax_strat)
    print(("  ✅" if not _axok else "  ❌") + " 四軸覆蓋 query 含 P+I 應通過（防誤報）：" + ("通過" if not _axok else str(_axok)))
    allok &= (not _axok)

    import axis_expansion_check
    # 稀疏策略：P 只有 1 個裸詞 COPD → 四軸沒展開 → FAIL
    allok &= _assert_fires("Gate⓪ 四軸展開（P 軸只有裸詞 COPD，未展開）",
        axis_expansion_check.check({"axes":{"P":{"synonyms":["COPD"],"in_query":True,"mandatory_screen":True},
                                            "I":{"synonyms":["triple therapy","ICS/LABA/LAMA","Trelegy"],"in_query":True}}}))
    # 純縮寫/代號、無全文形式 → 缺『縮寫↔全文』展開 → FAIL
    allok &= _assert_fires("Gate⓪ 四軸展開（I 軸只有縮寫/代號，無全文形式）",
        axis_expansion_check.check({"axes":{"P":{"synonyms":["COPD","chronic obstructive pulmonary disease","emphysema"],"in_query":True},
                                            "I":{"synonyms":["SITT","FF/UMEC/VI","BGF"],"in_query":True}}}))
    # 防誤報：兩軸都真的展開（≥3 且含全文形式）→ PASS
    _aeok = axis_expansion_check.check({"axes":{"P":{"synonyms":["COPD","chronic obstructive pulmonary disease","emphysema"],"in_query":True},
                                                "I":{"synonyms":["triple therapy","single-inhaler triple therapy","Trelegy"],"in_query":True}}})
    print(("  ✅" if not _aeok else "  ❌") + " 四軸展開：兩軸已展開應通過（防誤報）：" + ("通過" if not _aeok else str(_aeok)))
    allok &= (not _aeok)

    import comparator_purity_check
    # query 摻入 C 軸（in_query=false）同義詞『LABA/LAMA』（standalone）→ FAIL
    allok &= _assert_fires("Gate⓪／① 對照軸純度（query 摻入 C 軸 LABA/LAMA）",
        comparator_purity_check.check([{"leg":"OpenAlex","query":"COPD triple therapy versus LABA/LAMA"}], _ax_strat))
    # 防誤報：I 軸『ICS/LABA/LAMA』內含 C 軸子字串『LABA/LAMA』，遮蔽 I 軸後不應誤判 → PASS
    _cpok = comparator_purity_check.check([{"leg":"PubMed","query":'COPD AND "ICS/LABA/LAMA"'}], _ax_strat)
    print(("  ✅" if not _cpok else "  ❌") + " 對照軸純度：I 軸含 C 子字串不誤判（防誤報）：" + ("通過" if not _cpok else str(_cpok)))
    allok &= (not _cpok)

    import sr_division_check
    # SR filter 啟用、語料庫含『非 PubMed DB 腿主檢(EuropePMC)』→ FAIL（主檢噪音灌進池）
    _sr_strat = {"sr_filter_decision":"applied","legs":[
        {"leg":"PubMed"},{"leg":"EuropePMC"},{"leg":"EuropePMC-SR"},
        {"leg":"Consensus-SR"},{"leg":"ClinicalTrials.gov"}]}
    allok &= _assert_fires("Gate① SR分工（DB腿主檢EuropePMC灌進語料庫）",
        sr_division_check.check(_sr_strat, [{"uid":"u1","legs":["EuropePMC"]}]))
    # 防誤報：語料庫只含 PubMed(RCT)／-SR 變體／CT.gov → PASS
    _srok = sr_division_check.check(_sr_strat, [
        {"uid":"a","legs":["PubMed"]},{"uid":"b","legs":["EuropePMC-SR"]},
        {"uid":"c","legs":["Consensus-SR"]},{"uid":"d","legs":["ClinicalTrials.gov"]}])
    print(("  ✅" if not _srok else "  ❌") + " SR分工：只 -SR/PubMed/CT.gov 進池應通過（防誤報）：" + ("通過" if not _srok else str(_srok)))
    allok &= (not _srok)
    # 未啟用 SR filter（無 sr_filter_decision、無 -SR 子腿）→ 不適用、回 []（不誤擋）
    _srna = sr_division_check.check({"legs":[{"leg":"PubMed"},{"leg":"EuropePMC"}]}, [{"uid":"x","legs":["EuropePMC"]}])
    print(("  ✅" if not _srna else "  ❌") + " SR分工：未啟用SR filter不誤擋（防誤報）：" + ("通過" if not _srna else str(_srna)))
    allok &= (not _srna)

    import strict_screen_check
    # 切題卻缺 C 軸證據（C=unknown）→ 放水 → FAIL
    allok &= _assert_fires("Gate③ 切題卻缺 C 軸（放水）",
        strict_screen_check.check([{"uid":"u1","verdict":"切題","axis_hits":{"P":"yes","I":"yes","C":"unknown"}}], _ax_strat))
    # 離題卻無任何軸確認缺（P,I 命中、C 僅 unknown）→ 應移待評估 → FAIL
    allok &= _assert_fires("Gate③ 離題卻無確認缺軸（應移待評估）",
        strict_screen_check.check([{"uid":"u2","verdict":"離題","axis_hits":{"P":"yes","I":"yes","C":"unknown"}}], _ax_strat))
    # 正向：用明確 token / {status,evidence} 結構標全軸命中 → 應通過
    _ssok = strict_screen_check.check([{"uid":"u3","verdict":"切題","axis_hits":{
        "P":"yes","I":{"status":"yes","evidence":"FF/UMEC/VI"},"C":{"status":"yes","evidence":"vs UMEC/VI"}}}], _ax_strat)
    print(("  ✅" if not _ssok else "  ❌") + " 嚴格篩切題全軸命中應通過（防誤報）：" + ("通過" if not _ssok else str(_ssok)))
    allok &= (not _ssok)
    # 放水漏洞修正回歸：切題卻把自由文字當證據（「未提及對照」）→ 應被當 unknown → FAIL
    allok &= _assert_fires("Gate③ 切題填自由文字(未提及對照)不得當命中",
        strict_screen_check.check([{"uid":"u4","verdict":"切題","axis_hits":{"P":"yes","I":"yes","C":"未提及對照組"}}], _ax_strat))

    import report_check
    # 5 段制（v0.22）：缺日期到日/缺真實字串/佔位名/空標題/缺進行中表 → 須 FAIL
    bad = {"search_date":"2026","pico":{},"databases":[],"limits":"",
           "search_strategy":[{"leg":"PubMed","query":"copd triple therapy"}],
           "funnel":[{"step":"③ 嚴格篩","remain":"切題 5"}],
           "included_studies":[{"study":"待確認對照臂","reports":[["", "", "10.x","○"]]}],
           "ongoing_trials":[], "funnel_closure":""}
    allok &= _assert_fires("報告版型/內容（日期非到日/無真實字串/佔位名/空標題/無進行中表）",
        report_check.check(bad))
    # 合規 5 段 fixture：須通過（防誤報）
    valid = {"search_date":"2026-06-20","pico":{"P":"COPD","I":"triple","C":"LABA/LAMA"},
             "databases":["PubMed","Europe PMC","ClinicalTrials.gov"],
             "limits":"未加 RCT filter；無語言/年份限制",
             "search_strategy":[{"leg":"PubMed","query":"(COPD[tiab] OR emphysema[tiab]) AND (\"triple therapy\"[tiab] OR Trelegy[tiab])"}],
             "funnel":[{"step":"③ 嚴格篩","remain":"切題 5/離題 3"}],
             "included_studies":[{"study":"IMPACT","type":"RCT","reports":[["Once-daily single-inhaler triple","29992737","10.1056/NEJMoa1713901","PubMed○/Crossref○"]]}],
             "ongoing_trials":[["NCT00000000","A triple therapy trial"]],
             "funnel_closure":"切題 5 + 離題 3 = 8",
             "prisma_flow":{"identification":100,"screening":80,"included":5}}
    no_prisma = dict(valid); no_prisma.pop("prisma_flow")
    allok &= _assert_fires("報告缺 PRISMA 流程數據（prisma_flow）",
        [f for f in report_check.check(no_prisma) if "prisma_flow" in f])
    _vp = report_check.check(valid)
    print(("  ✅" if not _vp else "  ❌") + " 報告合規 fixture 應通過（防誤報）：" + ("通過" if not _vp else str(_vp)))
    allok &= (not _vp)
    # 修正回歸：included:0（零納入報告）為合法，prisma 檢查不得誤擋
    zero_inc = dict(valid); zero_inc["prisma_flow"] = {"identification":50,"screening":40,"included":0}
    _z = [f for f in report_check.check(zero_inc) if "prisma_flow" in f]
    print(("  ✅" if not _z else "  ❌") + " PRISMA included:0 應合法（防誤擋）：" + ("通過" if not _z else str(_z)))
    allok &= (not _z)
    # (M2) 欄位檢核機制：曖昧『缺』/空欄 → FAIL
    amb = dict(valid); amb["included_studies"]=[{"study":"IMPACT","type":"RCT","reports":[["A triple trial","缺","缺","PubMed○/Crossref未索引"]]}]
    allok &= _assert_fires("段4 欄位曖昧『缺』空欄", [f for f in report_check.check(amb) if "每格須填滿" in f])
    # (M2) 驗證欄無 ○（無任何索引確認存在性）→ FAIL
    nover = dict(valid); nover["included_studies"]=[{"study":"IMPACT","type":"RCT","reports":[["A triple trial","無","無","PubMed未索引／Crossref未索引"]]}]
    allok &= _assert_fires("段4 無索引驗證存在性(無○)", [f for f in report_check.check(nover) if "未經任何索引驗證" in f])
    # (M2) fetch_failed 殘留 → FAIL
    ff = dict(valid); ff["id_backfill"]={"fetch_failed":3}
    allok &= _assert_fires("段4 識別碼 fetch_failed 殘留", [f for f in report_check.check(ff) if "fetch_failed" in f])
    # (M2) 正向：缺值用明確『無』+ 驗證欄有 ○ → 通過（防誤報）
    okmark = dict(valid); okmark["included_studies"]=[{"study":"IMPACT","type":"RCT","reports":[["A triple trial","無","10.1/x","PubMed未索引／Crossref○"]]}]; okmark["id_backfill"]={"fetch_failed":0}
    _om = report_check.check(okmark)
    print(("  ✅" if not _om else "  ❌") + " 段4 缺值標『無』+驗證有○ 應通過（防誤報）：" + ("通過" if not _om else str(_om)))
    allok &= (not _om)

    import gate_guard, tempfile, json, io, shutil
    # ── ②b→③ 停頓點守門回歸（②b 完成後須經使用者確認才可進 ③，防搶跑）──
    _t2b = Path(tempfile.mkdtemp())
    json.dump([{"uid":"s1"}], io.open(_t2b/"g2b_survivors.json","w",encoding="utf-8"))
    json.dump([{"uid":"s1","verdict":"切題","abstract":"x"}], io.open(_t2b/"g3_FINAL_screen.json","w",encoding="utf-8"))
    # g3 已產出但無 g2b_checkpoint 核准 → FAIL
    allok &= _assert_fires("②b→③ 停頓點（③未經②b確認就搶跑）", gate_guard.check_2b_stop(_t2b))
    # 正向1：②b 完成、尚未進 ③（無 g3）→ 不適用(None)、不誤擋
    (_t2b/"g3_FINAL_screen.json").unlink()
    _s2 = gate_guard.check_2b_stop(_t2b)
    print(("  ✅" if _s2 is None else "  ❌")+" ②b→③：停在②b（無g3）不誤擋（防誤報）："+("通過" if _s2 is None else str(_s2)))
    allok &= (_s2 is None)
    # 正向2：g2b_checkpoint 已核准 + g3 → 通過
    json.dump([{"uid":"s1","verdict":"切題","abstract":"x"}], io.open(_t2b/"g3_FINAL_screen.json","w",encoding="utf-8"))
    json.dump({"approved_by_user":True}, io.open(_t2b/"g2b_checkpoint.json","w",encoding="utf-8"))
    _s3 = gate_guard.check_2b_stop(_t2b)
    print(("  ✅" if not _s3 else "  ❌")+" ②b→③：②b已核准後進③應通過（防誤報）："+("通過" if not _s3 else str(_s3)))
    allok &= (not _s3)
    shutil.rmtree(_t2b, ignore_errors=True)

    # ── 全文/摘要搜尋及嚴格離題篩選 守門回歸（取代 Stage A/B 切分＋待評估雙桶；單一產物 g3_FINAL_screen.json）──
    tmp = Path(tempfile.mkdtemp())
    # (1) 反坍縮：uid 重複 → FAIL
    json.dump([{"uid":"u0","verdict":"切題","abstract":"x"},
               {"uid":"u0","verdict":"離題","abstract":"y","tier":3,"fulltext_parse_attempted":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③ 反坍縮（uid 重複）", gate_guard.check_screen_partition(tmp))
    # (1b) 切題無內容(無abstract/非登錄AI/無實抓證明) → FAIL
    json.dump([{"uid":"n1","verdict":"切題","abstract":""}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③ 切題無內容卻拿到判定",
        [f for f in gate_guard.check_screen_partition(tmp) if ("無內容" in f or "實抓" in f)])
    # (1c) 正向：切題有摘要、離題 tier3、皆無證明齊 → 通過（防誤報）
    json.dump([{"uid":"a","verdict":"切題","abstract":"real abstract content here"},
               {"uid":"b","verdict":"離題","abstract":"off topic","tier":3,"fulltext_parse_attempted":True},
               {"uid":"c","verdict":"全文及摘要皆無","fulltext_parse_attempted":True,"channels_exhausted":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    _pp=gate_guard.check_screen_partition(tmp)
    print(("  ✅" if not _pp else "  ❌")+" ③ 分割閉合合法應通過（防誤報）："+("通過" if not _pp else str(_pp)))
    allok &= (not _pp)
    # (2) 離題只在 Tier3 定案：離題但未實取全文(無 tier3/fulltext_parse_attempted) → FAIL
    json.dump([{"uid":"e1","verdict":"離題","abstract":"thin abstract"}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③ 離題未升級到全文(Tier3)就定案", gate_guard.check_excl_requires_fulltext(tmp))
    # (2b) 正向：離題且 fulltext_parse_attempted → 通過（防誤報）
    json.dump([{"uid":"e2","verdict":"離題","abstract":"t","fulltext_parse_attempted":True}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    _ex=gate_guard.check_excl_requires_fulltext(tmp)
    print(("  ✅" if not _ex else "  ❌")+" ③ 離題已實取全文應通過（防誤報）："+("通過" if not _ex else str(_ex)))
    allok &= (not _ex)
    # (2c) 正向：登錄/AI 離題＝終端結構化內容、無對應全文可取 → tier2 即可、免 Tier3（防誤報）
    json.dump([{"uid":"e3","verdict":"離題","tier":2,"content_status":"registry","nct":"NCT9"},
               {"uid":"e4","verdict":"離題","tier":2,"content_status":"ai_summary"}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    _exr=gate_guard.check_excl_requires_fulltext(tmp)
    print(("  ✅" if not _exr else "  ❌")+" ③ 登錄/AI 離題(tier2 終端)應通過（防誤報）："+("通過" if not _exr else str(_exr)))
    allok &= (not _exr)
    # (3)『全文及摘要皆無』須證明三層皆失敗：有 abstract 卻丟此桶 → FAIL
    json.dump([{"uid":"z1","verdict":"全文及摘要皆無","abstract":"actually has content","fulltext_parse_attempted":True,"channels_exhausted":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③『全文及摘要皆無』卻其實有內容", gate_guard.check_nocontent_bucket(tmp))
    # (3b)『全文及摘要皆無』缺實取證明 → FAIL
    json.dump([{"uid":"z2","verdict":"全文及摘要皆無"}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③『全文及摘要皆無』未證明三層實取皆失敗", gate_guard.check_nocontent_bucket(tmp))
    # (3c) 正向：無內容且證明齊 → 通過（防誤報）
    json.dump([{"uid":"z3","verdict":"全文及摘要皆無","fulltext_parse_attempted":True,"channels_exhausted":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    _nc=gate_guard.check_nocontent_bucket(tmp)
    print(("  ✅" if not _nc else "  ❌")+" ③『全文及摘要皆無』證明齊應通過（防誤報）："+("通過" if not _nc else str(_nc)))
    allok &= (not _nc)
    # (3d)『全文及摘要皆無』有 DOI 卻無 unpaywall_checked（只試 PMC 就宣稱三層皆失敗）→ FAIL
    json.dump([{"uid":"z4","verdict":"全文及摘要皆無","doi":"10.1/x","fulltext_parse_attempted":True,"channels_exhausted":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("③『全文及摘要皆無』有DOI卻沒查Unpaywall",
        [f for f in gate_guard.check_nocontent_bucket(tmp) if "unpaywall" in f.lower()])
    # (3e) 正向：有 DOI 且 unpaywall_checked → 通過（防誤報）
    json.dump([{"uid":"z5","verdict":"全文及摘要皆無","doi":"10.1/x","fulltext_parse_attempted":True,"channels_exhausted":True,"unpaywall_checked":True}],
              io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    _nc2=gate_guard.check_nocontent_bucket(tmp)
    print(("  ✅" if not _nc2 else "  ❌")+" ③『全文及摘要皆無』有DOI且查過Unpaywall應通過（防誤報）："+("通過" if not _nc2 else str(_nc2)))
    allok &= (not _nc2)
    # 撤稿不得殘留
    json.dump([{"pmid":"999","verdict":"RETRACTED"}], io.open(tmp/"g6_verified.json","w",encoding="utf-8"))
    json.dump([{"pmid":"999","title":"retracted","verdict":"background"}], io.open(tmp/"g8_zotero_payload.json","w",encoding="utf-8"))
    allok &= _assert_fires("撤稿殘留 Zotero payload", gate_guard.check_no_retracted(tmp))
    # 審查 🔴 補強回歸：撤稿僅有 DOI（無 PMID，Crossref is-retracted）也須擋下
    json.dump([{"doi":"10.1/retracted","verdict":"RETRACTED"}], io.open(tmp/"g6_verified.json","w",encoding="utf-8"))
    json.dump([{"doi":"10.1/RETRACTED","title":"doi-only","verdict":"background"}], io.open(tmp/"g8_zotero_payload.json","w",encoding="utf-8"))
    allok &= _assert_fires("撤稿僅有 DOI（無PMID）也須擋下", gate_guard.check_no_retracted(tmp))
    shutil.rmtree(tmp, ignore_errors=True)

    # ④ 引文追蹤篩選方式：只憑標題丟棄 → FAIL；批次抓摘要+標題摘要篩 → 通過
    import citation_screen_check
    allok &= _assert_fires("④ 只憑標題丟棄新候選（Cochrane 紅線）",
        citation_screen_check.check({"screening_method":"title-only",
            "rounds":[{"round":1,"screened_on":"title-only","new_with_id":100,"abstracts_fetched":0,"title_only_dropped":80}]}))
    _cs = citation_screen_check.check({"screening_method":"title+abstract (batch)",
            "rounds":[{"round":1,"screened_on":"title+abstract","new_with_id":100,"abstracts_fetched":95,"title_only_dropped":0}]})
    print(("  ✅" if not _cs else "  ❌") + " ④ 批次抓摘要+標題摘要篩應通過（防誤報）：" + ("通過" if not _cs else str(_cs)))
    allok &= (not _cs)

    # fulltext_exhaust 防呆（🔴 審查）：OA 下載的 cookie/paywall 純文字(無科學特徵)不算真內容；真內容應通過
    import fulltext_exhaust as _fx
    _wall = ("We use cookies to improve your experience. By continuing you agree to our privacy "
             "policy and terms of service. Please sign in or subscribe to access this article. "
             "Copyright 2024 the publisher. All rights reserved. ") * 3
    allok &= _assert_true("fulltext_exhaust 防呆：cookie/paywall 牆頁不算真內容",
        not _fx._looks_like_content(_wall, 250))
    _real = ("Background: patients with COPD. Methods: randomized double-blind trial of triple therapy "
             "versus LABA/LAMA dual bronchodilator. Results: exacerbation rate ratio 0.75 (95% CI "
             "0.70-0.81), p<0.001. Conclusions: efficacy demonstrated with higher pneumonia risk.")
    allok &= _assert_true("fulltext_exhaust 防呆：真內容(含方法學特徵)應通過",
        _fx._looks_like_content(_real, 120))

    # ⑥驗證覆蓋／Phase1 PDF 實體（沿用）
    tmp2 = Path(tempfile.mkdtemp())
    # Bug6 驗證覆蓋：交接包有 included 但無 g6_verified
    json.dump({"papers":[{"paper_id":"P1","verdict":"included","pmid":"123"}]}, io.open(tmp2/"_corpus_seed.json","w",encoding="utf-8"))
    allok &= _assert_fires("⑥驗證覆蓋（included 未驗證）", gate_guard.check_verification_coverage(tmp2))
    # Bug7 PDF 實體：_search_report.json 無 pdf_path
    json.dump({"studies":[],"pdf_path":""}, io.open(tmp2/"_search_report.json","w",encoding="utf-8"))
    allok &= _assert_fires("Phase1 PDF 未產出/未登記", gate_guard.check_pdf_emitted(tmp2))
    # 修正回歸：無 PMID/DOI（NCT 登錄）的 included 不得被驗證覆蓋守門誤判
    json.dump({"papers":[{"paper_id":"NCTonly","verdict":"background","nct":"NCT01"}]}, io.open(tmp2/"_corpus_seed.json","w",encoding="utf-8"))
    json.dump([], io.open(tmp2/"g6_verified.json","w",encoding="utf-8"))
    _nv = gate_guard.check_verification_coverage(tmp2)
    print(("  ✅" if not _nv else "  ❌") + " 無 ID(NCT) 文獻不被驗證覆蓋誤判（防誤報）：" + ("通過" if not _nv else str(_nv)))
    allok &= (not _nv)
    shutil.rmtree(tmp2, ignore_errors=True)

    # Stop hook 可攜發現：掃哨兵旗標找『進行中』cache（修復前 _find_cache(None) 在非 Windows／無 run_state
    # 會回 None → hook 靜默 exit 0 → 守門等同失效；本測證明改用旗標掃描後找得到，且無旗標時休眠）
    tmpd = Path(tempfile.mkdtemp())
    (tmpd/"flagged").mkdir(); (tmpd/"flagged"/gate_guard.ACTIVE_FLAG).write_text("")
    (tmpd/"noflag").mkdir()
    _found = gate_guard._find_active_cache_by_flag(roots=[tmpd])
    _ok = (_found is not None and _found.name == "flagged")
    print(("  ✅" if _ok else "  ❌") + " Stop hook 旗標發現：找到帶旗標的進行中 cache：" + ("通過" if _ok else f"FAIL({_found})"))
    allok &= _ok
    (tmpd/"flagged"/gate_guard.ACTIVE_FLAG).unlink()
    _none = gate_guard._find_active_cache_by_flag(roots=[tmpd])
    print(("  ✅" if _none is None else "  ❌") + " 無旗標→回 None（hook 休眠、全域零打擾）：" + ("通過" if _none is None else str(_none)))
    allok &= (_none is None)
    shutil.rmtree(tmpd, ignore_errors=True)

    print(("\n✅ 全部守門有效。" if allok else "\n❌ 有守門失效，請修復！"))
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
