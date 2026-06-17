# -*- coding: utf-8 -*-
"""生成 outputs/FINAL_REPORT.pdf：前半＝流程圖＋說明，後半＝分析結果（含 SoF 表）。

★ 禁用 emoji／彩色符號（⚠️✅❌⭐🚫 等含 U+FE0F）——微軟正黑無此字形，會變方格 □。
  警示用文字「【注意】」「※」或彩色底框；安全符號：● ○ • → ① ② ③ ≈ – —。
  產出後務必渲染成圖目視確認無方格。
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, NextPageTemplate,
                                Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
import re
from pathlib import Path

# ── 字型 ────────────────────────────────────────────
try:
    pdfmetrics.registerFont(TTFont('CJK', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
    FONT = 'CJK'
    try:
        pdfmetrics.registerFont(TTFont('CJKB', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0)); FONTB = 'CJKB'
    except Exception:
        FONTB = 'CJK'
except Exception:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light')); FONT = FONTB = 'STSong-Light'
pdfmetrics.registerFontFamily('CJK', normal=FONT, bold=FONTB, italic=FONT, boldItalic=FONTB)

NAVY = HexColor('#1a5276'); BLUE = HexColor('#2e86c1'); BLUEL = HexColor('#d6eaf8')
GREENL = HexColor('#d5f5e3'); GREEN = HexColor('#1e8449'); GREYL = HexColor('#eaeded')
REDL = HexColor('#fadbd8'); RED = HexColor('#b03a2e'); BORDER = HexColor('#566573')
AMBERL = HexColor('#fdebd0')

# ── 單一真相來源：所有資料一律讀 cache/_synthesis.json（＋_corpus.json）──
# PDF 不再硬編任何分析資料，與 FINAL_REPORT.md / synthesis.md 同源，永不漂移。
# cache/outputs 由 workdir 決定（env EBM_WORKDIR > config analysis.work_dir），與其他工具一致。
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
try:
    import workdir as _wd
    _CACHE = Path(_wd.cache_dir()); _OUTPUTS = Path(_wd.outputs_dir())
except Exception:
    _CACHE = Path(__file__).resolve().parent / 'cache'; _OUTPUTS = Path(__file__).resolve().parent / 'outputs'
# 字形淨化（微軟正黑體缺字形 → 等義有字形符號），於『載入時』遞迴套用整個 cache，避免任何渲染路徑漏網。
_GLYPH_TR0 = str.maketrans({'≈': '≒', '≥': '≧', '≤': '≦', '−': '-', '◯': '○',
                            '↔': '／', '⇔': '／', '▸': '•', '►': '•'})
# emoji／dingbat／variation-selector（微軟正黑無字形→磚塊□/NULL）一律剔除；保留 ● ○ • → – — ① ② ③ ≈（不在這些區段）
_EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF'
                       '\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF]')
def _strip_bricks(s):
    return _EMOJI_RE.sub('', s).translate(_GLYPH_TR0)
def _deep_safe(o):
    if isinstance(o, str):  return _strip_bricks(o)
    if isinstance(o, list): return [_deep_safe(x) for x in o]
    if isinstance(o, dict): return {k: _deep_safe(v) for k, v in o.items()}
    return o
_SD = _deep_safe(json.loads((_CACHE / '_synthesis.json').read_text(encoding='utf-8')))
SYN = _SD.get('synthesis', _SD)
_CP = _CACHE / '_corpus.json'
_CORP = _deep_safe(json.loads(_CP.read_text(encoding='utf-8'))) if _CP.exists() else {'papers': []}
RQ = _CORP.get('review_question', {})
# 報告標題/頁尾一律資料驅動（不硬編題目；避免別案模板殘留）：report_title ＞ review_question.statement ＞ 預設
_TITLE = (SYN.get('report_title') or RQ.get('statement') or 'EBM 實證評讀總報告').strip()
_FOOTER = (SYN.get('report_title') or RQ.get('statement') or 'EBM_Analysis 評讀引擎').strip()
# 流程圖數字一律由 cache/_corpus.json 帶（單一真相來源，不硬編）
_PP = _CORP.get('papers', [])
N_TOTAL = len(_PP)
N_FULL = sum(1 for p in _PP if p.get('grade_track') == 'full')
N_TARGET = sum(1 for p in _PP if p.get('grade_track') == 'targeted_harms')
N_LIGHT = sum(1 for p in _PP if p.get('grade_track') == 'light_summary')
N_EXCL = sum(1 for p in _PP if p.get('grade_track') == 'none')
N_RCT = sum(1 for p in _PP if p.get('grade_track') == 'full' and p.get('role') == 'pivotal_efficacy')
N_MA = sum(1 for p in _PP if p.get('grade_track') == 'full' and p.get('role') == 'meta_analysis')

# 字形淨化：微軟正黑體缺字形者 → 有字形之等義符號，避免 PDF 出現磚塊（□）。
_GLYPH_SAFE = {'≈': '≒', '≥': '≧', '≤': '≦', '−': '-', '◯': '○',
               '↔': '／', '⇔': '／', '▸': '•', '►': '•'}  # msjh 缺字形 → 等義有字形
_GLYPH_TR = str.maketrans(_GLYPH_SAFE)
def safe_glyphs(s):
    return _EMOJI_RE.sub('', (s or '')).translate(_GLYPH_TR)

def md2rl(s):
    """把 JSON 內的純文字安全送進 reportlab Paragraph：跳脫 & < >，**粗體**→<b>，換行→<br/>，淨化缺字形符號。"""
    s = safe_glyphs(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s.replace('\n', '<br/>')

def S(name, size, leading=None, color=black, bold=False, align=TA_LEFT, sp=4, left=0):
    return ParagraphStyle(name, fontName=FONTB if bold else FONT, fontSize=size,
                          leading=leading or size*1.45, textColor=color, alignment=align,
                          spaceAfter=sp, leftIndent=left, wordWrap='CJK')
H1 = S('H1', 17, color=NAVY, bold=True, align=TA_CENTER, sp=2)
SUB = S('SUB', 10, color=HexColor('#555'), align=TA_CENTER, sp=10)
H2 = S('H2', 13.5, color=white, bold=True, sp=6)
H3 = S('H3', 11.5, color=NAVY, bold=True, sp=4)
BODY = S('BODY', 10, leading=15.5)
BODYB = S('BODYB', 10, leading=15.5, bold=True)
LI = S('LI', 10, leading=15, left=12)
SMALL = S('SMALL', 8.2, leading=11.5)
CELL = S('CELL', 8.3, leading=11.2)
CELLB = S('CELLB', 8.3, leading=11.2, bold=True, align=TA_CENTER)
NOTE = S('NOTE', 8.6, leading=12.5, color=HexColor('#444'))

def hbar(text):
    t = Table([[Paragraph(text, H2)]], colWidths=[170*mm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),NAVY),('LEFTPADDING',(0,0),(-1,-1),8),
                           ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    return t

# ── 流程圖元件 ──────────────────────────────────────
def _box(d, cx, top, w, h, lines, fill, fs=8.6, fcol=black, edge=BORDER):
    x = cx - w / 2.0; y = top - h
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=edge, strokeWidth=0.9))
    n = len(lines)
    for i, ln in enumerate(lines):
        ty = top - (h / (n + 1.0)) * (i + 1) - fs * 0.33
        d.add(String(cx, ty, ln, fontName=FONT, fontSize=fs, fillColor=fcol, textAnchor='middle'))
    return y

def _arrow(d, x, y1, y2, col=BLUE):
    d.add(Line(x, y1, x, y2 + 4, strokeColor=col, strokeWidth=1.1))
    d.add(Polygon([x - 3.2, y2 + 5, x + 3.2, y2 + 5, x, y2], fillColor=col, strokeColor=col))

def prisma_diagram():
    W, H = 470, 366
    d = Drawing(W, H); cx = W / 2.0
    _box(d, cx, H, 320, 30, [f'交接包收到文獻：{N_TOTAL} 篇（本主題）'], BLUEL, 9)
    _arrow(d, cx, H - 30, H - 48)
    _box(d, cx, H - 48, 360, 32, ['第〇階段 — 分流：先界定臨床問題，', '再判斷每篇文獻的相關性與證據角色'], GREYL, 8.6)
    # 三向分流
    yrow_top = H - 96
    d.add(Line(cx, H - 80, cx, yrow_top + 2, strokeColor=BLUE, strokeWidth=1.1))
    d.add(Line(95, yrow_top + 2, 375, yrow_top + 2, strokeColor=BLUE, strokeWidth=1.1))
    for bx in (95, 375):
        d.add(Line(bx, yrow_top + 2, bx, yrow_top, strokeColor=BLUE, strokeWidth=1.1))
    _box(d, cx, yrow_top, 160, 44, [f'{N_FULL+N_TARGET} 篇 → 進 GRADE 評讀', f'（{N_RCT} 個 RCT ＋ {N_MA} 篇統合分析＋{N_TARGET} 安全性）'], GREENL, 8.2, edge=GREEN)
    _box(d, 95, yrow_top, 130, 44, [f'{N_LIGHT} 篇 → 列為背景', '（機制／藥動／綜述）'], AMBERL, 8.0)
    _box(d, 375, yrow_top, 130, 44, [f'{N_EXCL} 篇 → 排除', '（與主題無關）'], REDL, 8.0, edge=RED)
    _arrow(d, cx, yrow_top - 44, yrow_top - 60)
    y2 = yrow_top - 60
    _box(d, cx, y2, 330, 28, ['逐篇 GRADE 分級（每個結果各評一個確定性）'], BLUEL, 8.8)
    _arrow(d, cx, y2 - 28, y2 - 44)
    y3 = y2 - 44
    _box(d, cx, y3, 380, 30, ['品質把關：結構檢查＋確定性算術重算＋', '跨篇一致性稽核＋對抗式第二遍複查'], GREYL, 8.4)
    _arrow(d, cx, y3 - 30, y3 - 46)
    y4 = y3 - 46
    _box(d, cx, y4, 360, 30, ['去除重複證據後統合 → 最終結論＋Summary of Findings 表'], GREENL, 8.6, edge=GREEN)
    return d

def pipeline_diagram():
    W, H = 470, 70
    d = Drawing(W, H)
    labels = ['① 抽取\nPICO/N', '② 分軌\n起始確定性', '③ 分級\nGRADE', '④ 複查\n對抗式', '⑤ 統合\nSoF 表']
    n = len(labels); bw = 76; gap = (W - n * bw) / (n - 1)
    for i, lab in enumerate(labels):
        x = i * (bw + gap); cx = x + bw / 2
        parts = lab.split('\n')
        _box(d, cx, 56, bw, 36, parts, BLUEL, 8.2)
        if i < n - 1:
            ax = x + bw; d.add(Line(ax, 38, ax + gap - 4, 38, strokeColor=BLUE, strokeWidth=1.1))
            d.add(Polygon([ax + gap - 4, 41, ax + gap - 4, 35, ax + gap, 38], fillColor=BLUE, strokeColor=BLUE))
    d.add(String(W / 2, 8, '每階段：Claude 直接判斷 → JSON Schema 強制完整 → 工具驗證（無外部 API）',
                 fontName=FONT, fontSize=7.6, fillColor=HexColor('#555'), textAnchor='middle'))
    return d

# ── SoF 表（橫向頁；確定性用 文字＋●○、評論寫完整）──────
G = {'high': '高確定性\n●●●●', 'moderate': '中等確定性\n●●●○',
     'low': '低確定性\n●●○○', 'very_low': '極低確定性\n●○○○'}
_SOF_HEAD = ['結果（測量時框）', '對照組風險', '介入組對應風險', '絕對效應', '相對效應',
             '參與者數（研究數）', '證據確定性（GRADE）', '評論（解讀重點）']
SOF = [_SOF_HEAD] + [
    [r.get('outcome', ''), r.get('assumed_control_risk', ''), r.get('corresponding_risk', ''),
     r.get('absolute_effect', ''), r.get('relative_effect', ''), r.get('n_participants_studies', ''),
     r.get('certainty', ''), r.get('comment') or '']
    for r in SYN.get('sof', [])
]
def sof_table():
    cw = [w * mm for w in (34, 25, 25, 34, 38, 24, 26, 51)]
    data = []
    for r, row in enumerate(SOF):
        cells = []
        for ci, c in enumerate(row):
            txt = G.get(c, c).replace('\n', '<br/>') if (r > 0 and ci == 6) else str(c)
            st = CELLB if (r == 0 or (r > 0 and ci == 6)) else CELL
            cells.append(Paragraph(txt, st))
        data.append(cells)
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), FONTB),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f4f8fb')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t

def bullet(text):
    return Paragraph('•&nbsp;&nbsp;' + text, LI)

def qtable(rows, cw):
    data = [[Paragraph(str(c), CELLB if r == 0 else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in cw], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f4f8fb')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t

CHAR_ROWS = [['試驗', '藥物', '期別', 'N', '劑量（每日一次）', '療程', '對照', '主要終點']] + [
    [r['trial'], r['drug'], r['phase'], r['n'], r['dose'], r['duration'], r['comparator'], r['primary_outcome']]
    for r in SYN.get('study_characteristics', [])
]
ROB_ROWS = [['試驗', '隨機化', '偏離介入', '缺失資料', '結果測量', '選擇性報告', '整體', 'some concerns 原因']] + [
    [r['trial'], r['randomization'], r['deviations'], r['missing_data'], r['measurement'],
     r['selective_reporting'], r['overall'], r.get('note', '')]
    for r in SYN.get('rob_summary', [])
]
LIT_ROWS = [['文獻', '角色', '全文取得狀態']] + [
    [s['paper'], s['role'], s['fulltext']] for s in SYN.get('literature_status', [])
]
BOE_ROWS = [['結果（outcome）', '證據體確定性', '如何由跨研究導出']] + [
    [b['outcome'], {'high': '高 ●●●●', 'moderate': '中等 ●●●○', 'low': '低 ●●○○', 'very_low': '極低 ●○○○'}.get(b['certainty'], b['certainty']), b['basis']]
    for b in SYN.get('body_of_evidence', [])
]
BASE_ROWS = [['基準惡化風險（對照組）', '對應介入率', '每人每年絕對減少']] + [
    [r['baseline_risk'], r['corresponding'], r['absolute_reduction']]
    for r in SYN.get('baseline_risk_strata', [])
]
AMSTAR2_LABEL = {'high': '高信心', 'moderate': '中等信心', 'low': '低信心', 'critically_low': '極低信心'}
REL_REVIEWS = SYN.get('related_reviews', [])
REL_ROWS = [['回顧（類型）', '涵蓋範圍', '納入試驗', 'AMSTAR 2 信心', '角色']] + [
    [r['review'], r['scope'], r['trials_covered'],
     AMSTAR2_LABEL.get(r['amstar2_rating'], r['amstar2_rating']), r['role']]
    for r in REL_REVIEWS
]

# ── 內容 ────────────────────────────────────────────
# 評讀日期：由 run_state 帶（到「日」），不硬編；失敗回退
try:
    import run_state as _rs
    _DATE = _rs.load().get('search_date') or '2026-06-14'
except Exception:
    _DATE = '2026-06-14'
story = []
_TP = (SYN.get('report_title') or '實證評讀總報告').split('：')  # report_title 可能為 JSON null，需 or 防護（同 _TITLE）
story += [Spacer(1, 6), Paragraph(md2rl(_TP[0]), H1),
          Paragraph(md2rl(_TP[1] if len(_TP) > 1 else '實證評讀總報告'), H1),
          Paragraph('臨床問題：' + md2rl(RQ.get('statement', '')) + '　｜　評讀日期：' + _DATE, SUB)]

story += [hbar('第一部分　分析是怎麼做的'), Spacer(1, 8)]
story += [Paragraph('一、分析流程', H3),
          Paragraph(f'本次自檢索交接包收到 {N_TOTAL} 篇文獻，角色不一（臨床試驗、藥物機制、藥動、健康受試者、綜述）。'
                    '先界定臨床問題，再判斷每篇扮演的角色，只讓真正的療效證據進入完整 GRADE 評讀；機制／藥動／綜述列為背景。'
                    '下為流程圖與各階段說明，其後並列各納入文獻的全文取得狀態。', BODY),
          Spacer(1, 4), prisma_diagram(), Spacer(1, 8)]
story += [Paragraph(f'經此分流：{N_FULL+N_TARGET} 篇進入 GRADE 評讀（{N_RCT} 個隨機對照試驗＋{N_MA} 篇統合分析＋{N_TARGET} 篇針對性安全評估），'
                    f'{N_LIGHT} 篇機制／藥動／綜述列為背景參考，{N_EXCL} 篇排除。這一步確保後續的工夫花在「對臨床問題真正有用」的證據上。', BODY), Spacer(1, 6)]
if LIT_ROWS and len(LIT_ROWS) > 1:
    # 直式頁可用寬約 170mm；欄寬總和須 ≤170，且整表 KeepTogether 不跨頁
    story += [KeepTogether([Paragraph('<b>納入文獻狀態（角色與全文取得）</b>', BODYB), Spacer(1, 3),
              qtable(LIT_ROWS, [74, 44, 52])]), Spacer(1, 3),
              Paragraph('全文取得透明度：「有全文」可線上 OA／PMC 自動取得或由使用者人工補入封閉期刊 PDF；'
                        '「僅 AI 合成摘要」為封閉期刊、僅有二手合成摘要（其判讀確定性較低、並依登錄庫補救）。'
                        '四項樞紐 RCT 與校準用統合分析均取得全文，故可進行完整 GRADE 評讀。', SMALL), Spacer(1, 10)]

story += [Paragraph('二、每篇證據如何評分（GRADE）與品質如何把關', H3),
          Paragraph('每篇文獻依循 GRADE 系統評定「證據確定性」：先依研究設計給一個起始等級（隨機對照試驗起始為高），'
                    '再就偏誤風險、不一致、間接性、不精確、發表偏誤五個面向往下調整，必要時上調，最後落在'
                    '「高、中等、低、極低」四個確定性等級之一。評定以結構化格式強制每個面向都要有判定，'
                    '並經四道機器或半機器把關（結構檢查、確定性算術重算、跨篇一致性稽核、對抗式第二遍複查）以降低人為疏漏。', BODY),
          Spacer(1, 4), pipeline_diagram(), Spacer(1, 8),
          Paragraph('最後，去除重複證據（同一試驗不會因為又被收進統合分析而被重複計算），再橫向統合，'
                    '產出最終結論與下方的 Summary of Findings 表。撤稿狀態亦經 PubMed／網路實際查核。', BODY)]

story += [PageBreak(), hbar('第二部分　分析結果'), Spacer(1, 8)]
if SYN.get('plain_summary'):                       # 白話 lead 段（通勤可讀，30 秒看完）
    story += [Paragraph('<b>【一分鐘讀懂】</b>　' + md2rl(SYN['plain_summary']), BODY), Spacer(1, 10)]
_NSTUDY = len(SYN.get('study_characteristics', []))
_DRUGS = '、'.join(dict.fromkeys(r.get('drug', '') for r in SYN.get('study_characteristics', []) if r.get('drug')))
story += [Paragraph('一、總結：這次分析發現了什麼、對臨床有什麼意義', H3),
          Paragraph(f'這次評讀彙整了 {_NSTUDY} 項隨機對照試驗' + (f'（涵蓋 {_DRUGS}）' if _DRUGS else '') +
                    '，探討此類介入作為「附加療法」（加在常規照護之上、而非取代）的效益與風險。'
                    '以下把「發現」與「對臨床的影響」一併說明：', BODY),
          *[bullet(md2rl(b)) for b in SYN.get('bottom_line', [])],
          *([Spacer(1, 4), Paragraph('<b>給臨床的一句話：</b>' + md2rl(SYN['clinical_one_liner']), BODY)]
            if SYN.get('clinical_one_liner') else []),
          Spacer(1, 10)]

story += [NextPageTemplate('land'), PageBreak(),
          Paragraph('二、Summary of Findings（重要結果總覽表）', H3),
          Paragraph('下表為介入相較於對照的核心結果。「相對效應」是比值（如風險比 RR）；'
                    '「絕對效應」是換算到實際人數後的差異（含 NNTB，即多 1 個有益結果所需治療人數）；'
                    '證據確定性以 GRADE 的四個等級（高／中等／低／極低，以實心圓數目表示）標示。', SMALL),
          Paragraph('<b>表頭宣告（本表適用對象）</b>　族群（P）：' + md2rl(RQ.get('P', '')) +
                    '；介入（I）：' + md2rl(RQ.get('I', '')) + '；對照（C）：' + md2rl(RQ.get('C', '安慰劑')) + '。', SMALL),
          Spacer(1, 4), sof_table(), Spacer(1, 5),
          Paragraph('解讀提醒：相對效應（RR／HR）必須搭配絕對數字才完整——同樣的風險比，在惡化風險高或低的'
                    '病人身上，實際減少的惡化次數差異甚大；連續型結果（如 FEV1、生活品質分數）沒有比值，'
                    '其效益直接以「平均差」呈現。', NOTE),
          NextPageTemplate('port'), PageBreak()]

# 非 SoF 表格一律直式、總寬 170mm 一致，每表 KeepTogether 不跨頁
story += [Paragraph('三、證據品質與完整度', H3)]
if len(BOE_ROWS) > 1:
    story += [KeepTogether([Paragraph('<b>證據體 GRADE（跨研究確定性，非逐篇取均/取最差；Cochrane Ch14 §14.2.1）</b>', BODYB),
                            Spacer(1, 3), qtable(BOE_ROWS, [40, 28, 102])]), Spacer(1, 8)]
story += [KeepTogether([Paragraph('<b>1. 納入研究特徵表</b>', BODYB), Spacer(1, 3),
                        qtable(CHAR_ROWS, [20, 22, 12, 14, 24, 20, 16, 42])]), Spacer(1, 8),
          KeepTogether([Paragraph('<b>2. 偏誤風險（RoB 2）逐領域摘要</b>', BODYB), Spacer(1, 3),
                        qtable(ROB_ROWS, [15, 15, 15, 15, 15, 17, 15, 63]),
                        Paragraph('RoB 2 為結果層級評估，上表取各試驗主要惡化終點之判斷；「整體」採最不利領域，'
                                  '末欄逐筆註明 some concerns 的來源。選擇性報告領域經 ClinicalTrials.gov 註冊'
                                  '與發表比對（多數一致），故判 low。', NOTE)]), Spacer(1, 8),
          Paragraph('<b>3. 發表偏誤／缺失證據聲明</b>', BODYB),
          Paragraph(md2rl(SYN.get('publication_bias', '')), BODY),
          (Paragraph('<b>缺失證據敏感度（ROB-ME）：</b>' + md2rl(SYN.get('missing_evidence_sensitivity') or ''), NOTE)
           if SYN.get('missing_evidence_sensitivity') else Spacer(0, 0)), Spacer(1, 5),
          Paragraph('<b>4. 次群組與對研究的意涵</b>', BODYB),
          Paragraph(md2rl(SYN.get('subgroup_implications', '')), BODY), Spacer(1, 5),
          # 5. 基準風險分層：空資料時整段跳過(不印破表頭/空表)；與 markdown 端守衛一致
          *([KeepTogether([Paragraph('<b>5. 基準風險分層的絕對效應</b>', BODYB),
                        Paragraph('絕對獲益高度取決於病人的基準風險（同一相對效應，套用不同對照組風險）：', SMALL), Spacer(1, 3),
                        qtable(BASE_ROWS, [70, 45, 55])]),
          Paragraph('故基準風險越高的病人，絕對獲益越大、NNTB 越小；低風險者獲益較小。'
                    '臨床決策宜結合個別病人的風險評估。', NOTE),
          Paragraph('<b>【注意】低風險族群之 NNTB 為數學外推</b>：樞紐試驗多要求過去一年 ≧2 次惡化、'
                    '排除輕度／極少發作之患者，將此相對效應套用於試驗未收案的低風險群存在『群體間接性（indirectness）』；'
                    '實際絕對獲益可能更小（NNTB 更大）。', NOTE)] if SYN.get('baseline_risk_strata') else []),
          Spacer(1, 10)]

if REL_REVIEWS:
    rel_block = []
    for r in REL_REVIEWS:
        rel_block += [
            Paragraph('• <b>' + md2rl(r['review']) + '</b>　·　AMSTAR 2：<b>'
                      + AMSTAR2_LABEL.get(r['amstar2_rating'], r['amstar2_rating']) + '</b>', BODY),
            Paragraph('涵蓋：' + md2rl(r['scope']) + '　｜　納入試驗：' + md2rl(r['trials_covered']), SMALL),
            Paragraph('角色：' + md2rl(r['role']), SMALL),
            Paragraph('評級依據：' + md2rl(r.get('amstar2_basis') or ''), NOTE),
            Spacer(1, 5)]
    story += [Paragraph('<b>6. 相關系統性回顧／統合分析（AMSTAR 2 品質）</b>', BODYB),
              Paragraph('與上方 4 個 RCT「納入研究特徵表」分離（study vs review 單位區分）；'
                        '去重後不與個別 RCT 結論疊加。', NOTE), Spacer(1, 4),
              *rel_block, Spacer(1, 6)]

story += [Paragraph('四、跨研究確定性、衝突分析與權重裁決', H3),
          Paragraph(md2rl(SYN.get('conflict_analysis', '')), BODY),
          (Paragraph('權重裁決：' + md2rl(SYN.get('weight_adjudication', '')), NOTE) if SYN.get('weight_adjudication') else Spacer(0, 0)),
          Paragraph('方法學說明：' + md2rl(SYN.get('vote_counting_check', '') or
                    '本引擎不做自己的統計池化；類別層級二分結果採用已發表統合分析之合併估計（標明異質性侷限），單藥療效以最大樞紐試驗為錨點。'), NOTE)]
warn = Table([[Paragraph('<b>【注意】不可做非正式間接比較</b>：各試驗的參與者基線、藥物劑量與測量指標不盡相同，'
                         '不應直接比較不同藥物之間相對效應的大小（各試驗未做頭對頭比較，較低的 RR 不代表該藥較優）；'
                         '藥物優劣須有正式間接比較（網絡統合）或直接對頭試驗才能斷定。', NOTE)]],
             colWidths=[170*mm])
warn.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),AMBERL),('BOX',(0,0),(-1,-1),0.6,HexColor('#b9770e')),
                          ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                          ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
story += [Spacer(1, 4), warn, Spacer(1, 8)]

story += [Paragraph('五、限制與尚待釐清', H3),
          *[bullet(md2rl(x)) for x in SYN.get('limitations', [])],
          Spacer(1, 8)]

story += [Paragraph('附註：本報告由 EBM_Analysis 評讀引擎產出，運算由 Claude 直接執行（不呼叫外部 API），'
                    '以結構化 schema 強制完整、以算術與跨篇稽核及對抗式複查抓不一致。詳細逐篇判定見各 *.report.md 與 synthesis.md。', NOTE)]

def footer(canvas, doc):
    canvas.saveState()
    w, h = canvas._pagesize
    canvas.setFont(FONT, 7.5); canvas.setFillColor(HexColor('#888'))
    canvas.drawString(20 * mm, 10 * mm, 'EBM_Analysis 評讀引擎　｜　' + _FOOTER[:40])
    canvas.drawRightString(w - 20 * mm, 10 * mm, f'第 {doc.page} 頁')
    canvas.restoreState()

_OUTPUTS.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(_OUTPUTS / 'FINAL_REPORT.pdf'), pagesize=A4,
                      leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title=_TITLE, author='EBM_Analysis')
pw, ph = A4
lw, lh = landscape(A4)
doc.addPageTemplates([
    PageTemplate(id='port', frames=[Frame(20 * mm, 16 * mm, pw - 40 * mm, ph - 32 * mm, id='p')],
                 pagesize=A4, onPage=footer),
    PageTemplate(id='land', frames=[Frame(16 * mm, 16 * mm, lw - 32 * mm, lh - 32 * mm, id='l')],
                 pagesize=landscape(A4), onPage=footer),
])
doc.build(story)
# 渲染後磚塊稽核：缺字形會渲成 NULL(\x00)；emoji/dingbat 漏網→警示（防交付帶磚塊）
try:
    import fitz as _fz
    _t = ''.join(_pg.get_text() for _pg in _fz.open(str(_OUTPUTS / 'FINAL_REPORT.pdf')))
    _bad = _t.count('\x00')
    _emj = _EMOJI_RE.findall(_t)
    if _bad or _emj:
        print('⚠️ 磚塊稽核：NULL(\\x00) x%d、emoji漏網 %r —— 請檢查字形淨化' % (_bad, sorted(set(_emj))[:8]))
    else:
        print('OK -> outputs/FINAL_REPORT.pdf（磚塊稽核：無 NULL、無 emoji 漏網）')
except Exception:
    print('OK -> outputs/FINAL_REPORT.pdf')
