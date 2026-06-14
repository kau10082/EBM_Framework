# -*- coding: utf-8 -*-
"""無 API：由相對效應＋對照組基線，算「對應風險／絕對風險差／NNTB|NNTH（含 95% CI）」或「率差」。
供 SoF 表的絕對效應欄使用，避免手算錯（sof_table 護欄；Cochrane Ch15 §15.4）。

NNT 信賴區間：**不**由跨試驗彙整總數直接算，而是把 RR/OR 的 95% CI 上下限代入
『假設對照組風險 ACR』回推 NNTB/NNTH 區間（Ch15 §15.4）。
用詞：益處用 **NNTB**、危害用 **NNTH**（避免用 NNH，Cochrane 強烈建議；指明方向）。

  python tools/absrisk.py rr 0.64 0.404 --ci 0.52 0.78 --dir benefit   # 益處＋NNTB CI
  python tools/absrisk.py rd 0.007 0.030 --dir harm                    # 兩風險直接算 NNTH
  python tools/absrisk.py rr 0.79 1.286 --rate                         # 率：每人年（不套 NNT）
  python tools/absrisk.py or 0.62 0.48
"""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _norm(x):
    x = float(x); return x / 100.0 if x > 1 else x

def _corr(kind, eff, acr):
    if kind == "rr": return eff * acr
    if kind == "or": return (eff * acr) / (1 - acr + eff * acr)
    raise ValueError("kind 須為 rr/or")

def _nnt_term(direction):
    return {"benefit": "NNTB", "harm": "NNTH"}.get(direction, "NNT")

def _opt(argv, flag, n=1):
    if flag in argv:
        i = argv.index(flag); return argv[i + 1:i + 1 + n]
    return None

def selftest():
    """黃金值自我測試：公式正確性覆驗。"""
    cases = []
    # RR 0.64, ACR 0.404 → RD -0.1454, NNTB ~7；CI 0.52/0.78 → 5/11
    corr = _corr("rr", 0.64, 0.404); cases.append((round(corr, 3), 0.259))
    cases.append((round(1 / abs(corr - 0.404)), 7))
    cases.append((round(1 / abs(_corr("rr", 0.52, 0.404) - 0.404)), 5))
    cases.append((round(1 / abs(_corr("rr", 0.78, 0.404) - 0.404)), 11))
    # OR 0.62, ACR 0.48 → corr
    cases.append((round(_corr("or", 0.62, 0.48), 3), 0.364))
    bad = [(g, e) for g, e in cases if abs(g - e) > 0.51]
    if bad:
        print("❌ absrisk 自我測試失敗：", bad); return 1
    print("✅ absrisk 自我測試通過（NNTB/CI/OR 公式黃金值相符）"); return 0

