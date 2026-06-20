# -*- coding: utf-8 -*-
"""
build_search_pdf.py — EBM_Search 規範版 PDF 產生器（v0.22 簡化版：5 核心段落）
==============================================================================
讀『經 report_check 驗過的』_search_report.json，產出 5 個核心段落的 PDF：
  1. 檢索基本參數（PICO／檢索日期／資料庫清單／限制條件）
  2. 具體檢索策略（逐腿真實布林查詢字串，可重製）
  3. PRISMA 文獻篩選流程數據（漏斗各階段＋二分閉合＋流程圖）
  4. 最終納入證據清單（核心 RCT／重要 MA）：研究名稱·標題·DOI·PMID·PubMed/Crossref 驗證
  5. 進行中試驗：登錄號·標題
全部資料驅動（換主題不改碼）。字型 fallback：msjh.ttc → wqy-zenhei → Noto → Helvetica。
依賴：reportlab。用法：python build_search_pdf.py --in _search_report.json --out <報告.pdf> [--font ..]
"""
import sys, os, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

FONT_CANDIDATES = [
    r"C:/Windows/Fonts/msjh.ttc", r"C:/Windows/Fonts/msjhbd.ttc", r"C:/Windows/Fonts/mingliu.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

def _register_font(explicit=None):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for p in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if p and Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont("CJK", p, subfontIndex=0)); return "CJK"
            except Exception:
                continue
    sys.stderr.write("⚠️ 找不到 CJK 字型，中文會缺字；建議 --font 指定 msjh.ttc/wqy-zenhei.ttc\n")
    return "Helvetica"

def _safe(t):
    return (str(t).replace("✅","○").replace("✓","○").replace("≥","以上").replace("≤","以下")
            .replace("™","").replace("∧","且").replace("≠","不等於").replace("→","至").replace("↔","/"))

