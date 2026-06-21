# -*- coding: utf-8 -*-
"""
build_grade_pdf.py — EBM_Analysis GRADE 報告 PDF 產生器（reportlab）
====================================================================
讀 cache/_synthesis.json（phase4 物件），產出 outputs/FINAL_REPORT.pdf：
  1 白話總結  2 核心結論＋臨床一句話  3 納入研究特徵表  4 RoB2 摘要
  5 Summary of Findings（SoF，相對＋絕對並列、GRADE 確定性）
  6 證據體 GRADE  7 限制與發表偏誤  8 各核心試驗結論摘要
全資料驅動（換主題不改碼）。字型 fallback：msyh/msjh → wqy-zenhei → Noto → Helvetica。
★ 禁 emoji；TOFU 高風險符號一律 _safe() 淨化（與 render_smoketest 對齊）。
用法：python tools/build_grade_pdf.py [--in cache/_synthesis.json] [--out outputs/FINAL_REPORT.pdf] [--font ..]
"""
import sys, os, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = Path(__file__).resolve().parent

FONT_CANDIDATES = [
    r"C:/Windows/Fonts/msyh.ttc", r"C:/Windows/Fonts/msjh.ttc", r"C:/Windows/Fonts/mingliu.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]
# TOFU 高風險符號 → 安全替代（與 render_smoketest.TOFU 對齊，避免磚塊）
TOFU_MAP = {"≈":"約","≥":">=","≤":"<=","−":"-","◯":"○","↔":"/","⇔":"/","⇄":"/","⟷":"/",
            "▸":"·","►":"·","™":"","✅":"○","✓":"○","✔":"○","∧":"且","≠":"不等於"}
CERT_DOT = {"high":"●●●●","moderate":"●●●○","low":"●●○○","very_low":"●○○○"}
CERT_TXT = {"high":"高","moderate":"中","low":"低","very_low":"極低"}


def _register_font(explicit=None):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for p in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if p and Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont("CJK", p, subfontIndex=0)); return "CJK"
            except Exception:
                continue
    sys.stderr.write("找不到 CJK 字型，中文會缺字；建議 --font 指定 msyh.ttc/wqy-zenhei.ttc\n")
    return "Helvetica"


def _safe(t):
    s = str(t)
    for k, v in TOFU_MAP.items():
        s = s.replace(k, v)
    return s


