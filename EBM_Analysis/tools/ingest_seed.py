#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EBM_Analysis / tools/ingest_seed.py  (交接層, v1.0)
====================================================
吃 EBM_Search 寫出的交接包 `_corpus_seed.json`，做兩件確定性的事：
  1. 把交接包指向的全文 PDF **複製進 `inputs/`**（檔名 = <paper_id>.pdf）。
  2. 依 seed 的 `suggested` 映射與 `study` 去重，產出**預填的 Phase 0 草稿**
     `cache/_corpus.draft.json`（符合 `schema/phase0_corpus.json`）。

定位
----
- EBM 管線「**交接層**」的消費端：銜接 EBM_Search → EBM_Analysis。
- **草稿、非定稿**：本工具只「預填」。Phase 0 仍須在斷點把分流＋review question
  攤給使用者覆核確認，確認後才把草稿存成正式 `cache/_corpus.json`。
  故輸出檔名刻意為 `_corpus.draft.json`，不直接覆蓋 `_corpus.json`。
- 零相依（json / os / shutil / argparse）；jsonschema 驗證留給 `tools/validate.py`。

映射規則（seed.suggested → phase0_corpus；詳見 EBM_Framework/INTEGRATION.md）
  relevance / role / grade_track  ← 原樣帶入（EBM_Search 已決定的建議）
  design                          ← seed.design_hint
  overlap_with                    ← 共用同一 study 標籤的其他 paper_id（同試驗多報告）
  included_trials                 ← seed.included_trials（僅 MA）
  notes                           ← verdict / 全文狀態 / suggested.rationale 合併（可追溯）
  review_question                 ← review_question_seed（O 空則填待定佔位，符合 schema minItems:1）

用法
----
  python tools/ingest_seed.py --seed-dir "<交接包資料夾>"      # 內含 _corpus_seed.json
  python tools/ingest_seed.py --seed "<...>/_corpus_seed.json"
  python tools/ingest_seed.py --seed-dir "<...>" --dry-run     # 只看會做什麼，不複製不寫檔
