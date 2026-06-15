# -*- coding: utf-8 -*-
"""quote_verify 數字守門：difflib 模糊比對對『長句改一個數字』仍 >0.85，故須額外要求
quote 內每個數字串都在原文出現——否則捏造數字會矇混過關（反幻覺皇冠的真守門）。"""
import quote_verify as qv

SRC = ("the hazard ratio for exacerbation in the comparison of brensocatib with placebo was "
       "0.58 (95% confidence interval 0.35 to 0.95) in the 10-mg group; "
       "incidence rate ratio was 0·52 (95% CI 0·34-0·80)")
SN = qv._norm(SRC)
SD = qv._digits(SRC)
REAL = "hazard ratio for exacerbation in the comparison of brensocatib with placebo was 0.58 (95% confidence interval 0.35 to 0.95)"


def test_verbatim_matches():
    assert qv.match(REAL, SN, 0.85, SD)[0] is True


def test_fabricated_effect_number_caught():
    # 只改主效應 0.58→0.99，其餘逐字 → 沒有數字守門時 ratio≈0.91 會假陽性
    assert qv.match(REAL.replace("0.58", "0.99"), SN, 0.85, SD)[0] is False


def test_fabricated_ci_number_caught():
    assert qv.match(REAL.replace("0.35", "0.15"), SN, 0.85, SD)[0] is False


def test_middledot_decimal_ok():
    # Lancet 風格中點小數 0·52 應視為真（分隔符不敏感）
    assert qv.match("incidence rate ratio was 0·52 (95% CI 0·34-0·80)", SN, 0.85, SD)[0] is True


def test_fabricated_middledot_caught():
    assert qv.match("incidence rate ratio was 0·59 (95% CI 0·34-0·80)", SN, 0.85, SD)[0] is False


def test_digits_separator_agnostic():
    assert qv._digits("0.58") == {"0", "58"}
    assert qv._digits("2,525") == {"2", "525"}
    assert qv._digits("0·52") == {"0", "52"}
