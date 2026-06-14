#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EBM_Search / build_corpus_seed.py  (交接層, v1.0)
==================================================
把 EBM_Search Phase 1 收尾時已決定的事(必含軸→PICO 雛形、表二/表三背景的
verdict、study 標籤、證據等級、全文狀態、PDF 檔名)寫成 **交接包**
`_corpus_seed.json`，放進全文資料夾，供 EBM_Analysis 的 Phase 0 直接吃。

定位
----
- EBM 管線「**交接層**」：銜接 EBM_Search(檢索/驗證) → EBM_Analysis(評讀)。
  與引擎(xref_verify)、Zotero(zotero_import)、全文(fulltext_fetch)分離。
- 零相依：純 Python 3.8+ 標準庫(json / os / argparse)。
- **只驗證＋寫檔**：seed 內容由 EBM_Search(Claude 引擎)依報告三表組裝；本工具
  做契約把關(required/enum/一致性)再落地，避免交接包格式漂移。
- 契約正本＝`references/corpus_seed_schema.json`(本工具持有並對齊)。

用法
----
  # Claude 組好 seed dict → 存成 seed.json(或由 stdin) → 本工具驗證並寫出
  python build_corpus_seed.py --in seed.json --out-dir "<fulltext 資料夾>"
  python build_corpus_seed.py --in seed.json            # 寫到 seed.fulltext_dir 或 CWD
  cat seed.json | python build_corpus_seed.py --in -    # 由 stdin 讀

