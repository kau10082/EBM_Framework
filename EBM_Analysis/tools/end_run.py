# -*- coding: utf-8 -*-
"""
end_run.py — 「EBM 分析結案」一鍵整合：封存這輪 → 清空所有工作區，下一輪乾淨開始。
==============================================================================
動作（依序）：
  1) 封存 runs/<YYYY-MM>_<slug>/：
       audit/        ← cache/*.json（_corpus、*.p1-p3、_synthesis 等審計軌跡）
       deliverables/ ← outputs/* ＋ reports/*（FINAL_REPORT、SR/GRADE 報告 PDF/MD）
       handoff/      ← 交接資料夾的中繼檔（_corpus_seed.json、_search_report.json、_需補全文清單.txt）
       MANIFEST.txt  ← 清掉了哪些檔（含手工 PDF 檔名，供日後追溯）
  2) 清空：cache/、outputs/、inputs/（保留 .gitkeep）、reports/、交接全文資料夾（整個刪，含手工/下載 PDF）、run_state.json
封存範圍：cache/outputs/reports 全檔複製；inputs/與交接夾的版權 PDF 依 --keep-pdfs
（未 keep 時只在 MANIFEST 記檔名不複製）。runs/ 為本機、gitignored。

用法：python tools/end_run.py [--keep-pdfs] [--dry-run]
  --keep-pdfs  封存時連 inputs/交接夾的手工/下載 PDF 一起複製進 runs/（預設只記檔名不複製）
  --dry-run    只列出會做什麼、不複製不刪除
"""
import sys, os, shutil
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workdir
try:
    import run_state
    ST = run_state.load()
except Exception as _e:
    sys.stderr.write("⚠ run_state.json 讀取失敗（%s）：slug/日期將用預設值，請確認封存目錄名\n" % str(_e)[:60])
    ST = {}

def _entries(p):
    # 回傳所有項目（含子目錄）——子目錄也要被封存，否則 clear_dir 會 rmtree 未封存的子目錄＝資料遺失
    p = Path(p)
    return list(p.iterdir()) if p.is_dir() else []

