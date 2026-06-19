# -*- coding: utf-8 -*-
"""
stage1_check.py — Stage A→B 邊界硬 gate（檢索切兩段的關鍵守門）
==============================================================
驗證 _stage1_corpus.json 的完整性與邊界不變量，PASS 才准進 Stage B（嚴格篩）。
把「待評估屬哪關」「全文狀態有沒有 resolved」「每腿有沒有取盡」從靠 Claude 記得，
釘成磁碟邊界的機器條件。

不變量：
 1. schema_version=stage1-1.0；必備 legs/candidates/awaiting。
 2. 每筆 candidate：title 非空、fulltext_status∈{have,ai_summary_only,none}、
    abstract_status∈{have,none}，且**不得 fulltext=none 又 abstract=none**（無內容者該在 awaiting）。
 3. awaiting：reason∈{兩者皆無,待人工補全文}；待人工補全文須 channels_exhausted=true。
 4. legs：交由 leg_exhaust_check 斷言可窮盡腿 fetched≥hitCount（取盡）。
 5. candidate 與 awaiting 的 paper_id 不重疊（分割互斥）。

用法：python stage1_check.py --in _stage1_corpus.json
程式內：import stage1_check; fails = stage1_check.check(data)
"""
import sys, json, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

FT = {"have", "ai_summary_only", "none"}
AB = {"have", "none"}
REASON = {"兩者皆無", "待人工補全文"}

def check(data):
    fails = []
    if not isinstance(data, dict):
        return ["頂層須為物件"]
    if data.get("schema_version") != "stage1-1.0":
        fails.append("schema_version 須為 stage1-1.0（實得 %r）" % data.get("schema_version"))
    for k in ("legs", "candidates", "awaiting"):
        if not isinstance(data.get(k), list):
            fails.append("缺陣列欄位 %s" % k)
    cands = data.get("candidates", []) or []
    awas = data.get("awaiting", []) or []
    if not cands:
        fails.append("candidates 空：Stage A 未交出任何可篩候選")
    for i, c in enumerate(cands):
        tag = "candidate[%d](%s)" % (i, c.get("paper_id"))
        if not str(c.get("title") or "").strip():
            fails.append("%s title 空" % tag)
        fs, as_ = c.get("fulltext_status"), c.get("abstract_status")
        if fs not in FT:
            fails.append("%s fulltext_status 非法/未 resolved：%r（不得留空/?）" % (tag, fs))
        if as_ not in AB:
            fails.append("%s abstract_status 非法/未 resolved：%r" % (tag, as_))
        if as_ == "have" and not str(c.get("abstract") or "").strip():
            fails.append("%s abstract_status=have 但 abstract 內容空（Bug2：②b 須對標題+摘要篩，"
                         "標記有摘要卻無實體內容＝只能憑標題；應實際回填摘要或改判 none→awaiting）" % tag)
        if fs == "none" and as_ == "none":
            fails.append("%s 無全文又無摘要卻列 candidate：應移 awaiting（待評估屬 Stage A，不進 Stage B 篩選）" % tag)
        if c.get("verdict") != "candidate":
            fails.append("%s verdict 須為 candidate（Stage A 不定納入）" % tag)
    for i, a in enumerate(awas):
        if a.get("reason") not in REASON:
            fails.append("awaiting[%d](%s) reason 非法：%r" % (i, a.get("paper_id"), a.get("reason")))
        if a.get("reason") == "待人工補全文" and not a.get("channels_exhausted"):
            fails.append("awaiting[%d](%s) 待人工補全文須 channels_exhausted=true（單次失敗≠窮盡）" % (i, a.get("paper_id")))
    # 分割互斥
    cs = {c.get("paper_id") for c in cands}; as2 = {a.get("paper_id") for a in awas}
    ov = cs & as2
    if ov:
        fails.append("candidate 與 awaiting paper_id 重疊 %d 筆：分割不互斥" % len(ov))
    # 取盡
    try:
        import leg_exhaust_check
        fails += leg_exhaust_check.check(data.get("legs", []))
    except Exception as e:
        fails.append("leg_exhaust_check 載入失敗：%s" % str(e)[:60])
    return fails

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="infile", required=True)
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print("⏭  找不到 %s" % a.infile); sys.exit(0)
    fails = check(json.loads(p.read_text(encoding="utf-8")))
    if fails:
        print("❌ Stage A→B 邊界守門未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ Stage A→B 邊界通過（全文狀態 resolved・待評估不混入候選・每腿取盡・分割互斥）。")

if __name__ == "__main__":
    main()
