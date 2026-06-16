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

    import leg_exhaust_check
    allok &= _assert_fires("Gate① 取盡（OpenAlex 600/1216）",
        leg_exhaust_check.check([{"leg":"PubMed","hitCount":218,"fetched":218,"exhaustible":True},
                                 {"leg":"OpenAlex","hitCount":1216,"fetched":600,"exhaustible":True},
                                 {"leg":"EuropePMC","hitCount":6252,"fetched":6252,"exhaustible":True},
                                 {"leg":"ClinicalTrials.gov","hitCount":137,"fetched":137,"exhaustible":True}]))

    import report_check
    bad = {"funnel":[{"step":"③ 嚴格篩","remain":"待覆核 73"}],
           "studies":[{"study":"待確認對照臂","reports":[["",  "", "10.x","線上","○"]]}],
           "background":[["t","","10.x","SR"]], "ongoing_trials":[], "funnel_closure":""}
    allok &= _assert_fires("報告版型/內容（佔位名/空標題/缺PMID/背景欄/無進行中表）",
        report_check.check(bad))

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
    shutil.rmtree(tmp, ignore_errors=True)

    print(("\n✅ 全部守門有效。" if allok else "\n❌ 有守門失效，請修復！"))
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
