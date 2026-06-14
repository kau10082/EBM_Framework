#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EBM_Framework / pack_framework.py
=================================
把整個 EBM_Framework 安全打包成單一 skill ZIP（供匯入 Claude Desktop）。
零相依（只用標準庫 zipfile）。ZIP 內路徑一律正斜線（Compress-Archive 會用反斜線致匯入失敗）。

模式（預設＝私用版）：
- `python pack_framework.py`              → **私用版**（含 config/settings.yaml 真值，自用方便）
                                             檔名 EBM_Framework_skill_private.zip ⚠️ 勿外流
- `python pack_framework.py --shareable`  → 可分享版（排除真值，只含 *.example.yaml）
                                             檔名 EBM_Framework_skill.zip

兩版皆排除（版權／執行產物，絕不進 ZIP）：
- 版權／PHI：EBM_Analysis/{inputs,cache,outputs} 內容（保留 .gitkeep）、runs/、fulltext/、所有 *.pdf
- 雜項：.git、__pycache__、.venv、.claude（Claude-Code 專案啟動器，打包版用根 SKILL.md）、
  scimago_quartiles.json（2MB 快取）、node_modules、底線開頭暫存檔（_*）、*.zip、*.pyc
- 可分享版另排除：settings.yaml、.env

輸出位置：config/settings.yaml 的 packaging.output_dir；否則 Windows『文件』\\EBM_Framework\\packages；
         再否則 repo 上層。環境變數 SKILL_ZIP_DIR 可覆寫。
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))

EX_DIRS = {".git", "__pycache__", ".venv", "venv", ".claude", "runs", "fulltext", "node_modules"}
EX_FILES = {"settings.yaml", ".env", "scimago_quartiles.json"}
EX_EXT = {".zip", ".pyc", ".pdf"}
# 這些子資料夾只保留 .gitkeep（版權全文／衍生內容／PHI 不打包）
KEEPGITKEEP_PREFIXES = ("EBM_Analysis/inputs/", "EBM_Analysis/cache/", "EBM_Analysis/outputs/")


def _packaging_dir():
    override = os.environ.get("SKILL_ZIP_DIR")
    if override and os.path.isdir(override):
        return override
    # 讀 config/settings.yaml 的 packaging.output_dir（極簡解析）
    cfg = os.path.join(ROOT, "config", "settings.yaml")
    try:
        section = None
        with open(cfg, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0].rstrip("\n")
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                k, _, v = line.strip().partition(":")
                if indent == 0:
                    section = k.strip() if v.strip() == "" else None
                elif section == "packaging" and k.strip() == "output_dir":
                    val = v.strip().strip('"').strip("'")
                    if val and os.path.isdir(os.path.dirname(val) or val):
                        return val
    except OSError:
        pass
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            raw, _ = winreg.QueryValueEx(k, "Personal")
        docs = os.path.expandvars(raw)
        if os.path.isdir(docs):
            return os.path.join(docs, "EBM_Framework", "packages")
    except Exception:
        pass
    return os.path.dirname(ROOT)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    argv = sys.argv[1:] if argv is None else argv
    # 預設＝私用版（含 config/settings.yaml 真值，自用方便）。要產「可分享版」（排除真值）加 --shareable 或 --no-secrets。
    with_secrets = "--shareable" not in argv and "--no-secrets" not in argv

    ex_files = set(EX_FILES)
    if with_secrets:
        ex_files.discard("settings.yaml")     # 允許含真值設定
        ex_files.discard(".env")

    out_dir = _packaging_dir()
    os.makedirs(out_dir, exist_ok=True)
    out_name = "EBM_Framework_skill_private.zip" if with_secrets else "EBM_Framework_skill.zip"
    out = os.path.join(out_dir, out_name)
    if os.path.exists(out):
        os.remove(out)

    n, skipped = 0, 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in EX_DIRS and not d.startswith("_")]
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                # 排除規則（版權 PDF／git／快取一律排除；真值設定僅 --with-secrets 才含）
                if f in ex_files or os.path.splitext(f)[1].lower() in EX_EXT or f.startswith("_"):
                    skipped += 1
                    continue
                if any(rel.startswith(p) for p in KEEPGITKEEP_PREFIXES) and f != ".gitkeep":
                    skipped += 1
                    continue
                z.write(full, rel)
                n += 1

    mode = "私用版(含真值)" if with_secrets else "可分享版"
    print("打包 %d 檔（排除 %d）[%s] → %s" % (n, skipped, mode, out))
    with zipfile.ZipFile(out) as z:
        names = sorted(z.namelist())
        bad = [x for x in names if "\\" in x]
        copyright_leak = [x for x in names if x.lower().endswith(".pdf") or x.startswith("EBM_Analysis/runs/")]
        print("ZIP 內檔數:", len(names))
        print("根 SKILL.md 存在:", "OK" if "SKILL.md" in names else "!!! 缺")
        print("版權/PDF/runs 外洩:", copyright_leak or "無 OK")
        print("含反斜線路徑:", bad or "無 OK")
        if with_secrets:
            has_cfg = "config/settings.yaml" in names
            print("含真值 config/settings.yaml:", "有 ⚠️ 私用版，勿外流／勿上傳公開處" if has_cfg else "!!! 未含")
        else:
            secret_leak = [x for x in names if x.endswith("settings.yaml") or x.endswith(".env")]
            print("機敏外洩(settings.yaml/.env):", secret_leak or "無 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
