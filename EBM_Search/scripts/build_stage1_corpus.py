# -*- coding: utf-8 -*-
"""
build_stage1_corpus.py — Stage A 收尾：確定性寫出 _stage1_corpus.json（交班給 Stage B）
========================================================================================
從 Stage A 的 cache 產物確定性組裝交接契約（schema：references/stage1_corpus_schema.json）：
  legs        ← g1_legs_manifest.json（取盡證據）
  candidates  ← g2c_FINAL_content.json 中『有內容(摘要或全文)』者，verdict=candidate
  awaiting    ← 無內容者（兩者皆無 / 待人工補全文，channels_exhausted）
每筆全文狀態務實填（have/ai_summary_only/none）、abstract_status（have/none）、管道/URL；
寫出前自我驗證（呼叫 stage1_check）——有缺格/邊界違規即 FAIL，不產出。

用法：python build_stage1_corpus.py --cache <dir> --out <_stage1_corpus.json> [--topic .. --pico-json ..]
"""
import sys, os, re, json, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _load(cache, f):
    p = Path(cache) / f
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None

def _pid(r):
    return ("PMID" + str(r["pmid"])) if r.get("pmid") else ("DOI" + re.sub(r"[^\w.-]", "_", str(r.get("doi"))) if r.get("doi") else ("UID" + str(r.get("uid") or "")))

def build(cache, topic="", pico=None):
    content = _load(cache, "g2c_FINAL_content.json") or []
    awaiting_src = _load(cache, "g2c_awaiting_classification.json") or []
    legs = _load(cache, "g1_legs_manifest.json") or []
    pico = pico or {"statement": topic, "P": "", "I": "", "C": "", "O": []}

    awaiting_uids = {a.get("uid") for a in awaiting_src}
    candidates, awaiting = [], []
    for c in content:
        ab = (c.get("abstract") or "").strip()
        has_ft = str(c.get("class") or "").startswith("有全文")
        # 內容判定：有摘要 or 有全文路徑 → candidate；否則 awaiting
        if c.get("uid") in awaiting_uids and not ab:
            continue  # 由 awaiting_src 統一處理
        ft_status = "have" if has_ft else ("ai_summary_only" if ab else "none")
        if ft_status == "none" and not ab:
            awaiting.append({"paper_id": _pid(c), "title": c.get("title") or "", "pmid": c.get("pmid"),
                             "doi": c.get("doi"), "reason": "兩者皆無", "channels_exhausted": True})
            continue
        candidates.append({
            "paper_id": _pid(c), "title": (c.get("title") or "").strip() or ("(" + _pid(c) + ")"),
            "pmid": c.get("pmid"), "doi": c.get("doi"), "journal": c.get("journal"), "year": c.get("year"),
            "verdict": "candidate",
            "fulltext_status": ft_status,
            "abstract_status": "have" if ab else "none",
            "fulltext_channel": ("online" if has_ft else ("abstract_only" if ab else "manual_pending")),
            "fulltext_url": ("https://doi.org/" + c["doi"]) if c.get("doi") else None,
            "abstract": ab or None,
        })
    # awaiting_src（含 channels_exhausted / 待人工補全文）
    for a in awaiting_src:
        v = a.get("verdict") or ""
        reason = "待人工補全文" if ("待人工補全文" in v or a.get("channels_exhausted")) else "兩者皆無"
        awaiting.append({"paper_id": _pid(a), "title": a.get("title") or "", "pmid": a.get("pmid"),
                         "doi": a.get("doi"), "reason": reason, "channels_exhausted": bool(a.get("channels_exhausted"))})
    return {
        "schema_version": "stage1-1.0", "topic": topic, "search_date": "",
        "review_question_seed": pico, "legs": legs,
        "candidates": candidates, "awaiting": awaiting,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--topic", default="")
    ap.add_argument("--search-date", default="")
    ap.add_argument("--pico-json", default=None, help="review_question_seed JSON 檔(可選)")
    a = ap.parse_args()
    pico = None
    if a.pico_json and Path(a.pico_json).exists():
        pico = json.loads(Path(a.pico_json).read_text(encoding="utf-8"))
    data = build(a.cache, topic=a.topic, pico=pico)
    if a.search_date: data["search_date"] = a.search_date
    # 自我驗證（邊界守門）
    try:
        import stage1_check
        fails = stage1_check.check(data)
    except Exception as e:
        fails = [f"stage1_check 載入失敗：{str(e)[:80]}"]
    if fails:
        print("❌ Stage A 交接包未過邊界守門（不寫出）：")
        for f in fails: print("  -", f)
        sys.exit(1)
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Stage A 交接包寫出：candidates {len(data['candidates'])} ／ awaiting {len(data['awaiting'])} ／ legs {len(data['legs'])} → {a.out}")

if __name__ == "__main__":
    main()
