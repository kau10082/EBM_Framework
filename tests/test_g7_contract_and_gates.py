# -*- coding: utf-8 -*-
"""本輪全 repo 體檢修正的回歸測試（釘住行為，防再飄移）：
  1. classify_units.records_of — g7_units 兩代形狀（rows/unit vs records/role）統一讀取層。
  2. gate_guard ⑤b 守門對『產出端真實形狀』有效（曾因讀 records 鍵而對 rows 形狀靜默跳檢）。
  3. gate_guard 壞 JSON fail-closed（壞檔 ≠ 尚未產出，不得被當『尚未到此關』放行）。
  4. funnel_check.check_flow — 現行 5 段版型的流程數字閉合（逐列、跨列、對帳算式）。
"""
import json
import classify_units as cu
import gate_guard as gg
import funnel_check as fc


def test_records_of_rows_shape_derives_role():
    g7 = {"n": 3, "rows": [{"uid": "a", "unit": "核心:x"},
                           {"uid": "b", "unit": "", "design": "背景:y"},
                           {"uid": "c", "unit": "待評估:會議摘要", "design": "背景:z"}]}
    roles = {r["uid"]: r["role"] for r in cu.records_of(g7)}
    assert roles == {"a": "core", "b": "background", "c": "awaiting"}


def test_records_of_legacy_and_bare_shapes():
    assert cu.records_of({"records": [{"uid": "d", "role": "core"}]})[0]["role"] == "core"
    assert cu.records_of([{"uid": "e", "unit": "核心:q"}])[0]["role"] == "core"
    assert cu.records_of(None) == []


def test_gate_units_only_concordant_fires_on_rows_shape(tmp_path):
    (tmp_path / "g3_FINAL_screen.json").write_text(json.dumps(
        [{"uid": "u1", "verdict": "切題"}, {"uid": "u2", "verdict": "離題"}]), encoding="utf-8")
    (tmp_path / "g7_units.json").write_text(json.dumps(
        {"n": 2, "rows": [{"uid": "u1", "unit": "核心:x"}, {"uid": "u2", "unit": "", "design": "背景:誤灌"}]}),
        encoding="utf-8")
    fails = gg.check_units_only_concordant(tmp_path)
    assert fails and any("u2" in f or "離題" in f for f in fails)


def test_gate_units_unrecognized_shape_fails_closed(tmp_path):
    (tmp_path / "g7_units.json").write_text(json.dumps({"foo": [1, 2]}), encoding="utf-8")
    fails = gg.check_units_no_nocontent(tmp_path)
    assert fails and any("無法辨識" in f for f in fails)


def test_gate_corrupt_json_fails_closed(tmp_path):
    (tmp_path / "g3_FINAL_screen.json").write_text("{broken json", encoding="utf-8")
    gg._CORRUPT.clear()
    assert gg.check_screen_partition(tmp_path) is None   # 單一 check 仍跳過…
    fails = gg._corrupt_fails()                          # …但 orchestrator 會把壞檔亮成 FAIL
    assert fails and any("g3_FINAL_screen" in f for f in fails)
    gg._CORRUPT.clear()


def _flow_data(rows, reconcile=""):
    return {"flow": rows, "flow_reconcile": reconcile}


def test_flow_closure_passes_consistent_flow():
    rows = [
        {"stage": "識別", "start": "—", "excluded": "—", "remain": "500（文獻聯集）"},
        {"stage": "②b", "start": "500", "excluded": "剔除明顯離題 100", "remain": "400"},
        {"stage": "③", "start": "400", "excluded": "離題 300、全文及摘要皆無 20", "remain": "切題 80"},
        {"stage": "④", "start": "80", "excluded": "—（新增 +5）", "remain": "85"},
        {"stage": "⑤a", "start": "85", "excluded": "撤稿 −1、無法驗證 −2（皆剔除，不入分析）", "remain": "82"},
    ]
    assert fc.check_flow(_flow_data(rows, "對帳：核心 26 ＋ 背景 35 ＋ 待評估 21 ＝ 82。")) == []


def test_flow_closure_catches_bad_row_and_bad_chain():
    rows = [
        {"stage": "②b", "start": "500", "excluded": "剔除 100", "remain": "390"},   # 500−100≠390
        {"stage": "③", "start": "400", "excluded": "離題 10", "remain": "390"},     # 上關剩 390 ≠ 起始 400
    ]
    fails = fc.check_flow(_flow_data(rows))
    assert any("不閉合" in f for f in fails) and any("不銜接" in f for f in fails)


def test_flow_closure_catches_bad_reconcile():
    fails = fc.check_flow(_flow_data([], "對帳：核心 26 ＋ 背景 35 ＝ 100。"))
    assert any("對帳不成立" in f for f in fails)
