# -*- coding: utf-8 -*-
"""
build_search_pdf.py — EBM_Search 規範版 PDF 標準產生器（資料驅動、字型 fallback）
==============================================================================
讀『經 report_check 驗過的』_search_report.json，產出 SEARCH_SPEC 固定章節的 PDF：
  ① 標題＋meta ② 臨床重點 ③ 檢索原則(必含軸同義詞＋各腿 query) ④ 檢索腿狀態
  ⑤ 清單一漏斗＋對帳閉合 ⑥ PRISMA 2020 流程圖(reportlab.graphics) ⑦ 納入核心證據
  (逐 Study 逐篇報告表[標題,PMID,DOI,全文狀態,交叉檢核])＋APA ⑧ 背景表 ⑨ 進行中試驗
  ⑩ 清單三 ⑪ 未納入來源＋MECIR 侷限＋頁尾註記。

全部資料驅動（換主題不改碼）：內容取自 _search_report.json 欄位。
**字型 fallback**：Windows 微軟正黑 msjh.ttc → Linux WenQuanYi wqy-zenhei → Noto CJK；
皆找不到才退 Helvetica(中文會缺字，於 stderr 警告)。— 故本機(Windows)與雲端(Linux)皆可產。

依賴：reportlab（缺則提示 `pip install reportlab`）。
用法：python build_search_pdf.py --in _search_report.json --out <報告.pdf> [--font <ttf/ttc 路徑>]
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
                pdfmetrics.registerFont(TTFont("CJK", p, subfontIndex=0))
                return "CJK"
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
    def H(t, sz=12.5): return P("<b>"+t+"</b>", sz, sp=4)
    def cell(t, sz=8): return Paragraph(f'<font name="{F}" size="{sz}">{_safe(t)}</font>',
                         ParagraphStyle("c", leading=sz+2, wordWrap="CJK"))
    def tstyle():
        return TableStyle([("FONTNAME",(0,0),(-1,-1),F),("FONTSIZE",(0,0),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.4,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d9e6f2")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f4f7fb")])])
    PG=landscape(A4)  # ★ A4 橫向(容寬表，對齊 SEARCH_SPEC『A4 橫向容寬表』與範本)
    out=str(out); doc=SimpleDocTemplate(out,pagesize=PG,topMargin=12*mm,bottomMargin=12*mm,leftMargin=12*mm,rightMargin=12*mm)
    W=PG[0]-24*mm; S=[]
    legs=data.get("legs",[]); pf=data.get("prisma_flow",{}); exc=data.get("excluded",{})
    # 1 title
    S.append(P("<b>EBM 檢索報告</b>",15,sp=2))
    S.append(P(f"主題：{data.get('topic','')}",8.5,col="#555"))
    S.append(P(f"引擎 {data.get('engine','EBM_Search')}（SR 對齊·敏感度優先）｜檢索日 {data.get('search_date','')}｜定位：rapid-review 級系統性回顧輔助",8.5,col="#555",sp=6))
    # 2 bottom line
    S.append(H("一、臨床重點"))
    S.append(P(data.get("clinical_bottom_line","（臨床重點待填）"),9.5,sp=6))
    # 3 檢索原則
    S.append(H("二、檢索原則／方法（必含軸＋各腿 query）"))
    al=data.get("axis_labels",{})
    for ax,syn in (data.get("axes") or {}).items():
        S.append(P(f"・{ax}（{al.get(ax,'')}）：{'、'.join(syn[:14])} …",8.5,sp=1))
    S.append(P("<b>各腿實際 query：</b>",9.5,sp=1))
    for l in legs:
        if l.get("skip"): S.append(P(f"・{l['leg']}：跳過（{l['skip']}）",8,sp=1,col="#777"))
        else: S.append(P(f"・{l['leg']}：{str(l.get('q',''))[:240]}",8,sp=1))
    S.append(Spacer(1,3*mm))
    # 4 腿狀態
    S.append(H("三、檢索腿狀態"))
    lr=[["腿","命中","狀態"]]+[[l["leg"],"—" if l.get("skip") else str(l.get("hit")),"跳過："+l["skip"] if l.get("skip") else "已取盡"] for l in legs]
    t=Table(lr,colWidths=[42*mm,25*mm,W-67*mm]); t.setStyle(tstyle()); S.append(t); S.append(Spacer(1,4*mm))
    # 5 清單一
    S.append(H("四、清單一：檢索流程漏斗（對帳）"))
    fr=[["階段","數量/說明"]]+[[s.get("step",""),str(s.get("remain",""))+(("｜"+s["change"]) if s.get("change") else "")] for s in data.get("funnel",[])]
    t=Table(fr,colWidths=[55*mm,W-55*mm]); t.setStyle(tstyle()); S.append(t)
    S.append(P("對帳："+data.get("funnel_closure",""),8.5,col="#333",sp=6))
    # 6 PRISMA flow
    S.append(H("五、PRISMA 2020 檢索流程圖"))
    legtxt="；".join(f"{l['leg']}{l.get('hit')}" for l in legs if not l.get("skip"))
    skiptxt="；".join(f"{l['leg']}跳過" for l in legs if l.get("skip"))
    d=Drawing(W,196)
    def box(x,y,w,h,txt,fill="#eef3fb"):
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor(fill),strokeColor=colors.HexColor("#33689e"),strokeWidth=0.8))
        for i,ln in enumerate(txt.split("\n")): d.add(String(x+4,y+h-11-i*10,_safe(ln),fontName=F,fontSize=7))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=colors.grey,strokeWidth=0.8)); d.add(Polygon(points=[x2-3,y2+4,x2+3,y2+4,x2,y2],fillColor=colors.grey,strokeColor=colors.grey))
    box(0,168,W*0.62,26,f"辨識 Identification：各腿命中合計 {pf.get('identification','')}\n{legtxt}　（{skiptxt}）")
    box(0,140,W*0.62,20,f"去重 Dedup：跨源去重聯集 ＝ {pf.get('dedup','')}")
    box(0,108,W*0.62,26,f"篩選 Screening：初篩保留 {pf.get('screening','')}\n有內容進嚴格篩；待評估 {pf.get('awaiting','')}（不進篩選）")
    box(0,78,W*0.62,20,f"③ 嚴格篩二分：離題 {pf.get('excluded_screen','')}（切題進納入）")
    box(0,44,W*0.62,26,f"納入 Included ＝ {pf.get('included','')}：原始 RCT 報告 {pf.get('included_rct_reports','')}\n＋ SR/MA 背景 {pf.get('srma_background','')}（＋其他背景）")
    box(W*0.66,140,W*0.34,28,f"其他方法（引文追蹤臂）\nSR/MA 種子反向+正向\n新增切題 +{pf.get('citation_arm','')}")
    box(W*0.66,88,W*0.34,40,"排除（清單三）：\n"+"\n".join(f"{k} {v}" for k,v in list(exc.items())[:4]))
    for y1 in (168,140,108,78): arrow(W*0.31,y1,W*0.31,y1-8)
    arrow(W*0.66,152,W*0.62,56)
    S.append(d); S.append(Spacer(1,3*mm))
    # 7 核心證據逐 Study
    S.append(H("六、納入的核心證據（原始 RCT，依 Study 逐篇列報告）"))
    S.append(P(f"主題回顯：{data.get('topic','')}。欄位：標題｜PMID｜DOI｜全文狀態｜交叉檢核。",8.5,col="#555",sp=3))
    for grp in data.get("studies",[]):
        head=P("<b>● "+grp.get("study","")+f"（{len(grp.get('reports',[]))} 報告）</b>",9.5,sp=1)
        tr=[["標題","PMID","DOI","全文","檢核"]]+[[cell(r[0],7.5),cell(r[1],7.5),cell(r[2],7),cell(r[3],7.5),cell(r[4],7.5)] for r in grp.get("reports",[])]
        t=Table(tr,colWidths=[W-72*mm,20*mm,28*mm,12*mm,12*mm]); t.setStyle(tstyle())
        if len(grp.get("reports",[]))<=6: S.append(KeepTogether([head,t,Spacer(1,2.5*mm)]))
        else: S+=[head,t,Spacer(1,2.5*mm)]
    if data.get("unident_rct"): S.append(P(f"另有未連結試驗名之 RCT 報告 {data['unident_rct']} 篇＝待人工連結，未列入上表。",8.5,col="#777",sp=5))
    # 7b APA
    meta=data.get("meta",{})
    if meta:
        S.append(H("七、納入文獻 APA 清單（書目來自 PubMed 實際 metadata）"))
        n=0
        for grp in data.get("studies",[]):
            for r in grp.get("reports",[]):
                m=meta.get(str(r[1]))
                if not m: continue
                n+=1; etal=" et al." if m.get("nau",0)>1 else ""
                S.append(P(f"{n}. {m.get('first','')}{etal} ({m.get('year','')}). {m.get('title','')} {m.get('journal','')}." + (f" https://doi.org/{m['doi']}" if m.get('doi') else ""),7.8,sp=1))
        S.append(Spacer(1,4*mm))
    # 8 背景表
    S.append(H("八、背景／對照參考（不計入原始研究納入數）"))
    br=[["標題","PMID","DOI","型態","全文","檢核"]]+[[cell(r[0],7.3),cell(r[1],7),cell(r[2],6.8),cell(r[3],7),cell(r[4],7),cell(r[5],7)] for r in data.get("background",[])]
    t=Table(br,colWidths=[W-92*mm,18*mm,30*mm,16*mm,12*mm,16*mm]); t.setStyle(tstyle()); S.append(t); S.append(Spacer(1,4*mm))
    # 9 進行中
    S.append(H("九、進行中／登錄試驗（CT.gov）"))
    orr=[["登錄號","內容","狀態"]]+[[cell(o[0],7.5),cell(o[1],7.5),cell(o[2],7.5)] for o in data.get("ongoing_trials",[])[:30]]
    t=Table(orr,colWidths=[28*mm,W-58*mm,30*mm]); t.setStyle(tstyle()); S.append(t); S.append(Spacer(1,4*mm))
    # 10 清單三
    S.append(H("十、清單三：剔除／排除（對帳）"))
    xr=[["類別","數量"]]+[[k,str(v)] for k,v in exc.items()]
    t=Table(xr,colWidths=[W-30*mm,30*mm]); t.setStyle(tstyle()); S.append(t); S.append(Spacer(1,4*mm))
    # 11 限制
    S.append(H("十一、未納入來源與方法學侷限（透明度）"))
    S.append(P(data.get("limitations_note") or
        "・未涵蓋 Embase／CENTRAL／CINAHL／WHO ICTRP／FDA-EMA 監管文件（無免費 API）。<br/>"
        "・單一 AI 演算法篩選，未達 MECIR C39 雙人獨立 → rapid-review 級，最終納入建議人工覆核。<br/>"
        "・全文狀態部分以 metadata 判定；正式全文補入(⑤b)＋have 實抓驗證請於本機執行。<br/>"
        "・未連結試驗名之 RCT 報告、背景細分＝待人工。",9,sp=4))
    S.append(P("頁尾方法學註記：本報告為 EBM_Search Phase 1 產物；GRADE/RoB/效應量於下游 EBM_Analysis 評讀。",7.5,col="#888"))
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
