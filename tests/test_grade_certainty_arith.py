# -*- coding: utf-8 -*-
"""validate.check_p3_certainty 須忠實重現標準 GRADE 算術 net = start − down + up（末端統一夾）。
不得對 down/up 提前獨立封頂——否則極端組合會偏離標準、誤判作者正確的評級。"""
import validate as v


def _p3(start, downs, ups, final):
    return {"outcomes": [{
        "outcome_name": "t", "certainty_start": start,
        "downgrade_domains": {f"d{i}": {"verdict": x} for i, x in enumerate(downs)},
        "upgrade_domains": {f"u{i}": {"verdict": x} for i, x in enumerate(ups)},
        "certainty_final": final}]}


def test_no_premature_down_cap():
    # start=high(3), down=5(很嚴重2+很嚴重2+嚴重1), up=2(up_two) → 標準 net=0=very_low
    downs = ["very_serious", "very_serious", "serious"]
    assert not v.check_p3_certainty(_p3("high", downs, ["up_two"], "very_low"))  # 正確填不報錯
    assert v.check_p3_certainty(_p3("high", downs, ["up_two"], "moderate"))      # 舊 down 封頂會算 moderate→現視為不一致


def test_no_premature_up_cap():
    # start=low(1), down=3, up=4(up_two+up_two) → 標準 net=2=moderate
    assert not v.check_p3_certainty(_p3("low", ["very_serious", "serious"], ["up_two", "up_two"], "moderate"))
    assert v.check_p3_certainty(_p3("low", ["very_serious", "serious"], ["up_two", "up_two"], "low"))


def test_normal_case_still_ok():
    # start=high, down=1(serious), up=0 → moderate
    assert not v.check_p3_certainty(_p3("high", ["serious"], [], "moderate"))
