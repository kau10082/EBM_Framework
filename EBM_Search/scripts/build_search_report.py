# -*- coding: utf-8 -*-
"""
build_search_report.py — 檢索（SR）報告 PDF 正規產生器（與 GRADE 端 _build_pdf.py 對稱）
======================================================================================
讀「資料 JSON（_search_report.json）」渲染檢索篩選報告 PDF，**不硬編題目內容**。
版型＝標準範本：左 PRISMA 流程圖＋右逐階段說明、納入研究分組表、進行中試驗、背景、
APA、檢索原則（四軸＋必含軸）、方法學註記。內建字形淨化（msjh 缺字形→等義字，防磚塊）。

用法：
  python build_search_report.py --in <…>/_search_report.json [--out <dir>] [--name <file.pdf>]
  不給 --in 時，依 run_state.json 的 paths.search_report_data 或 fulltext_dir/_search_report.json 找。
資料 JSON 結構見本檔末 SCHEMA_HINT 或 references/search_report_schema.json。
"""
import os, sys, json, argparse, re
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# ── 字形淨化（msjh 缺字形 → 等義有字形；雙向箭頭/三角項目符全缺）──
_SAFE_TR = str.maketrans({'≈': '≒', '≥': '≧', '≤': '≦', '−': '-', '◯': '○',
                          '↔': '／', '⇔': '／', '⇄': '／', '⟷': '／', '▸': '•', '►': '•'})
def safe(t): return (t or '').translate(_SAFE_TR)

def _font():
    for p in (r"C:/Windows/Fonts/msjh.ttc", r"C:/Windows/Fonts/msjh.ttf"):
        if os.path.exists(p):
            try: pdfmetrics.registerFont(TTFont("CJK", p, subfontIndex=0)); return
            except Exception: pdfmetrics.registerFont(TTFont("CJK", p)); return
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

def _resolve_in(arg):
    if arg: return arg
    # 試 run_state
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
    # config report.pdf_output_dir
    cfg = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    if cfg.exists():
        m = re.search(r'pdf_output_dir\s*:\s*"?([^"\n]+)"?', cfg.read_text(encoding="utf-8"))
        if m and m.group(1).strip(): return m.group(1).strip()
    return os.path.join(os.path.expanduser("~"), "Documents")

