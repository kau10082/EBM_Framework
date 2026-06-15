# -*- coding: utf-8 -*-
"""
funnel_check.py — 檢索流程圖『數字逐關閉合』硬 gate（反飄移）
==============================================================
讀 _search_report.json，把 funnel 各步 change/closure 文字裡的算式標記
  【357 − 172 = 185】【129+45+11=185】【30+5+80=115】
逐條解析→實算→比對，任一不成立即 FAIL。並硬性要求 funnel 至少含 N 條算式
（杜絕「沒寫算式＝沒被核」）。把使用者『流程圖數字務必逐關核閉合』變機器看守。

用法：python funnel_check.py [--in _search_report.json]
程式內：import funnel_check; fails = funnel_check.check(data)
"""
import sys, re, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# 全形/數學符號 → ASCII 運算子
_OPS = {"−": "-", "－": "-", "＋": "+", "＝": "=", "×": "*", "·": "*", "，": "", ",": ""}
_EXPR = re.compile(r"【([^】]*?=[^】]*?)】")

def _normalize(expr):
    for k, v in _OPS.items():
        expr = expr.replace(k, v)
    return expr

def _safe_eval(side):
    """只允許數字與 + - * 的算式；其他字元→None（不評估）。"""
    s = side.replace(" ", "")
    if not s or not re.fullmatch(r"[0-9+\-*]+", s):
        return None
    try:
        return eval(s, {"__builtins__": {}}, {})  # noqa: S307 受限字元集
    except Exception:
        return None

def check(data, min_exprs=3):
    """回傳 fails 清單（空＝通過）。"""
    fails = []
    funnel = data.get("funnel", []) or []
    blob = " ".join([(s.get("change") or "") + " " + (s.get("remain") or "") + " " + (s.get("annot") or "")
                     for s in funnel]) + " " + (data.get("funnel_closure") or "")
    blob = _normalize(blob)                      # 先把全形運算子(＝－＋)轉 ASCII，再抽【...】
    exprs = _EXPR.findall(blob)
    checked = 0
    for raw in exprs:
        e = _normalize(raw)
        if "=" not in e:
            continue
        lhs, rhs = e.split("=", 1)
        L, R = _safe_eval(lhs), _safe_eval(rhs)
        if L is None or R is None:
            continue
        checked += 1
        if L != R:
            fails.append(f"流程圖算式不成立：【{raw.strip()}】→ 左 {L} ≠ 右 {R}")
    if checked < min_exprs:
        fails.append(f"流程圖算式不足（只解析到 {checked} 條，需 ≥{min_exprs}）：每關轉換須附【a−b=c】算式供機器核閉合，禁裸數字")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default=None)
    a = ap.parse_args()
    src = a.infile
    if not src:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "EBM_Analysis" / "tools"))
            import run_state
            ftd = (run_state.load() or {}).get("paths", {}).get("fulltext_dir")
            cand = (Path(ftd) / "_search_report.json") if ftd else None
            src = str(cand) if cand and cand.exists() else None
        except Exception:
            src = None
    if not src or not Path(src).exists():
        print("⏭  找不到 _search_report.json（--in 指定）"); return
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    fails = check(data)
    if fails:
        print("❌ 流程圖數字閉合檢查未過：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 流程圖數字逐關閉合（所有【算式】成立）。")

if __name__ == "__main__":
    main()
