# -*- coding: utf-8 -*-
"""EBM_Analysis 工具的「工作根」解析（零相依）。

把 inputs/cache/outputs/runs 這些**執行期資料**導到一個工作夾，而不是腳本所在資料夾——
重點：當本框架以**打包 skill** 安裝執行時，腳本位於唯讀/會被重匯入覆蓋的安裝包資料夾，
若把 run 資料寫在那裡，重匯入 skill 就會連同你的分析快取／報告一起被洗掉。

解析順序（第一個有值者勝出）：
  1) 環境變數 EBM_WORKDIR
  2) 根 config 的 analysis.work_dir（config 路徑：env EBM_CONFIG ＞ <skill_root>/config/settings.yaml
     ＞ <EBM_Analysis>/config/settings.yaml 本地回退——子計畫獨立打包看不到根 config 時用）
  3) 退回 EBM_Analysis 專案資料夾本身（Claude Code 專案模式的原行為，向後相容）

schema/ 等「程式資料」不歸這裡管（仍隨腳本放安裝包）；本模組只管「執行期產出」。
"""
import os

_ANALYSIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # EBM_Analysis
_ROOT = os.path.dirname(_ANALYSIS)                                       # skill root / EBM_Framework


def _config_path():
    env = os.environ.get("EBM_CONFIG")
    if env and os.path.exists(env):
        return env
    # 根 config 優先；找不到再回退子計畫本地 config（子計畫獨立打包成 skill 時）
    for p in (os.path.join(_ROOT, "config", "settings.yaml"),
              os.path.join(_ANALYSIS, "config", "settings.yaml")):
        if os.path.exists(p):
            return p
    return None


def _work_dir_from_config():
    p = _config_path()
    if not p:
        return None
    try:
        section = None
        with open(p, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0].rstrip("\n")
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                k, _, v = line.strip().partition(":")
                if indent == 0:
                    section = k.strip() if v.strip() == "" else None
                elif section == "analysis" and k.strip() == "work_dir":
                    return v.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def work_root():
    """回傳工作根（絕對路徑）。"""
    env = os.environ.get("EBM_WORKDIR")
    if env:
        return env
    cfg = _work_dir_from_config()
    if cfg:
        return cfg
    return _ANALYSIS


def _sub(name, create=True):
    d = os.path.join(work_root(), name)
    if create:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass
    return d


def inputs_dir(create=True):
    return _sub("inputs", create)


def cache_dir(create=True):
    return _sub("cache", create)


def outputs_dir(create=True):
    return _sub("outputs", create)


def runs_dir(create=True):
    return _sub("runs", create)