def main():
    keep_pdfs = "--keep-pdfs" in sys.argv
    dry = "--dry-run" in sys.argv
    slug = ST.get("slug") or "run"
    date = (ST.get("search_date") or "")[:7] or "unknown"
    CACHE = Path(workdir.cache_dir()); OUTPUTS = Path(workdir.outputs_dir()); INPUTS = Path(workdir.inputs_dir())
    reports = ST.get("paths", {}).get("reports_dir")
    if not reports:
        # 防呆：run_state 未記 reports_dir 時，從 config 解析（否則 SR/GRADE 成品 PDF 漏封存——實測曾漏 SR 報告 PDF）
        try:
            import re as _re
            cfgp = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
            if cfgp.exists():
                txt = cfgp.read_text(encoding="utf-8")
                m = _re.search(r'analysis:.*?pdf_output_dir\s*:\s*"?([^"\n#]+)', txt, _re.S)
                if m and m.group(1).strip():
                    reports = m.group(1).strip()
                    print(f"  （reports_dir 未在 run_state，已從 config 的 analysis 區解析：{reports}）")
                else:
                    # 不得退而抓「檔案中第一個 pdf_output_dir」——那多半是 report.pdf_output_dir
                    # （EBM_Search 檢索報告夾），清了會把其他主題的成品一併搬走/刪掉。
                    print("  （config 無 analysis.pdf_output_dir：本輪不封存/不清 reports；"
                          "少封存可人工補，抓錯夾會清到別的主題成品）")
        except Exception:
            pass
    ftd = ST.get("paths", {}).get("fulltext_dir")
    arch = Path(workdir.runs_dir()) / f"{date}_{slug}"
    # 碰撞防護：同名封存已存在（同主題同月重做、或 run_state 缺損落到預設 unknown_run）→ 加序號，
    # 絕不覆蓋既有封存——MANIFEST 是「未複製即刪的版權 PDF」唯一存證，覆寫＝紀錄永久遺失。
    if arch.exists():
        i = 2
        while (Path(workdir.runs_dir()) / f"{date}_{slug}_{i}").exists():
            i += 1
        arch = Path(workdir.runs_dir()) / f"{date}_{slug}_{i}"
        print(f"  （封存目錄已存在，本輪改存：{arch.name}）")
    print(f"== EBM 分析結案：{slug}（{date}）{'［DRY-RUN］' if dry else ''} ==")
    print(f"封存到：{arch}")

    manifest = [f"# 結案封存 {slug} {date}", ""]
    def archive(srcdir, sub, exts=None, label=""):
        n = 0
        for f in _entries(srcdir):
            if f.is_dir():   # 子目錄整棵封存（clear_dir 之後會 rmtree 子目錄，未封存即刪＝資料遺失）
                if not dry:
                    shutil.copytree(f, arch / sub / f.name, dirs_exist_ok=True)
                n += 1; continue
            if exts and f.suffix.lower() not in exts:
                if f.suffix.lower() == ".pdf" and not keep_pdfs:
                    manifest.append(f"[未複製·已刪] {label}/{f.name}（{f.stat().st_size//1024} KB）"); continue
            d = arch / sub
            if not dry:
                d.mkdir(parents=True, exist_ok=True); shutil.copy2(f, d / f.name)
            n += 1
        return n

    # 1) 封存
    a1 = archive(CACHE, "audit", label="cache")
    a2 = archive(OUTPUTS, "deliverables", label="outputs")
    a3 = archive(reports, "deliverables", label="reports") if reports else 0
    # inputs/ 的全文（使用者手工提供）也要封存——否則 inputs 只被清空、檔案不留存（曾漏）。
    # 明確規則（不走 archive() 的 exts 旁路，避免日後白名單化時非 PDF 檔被 clear_dir 清空卻沒封存）：
    #   ★ 非 PDF 一律封存進 sources/；PDF 僅 --keep-pdfs 時複製，否則只在 MANIFEST 記檔名（版權 PDF 同 reports 處理）。
    #   故「刪除卻未封存」的唯一情形＝版權 PDF 且未 --keep-pdfs（刻意、且已記檔名），不會誤刪其他型別。
    a5 = 0
    for f in _entries(INPUTS):
        if f.is_dir():   # 子目錄整棵封存
            if not dry:
                shutil.copytree(f, arch / "sources" / f.name, dirs_exist_ok=True)
            a5 += 1; continue
        if f.suffix.lower() == ".pdf" and not keep_pdfs:
            manifest.append(f"[未複製·已刪] sources/{f.name}（{f.stat().st_size//1024} KB）"); continue
        if not dry:
            (arch / "sources").mkdir(parents=True, exist_ok=True); shutil.copy2(f, arch / "sources" / f.name)
        a5 += 1
    # 交接資料夾：只存中繼檔（json/txt/md），PDF 依 --keep-pdfs
    a4 = 0
    if ftd:
        for f in _entries(ftd):
            if f.is_dir():   # 子目錄整棵封存
                if not dry:
                    shutil.copytree(f, arch / "handoff" / f.name, dirs_exist_ok=True)
                a4 += 1; continue
            if f.suffix.lower() == ".pdf" and not keep_pdfs:   # 版權 PDF 未 keep：只記檔名（同 reports/inputs）
                manifest.append(f"[未複製·已刪] handoff/{f.name}（{f.stat().st_size//1024} KB）"); continue
            # 其餘一律封存（含非白名單的 .csv/.png/.docx 等）——杜絕「沒封存卻被清空」的無聲遺失
            if not dry:
                (arch / "handoff").mkdir(parents=True, exist_ok=True); shutil.copy2(f, arch / "handoff" / f.name)
            a4 += 1
    if not dry:
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "MANIFEST.txt").write_text("\n".join(manifest), encoding="utf-8")
    print(f"  封存：audit {a1}｜deliverables {a2+a3}｜sources {a5}｜handoff {a4}")

    # 2) 清空
    clear_fails = []   # 收集刪除失敗項（OneDrive 暫鎖或真實權限錯誤）——結尾統一可見回報，不靜默吞
    def clear_dir(p, keep_gitkeep=True):
        if not p or not Path(p).is_dir(): return 0
        n = 0
        for f in Path(p).iterdir():
            if keep_gitkeep and f.name == ".gitkeep": continue
            if not dry:
                try:
                    (shutil.rmtree(f) if f.is_dir() else f.unlink())
                except Exception as e:
                    # 逐項跳過、別讓單一鎖檔中止整個清空（資料已先封存，安全）；但記錄下來結尾回報
                    clear_fails.append((str(f), type(e).__name__)); continue
            n += 1
        return n
    c1 = clear_dir(CACHE); c2 = clear_dir(OUTPUTS); c3 = clear_dir(INPUTS); c4 = clear_dir(reports, keep_gitkeep=False)
    # run_state 先重設（與資料夾刪除無關，避免後者被鎖時連帶跳過）
    rs = Path(workdir.work_root()) / "run_state.json"
    if rs.exists() and not dry:
        try: rs.unlink()
        except Exception as e: clear_fails.append((str(rs), type(e).__name__))   # 殘留污染下一輪，不得靜默
    # 交接全文資料夾：先清檔，再盡力刪空夾（OneDrive 可能鎖住空夾→忽略，空夾無害）
    c5 = 0
    if ftd and Path(ftd).is_dir():
        c5 = len(list(Path(ftd).iterdir()))
        if not dry:
            for f in Path(ftd).iterdir():
                try: (shutil.rmtree(f) if f.is_dir() else f.unlink())
                except Exception as e: clear_fails.append((str(f), type(e).__name__))
            try: os.rmdir(ftd)
            except Exception: print("  （交接夾內容已清空；空夾被 OneDrive 暫鎖、留著無害）")
    print(f"  清空：cache {c1}｜outputs {c2}｜inputs {c3}｜reports {c4}｜交接夾 {c5}（整夾刪）｜run_state 重設")
    # 清空失敗一律可見回報（區分 OneDrive 暫鎖空夾 vs 真實刪除失敗，避免殘留靜默污染下一輪）
    if clear_fails:
        locks = sum(1 for _, et in clear_fails if et in ("PermissionError", "OSError"))
        print(f"  ⚠️ 清空未完成 {len(clear_fails)} 項（其中 {locks} 項疑似 OneDrive 暫鎖）。"
              "若非空夾/暫鎖，請手動確認並清除，以免污染下一輪：")
        for path, et in clear_fails[:12]:
            base = os.path.basename(path.rstrip("/" + chr(92))) or path   # 先算好再進 f-string（Python <=3.11 禁止 f-string 運算式含反斜線，曾整支 SyntaxError）
            print(f"       - {base}（{et}）")
    if clear_fails and not dry:
        # MANIFEST 補記：上方「[未複製·已刪]」是在刪除前寫的；實際刪除失敗者在此校正，避免存證與事實不符
        try:
            with open(arch / "MANIFEST.txt", "a", encoding="utf-8") as mf:
                mf.write("\n\n## 清空結果校正（下列項目刪除失敗、實際仍在原處）\n")
                for path, et in clear_fails:
                    mf.write(f"[刪除失敗·仍在原處] {path}（{et}）\n")
        except Exception:
            print("  ⚠️ MANIFEST 校正寫入失敗——請人工核對封存紀錄與實際檔案")
    print("✅ 結案完成，下一輪可乾淨開始。" if not dry else "（DRY-RUN：未實際變更）")
    if clear_fails and not dry:
        print("   （注意：上方有未清除項，非全乾淨——請依提示處理。）")
    print(f"   這輪記錄保存在：{arch}")

if __name__ == "__main__":
    main()
