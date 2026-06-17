# -*- coding: utf-8 -*-
"""gate_guard 守門例外→fail-closed 回歸測試。

背景：run_hook 組 checks 時直呼各 check；若某 check 自身拋例外且無兜底，
整個 hook 會以未捕捉例外退出 exit 1，而 Stop hook 只有 exit 2 才會 block，
exit 1 被當成『hook 出錯但放行』→ 守門靜默失效（fail-open）。
_safe 應把例外轉成一條 fail（fail-closed），守門不被繞過。"""
import gate_guard as gg


def _boom(_cache):
    raise ValueError("壞 cache")


def _clean(_cache):
    return []  # 通過


def _fails(_cache):
    return ["有問題"]


def test_safe_converts_exception_to_failclosed():
    name, res = gg._safe("撤稿守門", _boom, None)
    assert name == "撤稿守門"
    assert res and any("fail-closed" in f for f in res)  # 例外→回報為未通過，而非崩潰放行


def test_safe_passes_through_clean_and_fails():
    assert gg._safe("a", _clean, None) == ("a", [])
    assert gg._safe("b", _fails, None) == ("b", ["有問題"])


def test_check_no_retracted_handles_list_seed(tmp_path):
    # seed.json 為 bare list（非 {papers:[...]}）時不可崩潰（曾缺 isinstance guard）
    import json
    (tmp_path / "g6_verified.json").write_text(
        json.dumps([{"pmid": "111", "verdict": "RETRACTED"}]), encoding="utf-8")
    (tmp_path / "seed.json").write_text(
        json.dumps([{"pmid": "111"}, {"pmid": "222"}]), encoding="utf-8")  # bare list
    res = gg.check_no_retracted(tmp_path)
    assert any("111" in f for f in res)  # 撤稿 111 在 list 形 seed 仍被抓到，且不拋例外
