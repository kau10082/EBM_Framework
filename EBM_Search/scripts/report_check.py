# -*- coding: utf-8 -*-
"""
report_check.py — SR 檢索報告『版型/內容』硬 gate（反這輪人工抓出的報告缺失）
==============================================================================
讀 _search_report.json，機器核對「使用者 2026-06 逐條糾正」的報告規則，任一不成立即 FAIL。
把原本只在記憶/SPEC 文字、別人 clone 拿不到、純靠人眼抓的東西，變成可攜可執行的稽核。

檢查項：
 1. ③ 嚴格篩只能切題/離題二分：funnel 各步『remain』不得出現「待覆核/待補」（中間態應已解析/移待評估）。
 2. 核心 Study 表：每筆 report 元組長度=5(title,pmid,doi,ft,xref)；title 非空且非佔位；pmid 非空。
 3. 研究名稱不得是佔位：不得含「待確認/請見/PENDING/未命名」。
 4. 子報告逐筆列：不得出現「另含 N 篇」這種省略字樣。
 5. 背景表：每筆 6 欄(含 pmid 與檢核 xref)；pmid 非空。
 6. 進行中/待結果試驗表必須存在且非空（ongoing_trials）。
 7. funnel_closure 要含『嚴格篩二分』算式（切題+離題=內容可篩數）。

用法：python report_check.py --in _search_report.json
程式內：import report_check; fails = report_check.check(data)
"""
import sys, re, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

PLACEHOLDER_STUDY = ("待確認", "請見", "pending", "未命名", "tbd", "待定")
PLACEHOLDER_TITLE = ("(無標題)", "（無標題）", "請見pmid", "見pmid", "no title", "")

def check(data):
    fails = []
    # 1. ③ 二分：funnel remain 不得有待覆核/待補
    for s in data.get("funnel", []):
        rm = str(s.get("remain", "")) + " " + str(s.get("change", ""))
        # 只在『嚴格篩』那一步嚴管 remain；change 可解釋
        if "嚴格篩" in str(s.get("step", "")):
            if re.search(r"待覆核|待補", str(s.get("remain", ""))):
                fails.append("③ 嚴格篩的 remain 出現『待覆核/待補』：應只切題/離題二分（中間態須解析或移②c待評估）")
    # 2-4. 核心 Study 表
    studies = data.get("studies", [])
    if not studies:
        fails.append("缺核心 Study 表（studies 空）")
    for grp in studies:
        name = str(grp.get("study", ""))
        if any(p in name.lower() for p in PLACEHOLDER_STUDY):
            fails.append(f"研究名稱為佔位『{name}』：須填真實試驗名（讀全文定案對照臂後再分流）")
        for rep in grp.get("reports", []):
            if not isinstance(rep, (list, tuple)) or len(rep) != 5:
                fails.append(f"[{name}] 報告元組須 5 欄(title,pmid,doi,ft,xref)，實得 {len(rep) if hasattr(rep,'__len__') else '?'}")
                continue
            title, pmid, doi, ft, xref = rep
            if not str(title).strip() or str(title).strip().lower() in PLACEHOLDER_TITLE:
                fails.append(f"[{name}] 報告標題空/佔位（pmid={pmid}）：渲染前須回填真實標題（EuropePMC core）")
            if not str(pmid).strip():
                fails.append(f"[{name}] 報告缺 PMID（title={str(title)[:30]}）")
            if str(ft).strip() in ("", "?", "？") or str(ft).strip() not in ("線上", "僅摘要", "需補"):
                fails.append(f"[{name}] 全文狀態空/非列舉值『{ft}』（pmid={pmid}）：須∈線上/僅摘要/需補，不得留 ?")
            if not str(doi).strip():
                fails.append(f"[{name}] DOI 欄空（pmid={pmid}）：無 DOI 須顯式填『缺』")
    # 4. 省略字樣（全文掃 studies 區）
    blob = json.dumps(studies, ensure_ascii=False)
    if re.search(r"另含\s*\d+\s*篇|以下略|共\s*\d+\s*篇\)", blob):
        fails.append("核心表出現『另含 N 篇/以下略』省略：子報告須逐筆列全")
    # 5. 背景表 6 欄 + pmid
    for r in data.get("background", []):
        if not isinstance(r, (list, tuple)) or len(r) != 6:
            fails.append(f"背景表元組須 6 欄(title,pmid,doi,type,ft,xref)，實得 {len(r) if hasattr(r,'__len__') else '?'}")
            continue
        for col, val in zip(("標題","PMID","DOI","型態","全文狀態","檢核"), r):
            if str(val).strip() in ("", "?", "？"):
                fails.append(f"背景表『{col}』空/?（{str(r[0])[:28]}）")
        if str(r[4]).strip() and str(r[4]).strip() not in ("線上", "僅摘要", "需補"):
            fails.append(f"背景表全文狀態非列舉值『{r[4]}』（{str(r[0])[:28]}）")
    # 6. 進行中試驗表
    if not data.get("ongoing_trials"):
        fails.append("缺『進行中/待結果試驗』表（ongoing_trials 空）：CT.gov 招募中/protocol 須列，供 PRISMA 完整度")
    # 7. funnel_closure 含二分算式
    fc = data.get("funnel_closure", "")
    if not re.search(r"切題.*離題|\d+\s*\+\s*\d+\s*=\s*\d+", fc):
        fails.append("funnel_closure 缺『嚴格篩二分』算式（切題+離題=內容可篩數）")
    return fails

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="infile", required=True)
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}"); sys.exit(0)
    fails = check(json.loads(p.read_text(encoding="utf-8")))
    if fails:
        print("❌ 報告版型/內容檢查未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 報告版型/內容通過（③二分・PMID欄・無佔位/空標題・背景檢核欄・進行中表・閉合算式）。")

if __name__ == "__main__":
    main()
