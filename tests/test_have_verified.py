# -*- coding: utf-8 -*-
"""『判 have 必須實抓驗證』守門 + verify_have_fetchable 真全文判定（防 OA 旗標高估）。"""
import gate_guard, verify_have_fetchable as v


def _seed(tmp_path, papers):
    import json
    p = tmp_path / "seed.json"
    p.write_text(json.dumps({"papers": papers}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_have_without_verified_fails(tmp_path):
    cache = _seed(tmp_path, [{"paper_id": "X", "verdict": "included", "fulltext_status": "have",
                              "fulltext_channel": "online", "suggested": {"grade_track": "full"}}])
    fails = gate_guard.check_have_verified(cache)
    assert fails and "未經" in fails[0]


def test_have_with_verified_passes(tmp_path):
    cache = _seed(tmp_path, [{"paper_id": "X", "verdict": "included", "fulltext_status": "have",
                              "fulltext_channel": "online", "fulltext_verified": True,
                              "suggested": {"grade_track": "full"}}])
    assert gate_guard.check_have_verified(cache) == []


def test_local_pdf_trusted(tmp_path):
    cache = _seed(tmp_path, [{"paper_id": "X", "verdict": "included", "fulltext_status": "have_manual",
                              "pdf_file": "X.pdf", "suggested": {"grade_track": "full"}}])
    assert gate_guard.check_have_verified(cache) == []


def test_is_real_fulltext_rejects_short_landing():
    assert v._is_real_fulltext("short metadata page") is False
    long_meta = "abstract " * 3000  # 長但無章節/統計特徵
    assert v._is_real_fulltext(long_meta) is False


def test_is_real_fulltext_accepts_real():
    txt = ("Introduction background ... Methods randomized ... Results 95% CI p<0.001 ... "
           "Discussion conclusion ...") + ("filler " * 3000)
    assert v._is_real_fulltext(txt) is True
