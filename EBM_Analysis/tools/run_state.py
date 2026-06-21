# -*- coding: utf-8 -*-
"""
run_state.py — 本次 EBM run 的『單一指標檔』(work/run_state.json)
================================================================
把一次分析的所有座標寫在一個檔，之後任何階段/工具/對話只讀這一檔就知道
corpus、cache、outputs、reports、fulltext、各成品 PDF/MD 在哪，不必每輪重推路徑。
（呼應「架構不是負擔、要收的是路徑與狀態一致性」。）

用法：
  python tools/run_state.py show                       # 印出目前 run 狀態
  python tools/run_state.py set --topic "X" --date 2026-06-14 --slug X_2026-06-14 \
        --seed <path> --stage phase4_complete           # 更新欄位(只覆寫有給的)
  在程式內：import run_state; run_state.update(stage="phase3_done", corpus={...})
"""
import json, sys, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir

STATE = Path(workdir.work_root()) / "run_state.json"

def load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"topic": None, "search_date": None, "slug": None,
            "paths": {}, "artifacts": {}, "corpus": {}, "stage": None}

def save(d):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return STATE

def update(**kw):
    d = load()
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            d[k].update(v)
        elif v is not None:
            d[k] = v
    save(d)
    return d

def autofill():
    """依 workdir/config 自動帶入標準路徑（不覆寫已有 topic/slug）。"""
    d = load()
    d["paths"] = {**d.get("paths", {}),
                  "cache_dir": str(Path(workdir.cache_dir())),
                  "outputs_dir": str(Path(workdir.outputs_dir())),
                  "work_root": str(Path(workdir.work_root()))}
    save(d)
    return d

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("show")
    s = sub.add_parser("set")
    for f in ("topic", "date", "slug", "seed", "fulltext_dir", "reports_dir", "stage"):
        s.add_argument("--" + f)
    a = ap.parse_args()
    if a.cmd == "show" or not a.cmd:
        autofill(); print(json.dumps(load(), ensure_ascii=False, indent=1)); return
    if a.cmd == "set":
        paths = {k: getattr(a, k) for k in ("seed", "fulltext_dir", "reports_dir") if getattr(a, k)}
        kw = {}
        if a.topic: kw["topic"] = a.topic
        if a.date: kw["search_date"] = a.date
        if a.slug: kw["slug"] = a.slug
        if a.stage: kw["stage"] = a.stage
        if paths: kw["paths"] = paths
        update(**kw); autofill(); print("已更新 →", STATE); print(json.dumps(load(), ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