輸出：<out-dir>/_corpus_seed.json（並回報絕對路徑與每篇分流摘要）。
退場碼：0＝寫出成功；2＝契約驗證失敗(列出每條錯誤，不寫檔)。
"""

import argparse
import json
import os
import sys

SEED_FILENAME = "_corpus_seed.json"
SCHEMA_VERSION = "1.0"

VERDICTS = {"included", "background"}
FULLTEXT_STATUS = {"have", "have_manual", "ai_summary_only", "none"}
RELEVANCE = {"direct", "indirect", "background", "excluded"}
ROLE = {"pivotal_efficacy", "meta_analysis", "safety", "supportive_secondary",
        "mechanism_pd", "pharmacokinetic", "narrative_review", "other"}
GRADE_TRACK = {"full", "targeted_harms", "light_summary", "none"}
EVIDENCE_LEVEL = {"L1", "L2", "L3", "L4", "L5", "未分類", None}


def _force_utf8_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def validate(seed):
    """對 corpus_seed 契約做務實驗證。回傳錯誤訊息 list(空＝通過)。"""
    errs = []

    if not isinstance(seed, dict):
        return ["頂層必須是 JSON 物件"]

    if seed.get("schema_version") != SCHEMA_VERSION:
        errs.append("schema_version 必須為 \"%s\"(實得 %r)" % (SCHEMA_VERSION, seed.get("schema_version")))

    for k in ("topic", "search_date"):
        if not isinstance(seed.get(k), str) or not seed.get(k):
            errs.append("缺必填字串欄位 %s" % k)

    rq = seed.get("review_question_seed")
    if not isinstance(rq, dict):
        errs.append("缺 review_question_seed 物件")
    else:
        for k in ("statement", "P", "I", "C"):
            if not isinstance(rq.get(k), str):
                errs.append("review_question_seed.%s 須為字串(可空字串)" % k)
        if not isinstance(rq.get("O"), list):
            errs.append("review_question_seed.O 須為陣列(EBM_Search 不以 O 為軸，通常 [])")

    papers = seed.get("papers")
    if not isinstance(papers, list) or not papers:
        errs.append("papers 須為非空陣列")
        return errs

    seen_ids = set()
    for i, p in enumerate(papers):
        tag = "papers[%d]" % i
        if not isinstance(p, dict):
            errs.append("%s 須為物件" % tag)
            continue
        pid = p.get("paper_id")
        if not isinstance(pid, str) or not pid:
            errs.append("%s 缺 paper_id" % tag)
        else:
            tag = "papers[%d](%s)" % (i, pid)
            if pid in seen_ids:
                errs.append("%s paper_id 重複" % tag)
            seen_ids.add(pid)
        if not isinstance(p.get("title"), str) or not p.get("title"):
            errs.append("%s 缺 title" % tag)
        if p.get("verdict") not in VERDICTS:
            errs.append("%s verdict 須為 included/background(實得 %r)" % (tag, p.get("verdict")))
        if p.get("fulltext_status") not in FULLTEXT_STATUS:
            errs.append("%s fulltext_status 非法(實得 %r)" % (tag, p.get("fulltext_status")))
        if "evidence_level" in p and p.get("evidence_level") not in EVIDENCE_LEVEL:
            errs.append("%s evidence_level 非法(實得 %r)" % (tag, p.get("evidence_level")))

        sug = p.get("suggested")
        if not isinstance(sug, dict):
            errs.append("%s 缺 suggested 物件" % tag)
        else:
            if sug.get("relevance") not in RELEVANCE:
                errs.append("%s suggested.relevance 非法(實得 %r)" % (tag, sug.get("relevance")))
            if sug.get("role") not in ROLE:
                errs.append("%s suggested.role 非法(實得 %r)" % (tag, sug.get("role")))
            if sug.get("grade_track") not in GRADE_TRACK:
                errs.append("%s suggested.grade_track 非法(實得 %r)" % (tag, sug.get("grade_track")))

        # 一致性：有全文者應給 pdf_file；無全文者建議 light_summary
        if p.get("fulltext_status") in ("have", "have_manual") and not p.get("pdf_file"):
            errs.append("%s fulltext_status=%s 但缺 pdf_file" % (tag, p.get("fulltext_status")))

    return errs


def _resolve_out_dir(args, seed):
    if args.out_dir:
        return os.path.abspath(args.out_dir)
    ftd = (seed.get("fulltext_dir") or "").strip()
    if ftd:
        return os.path.abspath(ftd)
    return os.getcwd()


def main(argv=None):
    _force_utf8_console()
    ap = argparse.ArgumentParser(description="驗證並寫出 EBM_Search→EBM_Analysis 交接包 _corpus_seed.json")
    ap.add_argument("--in", dest="infile", required=True, help="seed JSON 路徑(或 - 表 stdin)")
    ap.add_argument("--out-dir", dest="out_dir", default=None,
                    help="寫出資料夾(預設 = seed.fulltext_dir 或目前目錄)")
    ap.add_argument("--dry-run", action="store_true", help="只驗證、不寫檔")
    args = ap.parse_args(argv)

    raw = sys.stdin.read() if args.infile == "-" else open(args.infile, "r", encoding="utf-8").read()
    try:
        seed = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write("✗ seed 不是合法 JSON：%s\n" % e)
        return 2

    errs = validate(seed)
    if errs:
        sys.stderr.write("✗ 交接包契約驗證失敗(%d 條)，未寫檔：\n" % len(errs))
        for e in errs:
            sys.stderr.write("   - %s\n" % e)
        return 2

    papers = seed["papers"]
    n_inc = sum(1 for p in papers if p.get("verdict") == "included")
    n_bg = sum(1 for p in papers if p.get("verdict") == "background")
    n_pdf = sum(1 for p in papers if p.get("fulltext_status") in ("have", "have_manual"))
    n_full = sum(1 for p in papers if p.get("suggested", {}).get("grade_track") == "full")

    # 確保 fulltext_dir 寫入 seed(供 Analysis ingester 對回 PDF)
    out_dir = _resolve_out_dir(args, seed)
    if not seed.get("fulltext_dir"):
        seed["fulltext_dir"] = out_dir

    if args.dry_run:
        sys.stderr.write("✓ 契約通過(dry-run，未寫檔)。\n")
    else:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, SEED_FILENAME)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)
        sys.stderr.write("✓ 交接包已寫出 → %s\n" % os.path.normpath(out_path))

    sys.stderr.write(
        "  主題：%s ｜ 檢索日：%s\n"
        "  文獻 %d 篇：納入(included) %d ／背景(background) %d ｜有 PDF %d ｜建議 full-track %d\n" % (
            seed["topic"], seed["search_date"], len(papers), n_inc, n_bg, n_pdf, n_full))
    sys.stderr.write("  下一步：在 EBM_Analysis 對 Claude 說「繼續(進入 EBM 分析)」，"
                     "或 `python tools/ingest_seed.py --seed-dir \"%s\"`。\n" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
