# -*- coding: utf-8 -*-
"""
awaiting_stage_check.py — 鐵律『待評估只在 ②c(Stage A)產生，③ 必須二元(切題/離題)』硬 gate
================================================================================
使用者鐵律（2026-06 再三強調）：**「待評估」(awaiting classification) 只有 ②c 這一關會產生**。
②c＝判斷「有無可篩內容」：先看有無摘要→有摘要即有內容；沒摘要者再看有無全文；
**「無全文且無摘要」者才踢到待評估**（Stage A，擱置、不進 ③）。
進入 ③ 嚴格篩的都已有內容，故 **③(g3_FINAL_screen) 必須是『切題/離題』二元判定，不得再出現待評估**。

本守門讀 g3_FINAL_screen.json：任一筆 verdict/decision 帶待評估類字樣（待評估／待人工補全文／
兩者皆無／awaiting）＝FAIL（這種無內容者應在 ②c 就被路由到 g2c 待評估、根本不該進 ③）。

用法：python awaiting_stage_check.py --g3 g3_FINAL_screen.json
程式內：import awaiting_stage_check; fails = awaiting_stage_check.check(g3)
"""
import sys, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

AWAIT_TOKENS = ("待評估", "待人工補全文", "兩者皆無", "awaiting")

def _is_awaiting(v):
    s = str(v or "").strip().lower()
    if not s: return False
    return any(tok.lower() in s for tok in AWAIT_TOKENS)

def check(g3):
    """回傳 fails 清單（空＝通過）。g3: list[dict]（③ 嚴格篩輸出）。"""
    fails = []
    if not g3:
        return []  # ③ 尚未產出＝尚未到此關
    if not isinstance(g3, list):
        return ["g3_FINAL_screen.json 格式非清單：無法稽核 ③ 是否誤生待評估"]
    for e in g3:
        if not isinstance(e, dict):
            continue
        v = e.get("verdict") if e.get("verdict") is not None else e.get("decision")
        if _is_awaiting(v):
            uid = e.get("uid") or e.get("paper_id") or (str(e.get("title",""))[:40] or "?")
            fails.append(f"[{uid}] ③ 嚴格篩(g3)出現待評估類判定『{v}』："
                         f"待評估只能在 ②c(Stage A)產生；③ 必須切題/離題二元判定"
                         f"（無全文且無摘要者應在 ②c 就路由到待評估、不進 ③）")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g3", default="g3_FINAL_screen.json")
    a = ap.parse_args()
    p = Path(a.g3)
    if not p.exists():
        print(f"⏭  找不到 {a.g3}（③ 尚未產出）"); sys.exit(1)
    g3 = json.loads(p.read_text(encoding="utf-8"))
    fails = check(g3)
    if fails:
        print("❌ 待評估關責檢查未過："); [print("  -", f) for f in fails]; sys.exit(1)
    print("✅ 待評估關責：③(g3) 全為切題/離題二元判定，無誤生待評估（待評估只在 ②c）。")

if __name__ == "__main__":
    main()