def main(argv):
    if argv and argv[0] == "--selftest":
        return selftest()
    if argv and argv[0].lower() == "smd2or" and len(argv) >= 2:
        import math
        smd = float(argv[1]); orr = math.exp(1.81 * smd)
        print(f"SMD={smd} → OR≈{orr:.2f}（lnOR≈1.81×SMD，Ch15 §15.5.3.3）")
        ci = _opt(argv, "--ci", 2)
        if ci:
            lo, hi = sorted(math.exp(1.81 * float(b)) for b in ci)
            print(f"  OR 95% CI ≈ {lo:.2f}–{hi:.2f}")
        return 0
    if len(argv) < 3:
        print(__doc__); return 2
    kind = argv[0].lower()
    direction = (_opt(argv, "--dir") or [None])[0]
    term = _nnt_term(direction)

    # 防呆(v0.20.1)：rr/hr/or 位置順序「效應量在前、對照風險在後」易寫反——
    # 支援具名旗標覆寫(--rr/--hr/--or/--control)，順序就不會錯；計算前一律印醒目「解讀」行。
    def _pos(i):  # 位置參數：是數字才取，旗標(--x)回 None
        return argv[i] if (i < len(argv) and not str(argv[i]).startswith("--")) else None
    def _resolve():
        pe, pc = _pos(1), _pos(2)
        eff = float(pe) if pe is not None else None
        ctrl = _norm(pc) if pc is not None else None
        for fl in ("--rr", "--hr", "--or"):
            v = _opt(argv, fl)
            if v: eff = float(v[0])
        v = _opt(argv, "--control") or _opt(argv, "--acr") or _opt(argv, "--pc")
        if v: ctrl = _norm(v[0])
        if eff is None or ctrl is None:
            raise SystemExit(f"absrisk {kind}：需效應量與對照風險。位置式『absrisk {kind} <效應量> <對照風險>』"
                             f"（效應量在前），或具名式『absrisk {kind} --{kind} X --control Y』(順序不會錯)。")
        return eff, ctrl
    def _echo(eff, ctrl):
        print(f"▶ 解讀：效應量 {kind.upper()}={eff}、對照風險={ctrl*100:.1f}%"
              f"（若反了請改用：absrisk {kind} --{kind if kind in('rr','hr','or') else 'rr'} {eff} --control {ctrl}）")

    # SMD → OR（連續結果可解讀化，Ch15 §15.5.3.3：lnOR ≈ 1.81×SMD）
    if kind == "smd2or":
        import math
        smd = float(argv[1]); orr = math.exp(1.81 * smd)
        print(f"SMD={smd} → OR≈{orr:.2f}（lnOR≈1.81×SMD，Ch15 §15.5.3.3）")
        ci = _opt(argv, "--ci", 2)
        if ci:
            lo, hi = sorted(math.exp(1.81 * float(b)) for b in ci)
            print(f"  OR 95% CI ≈ {lo:.2f}–{hi:.2f}")
        return 0

    # 時間事件 HR → 絕對風險（Ch14 §14.1.5.2）：給對照組於某時點之事件風險 p_c → 介入 p_i=1-(1-p_c)^HR
    if kind == "hr":
        hr, pc = _resolve(); _echo(hr, pc)
        pi = 1 - (1 - pc) ** hr; rd = pi - pc
        print(f"HR={hr}，對照組事件風險 {pc*100:.1f}%（某時點）→ 介入組 {pi*100:.1f}%（假設比例風險）")
        print(f"  絕對風險差 RD = {rd*100:+.1f} 個百分點" + (f"；{term} = {1/abs(rd):.0f}" if abs(rd) > 1e-9 else ""))
        ci = _opt(argv, "--ci", 2)
        if ci:
            ns = []
            for b in ci:
                p = 1 - (1 - pc) ** float(b); d = p - pc
                if abs(d) > 1e-12: ns.append(1 / abs(d))
            if len(ns) == 2:
                a, z = sorted(ns); print(f"  {term} 95% CI = {a:.0f} 到 {z:.0f}（由 HR CI 代入）")
        return 0

    # 由事件數算風險差＋NNT 及其 95% CI：rdci  Cevents Cn  Ievents In
    if kind == "rdci":
        import math
        ce, cn, ie, ina = float(argv[1]), float(argv[2]), float(argv[3]), float(argv[4])
        pc, pi = ce / cn, ie / ina
        rd = pi - pc
        se = math.sqrt(pc * (1 - pc) / cn + pi * (1 - pi) / ina)
        lo, hi = rd - 1.96 * se, rd + 1.96 * se
        print(f"對照 {ce:.0f}/{cn:.0f}={pc*100:.2f}% ｜ 介入 {ie:.0f}/{ina:.0f}={pi*100:.2f}%")
        print(f"  風險差 RD = {rd*100:+.2f}pp（95% CI {lo*100:+.2f} 到 {hi*100:+.2f}pp）")
        crosses = lo <= 0 <= hi
        if abs(rd) > 1e-12:
            nnt = 1 / abs(rd)
            if crosses:
                print(f"  {term} = {nnt:.0f}，但 95% CI **跨越無差異（0）→ 含無限大／可能反向**（事件少、不精確）")
            else:
                a, b = sorted([1 / abs(lo), 1 / abs(hi)])
                print(f"  {term} = {nnt:.0f}（95% CI {a:.0f} 到 {b:.0f}）")
        return 0

    # 直接兩風險：rd CONTROL INTERVENTION
    if kind == "rd":
        acr, ir = _norm(argv[1]), _norm(argv[2])
        rd = ir - acr
        print(f"對照風險 {acr*100:.2f}% ｜ 介入風險 {ir*100:.2f}%")
        print(f"  絕對差 = {rd*100:+.2f} 個百分點")
        if abs(rd) > 1e-12:
            print(f"  {term} = {1/abs(rd):.0f}")
        return 0

    if "--rate" in argv:
        eff = float(argv[1]); acr = float(argv[2]); corr = eff * acr; rd = corr - acr
        print(f"率比 {eff}，對照率={acr}/單位時間 → 介入率 {corr:.3f}，率差 {rd:+.3f}/單位時間")
        print("  ⚠️ 率（count）結果不套 NNT。")
        return 0

    eff, acr = _resolve(); _echo(eff, acr)
    corr = _corr(kind, eff, acr); rd = corr - acr
    print(f"相對效應 {kind.upper()}={eff}，對照風險 ACR={acr*100:.1f}% → 對應介入風險 {corr*100:.1f}%")
    print(f"  絕對風險差 RD = {rd*100:+.1f} 個百分點")
    if abs(rd) > 1e-12:
        print(f"  {term} = {1/abs(rd):.0f}" + ("（益處：每治療此人數多 1 人獲益）" if direction=="benefit"
              else "（危害：每治療此人數多 1 人受害）" if direction=="harm" else "（方向待判）"))
    # CI：RR/OR 的 95% CI 代入 ACR
    ci = _opt(argv, "--ci", 2)
    if ci:
        lo, hi = float(ci[0]), float(ci[1])
        nnts = []
        for b in (lo, hi):
            c = _corr(kind, b, acr); d = c - acr
            if abs(d) > 1e-12: nnts.append(1/abs(d))
        if len(nnts) == 2:
            a, z = sorted(nnts)
            print(f"  {term} 95% CI = {a:.0f} 到 {z:.0f}　（由 {kind.upper()} CI {lo}–{hi} 代入 ACR 回推）")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
