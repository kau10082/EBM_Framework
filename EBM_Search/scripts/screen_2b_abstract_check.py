# -*- coding: utf-8 -*-
"""
screen_2b_abstract_check.py — 鐵律『②b 高敏初篩須以「標題＋摘要」篩，嚴禁只憑標題』硬 gate
================================================================================
使用者鐵律（2026-06，Cochrane／MECIR 高敏感紅線；與 ④ 的 `citation_screen_check` 對稱）：
**②b 初步篩選（高敏初篩）必須以『標題＋摘要』判定，不可只看標題**。許多 RCT/SR 標題用成分名／
縮寫／廣義詞（chronic lung disease／airflow obstruction／inhaled therapy／PK/沉積研究只寫藥名），
只看標題會漏殺隱藏的相關研究；高敏感階段必須批次抓回摘要再以『標題＋摘要』篩。
唯一例外：確實無摘要可抓者（登錄試驗、會議摘要、抓取後確認無摘要），標明狀態後可只用標題＋登錄欄位篩。

讀 g2b_screen.json（結構化）：
  {"screening_method": "title+abstract", "abstracts_fetched": <int>, "title_only_dropped": <int>,
   "records": [{"uid","verdict"(kept/removed),"pmid","doi","has_abstract"(bool),
                "abstract_status"(have/none_after_fetch/registry/conference/no_id), ...}, ...]}

逐項斷言：
  • screening_method 必含 'title+abstract'（宣告以標題＋摘要篩）；舊版『純 list』(title-only) → FAIL。
  • title_only_dropped == 0（沒有任何記錄被『只憑標題』剔除）。
  • 任一『被剔除(removed)且有 ID(pmid/doi)』的記錄，必須有摘要證據：has_abstract=true，
    或 abstract_status ∈ {none_after_fetch, registry, conference}（＝確實抓過/確無摘要）；
    若摘要狀態空白又無摘要＝只憑標題丟 → FAIL。
  • 有 ID 的記錄存在時，abstracts_fetched 必須 > 0（確實批次抓過摘要）。

用法：python screen_2b_abstract_check.py --in g2b_screen.json
程式內：import screen_2b_abstract_check; fails = screen_2b_abstract_check.check(g2b)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ABSTRACT_FETCHED_STATES = {"have", "none_after_fetch", "registry", "conference"}

def check(g2b):
    fails = []
    if not g2b:
        return []  # ②b 尚未跑
    if isinstance(g2b, list):
        return ["g2b_screen.json 為純 list（無 screening_method/摘要狀態）：疑為『只憑標題』初篩——"
                "②b 必須以『標題＋摘要』高敏初篩（Cochrane/MECIR 紅線），請批次抓摘要後改寫結構化篩選結果"]
    if not isinstance(g2b, dict):
        return ["g2b_screen.json 格式非物件：無法稽核 ②b 篩選方式"]
    method = str(g2b.get("screening_method") or "")
    records = g2b.get("records") or []
    if "title+abstract" not in method:
        fails.append(f"②b screening_method 未聲明 'title+abstract'（實得 {g2b.get('screening_method')!r}）："
                     "②b 須以標題＋摘要高敏初篩（嚴禁只憑標題）")
    if g2b.get("title_only_dropped", 0):
        fails.append(f"②b title_only_dropped={g2b.get('title_only_dropped')}>0："
                     "嚴禁只憑標題剔除記錄（Cochrane 高敏感紅線；應批次抓摘要後以標題＋摘要篩）")
    has_id_any = False
    title_only_drops = 0
    for r in records:
        pid = r.get("pmid"); doi = r.get("doi")
        has_id = bool((pid and str(pid).strip()) or (doi and str(doi).strip()))
        if has_id:
            has_id_any = True
        if r.get("verdict") == "removed" and has_id:
            ok = bool(r.get("has_abstract")) or str(r.get("abstract_status") or "") in ABSTRACT_FETCHED_STATES
            if not ok:
                title_only_drops += 1
    if title_only_drops:
        fails.append(f"②b 有 {title_only_drops} 筆『有 ID 卻無摘要證據(has_abstract/abstract_status 皆空)』的記錄被剔除："
                     "等於只憑標題丟（應先批次抓摘要，確認無摘要者標 abstract_status 後才可只用標題判）")
    if has_id_any and not g2b.get("abstracts_fetched", 0):
        fails.append("②b 存在有 ID 的記錄但 abstracts_fetched=0：未批次抓摘要（應 efetch/EuropePMC 批次取回再以標題＋摘要篩）")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="g2b_screen.json")
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}（②b 尚未跑）"); sys.exit(0)
    g2b = json.loads(p.read_text(encoding="utf-8"))
    fails = check(g2b)
    if fails:
        print("❌ ②b 標題＋摘要初篩檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ ②b：以『標題＋摘要』高敏初篩、批次抓摘要、無只憑標題剔除。")

if __name__ == "__main__":
    main()
