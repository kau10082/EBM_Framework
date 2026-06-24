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


def _doms(j):
    return {k: {"judgement": j} for k in
            ("confounding", "selection", "classification", "deviations", "missing_data", "measurement", "selection_reported")}


def _ri(**kw):
    """組合有效的 robins_i（含前置作業），可用 kw 覆寫。"""
    base = {"effect_of_interest": "assignment", "confounders_considered": ["baseline eos", "prior biologic"],
            "overall": "serious", "domains": _doms("serious")}
    base.update(kw)
    return base


def main():
    allok = True
    base = {"paper_id": "x", "integrity_check": {"retraction": False, "erratum_or_eoc": False, "action": "none"}}

    def c(robins, track="C", tool="robins_i", gs="low"):
        return {**base, "track": track, "grade_start": gs, "rob_tool": tool, "robins_i": robins}

    # 拿錯工具：NRSI(track C) 標 rob2 → FAIL
    allok &= _fires("Phase2 NRSI(track C) 用 RoB2（須 ROBINS-I）", V.check_p2_rob_routing(c(_ri(), tool="rob2")))
    # 拿錯工具：RCT(track B) 標 robins_i → FAIL
    allok &= _fires("Phase2 RCT(track B) 用 ROBINS-I（須 RoB2）",
                    V.check_p2_rob_routing({**base, "track": "B", "grade_start": "high", "rob_tool": "robins_i"}))
    # NRSI 缺七領域 → FAIL
    allok &= _fires("Phase2 NRSI 缺 robins_i 七領域", V.check_p2_rob_routing(c(_ri(domains={}))))
    # overall=low 無理由 → FAIL
    allok &= _fires("Phase2 ROBINS-I overall=low 無 low_justification",
                    V.check_p2_rob_routing(c(_ri(overall="low", domains=_doms("low")))))
    # 過半 no_information → FAIL
    allok &= _fires("Phase2 ROBINS-I 過半領域 no_information（充數規避）",
                    V.check_p2_rob_routing(c(_ri(domains=_doms("no_information")))))
    # 木桶原則：有 critical 領域卻 overall=serious → FAIL
    crit_one = _doms("moderate"); crit_one["confounding"] = {"judgement": "critical"}
    allok &= _fires("Phase2 木桶原則：critical 領域卻 overall=serious",
                    V.check_p2_rob_routing(c(_ri(overall="serious", domains=crit_one, meta_analysis_action="include"))))
    # critical 未排除於統合 → FAIL
    allok &= _fires("Phase2 critical 未設 meta_analysis_action=exclude",
                    V.check_p2_rob_routing(c(_ri(overall="critical", domains=crit_one, meta_analysis_action="include"))))
    # 前置作業缺 effect_of_interest → FAIL
    ri_no_eoi = _ri(); ri_no_eoi.pop("effect_of_interest")
    allok &= _fires("Phase2 ROBINS-I 缺前置作業 effect_of_interest", V.check_p2_rob_routing(c(ri_no_eoi)))
    # 前置作業缺 confounders_considered → FAIL
    allok &= _fires("Phase2 ROBINS-I 缺前置作業 confounders_considered",
                    V.check_p2_rob_routing(c(_ri(confounders_considered=[]))))

    # 正向防誤報
    allok &= _passes("Phase2 NRSI 正確用 ROBINS-I(serious) 應通過", V.check_p2_rob_routing(c(_ri())))
    allok &= _passes("Phase2 RCT 用 RoB2 應通過",
                     V.check_p2_rob_routing({**base, "track": "B", "grade_start": "high", "rob_tool": "rob2"}))
    allok &= _passes("Phase2 SR/MA 用 AMSTAR2 應通過",
                     V.check_p2_rob_routing({**base, "track": "A", "grade_start": "high", "rob_tool": "amstar2"}))
    allok &= _passes("Phase2 ROBINS-I low 附理由 應通過",
                     V.check_p2_rob_routing(c(_ri(overall="low", domains=_doms("low"),
                                                  low_justification="完整調整所有已知干擾＋E-value 敏感度分析"))))
    allok &= _passes("Phase2 ROBINS-I critical 且 exclude 應通過",
                     V.check_p2_rob_routing(c(_ri(overall="critical", domains=crit_one, meta_analysis_action="exclude"))))

    print("\n" + ("✅ 全部分析端守門有效。" if allok else "❌ 有守門未如預期，請檢查。"))
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
