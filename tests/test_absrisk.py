# -*- coding: utf-8 -*-
"""absrisk 單元測試——尤其守『rr/hr 參數順序(效應量在前)』，這是實測兩度傳反的 bug。"""
import subprocess
import sys
import re
from pathlib import Path

import absrisk  # 由 conftest 加入 sys.path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "EBM_Analysis" / "tools" / "absrisk.py"


def _run(*args):
    r = subprocess.run([sys.executable, str(TOOL), *args],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── 純函式：公式正確性 ──
def test_norm_fraction_vs_percent():
    assert abs(absrisk._norm("0.4") - 0.4) < 1e-9   # <=1 視為比例
    assert abs(absrisk._norm("40") - 0.4) < 1e-9    # >1 視為百分比 → /100


def test_corr_rr_and_or():
    # RR：corr = eff*acr
    assert abs(absrisk._corr("rr", 0.64, 0.40) - 0.256) < 1e-9
    # OR：odds 轉換
    oc = absrisk._corr("or", 0.5, 0.40)
    assert 0.0 < oc < 0.40  # OR<1 → 風險下降


# ── CLI 整合：rr/hr 算出正確 RD/NNT（守參數順序）──
def test_cli_rr_absolute_and_nnt():
    code, out = _run("rr", "0.64", "0.40", "--dir", "benefit")
    assert code == 0
    assert "解讀" in out and "RR=0.64" in out and "40.0%" in out  # 醒目解讀行
    assert "-14.4" in out                                          # RD = 25.6% - 40%
    assert re.search(r"NNTB\s*=\s*7", out)                         # 1/0.144 ≈ 7


def test_cli_hr_absolute_and_nnt():
    code, out = _run("hr", "0.66", "0.597")
    assert code == 0
    assert "HR=0.66" in out and "59.7%" in out
    assert "-14.6" in out and re.search(r"NNT\s*=\s*7", out)


def test_named_flags_equal_positional_and_orderproof():
    """具名旗標：順序顛倒也要得到同一結果——這就是防『傳反』的核心測試。"""
    _, pos = _run("rr", "0.64", "0.40", "--dir", "benefit")
    _, named = _run("rr", "--control", "0.40", "--rr", "0.64", "--dir", "benefit")  # 故意顛倒
    # 兩者的 RD 與 NNTB 必須一致
    for token in ("-14.4", "NNTB"):
        assert token in pos and token in named
    assert ("RR=0.64" in pos) and ("RR=0.64" in named)


def test_wrong_order_would_be_visible_in_echo():
    """若真的把對照(0.40)當效應量、效應(0.64)當對照傳→解讀行會印出 RR=0.4，一眼可辨。"""
    _, swapped = _run("rr", "0.40", "0.64", "--dir", "benefit")
    assert "RR=0.4" in swapped  # 解讀行忠實反映輸入，使用者能即時發現傳反


def test_selftest_passes():
    code, out = _run("--selftest")
    assert code == 0 and "✅" in out
