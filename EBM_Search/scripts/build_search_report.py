# -*- coding: utf-8 -*-
"""
build_search_report.py — 檢索（SR）報告 PDF 正規產生器（5 段固定版型）
======================================================================================
讀「資料 JSON（_search_report.json）」渲染檢索報告 PDF，**不硬編題目內容**。

★ 版型＝使用者定版的「5 段核心」（2026-06-24 定版，取代舊 PRISMA-流程圖版型；勿再用舊版或自創）：
  1. 檢索基本參數（Search Parameters）：PICO 簡述、檢索日期(精確到日)、資料庫/來源清單、限制條件(誠實交代 RCT/SR filter、語言、年份)。
  2. 具體檢索策略/完整字串（Exact Search Strategy）：各腿**逐字保留**的布林查詢字串(MECIR 可重製性)。
  3. PRISMA 文獻篩選流程數據（Selection Process / Flow）：每階段 起始數→排除(原因/數)→剩餘。
  4. 最終納入的證據清單（Included Studies）：核心 RCT/重要 MA；固定欄位＝
     **作者／年份／文獻類型 ｜ 標題 ｜ DOI ｜ PMID ｜ PubMed/Crossref 驗證**。**背景不列表**(只放核心)。
  5. 目前仍在進行中的 Trial：固定欄位＝**登錄號(NCT) ｜ 標題**(可選 狀態)。
內建字形淨化（msjh 缺字形→等義字，防磚塊）。

用法：
  python build_search_report.py --in <…>/_search_report.json [--out <dir>] [--name <file.pdf>]
資料 JSON 結構見本檔末 SCHEMA_HINT 或 references/search_report_schema.json。
"""
import os, sys, json, argparse, re
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                LongTable, Table, TableStyle, CondPageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# ── 字形淨化（msjh 缺字形 → 等義有字形）──
_SAFE_TR = str.maketrans({'≈': '≒', '≥': '≧', '≤': '≦', '−': '-', '◯': '○',
                          '↔': '／', '⇔': '／', '⇄': '／', '⟷': '／', '▸': '•', '►': '•',
                          '™': '', '✅': '○', '✓': '○', '✔': '○', '∧': '且', '≠': '不等於',
                          '⟶': '→'})
def safe(t): return (str(t) if t is not None else '').translate(_SAFE_TR)

def _font():
    cand = [(r"C:/Windows/Fonts/msjh.ttc", 0), (r"C:/Windows/Fonts/msjh.ttf", None),
            (r"C:/Windows/Fonts/mingliu.ttc", 0),
            ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
            ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
            ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
            ("/System/Library/Fonts/PingFang.ttc", 0)]
    try:
        import yaml
        base = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        if base.exists():
            cf = ((yaml.safe_load(base.read_text(encoding="utf-8")) or {}).get("analysis") or {}).get("cjk_font")
            if cf: cand.insert(0, (cf, 0 if str(cf).lower().endswith(".ttc") else None))
    except Exception:
        pass
    for p, idx in cand:
        if p and os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("CJK", p, subfontIndex=idx) if idx is not None else TTFont("CJK", p))
                return
            except Exception:
                continue
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    try:
        pdfmetrics.registerFontFamily("CJK", normal="STSong-Light")
        from reportlab.lib.fonts import addMapping
        addMapping("CJK", 0, 0, "STSong-Light")
    except Exception:
        pass

def _resolve_in(arg):
    if arg: return arg
    try:
        rs = Path(__file__).resolve().parents[1] / "EBM_Analysis" / "tools"
        sys.path.insert(0, str(rs)); import run_state
        st = run_state.load(); ftd = st.get("paths", {}).get("fulltext_dir")
        cand = st.get("paths", {}).get("search_report_data") or (os.path.join(ftd, "_search_report.json") if ftd else None)
        if cand and os.path.exists(cand): return cand
    except Exception: pass
    raise SystemExit("找不到資料 JSON：請用 --in 指定 _search_report.json")

def _out_dir(arg):
    if arg: return arg
    cfg = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    if cfg.exists():
        # 取值容許『單引號／雙引號／無引號』＋行內註解(# …)；單引號為 Windows 路徑常用寫法。
        # 舊版只剝雙引號 → 單引號設定值會回傳 'C:\…'(含引號)→ makedirs 失敗(2026-06 使用者糾正)。
        m = re.search(r'''pdf_output_dir\s*:\s*['"]?([^'"\n#]+)['"]?''', cfg.read_text(encoding="utf-8"))
        if m and m.group(1).strip(): return m.group(1).strip()
    return os.path.join(os.path.expanduser("~"), "Documents")

