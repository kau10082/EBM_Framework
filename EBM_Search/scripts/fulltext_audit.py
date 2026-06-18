# -*- coding: utf-8 -*-
"""
fulltext_audit.py — 全文取得『不可跳過 Unpaywall』硬 gate（反幻覺/反便宜行事）
==============================================================================
針對交接包/結果中**被判定取不到全文**者（fulltext_channel∈{ai_synthesis,none}
或 fulltext_status∈{ai_summary_only,none}），**強制重跑 Unpaywall**：
若 Unpaywall 其實找得到 OA PDF → FAIL（代表分類時漏跑 Unpaywall、把可讀判成不可讀）。

把記憶鐵律「②c 分類必跑 Unpaywall、別只看 OA 旗標」從『靠我記得』變機器看守
（本輪此錯復發兩次：EuropePMC isOpenAccess=N 就斷定 ASPEN 取不到，Unpaywall 其實有 green OA）。

用法：python fulltext_audit.py --seed <_corpus_seed.json>
程式內：import fulltext_audit; fails = fulltext_audit.audit(papers)  # papers: list[dict]
"""
import sys, os, json, argparse, time
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
# Unpaywall 的 email 由 unpaywall._mailto() 解析（env CROSSREF_MAILTO ＞ config crossref.mailto）；不在此寫死個資
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "EBM_Analysis" / "tools"))

NOT_GOT = {"ai_synthesis", "none", None, ""}
NOT_GOT_STATUS = {"ai_summary_only", "none", None, ""}

def audit(papers, sleep=0.15):
    """回 (fails, missed)；missed=被漏判的 [(paper, unpaywall_dict)]。"""
    try:
        import unpaywall
    except Exception as e:
        return [f"fulltext_audit 無法載入 unpaywall：{str(e)[:60]}"], []
    fails, missed, unverifiable = [], [], []
    for p in papers:
        ch = p.get("fulltext_channel"); st = p.get("fulltext_status")
        if ch not in NOT_GOT and st not in NOT_GOT_STATUS:
            continue                                   # 已判有全文者不必再查
        doi = p.get("doi")
        if not doi:
            continue                                   # 無 DOI 無法 Unpaywall，跳過（非失敗）
        d = unpaywall.lookup(doi); time.sleep(sleep)
        if "is_oa" not in d:
            # Unpaywall 沒查成（網路逾時/UA 被擋回 {}，或 import 失敗 _error）——查成功才會有 is_oa 鍵。
            # 不可把「查失敗」當「非 OA」靜默放行，否則 gate 形同沒跑（機器看守被無聲繞過）。
            unverifiable.append(doi); continue
        if d.get("is_oa") and (d.get("pdf_url") or d.get("landing_url")):
            missed.append((p, d))
            fails.append(f"[{(p.get('title') or p.get('paper_id') or doi)[:50]}] 判 {ch or st}，但 Unpaywall 找到 OA（{d.get('oa_status')}）：{(d.get('pdf_url') or d.get('landing_url'))[:80]} → 應改 have/online、重讀全文")
    if unverifiable:
        fails.append(f"{len(unverifiable)} 筆 Unpaywall 查詢未成功（網路/被擋/email 解析不到），無法判定分類是否誠實——請檢查網路後重跑，勿視為通過：{unverifiable[:5]}{'…' if len(unverifiable) > 5 else ''}")
    return fails, missed

def _load_papers(seed_path):
    obj = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    return obj.get("papers", obj if isinstance(obj, list) else [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    a = ap.parse_args()
    papers = _load_papers(a.seed)
    n_check = sum(1 for p in papers if (p.get("fulltext_channel") in NOT_GOT or p.get("fulltext_status") in NOT_GOT_STATUS) and p.get("doi"))
    fails, missed = audit(papers)
    print(f"fulltext_audit：複查 {n_check} 筆『判取不到且有 DOI』者")
    if fails:
        print(f"❌ {len(fails)} 筆漏跑 Unpaywall（其實有 OA）：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 取不到全文者均已過 Unpaywall（Unpaywall 亦查無 OA）——分類誠實。")

if __name__ == "__main__":
    main()
