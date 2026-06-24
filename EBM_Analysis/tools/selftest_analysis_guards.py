# -*- coding: utf-8 -*-
"""selftest_analysis_guards.py — 證明 EBM_Analysis 端機器守門有效（安裝/clone 後先跑）。
目前涵蓋：Phase 2 偏誤風險『工具↔設計』三路徑路由（A→AMSTAR2 / B→RoB2 / C(NRSI)→ROBINS-I）。
仿 EBM_Search/scripts/selftest_guards.py 的『會 FAIL／防誤報』雙向斷言。"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import validate as V


def _fires(name, fails):
    ok = bool(fails)
    print(("  ✅" if ok else "  ❌") + f" {name}：" + ("會 FAIL（守門有效）" if ok else "未擋下（守門失效）"))
    return ok


def _passes(name, fails):
    ok = not fails
    print(("  ✅" if ok else "  ❌") + f" {name}：" + ("通過" if ok else f"誤報 {fails}"))
    return ok


def main():
    allok = True
    base = {"paper_id": "x", "integrity_check": {"retraction": False, "erratum_or_eoc": False, "action": "none"}}
    full_doms = {k: {"judgement": "serious"} for k in
                 ("confounding", "selection", "classification", "deviations", "missing_data", "measurement", "selection_reported")}

    # 拿錯工具：NRSI(track C) 標 rob2 → FAIL
    allok &= _fires("Phase2 NRSI(track C) 用 RoB2（須 ROBINS-I）",
                    V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "rob2",
                                            "robins_i": {"overall": "serious", "domains": full_doms}}))
    # 拿錯工具：RCT(track B) 標 robins_i → FAIL
    allok &= _fires("Phase2 RCT(track B) 用 ROBINS-I（須 RoB2）",
                    V.check_p2_rob_routing({**base, "track": "B", "grade_start": "high", "rob_tool": "robins_i"}))
    # NRSI 缺七領域 → FAIL
    allok &= _fires("Phase2 NRSI 缺 robins_i 七領域",
                    V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "robins_i", "robins_i": {"overall": "serious", "domains": {}}}))
    # ROBINS-I overall=low 無理由 → FAIL（NRSI 判低偏誤極罕見）
    low_doms = {k: {"judgement": "low"} for k in full_doms}
    allok &= _fires("Phase2 ROBINS-I overall=low 無 low_justification",
                    V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "robins_i",
                                            "robins_i": {"overall": "low", "domains": low_doms}}))
    # 過半領域 no_information → FAIL（防以無資訊充數）
    ni_doms = {k: {"judgement": "no_information"} for k in full_doms}
    allok &= _fires("Phase2 ROBINS-I 過半領域 no_information（充數規避）",
                    V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "robins_i",
                                            "robins_i": {"overall": "serious", "domains": ni_doms}}))

    # 正向防誤報：NRSI 正確用 ROBINS-I、serious → 通過
    allok &= _passes("Phase2 NRSI 正確用 ROBINS-I(serious) 應通過",
                     V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "robins_i",
                                             "robins_i": {"overall": "serious", "domains": full_doms}}))
    # 正向：RCT 用 RoB2 → 通過
    allok &= _passes("Phase2 RCT 用 RoB2 應通過",
                     V.check_p2_rob_routing({**base, "track": "B", "grade_start": "high", "rob_tool": "rob2"}))
    # 正向：SR/MA 用 AMSTAR2 → 通過
    allok &= _passes("Phase2 SR/MA 用 AMSTAR2 應通過",
                     V.check_p2_rob_routing({**base, "track": "A", "grade_start": "high", "rob_tool": "amstar2"}))
    # 正向：ROBINS-I overall=low 附理由 → 通過
    allok &= _passes("Phase2 ROBINS-I low 附 low_justification 應通過",
                     V.check_p2_rob_routing({**base, "track": "C", "grade_start": "low", "rob_tool": "robins_i",
                                             "robins_i": {"overall": "low", "low_justification": "雙胞胎設計、完整調整所有已知干擾且做 E-value 敏感度分析", "domains": low_doms}}))

    print("\n" + ("✅ 全部分析端守門有效。" if allok else "❌ 有守門未如預期，請檢查。"))
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
