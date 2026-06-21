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
- **過濾＋驗證＋寫檔**：seed 內容由 EBM_Search(Claude 引擎)依報告三表組裝；本工具
  (a) 預設**只交接『納入一起分析』者**(PRISMA Included＝核心RCT+子研究+納入SR/MA；
      verdict=included 且 grade_track∈{full,targeted_harms,light_summary})——背景與
      僅登錄端/待評估(grade_track=none)不進交接(用 --include-background 可全帶,舊行為)；
  (b) 做契約把關(required/enum/一致性)再落地，避免交接包格式漂移。
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

# ★ 2026-06 使用者糾正：交接包預設**只交接『納入一起分析』者**＝PRISMA 流程末步「Included」產生的
#   核心 RCT＋子研究 ＋ 納入分析的 SR/MA（即 verdict=included 且 grade_track∈下列三者）。
#   背景(verdict=background)與『僅登錄端/待評估』(grade_track=none)不進交接——它們是分流脈絡、非評讀單位，
#   會稀釋下游 Phase 0 的分析名單。要連背景一併交接(舊行為、供脈絡)用 --include-background。
ANALYSIS_GRADE_TRACKS = {"full", "targeted_harms", "light_summary"}


def filter_analysis_set(papers):
    """回 (kept, dropped)：只留『納入一起分析』者(核心RCT+子研究+納入SR/MA)。"""
    kept, dropped = [], []
    for p in (papers or []):
        gt = (p.get("suggested") or {}).get("grade_track")
        if p.get("verdict") == "included" and gt in ANALYSIS_GRADE_TRACKS:
            kept.append(p)
        else:
            dropped.append(p)
    return kept, dropped



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

        # 一致性：有全文者要有「可取得依據」。本機管道(local/人工補)要 pdf_file；
        # 線上管道(Claude 線上直讀,不必下載 PDF；對齊 analysis-read-fulltext-not-download)改要 fulltext_url 或 doi/pmid。
        if p.get("fulltext_status") in ("have", "have_manual"):
            ch = p.get("fulltext_channel")
            if ch == "online":
                if not (p.get("fulltext_url") or p.get("doi") or p.get("pmid")):
                    errs.append("%s fulltext_status=%s channel=online 但缺 fulltext_url/doi/pmid(線上取得依據)"
                                % (tag, p.get("fulltext_status")))
            elif not p.get("pdf_file"):  # local / 人工補 / 未標 channel → 視為本機，需 pdf_file
                errs.append("%s fulltext_status=%s(本機管道) 但缺 pdf_file" % (tag, p.get("fulltext_status")))

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
    ap.add_argument("--include-background", action="store_true",
                    help="連背景(verdict=background)與僅登錄/待評估(grade_track=none)一併交接(舊行為)；"
                         "預設只交接『納入一起分析』者(核心RCT+子研究+納入SR/MA)")
    args = ap.parse_args(argv)

    raw = sys.stdin.read() if args.infile == "-" else open(args.infile, "r", encoding="utf-8").read()
    try:
        seed = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write("✗ seed 不是合法 JSON：%s\n" % e)
        return 2

    # 預設過濾：只交接『納入一起分析』者(PRISMA Included＝核心RCT+子研究+納入SR/MA)。
    if not args.include_background and isinstance(seed, dict) and isinstance(seed.get("papers"), list):
        kept, dropped = filter_analysis_set(seed["papers"])
        if not kept:
            sys.stderr.write("✗ 過濾後無任何『納入一起分析』文獻(核心RCT+子研究+納入SR/MA)："
                             "請確認 suggested.grade_track 已正確標記，或用 --include-background。\n")
            return 2
        seed["papers"] = kept
        sys.stderr.write("  交接過濾：只交接『納入一起分析』者(核心RCT+子研究+納入SR/MA)＝%d 篇；"
                         "略過背景/僅登錄端/待評估 %d 篇(要全帶用 --include-background)。\n"
                         % (len(kept), len(dropped)))

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