def build(infile, out, font=None):
    data = json.loads(Path(infile).read_text(encoding="utf-8"))
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
    F = _register_font(font)
    def P(t, sz=10, sp=2, col="#000000"):
        return Paragraph(f'<font name="{F}" size="{sz}" color="{col}">{_safe(t)}</font>',
                         ParagraphStyle("s", leading=sz+3, spaceAfter=sp, wordWrap="CJK"))
    def H(t, sz=13): return P("<b>"+t+"</b>", sz, sp=5)
    def cell(t, sz=8): return Paragraph(f'<font name="{F}" size="{sz}">{_safe(t)}</font>',
                         ParagraphStyle("c", leading=sz+2, wordWrap="CJK"))
    def tstyle():
        return TableStyle([("FONTNAME",(0,0),(-1,-1),F),("FONTSIZE",(0,0),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.4,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d9e6f2")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f4f7fb")])])
    PG=landscape(A4)
    out=str(out); doc=SimpleDocTemplate(out,pagesize=PG,topMargin=12*mm,bottomMargin=12*mm,leftMargin=12*mm,rightMargin=12*mm)
    W=PG[0]-24*mm; S=[]
    pf=data.get("prisma_flow",{})
    # title
    S.append(P("<b>EBM 檢索報告（系統性回顧對齊·rapid-review）</b>",15,sp=2))
    S.append(P(f"主題：{data.get('topic','')}",9,col="#555",sp=6))

    # ── 段1 檢索基本參數 ──
    S.append(H("一、檢索基本參數"))
    pico=data.get("pico",{})
    S.append(P(f"<b>PICO 簡述：</b>P＝{pico.get('P','')}；I＝{pico.get('I','')}；C＝{pico.get('C','')}；O＝{pico.get('O','（檢索不設 O 軸）')}",9,sp=2))
    S.append(P(f"<b>檢索日期：</b>{data.get('search_date','')}（精確到日）",9,sp=2))
    S.append(P(f"<b>資料庫／來源：</b>{'；'.join(data.get('databases',[]))}",9,sp=2))
    S.append(P(f"<b>限制條件：</b>{data.get('limits','')}",9,sp=6))

    # ── 段2 具體檢索策略 ──
    S.append(H("二、具體檢索策略（實際送出之查詢字串，可重製）"))
    for s in data.get("search_strategy",[]):
        if s.get("skip"):
            S.append(P(f"・<b>{s['leg']}</b>：跳過（{s['skip']}）",8.5,sp=2,col="#777")); continue
        S.append(P(f"・<b>{s['leg']}</b>：",9,sp=1))
        S.append(P(f"<font face='Courier'>{s.get('query','')}</font>",7.8,sp=4,col="#222"))
    S.append(Spacer(1,2*mm))

    # ── 段3 PRISMA 流程數據 ──
    S.append(H("三、PRISMA 文獻篩選流程數據"))
    fr=[["階段","數量/說明"]]+[[s.get("step",""),str(s.get("remain",""))+(("｜"+s["change"]) if s.get("change") else "")] for s in data.get("funnel",[])]
    if len(fr)>1:
        t=Table(fr,colWidths=[60*mm,W-60*mm]); t.setStyle(tstyle()); S.append(t)
    S.append(P("二分閉合："+data.get("funnel_closure",""),9,col="#333",sp=4))
    # 流程圖
    legs=data.get("search_strategy",[])
    legtxt="；".join(f"{l['leg']}{l.get('hit','')}" for l in legs if not l.get("skip") and l.get('hit') is not None)
    d=Drawing(W,150)
    def box(x,y,w,h,txt,fill="#eef3fb"):
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor(fill),strokeColor=colors.HexColor("#33689e"),strokeWidth=0.8))
        for i,ln in enumerate(txt.split("\n")): d.add(String(x+4,y+h-11-i*10,_safe(ln),fontName=F,fontSize=7))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=colors.grey,strokeWidth=0.8)); d.add(Polygon(points=[x2-3,y2+4,x2+3,y2+4,x2,y2],fillColor=colors.grey,strokeColor=colors.grey))
    box(0,122,W*0.62,26,f"辨識 Identification：各腿命中合計 {pf.get('identification','')}\n{legtxt}")
    box(0,96,W*0.62,18,f"去重 Dedup：跨源去重聯集 ＝ {pf.get('dedup','')}")
    box(0,66,W*0.62,24,f"篩選 Screening：初篩保留 {pf.get('screening','')}；待評估 {pf.get('awaiting','')}（不進嚴格篩）")
    box(0,38,W*0.62,22,f"③ 嚴格篩二分：離題 {pf.get('excluded_screen','')}（切題進納入）")
    box(0,8,W*0.62,24,f"納入 Included ＝ {pf.get('included','')}（核心 RCT 報告＋SR/MA＋背景）")
    box(W*0.66,90,W*0.34,30,f"其他方法（引文追蹤）\nSR/MA·樞紐種子反向+正向\n新增切題 +{pf.get('citation_arm','')}")
    for y1 in (122,96,66,38): arrow(W*0.31,y1,W*0.31,y1-8)
    arrow(W*0.66,100,W*0.62,24)
    S.append(d); S.append(Spacer(1,3*mm))

    # ── 段4 最終納入證據清單 ──
    S.append(H("四、最終納入的證據清單（核心 RCT／重要 MA）"))
    S.append(P("欄位：研究名稱｜標題｜DOI｜PMID｜PubMed/Crossref 驗證",8.5,col="#555",sp=3))
    for grp in data.get("included_studies",[]):
        head=P(f"<b>● {grp.get('study','')}（{grp.get('type','')}，{len(grp.get('reports',[]))} 報告）</b>",9.5,sp=1)
        tr=[["標題","DOI","PMID","驗證"]]+[[cell(r[0],7.5),cell(r[2],7),cell(r[1],7.5),cell(r[3],7.5)] for r in grp.get("reports",[])]
        t=Table(tr,colWidths=[W-92*mm,40*mm,22*mm,30*mm]); t.setStyle(tstyle())
        if len(grp.get("reports",[]))<=8: S.append(KeepTogether([head,t,Spacer(1,2.5*mm)]))
        else: S+=[head,t,Spacer(1,2.5*mm)]

    # ── 段5 進行中試驗 ──
    S.append(H("五、目前仍在進行中的試驗（CT.gov）"))
    orr=[["登錄號","標題"]]+[[cell(o[0],7.8),cell(o[1],7.8)] for o in data.get("ongoing_trials",[])]
    t=Table(orr,colWidths=[30*mm,W-30*mm]); t.setStyle(tstyle()); S.append(t)
    S.append(Spacer(1,3*mm))
    S.append(P("頁尾：本報告為 EBM_Search Phase 1 產物（5 段制）；單一 AI 篩選＝rapid-review，最終納入建議人工覆核；GRADE/RoB 於下游 EBM_Analysis。",7.5,col="#888"))
    doc.build(S)
    print(f"✅ PDF 產出：{out}（{os.path.getsize(out)} bytes，字型 {F}）")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--in",dest="infile",required=True)
    ap.add_argument("--out",required=True); ap.add_argument("--font",default=None)
    a=ap.parse_args()
    try: import reportlab  # noqa
    except Exception:
        sys.stderr.write("需要 reportlab：pip install reportlab\n"); sys.exit(1)
    build(a.infile,a.out,a.font)

if __name__=="__main__":
    main()
