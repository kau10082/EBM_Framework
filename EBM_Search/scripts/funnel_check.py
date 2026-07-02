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
    s = re.sub(r"(^|[+\-*])0+(\d)", r"\1\2", s)   # 去多位數前導零（007→7）；否則 eval 拋 SyntaxError 被當解析失敗靜默跳過
    try:
        return eval(s, {"__builtins__": {}}, {})  # noqa: S307 受限字元集
    except Exception:
        return None

_SIGNED = re.compile(r"([+\-])?\s*(\d+)")
_PAREN = re.compile(r"[（(][^（()）]*[)）]")   # 括號註記（細項/說明常在括號內）

def _signed_in(txt):
    """已正規化文字內的帶號數字：[(sign, int), ...]；sign ∈ {'+','-',''}。"""
    return [(m.group(1) or "", int(m.group(2))) for m in _SIGNED.finditer(txt)]

def _nums(cell):
    """抽出格內帶號數字（原樣解讀）。輸入先過 _normalize（全形→ASCII、去千分位）。"""
    return _signed_in(_normalize(str(cell or "")))

def _single(cell):
    """start/remain 抽『單一計數』：優先剝除括號註記後恰 1 數者（如『核心 26（＋base 8）』→26），
    否則回原樣抽出的全部數字（呼叫端以 len==1 決定是否可檢）。"""
    raw = _normalize(str(cell or ""))
    stripped = [n for _, n in _signed_in(_PAREN.sub(" ", raw))]
    if len(stripped) == 1:
        return stripped
    return [n for _, n in _signed_in(raw)]

def _delta_candidates(cell):
    """excluded 格的變化量『候選解讀』（去重 list）：(1) 全部帶號數字直加減；(2) 先剝除括號註記再加減。
    逐列檢查時**任一解讀能閉合即通過**——括號細項備註（如『剔除 15（重複 10、離題 5）』）總數與細項
    同格並存，單一解讀會把 15+10+5 全加而假 FAIL（Antigravity 初審 🔴）；而『—（新增 +5）』的加項
    又只存在於括號內，故兩種解讀都要保留。"""
    raw = _normalize(str(cell or ""))
    cands = []
    for txt in (raw, _PAREN.sub(" ", raw)):
        d = sum(n if sg == "+" else -n for sg, n in _signed_in(txt))
        if d not in cands:
            cands.append(d)
    return cands

def check_flow(data):
    """現行 5 段版型（flow: [{stage,start,excluded,remain}] ＋ flow_reconcile 字串）的數字閉合檢查：
    (a) 逐列：start（恰 1 數）±excluded 帶號數（無號/−＝扣除、+＝新增；括號細項容錯，任一解讀閉合即過）
        ＝ remain（恰 1 數）；任一格數字數量不合（0 或 >1）→ 該列略過（首列 Identification 的「—」即此類）。
    (b) 跨列：remain[i] 與 start[i+1] 都恰 1 數時必須相等（上一關剩餘＝下一關起始）。
    (c) flow_reconcile 內「a + b + c = d」型算式實算比對。"""
    fails = []
    flow = data.get("flow") or []
    parsed = []
    for i, st in enumerate(flow):
        if not isinstance(st, dict):
            parsed.append((None, None)); continue
        s = _single(st.get("start"))
        r = _single(st.get("remain"))
        parsed.append((s, r))
        if len(s) == 1 and len(r) == 1:
            deltas = _delta_candidates(st.get("excluded"))
            if all(s[0] + d != r[0] for d in deltas):
                d0 = deltas[-1]   # 顯示剝括號後的解讀（通常最接近本意）
                fails.append(f"flow[{i}]（{str(st.get('stage',''))[:20]}）數字不閉合："
                             f"起始 {s[0]} {'+' if d0 >= 0 else '−'} {abs(d0)} ≠ 剩餘 {r[0]}"
                             f"（start={st.get('start')!r} excluded={st.get('excluded')!r} remain={st.get('remain')!r}）")
    for i in range(len(parsed) - 1):
        r_prev = parsed[i][1]; s_next = parsed[i + 1][0]
        if r_prev and s_next and len(r_prev) == 1 and len(s_next) == 1 and r_prev[0] != s_next[0]:
            fails.append(f"flow[{i}]→flow[{i+1}] 不銜接：上一關剩餘 {r_prev[0]} ≠ 下一關起始 {s_next[0]}")
    rec = _normalize(str(data.get("flow_reconcile") or ""))
    # 對帳句形如「核心 26 + 背景 35 + 待評估 21 = 82」：數字間可夾中文標籤，故容許 + 前後的非數字文字
    for m in re.finditer(r"(\d+(?:[^+=\d]*\+[^+=\d]*\d+)+)[^=\d]*=[^\d]*(\d+)", rec):
        total = sum(int(x) for x in re.findall(r"\d+", m.group(1)))
        if total != int(m.group(2)):
            fails.append(f"flow_reconcile 對帳不成立：{m.group(0)}（實算＝{total}）")
    return fails

def check(data, min_exprs=3):
    """回傳 fails 清單（空＝通過）。相容兩代格式：舊 funnel（【算式】標記）與現行 flow（start/excluded/remain）。"""
    fails = []
    funnel = data.get("funnel", []) or []
    if funnel or data.get("funnel_closure"):   # 舊版 funnel 格式：抽【...】算式逐條核
        blob = " ".join([(s.get("change") or "") + " " + (s.get("remain") or "") + " " + (s.get("annot") or "")
                         for s in funnel]) + " " + (data.get("funnel_closure") or "")
        blob = _normalize(blob)                  # 先把全形運算子(＝－＋)轉 ASCII，再抽【...】
        exprs = _EXPR.findall(blob)
        checked = 0
        for raw in exprs:
            e = _normalize(raw)
            if "=" not in e:
                continue
            lhs, rhs = e.split("=", 1)
            L, R = _safe_eval(lhs), _safe_eval(rhs)
            if L is None or R is None:
                # 看起來像算式(含數字+運算子)卻解析失敗→格式錯誤/含不支援運算(/、括號、錯字)，不可靜默跳過
                if re.search(r"\d", e) and re.search(r"[+\-*/()]", e):
                    fails.append(f"流程圖算式無法解析：【{raw.strip()}】（僅支援 +−* 與數字；勿用 / 或括號或錯字，否則失去校驗）")
                continue
            checked += 1
            if L != R:
                fails.append(f"流程圖算式不成立：【{raw.strip()}】→ 左 {L} ≠ 右 {R}")
        if checked < min_exprs:
            fails.append(f"流程圖算式不足（只解析到 {checked} 條，需 ≥{min_exprs}）：每關轉換須附【a−b=c】算式供機器核閉合，禁裸數字")
    fails.extend(check_flow(data))
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