"""

import argparse
import json
import os
import shutil
import sys

SEED_FILENAME = "_corpus_seed.json"
SUPPORTED_SCHEMA = "1.0"
O_PLACEHOLDER = "（待 Phase 0 與使用者補定）"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workdir  # noqa: E402  執行期資料導向工作夾（見 workdir.py）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUTS_DIR = workdir.inputs_dir()
CACHE_DIR = workdir.cache_dir()


def _force_utf8_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _resolve_seed_path(args):
    if args.seed:
        return os.path.abspath(args.seed)
    if args.seed_dir:
        return os.path.join(os.path.abspath(args.seed_dir), SEED_FILENAME)
    raise SystemExit("需指定 --seed-dir 或 --seed")


def _fulltext_dir(seed, seed_path):
    """PDF 來源目錄：優先 seed.fulltext_dir，否則 seed 檔所在資料夾。"""
    ftd = (seed.get("fulltext_dir") or "").strip()
    return os.path.abspath(ftd) if ftd else os.path.dirname(seed_path)


def _build_overlap(papers):
    """同一 study 標籤的多篇 → 互相 overlap_with（排除自己）。"""
    by_study = {}
    for p in papers:
        st = (p.get("study") or "").strip()
        if st:
            by_study.setdefault(st, []).append(p["paper_id"])
    overlap = {}
    for ids in by_study.values():
        if len(ids) > 1:
            for pid in ids:
                overlap[pid] = [x for x in ids if x != pid]
    return overlap


def _note_for(p):
    bits = ["verdict=%s" % p.get("verdict", "?")]
    if p.get("study"):
        bits.append("study=%s" % p["study"])
    if p.get("evidence_level"):
        bits.append(p["evidence_level"])
    bits.append("全文=%s" % p.get("fulltext_status", "?"))
    sug = p.get("suggested") or {}
    if sug.get("rationale"):
        bits.append(sug["rationale"])
    if p.get("fulltext_status") in ("ai_summary_only", "none"):
        bits.append("⚠️無全文PDF：建議 light_summary 或人工補全文後再升 full")
    return "（由 EBM_Search 交接預填，待覆核）" + "；".join(bits)


def main(argv=None):
    _force_utf8_console()
    ap = argparse.ArgumentParser(description="吃 EBM_Search 交接包 → 複製 PDF 進 inputs/ ＋ 預填 Phase 0 草稿")
    ap.add_argument("--seed-dir", dest="seed_dir", default=None, help="含 _corpus_seed.json 的資料夾")
    ap.add_argument("--seed", dest="seed", default=None, help="_corpus_seed.json 的直接路徑")
    ap.add_argument("--dry-run", action="store_true", help="只報告會做什麼，不複製、不寫檔")
    args = ap.parse_args(argv)

    seed_path = _resolve_seed_path(args)
    if not os.path.isfile(seed_path):
        sys.stderr.write("✗ 找不到交接包：%s\n" % seed_path)
        return 2
    with open(seed_path, "r", encoding="utf-8") as f:
        seed = json.load(f)

    if seed.get("schema_version") != SUPPORTED_SCHEMA:
        sys.stderr.write("✗ 交接包 schema_version=%r，本工具支援 %s\n" % (
            seed.get("schema_version"), SUPPORTED_SCHEMA))
        return 2

    papers = seed.get("papers") or []
    if not papers:
        sys.stderr.write("✗ 交接包 papers 為空\n")
        return 2
    # 缺 paper_id 給明確錯誤（取代下游 p["paper_id"] 的 bare KeyError；ingest 只驗 schema_version，這層補防呆）
    missing_pid = [i + 1 for i, p in enumerate(papers) if not p.get("paper_id")]
    if missing_pid:
        sys.stderr.write("✗ 交接包第 %s 筆 paper 缺 paper_id（無法建 corpus／分組／複製 PDF）\n" % missing_pid)
        return 2

    ft_dir = _fulltext_dir(seed, seed_path)
    overlap = _build_overlap(papers)

    # ── 1. 複製 PDF 進 inputs/ ──────────────────────────────
    copied, missing, no_pdf = [], [], []
    if not args.dry_run:
        os.makedirs(INPUTS_DIR, exist_ok=True)
    for p in papers:
        pid = p["paper_id"]
        pdf = p.get("pdf_file")
        if not pdf:
            no_pdf.append(pid)
            continue
        src = pdf if os.path.isabs(pdf) else os.path.join(ft_dir, pdf)
        if not os.path.isfile(src):
            missing.append((pid, src))
            continue
        ext = os.path.splitext(pdf)[1] or ".pdf"
        dest = os.path.join(INPUTS_DIR, pid + ext)
        if not args.dry_run:
            shutil.copy2(src, dest)
        copied.append(pid)

    # ── 2. 預填 Phase 0 草稿 ─────────────────────────────────
    rq = seed.get("review_question_seed") or {}
    o_list = list(rq.get("O") or [])
    if not o_list:
        o_list = [O_PLACEHOLDER]
    review_question = {
        "statement": rq.get("statement") or seed.get("topic", ""),
        "P": rq.get("P", ""),
        "I": rq.get("I", ""),
        "C": rq.get("C", ""),
        "O": o_list,
    }

    draft_papers = []
    for p in papers:
        pid = p["paper_id"]
        sug = p.get("suggested") or {}
        item = {
            "paper_id": pid,
            "relevance": sug.get("relevance", "background"),
            "role": sug.get("role", "other"),
            "grade_track": sug.get("grade_track", "light_summary"),
            "notes": _note_for(p),
        }
        if p.get("title"):
            item["title"] = p["title"]
        if p.get("design_hint"):
            item["design"] = p["design_hint"]
        if p.get("included_trials"):
            item["included_trials"] = list(p["included_trials"])
        if overlap.get(pid):
            item["overlap_with"] = overlap[pid]
        draft_papers.append(item)

    n_inc = sum(1 for p in papers if p.get("verdict") == "included")
    n_bg = sum(1 for p in papers if p.get("verdict") == "background")
    n_full = sum(1 for x in draft_papers if x["grade_track"] == "full")
    corpus = {
        "review_question": review_question,
        "papers": draft_papers,
        "overlap_notes": (
            "★草稿：由 EBM_Search 交接包 _corpus_seed.json 預填，review question 與每篇分流"
            "（relevance/role/grade_track）均為建議值，須在 Phase 0 斷點與使用者覆核後才定稿為 "
            "_corpus.json。主題：%s（檢索日 %s）。納入 %d／背景 %d；建議 full-track %d。%s" % (
                seed.get("topic", ""), seed.get("search_date", ""), n_inc, n_bg, n_full,
                seed.get("handoff_notes") or "")),
    }

    draft_path = os.path.join(CACHE_DIR, "_corpus.draft.json")
    if not args.dry_run:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, ensure_ascii=False, indent=2)

    # ── 報告 ────────────────────────────────────────────────
    tag = "DRY-RUN（未複製、未寫檔）" if args.dry_run else "已執行"
    sys.stderr.write("EBM_Search 交接包匯入（%s）\n" % tag)
    sys.stderr.write("  來源：%s\n" % os.path.normpath(seed_path))
    sys.stderr.write("  主題：%s ｜ 檢索日：%s\n" % (seed.get("topic", ""), seed.get("search_date", "")))
    sys.stderr.write("  PDF → inputs/：複製 %d ｜缺檔 %d ｜無 PDF(背景/僅摘要) %d\n" % (
        len(copied), len(missing), len(no_pdf)))
    for pid, src in missing:
        sys.stderr.write("    ⚠️ 缺檔：%s ← %s\n" % (pid, os.path.normpath(src)))
    if no_pdf:
        sys.stderr.write("    （無 PDF，預填為背景/light_summary）：%s\n" % "、".join(no_pdf))
    sys.stderr.write("  草稿 → %s\n" % os.path.normpath(draft_path))
    sys.stderr.write("  分流預填：納入 %d ／背景 %d ｜建議 full-track %d\n" % (n_inc, n_bg, n_full))
    sys.stderr.write("  下一步（Phase 0）：把草稿的 review question＋逐篇分流攤給使用者覆核；"
                     "確認後存成 cache/_corpus.json，再 `python tools/validate.py p0 cache/_corpus.json`。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
