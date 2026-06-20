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
    bad = {"funnel":[{"step":"③ 嚴格篩","remain":"待覆核 73"}],
           "studies":[{"study":"待確認對照臂","reports":[["",  "", "10.x","線上","○"]]}],
           "background":[["t","","10.x","SR"]], "ongoing_trials":[], "funnel_closure":""}
    allok &= _assert_fires("報告版型/內容（佔位名/空標題/缺PMID/背景欄/無進行中表）",
        report_check.check(bad))
    # PRISMA 流程圖缺失（Bug7）：其餘合規、僅缺 prisma_flow → 須 FAIL 且指名 prisma_flow
    valid = {"funnel":[{"step":"③ 嚴格篩","remain":"切題 5/離題 3"}],
             "studies":[{"study":"IMPACT","reports":[["Once-daily single-inhaler triple","29992737","10.1056/NEJMoa1713901","線上","C+PM"]]}],
             "background":[["Some SR","12345678","10.1/x","SR-MA","線上","PM"]],
             "ongoing_trials":[["NCT00000000","recruiting"]],
             "funnel_closure":"切題 5 + 離題 3 = 8",
             "prisma_flow":{"identification":100,"screening":80,"included":5}}
    no_prisma = dict(valid); no_prisma.pop("prisma_flow")
    allok &= _assert_fires("報告缺 PRISMA 流程圖（prisma_flow）",
        [f for f in report_check.check(no_prisma) if "prisma_flow" in f])
    _vp = report_check.check(valid)
    print(("  ✅" if not _vp else "  ❌") + " 報告合規 fixture 應通過（防誤報）：" + ("通過" if not _vp else str(_vp)))
    allok &= (not _vp)
    # 修正回歸：included:0（零納入報告）為合法，prisma 檢查不得誤擋
    zero_inc = dict(valid); zero_inc["prisma_flow"] = {"identification":50,"screening":40,"included":0}
    _z = [f for f in report_check.check(zero_inc) if "prisma_flow" in f]
    print(("  ✅" if not _z else "  ❌") + " PRISMA included:0 應合法（防誤擋）：" + ("通過" if not _z else str(_z)))
    allok &= (not _z)

    import stage1_check
    allok &= _assert_fires("Stage A→B 邊界（無內容混入候選）",
        stage1_check.check({"schema_version":"stage1-1.0","legs":[{"leg":"PubMed","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"OpenAlex","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"EuropePMC","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"ClinicalTrials.gov","hitCount":1,"fetched":1,"exhaustible":True}],
          "candidates":[{"paper_id":"P1","title":"x","verdict":"candidate","fulltext_status":"none","abstract_status":"none"}],"awaiting":[]}))
    # Bug2：候選宣稱 abstract_status=have 卻無摘要內容 → 須 FAIL（只能憑標題篩）
    allok &= _assert_fires("Stage A 候選 abstract_status=have 但摘要內容空",
        [f for f in stage1_check.check({"schema_version":"stage1-1.0",
          "legs":[{"leg":"PubMed","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"OpenAlex","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"EuropePMC","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"ClinicalTrials.gov","hitCount":1,"fetched":1,"exhaustible":True}],
          "candidates":[{"paper_id":"P1","title":"x","verdict":"candidate","fulltext_status":"ai_summary_only","abstract_status":"have","abstract":""}],"awaiting":[]}) if "abstract" in f])
    # 防『未查全文就丟兩者皆無』：awaiting 標兩者皆無卻有 pmid → 須 FAIL
    _legs4=[{"leg":"PubMed","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"OpenAlex","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"EuropePMC","hitCount":1,"fetched":1,"exhaustible":True},{"leg":"ClinicalTrials.gov","hitCount":1,"fetched":1,"exhaustible":True}]
    _ok_cand=[{"paper_id":"C1","title":"t","verdict":"candidate","fulltext_status":"none","abstract_status":"have","abstract":"real abstract"}]
    allok &= _assert_fires("Stage A 待評估『兩者皆無』卻有 pmid（未查全文）",
        [f for f in stage1_check.check({"schema_version":"stage1-1.0","legs":_legs4,"candidates":_ok_cand,
          "awaiting":[{"paper_id":"A1","title":"y","reason":"兩者皆無","pmid":"12345678"}]}) if "兩者皆無" in f])
    # 審查 🔴 補強回歸：只有 oa_url（無 doi/pmid）也是全文路徑 → 兩者皆無 須 FAIL
    allok &= _assert_fires("Stage A 待評估『兩者皆無』只有 oa_url（無ID但有OA路徑）",
        [f for f in stage1_check.check({"schema_version":"stage1-1.0","legs":_legs4,"candidates":_ok_cand,
          "awaiting":[{"paper_id":"A4","title":"oa","reason":"兩者皆無","oa_url":"https://oa.example/y.pdf"}]}) if "oa_url" in f])
    # 審查 🟡 補強回歸：只有 pmcid（Europe PMC 常見）也是全文路徑 → 兩者皆無 須 FAIL
    allok &= _assert_fires("Stage A 待評估『兩者皆無』只有 pmcid（無其他ID）",
        [f for f in stage1_check.check({"schema_version":"stage1-1.0","legs":_legs4,"candidates":_ok_cand,
          "awaiting":[{"paper_id":"A5","title":"pmc","reason":"兩者皆無","pmcid":"PMC123456"}]}) if "pmcid" in f])
    # 防『有 OA 卻不抓就丟待評估』：待人工補全文帶 oa_url 卻未實際抓取 → 須 FAIL
    allok &= _assert_fires("Stage A 待評估有 oa_url 卻未抓 OA 全文",
        [f for f in stage1_check.check({"schema_version":"stage1-1.0","legs":_legs4,"candidates":_ok_cand,
          "awaiting":[{"paper_id":"A3","title":"w","reason":"待人工補全文","channels_exhausted":True,
                       "doi":"10.1/y","oa_url":"https://oa.example/x.pdf"}]}) if "oa_url" in f])
    # 正向：兩者皆無無 ID 合法；有 ID＋待人工補全文＋channels_exhausted 合法；
    #       有 oa_url 但已標 oa_fetch_attempted（抓過取不到）合法（防誤報）
    _wok=stage1_check.check({"schema_version":"stage1-1.0","legs":_legs4,"candidates":_ok_cand,
          "awaiting":[{"paper_id":"A1","title":"y","reason":"兩者皆無"},
                      {"paper_id":"A2","title":"z","reason":"待人工補全文","channels_exhausted":True,"doi":"10.1/x"},
                      {"paper_id":"A3","title":"w","reason":"待人工補全文","channels_exhausted":True,
                       "doi":"10.1/y","oa_url":"https://oa.example/x.pdf","oa_fetch_attempted":True}]})
    print(("  ✅" if not _wok else "  ❌") + " Stage A 待評估合法分類應通過（防誤報）：" + ("通過" if not _wok else str(_wok)))
    allok &= (not _wok)

    import gate_guard, tempfile, json, io, shutil, os
    # 反坍縮：偽造一筆無內容卻在 screened
    tmp = Path(tempfile.mkdtemp())
    json.dump([{"uid":"u0","abstract":"","title":"no-content"}], io.open(tmp/"g2c_FINAL_content.json","w",encoding="utf-8"))
    json.dump([{"uid":"u0","verdict":"切題"}], io.open(tmp/"g3_FINAL_screen.json","w",encoding="utf-8"))
    json.dump([], io.open(tmp/"g2c_awaiting_classification.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate③ 反坍縮（無內容卻在已篩）", gate_guard.check_partition_provenance(tmp))
    # Unpaywall 覆蓋：非全文有DOI但沒查
    json.dump([{"class":"僅摘要","doi":"10.1/x","title":"t"}], io.open(tmp/"g2c_FINAL_content.json","w",encoding="utf-8"))
    json.dump({}, io.open(tmp/"g2c_unpaywall.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate②c Unpaywall 覆蓋（漏跑）", gate_guard.check_unpaywall_coverage(tmp))
    # 撤稿不得殘留
    json.dump([{"pmid":"999","verdict":"RETRACTED"}], io.open(tmp/"g6_verified.json","w",encoding="utf-8"))
    json.dump([{"pmid":"999","title":"retracted","verdict":"background"}], io.open(tmp/"g8_zotero_payload.json","w",encoding="utf-8"))
    allok &= _assert_fires("撤稿殘留 Zotero payload", gate_guard.check_no_retracted(tmp))
    # 審查 🔴 補強回歸：撤稿僅有 DOI（無 PMID，Crossref is-retracted）也須擋下
    json.dump([{"doi":"10.1/retracted","verdict":"RETRACTED"}], io.open(tmp/"g6_verified.json","w",encoding="utf-8"))
    json.dump([{"doi":"10.1/RETRACTED","title":"doi-only","verdict":"background"}], io.open(tmp/"g8_zotero_payload.json","w",encoding="utf-8"))
    allok &= _assert_fires("撤稿僅有 DOI（無PMID）也須擋下", gate_guard.check_no_retracted(tmp))
    shutil.rmtree(tmp, ignore_errors=True)

    # ③待評估須先核對全文：g2c_awaiting_classification 有 doi/pmid 卻無全文核對證明 → FAIL
    tmp3 = Path(tempfile.mkdtemp())
    json.dump([{"paper_id":"W1","title":"x","pmid":"123","reason":"待全文"}], io.open(tmp3/"g2c_awaiting_classification.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate③ 待評估只憑摘要 punt（未核對全文）", gate_guard.check_screen_awaiting_resolved(tmp3))
    # 審查 🔴 補強回歸：只有 oa_url（無 doi/pmid）也須核對全文 → FAIL
    json.dump([{"paper_id":"W4","title":"oa","oa_url":"https://oa.example/z.pdf","reason":"待全文"}], io.open(tmp3/"g2c_awaiting_classification.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate③ 待評估只有 oa_url（無ID）也須核對全文", gate_guard.check_screen_awaiting_resolved(tmp3))
    # 正向：抓過全文仍無法核對(oa_fetch_attempted)→合法；無 ID→合法（防誤報）
    json.dump([{"paper_id":"W2","title":"y","pmid":"123","reason":"待全文","oa_fetch_attempted":True},
               {"paper_id":"W3","title":"z","reason":"待全文"}], io.open(tmp3/"g2c_awaiting_classification.json","w",encoding="utf-8"))
    _aw=gate_guard.check_screen_awaiting_resolved(tmp3)
    print(("  ✅" if not _aw else "  ❌") + " Gate③ 待評估已核對全文應通過（防誤報）：" + ("通過" if not _aw else str(_aw)))
    allok &= (not _aw)
    # 審查 🔴 補強回歸：check_waiting_fulltext 的全文路徑須含 oa_url
    json.dump([{"verdict":"待評估","title":"oa","oa_url":"https://oa.example/w.pdf"}], io.open(tmp3/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("Gate③ check_waiting_fulltext：有 oa_url 卻丟待評估", gate_guard.check_waiting_fulltext(tmp3))
    shutil.rmtree(tmp3, ignore_errors=True)

    # 待評估三管道：有 ID 卻沒把線上全文查盡就 punt → FAIL；三管道全查盡 → 通過
    import awaiting_channels_check
    allok &= _assert_fires("待評估三管道（有ID但缺 online_fulltext_checked）",
        awaiting_channels_check.check([{"paper_id":"A1","pmid":"123","reason":"待人工補全文",
                                        "abstract_checked":True,"oa_fetch_attempted":True,"channels_exhausted":True}]))
    allok &= _assert_fires("待評估『兩者皆無』卻帶 ID",
        awaiting_channels_check.check([{"paper_id":"A2","doi":"10.1/x","reason":"兩者皆無","abstract_checked":True}]))
    _acok = awaiting_channels_check.check([
        {"paper_id":"A3","pmid":"9","reason":"待人工補全文","abstract_checked":True,
         "online_fulltext_checked":True,"unpaywall_checked":True,"channels_exhausted":True},
        {"paper_id":"A4","reason":"兩者皆無","abstract_checked":True}])
    print(("  ✅" if not _acok else "  ❌") + " 待評估三管道：三管道全查盡應通過（防誤報）：" + ("通過" if not _acok else str(_acok)))
    allok &= (not _acok)

    # 待評估關責：③(g3) 出現待評估 → FAIL（待評估只能在 ②c 產生）
    import awaiting_stage_check
    allok &= _assert_fires("③ 誤生待評估（待評估只能在②c）",
        awaiting_stage_check.check([{"uid":"u1","verdict":"待評估","title":"x"}]))
    _asok = awaiting_stage_check.check([{"uid":"u1","verdict":"切題"},{"uid":"u2","verdict":"離題"}])
    print(("  ✅" if not _asok else "  ❌") + " 待評估關責：③ 全為切題/離題應通過（防誤報）：" + ("通過" if not _asok else str(_asok)))
    allok &= (not _asok)

    # Bug3 順序：g3 存在但缺 g2c/_stage1_corpus → ③ 早於 ②c
    tmp2 = Path(tempfile.mkdtemp())
    json.dump([{"uid":"u1","verdict":"切題"}], io.open(tmp2/"g3_FINAL_screen.json","w",encoding="utf-8"))
    allok &= _assert_fires("②c→③ 順序（③早於②c）", gate_guard.check_screen_order(tmp2))
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
