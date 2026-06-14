# -*- coding: utf-8 -*-
"""render_smoketest 純邏輯測試：磚塊/章節跳號/空表/SoF 死亡+SAE/列數一致。"""
import render_smoketest as rs


def _good_data():
    return {
        "sof": [
            {"outcome": "延後惡化(首次惡化時間)"},
            {"outcome": "年化肺惡化率"},
            {"outcome": "全因死亡"},
            {"outcome": "嚴重不良事件 SAE"},
        ],
        "body_of_evidence": [{"outcome": "x", "certainty": "moderate", "basis": "y"}],
        "baseline_risk_strata": [{"baseline_risk": "低", "corresponding": "a", "absolute_reduction": "b"}],
    }


# 章節號的偵測要求行首（對齊真實 PDF 版面）→ 用換行分隔
GOOD_TXT = ("1. 一節\n2. 二節\n3. 三節\n4. 四節\n5. 五節\n"
            "延後惡化(首次惡化時間) 年化肺惡化率 全因死亡 嚴重不良事件 SAE")


def test_clean_report_passes():
    assert rs.checks_on(GOOD_TXT, _good_data()) == []


def test_v1_tofu_detected():
    fails = rs.checks_on(GOOD_TXT + " ✅∧≠", _good_data())
    assert any("V1" in f for f in fails)


def test_v2_section_gap_detected():
    # 章節 4 直接跳到 6（缺 5）；行首編號才會被偵測
    txt = ("1. a\n2. b\n3. c\n4. d\n6. f\n"
           "延後惡化(首次惡化時間) 年化肺惡化率 全因死亡 嚴重不良事件 SAE")
    fails = rs.checks_on(txt, _good_data())
    assert any("V2" in f and "5" in f for f in fails)


def test_v3_empty_table_detected():
    d = _good_data(); d["baseline_risk_strata"] = []   # 空選填陣列→破表
    fails = rs.checks_on(GOOD_TXT, d)
    assert any("V3" in f and "baseline_risk_strata" in f for f in fails)


def test_v4_missing_mortality_or_sae():
    d = _good_data(); d["sof"] = [{"outcome": "年化肺惡化率"}]   # 缺死亡+SAE
    fails = rs.checks_on("1. a 年化肺惡化率", d)
    assert any("死亡" in f for f in fails) and any("SAE" in f for f in fails)


def test_v5_sof_row_swallowed():
    # 資料有「全因死亡」但 PDF 文字裡找不到→疑遭吞
    d = _good_data()
    txt = "1.x 延後惡化(首次惡化時間) 年化肺惡化率 嚴重不良事件 SAE"  # 故意漏「全因死亡」
    fails = rs.checks_on(txt, d)
    assert any("V5" in f for f in fails)
