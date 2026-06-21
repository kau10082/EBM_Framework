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
import sys, re, json, argparse, hashlib
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
    # 穩定唯一鍵：pmid ＞ doi ＞ uid。三者皆缺時**不可**回固定字串（會讓多筆無 ID 記錄全坍縮成同一
    # paper_id，破壞 Stage A candidate/awaiting 互斥判定——SEARCH_SPEC 鐵律）；改以內容雜湊保證唯一。
    if r.get("pmid"):
        return "PMID" + str(r["pmid"])
    if r.get("doi"):
        return "DOI" + re.sub(r"[^\w.-]", "_", str(r["doi"]))
    if r.get("uid"):
        return "UID" + str(r["uid"])
    # 無 uid/pmid/doi：以「正規化標題」雜湊當穩定鍵——跨 cache 檔一致（不混入 class/verdict 等狀態欄位，
    # 否則同一篇在 g2c_FINAL_content 與 g2c_awaiting 算出不同 hash → 繞過互斥檢查）。標題也空才退回整筆雜湊。
    t = re.sub(r"[^0-9a-z一-鿿]", "", (r.get("title") or "").lower())
    basis = t or json.dumps(r, ensure_ascii=False, sort_keys=True)
    return "H" + hashlib.md5(basis.encode("utf-8")).hexdigest()[:12]

def build(cache, topic="", pico=None):
    content = _load(cache, "g2c_FINAL_content.json") or []
    awaiting_src = _load(cache, "g2c_awaiting_classification.json") or []
    legs = _load(cache, "g1_legs_manifest.json") or []
    pico = pico or {"statement": topic, "P": "", "I": "", "C": "", "O": []}

    # 待評估類 class（②c 已判無內容）：交 awaiting_src 統一處理，不進 candidate
    AWAIT_CLASSES = ("待人工補全文", "兩者皆無")
    candidates, awaiting = [], []
    for c in content:
        cls = str(c.get("class") or "")
        ab = (c.get("abstract") or "").strip()
        if cls.startswith(AWAIT_CLASSES):
            continue
        # ★ 忠實沿用 ②c 的 class 分流決定 fulltext_status——**不再憑『有無摘要』重推**
        # （否則登錄試驗/有全文但無自由文字摘要者會被誤降 none→誤丟 awaiting；2026-06 實測 135 筆 CT.gov 被誤分類）。
        if cls.startswith("有全文"):
            ft_status, channel = "have", "online"
        elif cls.startswith("登錄"):
            ft_status, channel = "have", "registry"      # CT.gov 登錄＝結構化內容（非 awaiting）
        elif ab:
            ft_status, channel = "ai_summary_only", "abstract_only"
        else:
            ft_status, channel = "none", "manual_pending"  # 保底（②c 判為 content 者理應有內容）
        candidates.append({
            "paper_id": _pid(c), "title": (c.get("title") or "").strip() or ("(" + _pid(c) + ")"),
            "pmid": c.get("pmid"), "doi": c.get("doi"), "journal": c.get("journal"), "year": c.get("year"),
            "verdict": "candidate",
            "fulltext_status": ft_status,
            "abstract_status": "have" if ab else "none",
            "fulltext_channel": channel,
            "fulltext_url": ("https://doi.org/" + c["doi"]) if c.get("doi") else None,
            "abstract": ab or None,
        })
    # awaiting 一律來自 awaiting_src（②c 已定的待評估），reason 以其『明確 reason』為準——
    # **不可用 channels_exhausted 反推 reason**（兩者皆無 也帶 channels_exhausted，會被誤標成待人工補全文）。
    for a in awaiting_src:
        r = a.get("reason") or a.get("verdict") or ""
        reason = r if r in ("待人工補全文", "兩者皆無") else ("待人工補全文" if a.get("channels_exhausted") else "兩者皆無")
        entry = {"paper_id": _pid(a), "title": a.get("title") or "", "pmid": a.get("pmid"),
                 "doi": a.get("doi"), "reason": reason, "channels_exhausted": bool(a.get("channels_exhausted"))}
        if a.get("oa_url"): entry["oa_url"] = a["oa_url"]
        if a.get("oa_fetch_attempted"): entry["oa_fetch_attempted"] = True
        if a.get("pmcid"): entry["pmcid"] = a["pmcid"]
        awaiting.append(entry)
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
