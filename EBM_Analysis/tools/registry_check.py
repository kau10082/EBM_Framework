# -*- coding: utf-8 -*-
"""
registry_check.py — ClinicalTrials.gov 註冊 vs 發表『選擇性報告』自動核對（RoB 2 Domain 5）
============================================================================================
給 NCT 號，抓 ClinicalTrials.gov API v2 的『預先指定主要結果＋時框＋主要完成日』，
供 EBM_Analysis 與發表論文比對：是否更改主要結果、測量時間點、或選擇性不報告
（MECIR C54/C55；RoB 2 Domain 5：是否依未盲前定稿之計畫分析）。無 API key、零相依。

用法：
  python tools/registry_check.py NCT03218917 NCT04594369 ...
  python tools/registry_check.py NCT04594369 --published "Annualized rate of pulmonary exacerbations over 52 weeks"
回傳每個 NCT 的 registered primary outcome；給 --published 時做粗略字串比對、提示 switching 疑慮。
"""
import sys, json, urllib.request, urllib.parse, re
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
API = "https://clinicaltrials.gov/api/v2/studies/"

def fetch(nct):
    # 取 primary + secondary（次要結果更常被選擇性報告，Ch7 §7.2.3.3）
    fields = ("protocolSection.outcomesModule.primaryOutcomes,"
              "protocolSection.outcomesModule.secondaryOutcomes,"
              "protocolSection.statusModule.primaryCompletionDateStruct")
    url = API + nct + "?" + urllib.parse.urlencode({"fields": fields})
    req = urllib.request.Request(url, headers={"User-Agent": "EBM/1.0 (kau10082ai@gmail.com)"})
    j = json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))
    ps = j.get("protocolSection", {})
    om = ps.get("outcomesModule", {})
    po = om.get("primaryOutcomes", [])
    so = om.get("secondaryOutcomes", [])
    pcd = ps.get("statusModule", {}).get("primaryCompletionDateStruct", {})
    return po, pcd, so

def _toks(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {"the","of","to","over","a","in","and","up","week","weeks"}

def main(argv):
    ncts = [a for a in argv if a.upper().startswith("NCT")]
    pub = None
    if "--published" in argv:
        pub = argv[argv.index("--published") + 1]
    if not ncts:
        print(__doc__); return 2
    for nct in ncts:
        try:
            po, pcd, so = fetch(nct)
            if not po:
                print(f"{nct}: 註冊無主要結果欄"); continue
            m = po[0].get("measure", "?"); tf = po[0].get("timeFrame", "?")
            print(f"{nct}")
            print(f"  註冊主要結果：{m}")
            print(f"  時框：{tf}　｜　主要完成日：{pcd.get('date','?')} ({pcd.get('type','')})")
            print(f"  註冊次要結果：{len(so)} 項" + (f"（首項：{so[0].get('measure','?')[:50]}）" if so else "") + "　← 須一併比對是否選擇性報告/低報")
            if pub:
                overlap = _toks(m) & _toks(pub)
                ratio = len(overlap) / max(1, len(_toks(m)))
                verdict = "一致(consistent)" if ratio >= 0.6 else ("疑更改/不一致(possible switching)" if ratio < 0.3 else "部分相符，請人工覆核")
                print(f"  vs 發表「{pub[:60]}」→ 詞彙重疊 {ratio:.0%} → {verdict}")
        except Exception as e:
            print(f"{nct}: 取得失敗 {str(e)[:60]}")
    print("\n註：字串比對僅供初篩；最終 outcome switching 判定須人工核對註冊歷史版本與發表全文。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
