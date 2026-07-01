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
    try:  # 無任何 TTF 時退 reportlab 內建 CID 字型（繁體覆蓋有限但不會整片缺字）
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        sys.stderr.write("找不到 TTF CJK 字型，改用內建 STSong-Light（繁體覆蓋有限；建議 --font 指定 msjh.ttc/wqy-zenhei.ttc）\n")
        return "STSong-Light"
    except Exception:
        pass
    sys.stderr.write("找不到 CJK 字型，中文會缺字；建議 --font 指定 msyh.ttc/wqy-zenhei.ttc\n")
    return "Helvetica"


def _safe(t):
    s = str(t)
    for k, v in TOFU_MAP.items():
        s = s.replace(k, v)
    return s


# 允許保留的 reportlab 行內標籤（其餘 < > & 一律跳脫，避免資料含 '<'(如 '<MCID') 讓 paragraph parser 崩潰）
_KEEP_TAGS = ("b", "/b", "i", "/i", "sup", "/sup", "sub", "/sub", "br/")


def _markup(t):
    """資料→reportlab 安全標記：先 TOFU 淨化，再跳脫 & < >（修『資料含 < 使 PDF 崩潰』bug，
    2026-06 使用者回報），最後還原白名單行內標籤(<b>/<i>/<sup>/<sub>/<br/>)使刻意粗體仍有效。
    註：TOFU_MAP 會把 ≤→'<='、≥→'>='，跳脫後成 '&lt;='/'&gt;='，渲染為字面 '<='/'>='、不再破壞解析。"""
    s = _safe(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for tag in _KEEP_TAGS:
        s = s.replace("&lt;%s&gt;" % tag, "<%s>" % tag)
    return s


def build(infile, out, font=None, layout="cochrane5"):
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
        return Paragraph(f'<font name="{F}" size="{sz}" color="{col}">{_markup(t)}</font>',
                         ParagraphStyle("s", leading=sz + 4, spaceAfter=sp, wordWrap="CJK"))
    def H(t, sz=13): return P("<b>" + t + "</b>", sz, sp=5)
    def cell(t, sz=8):
        return Paragraph(f'<font name="{F}" size="{sz}">{_markup(t)}</font>',
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

    if layout == "cochrane5":
        # 欄寬以『比例』分配，保證欄數正確且總和恰為頁寬 W（避免超寬/欄數不符）
        FR = lambda *fr: [round(f * W, 2) for f in fr]
        # ── 0 文獻篩選流程（PRISMA-style；2026-06 使用者要求新增於最前）──
        flow = syn.get("screening_flow") or []
        if flow:
            S.append(H("0、文獻篩選流程（Study Selection Flow，PRISMA-style）"))
            S.append(P("從多源廣蒐到最終納入分析的逐階段識別／排除／留存（檢索→篩選→收斂）。", 8.5, col="#555", sp=3))
            rows = [["階段", "流入", "排除（理由）", "留存／結果", "說明"]]
            for fstage in flow:
                rows.append([cell(fstage.get("stage", ""), 7.5), cell(fstage.get("start", ""), 7.5),
                             cell(fstage.get("excluded", ""), 7.5), cell(fstage.get("remain", ""), 7.5),
                             cell(fstage.get("note", "") or "", 7)])
            t = Table(rows, colWidths=FR(0.26, 0.10, 0.22, 0.18, 0.24)); t.setStyle(tstyle()); S.append(t)
            S.append(Spacer(1, 3 * mm))
        # ── 1 納入研究特徵摘要表（7 欄）──
        S.append(H("1、納入研究特徵摘要表（Characteristics of Included Studies）"))
        S.append(P("證明各試驗臨床上『可擺在一起比』（Cochrane Ch9）：研究設計／基準風險／介入·對照精確內容／追蹤時框。", 8.5, col="#555", sp=3))
        rows = [["試驗", "研究設計", "N／族群（基準風險）", "介入臂", "對照臂", "追蹤", "主要終點"]]
        for r in (syn.get("study_characteristics") or []):
            # 設計感知：讀 design_detail（schema 已納契約）；缺值只印 phase——不得偽造『多中心雙盲平行』
            rows.append([cell(r.get("trial", ""), 7.5), cell(r.get("design_detail") or r.get("phase", "") or "—", 7.5),
                         cell(r.get("n", ""), 7.5), cell(r.get("drug", "") + "（" + r.get("dose", "") + "）", 7.5),
                         cell(r.get("comparator", ""), 7.5), cell(r.get("duration", ""), 7.5), cell(r.get("primary_outcome", ""), 7.5)])
        t = Table(rows, colWidths=FR(0.08, 0.15, 0.13, 0.22, 0.13, 0.08, 0.21)); t.setStyle(tstyle()); S.append(t)
        for st in (syn.get("baseline_risk_strata") or []):
            S.append(P("· 基準風險分層：" + st.get("baseline_risk", "") + " → " + st.get("absolute_reduction", ""), 8, col="#555", sp=1))
        S.append(Spacer(1, 3 * mm))

        # ── 2 偏誤風險／方法學品質評估（8 欄；標題＋欄名隨分析單位而異：RCT→RoB2、SR/NMA→AMSTAR2、MAIC→TSD18）──
        rsec = syn.get("rob_section") or {}
        S.append(H("2、" + (rsec.get("title") or "個別試驗偏誤風險評估（Risk of Bias 2）")))
        S.append(P(rsec.get("intro") or "逐篇逐領域 RoB 2（Cochrane Ch8）；對 some concerns/high 具體點出設計瑕疵。", 8.5, col="#555", sp=3))
        _defcols = ["試驗", "隨機化", "偏離介入", "缺失資料", "結果測量", "選擇性報告", "整體", "瑕疵說明（concern 來源）"]
        _cols = rsec.get("columns") or _defcols
        rows = [(_cols + _defcols[len(_cols):])[:8]]
        for r in (syn.get("rob_summary") or []):
            rows.append([cell(r.get("trial", ""), 7.5), cell(r.get("randomization", ""), 7.5), cell(r.get("deviations", ""), 7.5),
                         cell(r.get("missing_data", ""), 7.5), cell(r.get("measurement", ""), 7.5), cell(r.get("selective_reporting", ""), 7.5),
                         cell(r.get("overall", ""), 7.5), cell((r.get("evidence_basis", "") + "：" + (r.get("note", "") or "")), 7)])
        # 欄寬資料驅動：AMSTAR2/MAIC 的欄內容（綜整名＋關鍵領域敘述）比 RCT 的 RoB2(短判定詞)長，
        # 故 rob_section.colwidths 可覆寫預設，避免窄欄(0.08)文字溢出（2026-06 使用者回報）。
        _cw = rsec.get("colwidths") or [0.08, 0.08, 0.08, 0.08, 0.08, 0.10, 0.07, 0.43]
        if len(_cw) != 8:   # 欄寬數必須＝欄數，否則 reportlab 直接例外；長度不符時退回預設並警示
            sys.stderr.write("⚠ rob_section.colwidths 長度 %d ≠ 8，改用預設欄寬\n" % len(_cw))
            _cw = [0.08, 0.08, 0.08, 0.08, 0.08, 0.10, 0.07, 0.43]
        t = Table(rows, colWidths=FR(*_cw)); t.setStyle(tstyle()); S.append(t)
        S.append(Spacer(1, 3 * mm))

        # ── 3 數據綜整與統合分析（7 欄）──
        S.append(H("3、數據綜整與統合分析（Data Synthesis／Meta-Analysis）"))
        S.append(P("逐核心結局之池化合併效應＋異質性 I^2（Cochrane Ch10）；未池化者說明理由。", 8.5, col="#555", sp=3))
        rows = [["核心結局", "模型", "合併效應（95% CI）", "I^2", "逐試驗效應", "絕對效應換算", "異質性判讀／理由"]]
        for m in (syn.get("meta_analysis") or []):
            eff = m.get("pooled_effect", "") + ("（" + m.get("ci", "") + "）" if m.get("ci") else "")
            rows.append([cell(m.get("outcome", ""), 7.5), cell({"fixed": "固定效應", "random": "隨機效應", "not_pooled": "未池化"}.get(m.get("model"), m.get("model")), 7.5),
                         cell(eff, 7.5), cell(m.get("i2") or "—", 7.5), cell(m.get("per_study") or "", 7),
                         cell(m.get("absolute") or "", 7), cell(m.get("heterogeneity", ""), 7)])
        t = Table(rows, colWidths=FR(0.12, 0.07, 0.14, 0.05, 0.21, 0.18, 0.23)); t.setStyle(tstyle()); S.append(t)
        S.append(Spacer(1, 3 * mm))

        # ── 4 GRADE 證據確定性評級（3 欄）──
        S.append(H("4、GRADE 證據確定性評級（Evidence Profile）"))
        S.append(P("逐核心結局自 RCT 起始『高』，跑 5 大下調領域（偏誤／不一致／間接／不精確／發表偏誤）結算（Cochrane Ch14）。", 8.5, col="#555", sp=3))
        rows = [["核心結局", "確定性", "下調領域結算（依據）"]]
        for b in (syn.get("body_of_evidence") or []):
            c = b.get("certainty", "")
            rows.append([cell(b.get("outcome", ""), 8), cell(f"{CERT_DOT.get(c,'')} {CERT_TXT.get(c,c)}", 8), cell(b.get("basis", ""), 7.5)])
        t = Table(rows, colWidths=FR(0.18, 0.10, 0.72)); t.setStyle(tstyle()); S.append(t)
        S.append(Spacer(1, 3 * mm))

        # ── 5 SoF 表 + 臨床決策建議（8 欄）──
        S.append(H("5、發現摘要表（SoF）與臨床決策建議"))
        rows = [["結局（時框）", "假設對照風險", "對應介入風險", "絕對效應（每千人／率差）", "相對效應（95% CI）", "N（研究）", "確定性", "降級腳註"]]
        for o in (syn.get("sof") or []):
            c = o.get("certainty", "")
            rows.append([cell(o.get("outcome", ""), 7.5), cell(o.get("assumed_control_risk", ""), 7), cell(o.get("corresponding_risk", ""), 7),
                         cell(o.get("absolute_effect", ""), 7), cell(o.get("relative_effect", ""), 7), cell(o.get("n_participants_studies", ""), 7),
                         cell(f"{CERT_DOT.get(c,'')} {CERT_TXT.get(c,c)}", 7.5), cell(o.get("comment", "") or "", 7)])
        t = Table(rows, colWidths=FR(0.11, 0.11, 0.09, 0.16, 0.17, 0.09, 0.07, 0.20)); t.setStyle(tstyle()); S.append(t)
        for fn in (syn.get("sof_footnotes") or []):
            S.append(P("　" + fn, 7.5, col="#555", sp=1))

        # ── 5b 多軌並行 SoF（三軌絕不混池；multitrack_integration 護欄）──
        tracks = syn.get("tracks") or {}
        if tracks:
            S.append(Spacer(1, 2 * mm))
            S.append(H("5b、多軌並行證據（RCT／NRSI／SR-MA 分軌，絕不混池）"))

            def _track_sof(label, blk, start_txt):
                if not blk:
                    return
                inc = blk.get("included_paper_ids") or []
                S.append(P(f"<b>{label}</b>（起始確定性：{start_txt}；合成：{blk.get('synthesis_mode','')}；納入 {len(inc)} 篇）", 9.5, sp=2))
                sof = blk.get("sof") or []
                if sof:
                    rows = [["結局", "假設對照風險", "對應介入風險", "絕對效應", "相對效應(95%CI)", "N(研究)", "確定性"]]
                    for o in sof:
                        c = o.get("certainty", "")
                        rows.append([cell(o.get("outcome", ""), 7.5), cell(o.get("assumed_control_risk", ""), 7), cell(o.get("corresponding_risk", ""), 7),
                                     cell(o.get("absolute_effect", ""), 7), cell(o.get("relative_effect", ""), 7), cell(o.get("n_participants_studies", ""), 7),
                                     cell(f"{CERT_DOT.get(c,'')} {CERT_TXT.get(c,c)}", 7.5)])
                    t = Table(rows, colWidths=FR(0.16, 0.13, 0.11, 0.17, 0.18, 0.10, 0.15)); t.setStyle(tstyle()); S.append(t)
                elif blk.get("certainty_summary"):
                    S.append(P("　敘事綜整：" + _safe(blk.get("certainty_summary")), 8, col="#555", sp=1))
            _track_sof("第一軌 RCT（RoB 2）＝主力", tracks.get("rct"), "高 ⊕⊕⊕⊕")
            _track_sof("第二軌 NRSI（ROBINS-I，獨立森林圖，critical 已剔除）", tracks.get("nrsi"), "低（起）")
            sc = tracks.get("srma_context") or {}
            if sc.get("reviews"):
                S.append(P("<b>第三軌 既有 SR/MA（AMSTAR 2）＝討論對照，不進統合（防 double-counting）</b>", 9.5, sp=2))
                rows = [["既有回顧", "AMSTAR2", "與本研究關係", "備註"]]
                for r in sc["reviews"]:
                    rows.append([cell(r.get("review", ""), 7.5), cell(r.get("amstar2_rating", ""), 7.5), cell(r.get("agreement", ""), 7.5), cell(r.get("note", "") or "", 7)])
                t = Table(rows, colWidths=FR(0.40, 0.12, 0.18, 0.30)); t.setStyle(tstyle()); S.append(t)
            if tracks.get("integration_note"):
                S.append(P("　整合（分層結論）：" + _safe(tracks["integration_note"]), 8.5, col="#333", sp=1))

        S.append(Spacer(1, 2 * mm))
        S.append(P("<b>臨床建議底線（Authors' Conclusions）</b>", 11, sp=3))
        for b in (syn.get("bottom_line") or []):
            S.append(P("● " + b, 9, sp=2))
        if syn.get("subgroup_implications"):
            S.append(P("<b>利弊平衡與次群組：</b>" + syn["subgroup_implications"], 8.5, sp=2, col="#444"))
        S.append(P("【Cochrane Ch15 規範】本報告提供利弊平衡與決策指引，但不下強制醫囑（不寫『必須全面改用』）；最終決策須納入個別病患價值觀、偏好與在地資源。", 8.5, sp=3, col="#7a1a1a"))
        for lim in (syn.get("limitations") or []):
            S.append(P("· 限制：" + lim, 7.8, col="#666", sp=1))
        S.append(Spacer(1, 2 * mm))

        # ── 6 給臨床的一句話（獨立段）──
        S.append(H("6、給臨床的一句話（Clinical Bottom Line）"))
        S.append(P(syn.get("clinical_one_liner") or "（未提供）", 11, sp=4, col="#1a4a7a"))
        S.append(P("頁尾：依 Cochrane Handbook 第 III 章報告規範渲染；單一 AI rapid review，最終納入與分級建議人工覆核。", 7.5, col="#888"))
        doc.build(S)
        print(f"✅ GRADE PDF（Cochrane 6 段）產出：{out}（{os.path.getsize(out)} bytes，字型 {F}）")
        return

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
    ap.add_argument("--layout", default="cochrane5", choices=["cochrane5", "default"],
                    help="cochrane5（預設，標準版）＝Cochrane 6 段（特徵表/RoB2/統合MA/GRADE/SoF含每千人+NNT+CI/臨床一句話）；default=舊 8 段")
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
    build(infile, out, a.font, a.layout)


if __name__ == "__main__":
    main()