def build(infile, out, font=None):
    data = json.loads(Path(infile).read_text(encoding="utf-8"))
    syn = data.get("synthesis", data)
    pp = data.get("per_paper", [])
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    F = _register_font(font)

    def P(t, sz=10, sp=2, col="#000000"):
        return Paragraph(f'<font name="{F}" size="{sz}" color="{col}">{_safe(t)}</font>',
                         ParagraphStyle("s", leading=sz + 4, spaceAfter=sp, wordWrap="CJK"))
    def H(t, sz=13): return P("<b>" + t + "</b>", sz, sp=5)
    def cell(t, sz=8):
        return Paragraph(f'<font name="{F}" size="{sz}">{_safe(t)}</font>',
                         ParagraphStyle("c", leading=sz + 2, wordWrap="CJK"))
    def tstyle():
        return TableStyle([("FONTNAME", (0, 0), (-1, -1), F), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e6f2")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")])])

    PG = landscape(A4)
    doc = SimpleDocTemplate(str(out), pagesize=PG, topMargin=12 * mm, bottomMargin=12 * mm,
                            leftMargin=12 * mm, rightMargin=12 * mm)
    W = PG[0] - 24 * mm
    S = []
    title = syn.get("report_title") or "EBM GRADE 評讀報告"
    S.append(P("<b>" + title + "</b>", 15, sp=2))
    S.append(P("（rapid review；GRADE 確定性：高 ●●●● / 中 ●●●○ / 低 ●●○○ / 極低 ●○○○）", 8.5, col="#666", sp=6))

    # 1 白話總結
    S.append(H("1、白話總結（一分鐘讀懂）"))
    S.append(P(syn.get("plain_summary") or "（未提供）", 10, sp=6))

    # 2 核心結論＋臨床一句話
    S.append(H("2、核心結論（Bottom Line）"))
    for b in (syn.get("bottom_line") or []):
        S.append(P("● " + b, 9.5, sp=2))
    if syn.get("clinical_one_liner"):
        S.append(P("<b>給臨床的一句話：</b>" + syn["clinical_one_liner"], 9.5, sp=6, col="#1a4a7a"))

    # 3 納入研究特徵表
    S.append(H("3、納入研究特徵表"))
    sc = syn.get("study_characteristics") or []
    if sc:
        rows = [["試驗", "藥物", "期別", "N", "劑量", "療程", "對照", "主要終點"]]
        for r in sc:
            rows.append([cell(r.get("trial", ""), 8), cell(r.get("drug", "")), cell(r.get("phase", "")),
                         cell(r.get("n", "")), cell(r.get("dose", "")), cell(r.get("duration", "")),
                         cell(r.get("comparator", "")), cell(r.get("primary_outcome", ""))])
        t = Table(rows, colWidths=[20 * mm, 34 * mm, 16 * mm, 22 * mm, 36 * mm, 16 * mm, 34 * mm, W - 178 * mm])
        t.setStyle(tstyle()); S.append(t)
    S.append(Spacer(1, 3 * mm))

    # 4 RoB2 摘要
    S.append(H("4、偏誤風險（RoB 2）摘要"))
    rb = syn.get("rob_summary") or []
    if rb:
        rows = [["試驗", "隨機化", "偏離", "缺失資料", "測量", "選擇性報告", "整體", "依據/註"]]
        for r in rb:
            note = (r.get("evidence_basis", "") + "；" + (r.get("note", "") or ""))
            rows.append([cell(r.get("trial", ""), 8), cell(r.get("randomization", "")), cell(r.get("deviations", "")),
                         cell(r.get("missing_data", "")), cell(r.get("measurement", "")),
                         cell(r.get("selective_reporting", "")), cell(r.get("overall", "")), cell(note, 7)])
        t = Table(rows, colWidths=[20 * mm, 20 * mm, 16 * mm, 22 * mm, 16 * mm, 24 * mm, 22 * mm, W - 140 * mm])
        t.setStyle(tstyle()); S.append(t)
    S.append(Spacer(1, 3 * mm))

    # 5 SoF
    S.append(H("5、結果彙總表（Summary of Findings）"))
    sof = syn.get("sof") or []
    rows = [["結局", "對照組風險", "介入組風險", "絕對效應", "相對效應", "N（研究）", "確定性", "說明"]]
    for o in sof:
        cert = o.get("certainty", "")
        cdisp = f"{CERT_DOT.get(cert,'')} {CERT_TXT.get(cert,cert)}"
        rows.append([cell(o.get("outcome", ""), 8), cell(o.get("assumed_control_risk", ""), 7.5),
                     cell(o.get("corresponding_risk", ""), 7.5), cell(o.get("absolute_effect", ""), 7.5),
                     cell(o.get("relative_effect", ""), 7.5), cell(o.get("n_participants_studies", ""), 7.5),
                     cell(cdisp, 7.5), cell(o.get("comment", "") or "", 7)])
    t = Table(rows, colWidths=[30 * mm, 30 * mm, 26 * mm, 40 * mm, 44 * mm, 26 * mm, 20 * mm, W - 216 * mm])
    t.setStyle(tstyle()); S.append(t)
    S.append(Spacer(1, 3 * mm))

    # 6 證據體 GRADE
    S.append(H("6、證據體 GRADE（跨研究逐結局）"))
    boe = syn.get("body_of_evidence") or []
    if boe:
        rows = [["結局", "確定性", "依據"]]
        for b in boe:
            cert = b.get("certainty", "")
            rows.append([cell(b.get("outcome", ""), 8), cell(f"{CERT_DOT.get(cert,'')} {CERT_TXT.get(cert,cert)}", 8),
                         cell(b.get("basis", ""), 7.5)])
        t = Table(rows, colWidths=[44 * mm, 24 * mm, W - 68 * mm]); t.setStyle(tstyle()); S.append(t)
    S.append(Spacer(1, 3 * mm))

    # 7 限制與發表偏誤
    S.append(H("7、限制與發表偏誤聲明"))
    for lim in (syn.get("limitations") or []):
        S.append(P("· " + lim, 9, sp=2))
    if syn.get("publication_bias"):
        S.append(P("<b>發表偏誤/利益衝突：</b>" + syn["publication_bias"], 8.5, sp=2, col="#444"))
    if syn.get("missing_evidence_sensitivity"):
        S.append(P("<b>缺失證據敏感度：</b>" + syn["missing_evidence_sensitivity"], 8.5, sp=4, col="#444"))

    # 8 各核心試驗結論摘要
    S.append(H("8、各核心試驗結論摘要"))
    for p in pp:
        bl = p.get("bottom_line", {})
        cert = bl.get("certainty", "")
        head = P(f"<b>● {p.get('paper_id','')}（確定性：{CERT_TXT.get(cert,cert)}）</b>", 9.5, sp=1)
        body = P(bl.get("text", ""), 9, sp=1)
        dash = P(p.get("dashboard", ""), 8, sp=4, col="#555")
        S.append(KeepTogether([head, body, dash, Spacer(1, 2 * mm)]))

    S.append(Spacer(1, 2 * mm))
    S.append(P("頁尾：本報告由 EBM_Analysis 依結構化 phases/guardrails/schema 渲染；單一 AI 評讀＝rapid review，最終納入與分級建議人工覆核。", 7.5, col="#888"))
    doc.build(S)
    print(f"✅ GRADE PDF 產出：{out}（{os.path.getsize(out)} bytes，字型 {F}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--font", default=None)
    a = ap.parse_args()
    try:
        sys.path.insert(0, str(HERE)); import workdir
        cache = workdir.cache_dir(); outputs = workdir.outputs_dir()
    except Exception:
        cache = str(HERE.parent / "cache"); outputs = str(HERE.parent / "outputs")
    infile = a.infile or os.path.join(cache, "_synthesis.json")
    out = a.out or os.path.join(outputs, "FINAL_REPORT.pdf")
    try:
        import reportlab  # noqa
    except Exception:
        sys.stderr.write("需要 reportlab：pip install reportlab\n"); sys.exit(1)
    build(infile, out, a.font)


if __name__ == "__main__":
    main()
