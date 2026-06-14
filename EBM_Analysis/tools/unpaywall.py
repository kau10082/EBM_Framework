# -*- coding: utf-8 -*-
"""
unpaywall.py — DOI → 開放取用(OA)全文 PDF 解析（評讀端薄包裝）
================================================================
重用 EBM_Search 既有 `unpaywall_lookup`，補上「評讀端也能用」這一段：
補全文/quote_verify 在退回 ai_synthesis 之前，先問 Unpaywall 有沒有免費全文 PDF。
（Unpaywall 免金鑰，只要 email；email 取自 config 的 crossref.mailto。）

用法：
  python unpaywall.py 10.1186/s12931-025-03407-2      # 印 OA 狀態＋PDF url
  程式內：from unpaywall import oa_pdf;  url = oa_pdf(doi)   # 回 PDF url 或 ''
"""
import os, sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
# 路徑：本工具 → EBM_Analysis/tools；search 端在 ../../EBM_Search/scripts
_SEARCH = HERE.parents[1] / "EBM_Search" / "scripts"
sys.path.insert(0, str(_SEARCH))
sys.path.insert(0, str(HERE))


def _mailto():
    """email 取自 env CROSSREF_MAILTO ＞ config crossref.mailto（Unpaywall 必填、非秘密）。"""
    m = os.environ.get("CROSSREF_MAILTO")
    if m:
        return m
    import re
    # HERE=EBM_Analysis/tools → parents[1]=EBM_Framework 根；config 在根/config
    for c in (HERE.parents[1] / "config" / "settings.yaml",
              HERE.parents[1] / "config" / "settings.example.yaml"):
        try:
            if c.exists():
                mm = re.search(r'mailto:\s*"?([^"\n]+?)"?\s*(?:#.*)?$',
                               c.read_text(encoding="utf-8"), re.M)
                if mm and "example.com" not in mm.group(1):
                    return mm.group(1).strip()
        except Exception:
            pass
    return "anonymous@example.com"


def lookup(doi, mailto=None):
    """回 Unpaywall dict {is_oa, oa_status, pdf_url, landing_url, host_type}；失敗回 {}。"""
    if not doi:
        return {}
    try:
        from fulltext_fetch import unpaywall_lookup
    except Exception as e:
        return {"_error": "無法載入 unpaywall_lookup: %s" % str(e)[:60]}
    return unpaywall_lookup(doi, mailto or _mailto()) or {}


def oa_pdf(doi, mailto=None):
    """便捷：回開放全文 PDF url（無則 landing_url；都無回 ''）。"""
    d = lookup(doi, mailto)
    return d.get("pdf_url") or d.get("landing_url") or ""


def main():
    if len(sys.argv) < 2:
        print("用法：python unpaywall.py <DOI>"); raise SystemExit(2)
    doi = sys.argv[1]
    d = lookup(doi)
    if d.get("_error"):
        print("❌", d["_error"]); raise SystemExit(1)
    if d.get("is_oa"):
        print("✅ OA（%s）｜PDF: %s" % (d.get("oa_status", "?"), d.get("pdf_url") or d.get("landing_url") or "(無直接 PDF)"))
    else:
        print("⛔ 非開放取用（Unpaywall 查無免費全文）— 此 DOI 宜走人工補 PDF 或 ai_synthesis")


if __name__ == "__main__":
    main()