def build(data, out_pdf):
    """渲染 5 段固定版型。data 結構見 SCHEMA_HINT / references/search_report_schema.json。"""
    _font()
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="CJK", fontSize=15, spaceAfter=4)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="CJK", fontSize=12,
                        textColor=colors.HexColor("#0b5394"), spaceBefore=10, spaceAfter=4)
    P  = ParagraphStyle("P", parent=ss["Normal"], fontName="CJK", fontSize=9, leading=12.5)
    SMALL = ParagraphStyle("SM", parent=ss["Normal"], fontName="CJK", fontSize=7.6, leading=10, textColor=colors.HexColor("#444"))
    MONO = ParagraphStyle("MONO", parent=ss["Normal"], fontName="CJK", fontSize=8, leading=11,
                          backColor=colors.HexColor("#f3f5f8"), borderPadding=3)
    CELL = ParagraphStyle("CELL", parent=ss["Normal"], fontName="CJK", fontSize=7.4, leading=9)
    def cc(t, s=CELL): return Paragraph(safe(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), s)
    def hstyle(bg):
        return TableStyle([("FONTNAME", (0, 0), (-1, -1), "CJK"), ("FONTSIZE", (0, 0), (-1, -1), 7.4),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(bg)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fa")])])

    E = []
    E.append(Paragraph(safe(data.get("title", "EBM Phase 1 系統性檢索報告")), H1))
    if data.get("topic"): E.append(Paragraph(safe(data["topic"]), P))

    # 1. 檢索基本參數
    E.append(Paragraph("1. 檢索基本參數（Search Parameters）", H2))
    pm = data.get("params", {})
    if pm.get("pico"):      E.append(Paragraph("<b>PICO 簡述：</b>" + safe(pm["pico"]), P))
    E.append(Paragraph("<b>檢索日期（Date of Search）：</b>" + safe(data.get("search_date", "")), P))
    if pm.get("databases"): E.append(Paragraph("<b>資料庫／來源：</b>" + safe("、".join(pm["databases"])), P))
    if pm.get("limits"):    E.append(Paragraph("<b>限制條件：</b>" + safe(pm["limits"]), P))

    # 2. 具體檢索策略／完整字串（逐字）
    E.append(Paragraph("2. 具體檢索策略／完整字串（Exact Search Strategy，逐字保留）", H2))
    for s in data.get("search_strings", []):
        E.append(Paragraph("<b>%s：</b>" % safe(s.get("leg", "")), P))
        E.append(Paragraph(safe(s.get("query", "") or "—"), MONO)); E.append(Spacer(1, 3))

    # 3. PRISMA 流程數據
    E.append(Paragraph("3. PRISMA 文獻篩選流程數據（Selection Process / Flow）", H2))
    fh = ["階段", "起始", "排除（原因／數）", "剩餘"]
    frows = [[cc(h, P) for h in fh]]
    for st in data.get("flow", []):
        frows.append([cc(st.get("stage", "")), cc(st.get("start", "")), cc(st.get("excluded", "")), cc(st.get("remain", ""))])
    t = LongTable(frows, colWidths=[120 * mm, 22 * mm, 80 * mm, 50 * mm], repeatRows=1); t.setStyle(hstyle("#0b5394")); E.append(t)
    if data.get("flow_reconcile"): E.append(Paragraph(safe(data["flow_reconcile"]), SMALL))

    # 4. 最終納入的證據清單（核心；固定欄位）
    E.append(CondPageBreak(40 * mm))
    E.append(Paragraph("4. 最終納入的證據清單（Included Studies；只列核心，背景不列表）", H2))
    ih = ["作者／年份／文獻類型", "標題", "DOI", "PMID", "PubMed/Crossref 驗證"]
    irows = [[cc(h, P) for h in ih]]
    for it in data.get("included", []):
        irows.append([cc(it.get("byline", "")), cc(it.get("title", "")), cc(it.get("doi", "") or "—"),
                      cc(it.get("pmid", "") or "—"), cc(it.get("verify", "") or "—")])
    t = LongTable(irows, colWidths=[40 * mm, 122 * mm, 52 * mm, 22 * mm, 36 * mm], repeatRows=1); t.setStyle(hstyle("#38761d")); E.append(t)
    if data.get("included_note"): E.append(Paragraph(safe(data["included_note"]), SMALL))

    # 5. 進行中試驗
    E.append(CondPageBreak(36 * mm))
    E.append(Paragraph("5. 目前仍在進行中的 Trial（ClinicalTrials.gov；供完整度查核，不計入證據）", H2))
    ong = data.get("ongoing", [])
    if ong:
        has_status = any(o.get("status") for o in ong)
        if has_status:
            orows = [[cc("登錄號", P), cc("標題", P), cc("狀態", P)]] + [[cc(o.get("nct", "")), cc(o.get("title", "")), cc(o.get("status", ""))] for o in ong]
            t = LongTable(orows, colWidths=[34 * mm, 180 * mm, 46 * mm], repeatRows=1)
        else:
            orows = [[cc("登錄號", P), cc("標題", P)]] + [[cc(o.get("nct", "")), cc(o.get("title", ""))] for o in ong]
            t = LongTable(orows, colWidths=[34 * mm, 226 * mm], repeatRows=1)
        t.setStyle(hstyle("#b45f06")); E.append(t)
    else:
        E.append(Paragraph(safe(data.get("ongoing_note", "（無『進行中／未發表』狀態之試驗。）")), CELL))

    doc = BaseDocTemplate(out_pdf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                          topMargin=12 * mm, bottomMargin=11 * mm, title=data.get("title", "檢索報告"))
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    sd = data.get("search_date", "")
    def footer(cv, d):
        cv.setFont("CJK", 7); cv.setFillColor(colors.grey)
        cv.drawRightString(doc.leftMargin + doc.width, 6 * mm, "EBM_Framework Phase 1 檢索報告 · %s · p.%d" % (sd, d.page))
    doc.addPageTemplates([PageTemplate(id="n", frames=[frame], onPage=footer)])
    doc.build(E)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile"); ap.add_argument("--out"); ap.add_argument("--name")
    a = ap.parse_args()
    src = _resolve_in(a.infile)
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    out_dir = _out_dir(a.out); os.makedirs(out_dir, exist_ok=True)
    name = a.name or (re.sub(r'[^\w\-]+', '_', data.get("topic", "search")) + f'_SR_report_{data.get("search_date","")}.pdf')
    if not name.lower().endswith(".pdf"): name += ".pdf"   # --name 未帶副檔名時補上(2026-06 使用者糾正：曾產出無副檔名檔)
    out_pdf = os.path.join(out_dir, name)
    build(data, out_pdf)
    # 把 pdf_path 登記回 _search_report.json，供 gate_guard『Phase1 PDF 實體產出』找得到
    # (舊版渲染後未回寫→守門報『_search_report.json 無 pdf_path』；2026-06 使用者糾正)
    try:
        data["pdf_path"] = out_pdf
        Path(src).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    print("WROTE:", out_pdf, "|", os.path.getsize(out_pdf), "bytes")

# ── SCHEMA_HINT（_search_report.json，5 段固定版型）─────────────────────────────
# {
#   "title": "EBM Phase 1 系統性檢索報告",
#   "topic": "Benralizumab vs Mepolizumab in severe eosinophilic asthma",
#   "search_date": "2026-06-24",
#   "params": {"pico": "...", "databases": ["PubMed", "OpenAlex", ...], "limits": "未套用 RCT/SR filter；無語言年份限制"},
#   "search_strings": [{"leg": "PubMed", "query": "(benralizumab OR ...) AND (mepolizumab OR ...) AND asthma"}, ...],
#   "flow": [{"stage": "②b 高敏初篩", "start": "1310", "excluded": "剔除離題 107", "remain": "1203"}, ...],
#   "flow_reconcile": "核心 26 + 背景 935 + 待評估 21 = 982 ...",
#   "included": [{"byline": "Akenroye 2022 / NMA", "title": "...", "doi": "...", "pmid": "...", "verify": "VERIFIED (PubMed+Crossref)"}, ...],
#   "included_note": "...",
#   "ongoing": [{"nct": "NCT...", "title": "...", "status": "RECRUITING"}, ...]
# }

if __name__ == "__main__":
    main()