def build(data, out_pdf):
    _font()
    ss = getSampleStyleSheet()
    def st(size, lead, color=colors.black, space=4, align=0):
        return ParagraphStyle(f"s{size}{align}", parent=ss["Normal"], fontName="CJK",
                              fontSize=size, leading=lead, textColor=color, spaceAfter=space, alignment=align)
    H1, H2 = st(15, 19, space=6), st(12, 16, colors.HexColor("#0b5394"), 5)
    BODY, SMALL, CELL = st(9, 13), st(8, 11, colors.HexColor("#444444")), st(8, 10.5)
    def P(t, s=BODY): return Paragraph(safe(t), s)
    FBOX = ParagraphStyle("FBOX", parent=ss["Normal"], fontName="CJK", fontSize=7, leading=8.6, textColor=colors.white, alignment=1)
    FANN = ParagraphStyle("FANN", parent=ss["Normal"], fontName="CJK", fontSize=6, leading=7.2, textColor=colors.HexColor("#666"), alignment=1)
    FARR = ParagraphStyle("FARR", parent=ss["Normal"], fontName="CJK", fontSize=6.5, leading=7, textColor=colors.HexColor("#0b5394"), alignment=1)
    BOXW = 92 * mm
    def fbox(txt, color="#0b5394", annot=None, last=False):
        items = []
        tb = Table([[Paragraph(safe(txt), FBOX)]], colWidths=[BOXW])
        tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
        items.append(tb)
        if annot: items.append(Paragraph(safe(annot), FANN))
        if not last: items.append(Paragraph("▼", FARR))
        return items
    def hdr_style(bg):
        return [("FONTNAME", (0, 0), (-1, -1), "CJK"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(bg)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]

    E = []
    E.append(P(data["title"], H1))
    E.append(P(f'EBM_Framework SR 模式｜檢索日期 {data.get("search_date","")}｜題目：{data.get("topic","")}', SMALL))
    E.append(P(data.get("method_summary", ""), BODY)); E.append(Spacer(1, 4))

    # 一、流程（左流程圖 + 右說明）
    E.append(P("一、檢索與篩選流程（PRISMA 2020）── 左：流程圖；右：逐階段說明（並行對照）", H2))
    flow = []
    for s in data.get("funnel", []):
        last = s is data["funnel"][-1]
        flow += fbox(f'<b>{s["step"]}</b><br/>{s.get("change","")}　｜　尚餘 <b>{s.get("remain","")}</b> 篇'
                     if s.get("remain") else f'<b>{s["step"]}</b><br/>{s.get("change","")}',
                     color=s.get("color", "#0b5394"), annot=s.get("annot"), last=last)
    nrows = [[P("<b>階段</b>", CELL), P("<b>說明（為人閱讀）</b>", CELL)]] + [[P(a, CELL), P(b, CELL)] for a, b in data.get("narrative", [])]
    narrT = Table(nrows, colWidths=[30 * mm, 142 * mm], repeatRows=1)
    narrT.setStyle(TableStyle(hdr_style("#0b5394") + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fa")])]))
    two = Table([[flow, narrT]], colWidths=[98 * mm, 174 * mm])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (1, 0), (-1, -1), 0)]))
    E.append(two); E.append(Spacer(1, 3))
    if data.get("funnel_closure"): E.append(P(data["funnel_closure"], SMALL))
    E.append(Spacer(1, 4))

    # 二、核心證據表（以 Study 分組）
    E.append(P("二、核心證據表：納入原始研究（以 Study 為單位；含全文狀態與交叉檢核）", H2))
    rows = [[P("<b>研究（期別/登錄）</b>", CELL), P("<b>報告（標題簡述／期刊年）</b>", CELL), P("<b>DOI</b>", CELL), P("<b>全文狀態</b>", CELL), P("<b>交叉檢核</b>", CELL)]]
    spans = []; r = 1
    for grp in data.get("studies", []):
        reps = grp["reports"]; start = r
        for i, (title, doi, ft, xref) in enumerate(reps):
            c0 = P(grp["study"].replace("\n", "<br/>"), CELL) if i == 0 else P("", CELL)
            rows.append([c0, P(title, CELL), P(doi, CELL), P(ft, CELL), P(xref, CELL)]); r += 1
        if len(reps) > 1: spans.append(("SPAN", (0, start), (0, start + len(reps) - 1)))
    t2 = Table(rows, colWidths=[34 * mm, 150 * mm, 52 * mm, 24 * mm, 14 * mm], repeatRows=1)
    t2.setStyle(TableStyle(hdr_style("#0b5394") + [("VALIGN", (0, 0), (-1, -1), "MIDDLE")] + spans))
    E.append(t2)
    if data.get("fulltext_legend"): E.append(P(data["fulltext_legend"], SMALL))
    E.append(Spacer(1, 4))

    # 二之二、進行中試驗
    if data.get("ongoing_trials"):
        E.append(P("二之二、進行中試驗（ClinicalTrials.gov；不計入證據，供完整度查核）", H2))
        orows = [[P("<b>登錄號</b>", CELL), P("<b>內容（藥物／類型）</b>", CELL), P("<b>狀態</b>", CELL)]] + [[P(a, CELL), P(b, CELL), P(c, CELL)] for a, b, c in data["ongoing_trials"]]
        t2b = Table(orows, colWidths=[34 * mm, 180 * mm, 60 * mm], repeatRows=1)
        t2b.setStyle(TableStyle(hdr_style("#b45f06") + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fcf0e6")]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        E.append(t2b)
        if data.get("ongoing_note"): E.append(P(data["ongoing_note"], SMALL))
        E.append(Spacer(1, 4))

    # 三、背景
    if data.get("background"):
        E.append(P("三、背景／對照參考（不計入納入 N；供脈絡）", H2))
        b = [[P("<b>背景文獻（標題／來源）</b>", CELL), P("<b>DOI</b>", CELL), P("<b>型態</b>", CELL), P("<b>全文狀態</b>", CELL)]] + [[P(t, CELL), P(d, CELL), P(ty, CELL), P(fs, CELL)] for t, d, ty, fs in data["background"]]
        t3 = Table(b, colWidths=[150 * mm, 52 * mm, 30 * mm, 42 * mm], repeatRows=1)
        t3.setStyle(TableStyle(hdr_style("#38761d") + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef7ea")]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        E.append(t3)
        if data.get("background_note"): E.append(P(data["background_note"], SMALL))
        E.append(Spacer(1, 4))

    # 四、APA
    if data.get("apa"):
        E.append(P("四、完整參考文獻（APA，納入報告）", H2))
        for i, a in enumerate(data["apa"], 1): E.append(P(f"{i}. {a}", SMALL))
        E.append(Spacer(1, 4))

    # 五、檢索原則
    if data.get("axes"):
        E.append(P("五、檢索原則／方法（四軸展開字眼與必含連言軸篩選字眼）", H2))
        E.append(P("<b>四軸別名展開（檢索用同義詞）：</b>", BODY))
        for ln in data["axes"]: E.append(P("　" + ln, SMALL))
        if data.get("conjunction_axes"):
            E.append(P("<b>必含連言軸（同時出現才納入）：</b>", BODY)); E.append(P("　" + data["conjunction_axes"], SMALL))
        E.append(Spacer(1, 4))

    # 方法學註記
    if data.get("method_notes"):
        E.append(P("方法學註記與限制", H2))
        for n in data["method_notes"]: E.append(P("• " + n, SMALL))

    SimpleDocTemplate(out_pdf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                      topMargin=11 * mm, bottomMargin=11 * mm, title=data.get("title", "檢索報告")).build(E)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile"); ap.add_argument("--out"); ap.add_argument("--name")
    a = ap.parse_args()
    src = _resolve_in(a.infile)
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    out_dir = _out_dir(a.out); os.makedirs(out_dir, exist_ok=True)
    name = a.name or (re.sub(r'[^\w\-]+', '_', data.get("topic", "search")) + f'_SR_report_{data.get("search_date","")}.pdf')
    out_pdf = os.path.join(out_dir, name)
    build(data, out_pdf)
    print("WROTE:", out_pdf, "|", os.path.getsize(out_pdf), "bytes")

if __name__ == "__main__":
    main()
