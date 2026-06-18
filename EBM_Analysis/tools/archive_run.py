# -*- coding: utf-8 -*-
"""無 API：把目前一次分析的 cache/outputs 封存成一個獨立 run，避免被下次分析覆蓋。

  python tools/archive_run.py <主題slug> [--date YYYY-MM] [--clear] [--with-text] [--move]

  <主題slug>      run 名稱（如 DPP1-bronchiectasis）
  --date          指定日期（預設今天 YYYY-MM）
  --with-text     連 cache 的抽取全文 .txt 一起存（含版權內容，預設不存）
  --no-sources    不產生 sources.md 來源清單（預設會產生）
  --clear         封存後清空 cache/ 與 outputs/（保留 .gitkeep），讓下次分析乾淨
  --move          同 --clear，但語意上是「搬移」

產出：runs/<date>_<slug>/
  ├── deliverables/  成品（FINAL_REPORT.md/pdf、synthesis.md、各 report.md、ledger.csv）
  ├── audit/         審計軌跡（p1–p4 JSON、_corpus、_synthesis、_adversarial_review）
  └── sources.md     來源清單（回顧問題＋文獻角色/引用/註冊號，自 _corpus.json 生成）

注意：runs/ 已被 .gitignore，封存內容含衍生分析與原文引用片段，留本機、勿上公開 repo。
"""
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir  # noqa: E402  執行期資料導向工作夾（見 workdir.py）
CACHE = Path(workdir.cache_dir())
OUTPUTS = Path(workdir.outputs_dir())
RUNS = Path(workdir.runs_dir())


def gen_sources(dest):
    corpus = CACHE / "_corpus.json"
    if not corpus.exists():
        return False
    d = json.loads(corpus.read_text(encoding="utf-8"))
    rq = d.get("review_question", {})
    L = ["# 證據來源清單", "", "## 回顧問題（Review Question）", rq.get("statement", ""), "",
         f"- **P**：{rq.get('P','')}", f"- **I**：{rq.get('I','')}",
         f"- **C**：{rq.get('C','')}", f"- **O**：{'、'.join(rq.get('O', []))}", "",
         "## 文獻清單", "",
         "| paper_id | 相關性 | 角色 | 評讀軌道 | 引用 | 註冊號 |",
         "|---|---|---|---|---|---|"]
    for p in d.get("papers", []):
        pid = p["paper_id"]
        cite = reg = ""
        p1 = CACHE / f"{pid}.p1.json"
        if p1.exists():
            cite = (json.loads(p1.read_text(encoding="utf-8")).get("citation", "") or "").replace("|", "／")
        p2 = CACHE / f"{pid}.p2.json"
        if p2.exists():
            j = json.loads(p2.read_text(encoding="utf-8"))
            reg = ((j.get("selective_reporting") or {}).get("registry")) or ""
        L.append(f"| {pid} | {p.get('relevance','')} | {p.get('role','')} | "
                 f"{p.get('grade_track','')} | {cite} | {reg} |")
    overlap = d.get("overlap_notes")
    if overlap:
        L += ["", "## 重疊／去重說明", overlap]
    (dest / "sources.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return True


def _copy_dir(src, files, dest):
    n = 0
    for f in files:
        if f.is_file() and f.name != ".gitkeep":
            shutil.copy2(f, dest / f.name)
            n += 1
    return n


def _clear(d):
    for f in d.iterdir():
        if f.name == ".gitkeep":
            continue
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    slug = argv[0]
    date = datetime.now().strftime("%Y-%m")
    if "--date" in argv:
        date = argv[argv.index("--date") + 1]
    with_text = "--with-text" in argv
    clear = ("--clear" in argv) or ("--move" in argv)
    no_sources = "--no-sources" in argv

    run = RUNS / f"{date}_{slug}"
    if run.exists():
        print(f"⚠️ {run} 已存在，請換名或先移除。")
        return 1
    deliver = run / "deliverables"
    audit = run / "audit"
    deliver.mkdir(parents=True)
    audit.mkdir(parents=True)

    # 成品 vs 審計分流
    deliver_names = {"FINAL_REPORT.md", "FINAL_REPORT.pdf", "synthesis.md", "ledger.csv"}
    dn = an = 0
    if OUTPUTS.exists():
        for f in OUTPUTS.iterdir():
            if f.name == ".gitkeep":
                continue
            if f.is_dir():   # 子目錄整棵入 audit——否則 --clear 的 rmtree 會刪掉未封存的子目錄＝資料遺失
                shutil.copytree(f, audit / f.name, dirs_exist_ok=True); an += 1
            elif f.name in deliver_names or f.name.endswith(".report.md"):
                shutil.copy2(f, deliver / f.name); dn += 1
            else:  # _adversarial_review.md、_stage_* 等 → 審計
                shutil.copy2(f, audit / f.name); an += 1

    # config reports 成品夾（SR/GRADE 報告 PDF）也入 deliverables——否則漏封存(同 end_run 曾犯之 bug)
    try:
        import re as _re
        cfgp = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        reports_dir = None
        if cfgp.exists():
            txt = cfgp.read_text(encoding="utf-8")
            m = (_re.search(r'analysis:.*?pdf_output_dir\s*:\s*"?([^"\n#]+)', txt, _re.S)
                 or _re.search(r'pdf_output_dir\s*:\s*"?([^"\n#]+)', txt))
            if m and m.group(1).strip():
                reports_dir = Path(m.group(1).strip())
        if reports_dir and reports_dir.exists():
            for f in reports_dir.iterdir():
                if f.is_file() and f.name != ".gitkeep" and not (deliver / f.name).exists():
                    shutil.copy2(f, deliver / f.name); dn += 1
    except Exception:
        pass

    # cache：JSON 入 audit；.txt 視 --with-text
    if CACHE.exists():
        for f in CACHE.glob("*.json"):
            shutil.copy2(f, audit / f.name); an += 1
        if with_text:
            tdir = audit / "extracted_text"
            tdir.mkdir(exist_ok=True)
            for f in CACHE.glob("*.txt"):
                shutil.copy2(f, tdir / f.name); an += 1
        # 其餘 cache 項目（非 .json、非 .txt）與子目錄也要封存——否則 --clear 會無差別刪除未封存者
        # （無聲資料遺失）。.txt 視為版權抽取全文、仍由上方 --with-text 控管（未加旗標＝刻意不存）。
        for f in CACHE.iterdir():
            if f.name == ".gitkeep" or f.suffix.lower() in (".json", ".txt"):
                continue
            if f.is_dir():
                shutil.copytree(f, audit / f.name, dirs_exist_ok=True); an += 1
            else:
                shutil.copy2(f, audit / f.name); an += 1

    has_src = False if no_sources else gen_sources(deliver)

    if clear:
        _clear(CACHE)
        _clear(OUTPUTS)

    src_msg = "未產生（--no-sources）" if no_sources else ("有" if has_src else "無（缺 _corpus.json）")
    print(f"✅ 封存完成 → {run.relative_to(ROOT)}")
    print(f"   deliverables: {dn} 檔　audit: {an} 檔　sources.md: {src_msg}")
    if clear:
        print("   已清空 cache/ 與 outputs/（保留 .gitkeep），可開始下一個分析。")
    else:
        print("   （未清空；如要清出空間給下次分析，加 --clear）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
