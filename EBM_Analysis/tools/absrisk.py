# -*- coding: utf-8 -*-
"""無 API：由相對效應＋對照組基線，算「對應風險／絕對風險差／NNT」或「率差」。
供 SoF 表的絕對效應欄使用，避免手算錯（sof_table 護欄）。

  python tools/absrisk.py rr 0.79 1.286 --rate     # 率：每人年
  python tools/absrisk.py rr 1.20 0.403            # 二分類比例（0–1 或 %）
  python tools/absrisk.py or 0.62 0.48
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _norm(x):
    """接受 0–1 或百分比（>1 視為 %）。"""
    x = float(x)
    return x / 100.0 if x > 1 else x


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    kind, eff = argv[0].lower(), float(argv[1])
    rate = "--rate" in argv

    if rate:
        acr = float(argv[2])  # 率，不正規化
        corr = eff * acr
        rd = corr - acr
        print(f"相對效應 {kind.upper()}={eff}，對照率={acr}/單位時間")
        print(f"  對應介入率 = {corr:.3f}")
        print(f"  率差 = {rd:+.3f}/單位時間（{'每單位時間少 '+format(-rd,'.3f')+' 次' if rd<0 else '增加'}）")
        print("  ⚠️ 率（count）結果不套二分類 NNT。")
        return 0

    acr = _norm(argv[2])
    if kind == "rr":
        corr = eff * acr
    elif kind == "or":
        corr = (eff * acr) / (1 - acr + eff * acr)
    else:
        print("kind 須為 rr 或 or"); return 2
    rd = corr - acr
    print(f"相對效應 {kind.upper()}={eff}，對照風險 ACR={acr*100:.1f}%")
    print(f"  對應介入風險 = {corr*100:.1f}%")
    print(f"  絕對風險差 RD = {rd*100:+.1f} 個百分點")
    if abs(rd) > 1e-9:
        nnt = 1 / abs(rd)
        print(f"  NNT = {nnt:.0f}（每治療此人數多 1 人改變結果狀態）")
        print("  ⚠️ NNTB/NNTH 方向須由人判定：若該結果為『益』（如無惡化），RD>0＝NNTB；"
              "若為『害』（如不良事件），RD>0＝NNTH。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
