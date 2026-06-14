#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consensus-verify / pack_skill.py
================================
安全打包 skill 成 ZIP,供匯入 Claude Desktop。零相依(只用標準庫 zipfile)。

為什麼不用 PowerShell 的 Compress-Archive?
  Windows PowerShell 5.1 的 Compress-Archive 會用「反斜線 \\」當 ZIP 內路徑分隔,
  違反 ZIP 規格(要正斜線 /),匯入時被判「path contains invalid characters」。
  本腳本用 Python zipfile,路徑一律正斜線 /,並排除真值檔(settings.yaml/.env)。

用法
----
  cd <repo>
  python scripts/pack_skill.py
  → 產出 <文件>/EBM_Search_skill.zip,並列出內容物。

輸出位置
--------
  預設放 Windows「文件」已知資料夾(GetFolderPath/MyDocuments,會自動跟隨 OneDrive
  Known-Folder 重導,例如 OneDrive\文件),與 PDF 報告同處、方便匯入 Claude Desktop。
  解析失敗(非 Windows 等)則退回 repo 上層資料夾。要覆寫:設環境變數 SKILL_ZIP_DIR=<絕對路徑>。
  ※ 不寫死含使用者名的路徑,保持 repo 可攜且無個資。

排除:settings.yaml、.env、*.zip、*.pyc、.git/、__pycache__/、底線開頭的暫存檔(_*)。
"""

import os
import sys
import zipfile


def _documents_dir():
    """解析 Windows『文件』已知資料夾(含 OneDrive 重導);失敗回 None。"""
    override = os.environ.get("SKILL_ZIP_DIR")
    if override and os.path.isdir(override):
        return override
    try:
        import winreg  # stdlib;僅 Windows 有
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            raw, _ = winreg.QueryValueEx(k, "Personal")   # 「文件」=Personal,含 OneDrive 重導
        path = os.path.expandvars(raw)                    # 展開 %USERPROFILE% 等
        return path if os.path.isdir(path) else None
    except Exception:
        return None


EX_FILES = {"settings.yaml", ".env", "scimago_quartiles.json"}  # 後者=2MB 分位快取,--build 可重建
EX_DIRS = {".git", "__pycache__", ".venv", "fulltext"}   # fulltext/ = Phase 3 下載輸出(PDF),勿打包
EX_EXT = {".zip", ".pyc", ".pdf"}


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ 的上一層 = repo 根
    name = os.path.basename(repo)
    out_dir = _documents_dir() or os.path.dirname(repo)                 # 預設「文件」;失敗退回 repo 上層
    out = os.path.join(out_dir, "%s_skill.zip" % name)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if os.path.exists(out):
        os.remove(out)
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in EX_DIRS]
            for f in files:
                if f in EX_FILES or os.path.splitext(f)[1].lower() in EX_EXT or f.startswith("_"):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, repo).replace("\\", "/")   # ← 強制正斜線
                z.write(full, rel)
                n += 1

    print("打包 %d 檔 → %s" % (n, out))
    with zipfile.ZipFile(out) as z:
        names = sorted(z.namelist())
        for nm in names:
            print("  ", nm)
        bad = [x for x in names if "\\" in x]
        leaked = [x for x in names if x.endswith("settings.yaml") or x.endswith(".env")]
        print("含反斜線:", bad or "無 OK")
        print("含真值檔(settings.yaml/.env):", leaked or "無 OK")


if __name__ == "__main__":
    main()
