# -*- coding: utf-8 -*-
"""
report_check.py — SR 檢索報告『版型/內容』硬 gate（v0.22 簡化版：5 核心段落）
==============================================================================
2026-06 使用者定版：search 階段 PDF 縮為 **5 個核心段落**：
  1. 檢索基本參數（PICO 簡述／檢索日期(精確到日)／資料庫清單／限制條件）
  2. 具體檢索策略（至少一組真實布林查詢字串，可重製，MECIR）
  3. PRISMA 文獻篩選流程數據（漏斗各階段數字＋二分閉合）
  4. 最終納入證據清單（核心 RCT／重要 MA）：欄位＝研究名稱·標題·DOI·PMID·PubMed/Crossref 驗證
  5. 進行中試驗：欄位＝登錄號·標題

讀 _search_report.json，機器核對上述 5 段必備內容，任一不成立即 FAIL。
（沿用仍適用的整合教訓：真實 query 字串、研究名稱非佔位、標題非空、識別碼齊、PRISMA 數、二分閉合。）

用法：python report_check.py --in _search_report.json
程式內：import report_check; fails = report_check.check(data)
"""
import sys, re, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

PLACEHOLDER_STUDY = ("待確認", "請見", "pending", "未命名", "tbd", "待定")
PLACEHOLDER_TITLE = ("(無標題)", "（無標題）", "請見pmid", "見pmid", "no title", "")

def check(data):
    fails = []
    # ── 段1 檢索基本參數 ──
    sd = str(data.get("search_date", "")).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", sd):
        fails.append(f"段1 檢索日期須精確到日 YYYY-MM-DD（實得『{sd}』；MECIR 時效性）")
    if not data.get("pico") or not isinstance(data.get("pico"), dict):
        fails.append("段1 缺 PICO 簡述（pico）")
    if not data.get("databases") or not isinstance(data.get("databases"), list):
        fails.append("段1 缺資料庫清單（databases，須條列涵蓋的資料庫/註冊平台）")
    if not str(data.get("limits", "")).strip():
        fails.append("段1 缺限制條件（limits，須誠實交代是否套 RCT filter／語言／年份限制）")
    # ── 段2 具體檢索策略：至少一組真實布林字串 ──
    strat = data.get("search_strategy", [])
    if not strat:
        fails.append("段2 缺具體檢索策略（search_strategy）：須保留至少一組實際送出的布林查詢字串")
    else:
        def _is_real_query(q):
            q = str(q or "")
            return len(q) >= 30 and (re.search(r"\bAND\b|\bOR\b", q) or "[tiab]" in q.lower() or "[" in q)
        if not any(_is_real_query(s.get("query")) for s in strat if not s.get("skip")):
            fails.append("段2 無任何『真實布林查詢字串』（含 AND/OR 或欄位標籤）：不能只寫關鍵字，至少一腿(如 PubMed)須一字不漏貼出")
    # ── 段3 PRISMA 流程數據 ──
    pf = data.get("prisma_flow")
    if not pf:
        fails.append("段3 缺 PRISMA 流程數據（prisma_flow）：須含 identification/screening/included 等階段數字")
    elif isinstance(pf, dict):
        miss = [k for k in ("identification", "screening", "included") if pf.get(k) in (None, "")]
        if miss:
            fails.append(f"段3 prisma_flow 缺/空欄位 {miss}（0 為合法值）")
    fc = data.get("funnel_closure", "")
    if not re.search(r"切題.*離題|\d+\s*\+\s*\d+\s*=\s*\d+", fc):
        fails.append("段3 funnel_closure 缺『嚴格篩二分』算式（切題+離題=內容可篩數）")
    # ── 段4 最終納入證據清單 ──
    inc = data.get("included_studies", [])
    if not inc:
        fails.append("段4 缺最終納入證據清單（included_studies 空）")
    for grp in inc:
        name = str(grp.get("study", ""))
        if any(p in name.lower() for p in PLACEHOLDER_STUDY):
            fails.append(f"段4 研究名稱為佔位『{name}』：須填真實試驗/研究名")
        for rep in grp.get("reports", []):
            if not isinstance(rep, (list, tuple)) or len(rep) != 4:
                fails.append(f"[{name}] 報告元組須 4 欄(title,pmid,doi,verified)，實得 {len(rep) if hasattr(rep,'__len__') else '?'}")
                continue
            title, pmid, doi, ver = rep
            if not str(title).strip() or str(title).strip().lower() in PLACEHOLDER_TITLE:
                fails.append(f"[{name}] 報告標題空/佔位（pmid={pmid}）")
            if not str(pmid).strip() and not str(doi).strip():
                fails.append(f"[{name}] 報告無 PMID 也無 DOI（title={str(title)[:30]}）：識別碼至少一個；皆無須顯式『缺』")
            if not str(ver).strip() or str(ver).strip() in ("?", "？"):
                fails.append(f"[{name}] 缺 PubMed/Crossref 驗證欄（pmid={pmid}）")
    blob = json.dumps(inc, ensure_ascii=False)
    if re.search(r"另含\s*\d+\s*篇|以下略|共\s*\d+\s*篇\)", blob):
        fails.append("段4 出現『另含 N 篇/以下略』省略：納入報告須逐筆列全")
    # ── 段5 進行中試驗 ──
    ot = data.get("ongoing_trials")
    if not ot:
        fails.append("段5 缺『進行中試驗』表（ongoing_trials 空）：CT.gov 招募中/未完成試驗須列")
    else:
        for r in ot:
            if not isinstance(r, (list, tuple)) or len(r) != 2:
                fails.append(f"段5 進行中試驗元組須 2 欄(登錄號,標題)，實得 {len(r) if hasattr(r,'__len__') else '?'}")
                continue
            if not str(r[0]).strip():
                fails.append(f"段5 進行中試驗缺登錄號（標題={str(r[1])[:30]}）")
    return fails

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="infile", required=True)
    a = ap.parse_args()
    p = Path(a.infile)
    if not p.exists():
        print(f"⏭  找不到 {a.infile}"); sys.exit(0)
    fails = check(json.loads(p.read_text(encoding="utf-8")))
    if fails:
        print("❌ 報告版型/內容檢查未過（5 段制）：")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 報告版型/內容通過（5 段：檢索參數·真實字串·PRISMA·納入清單·進行中試驗）。")

if __name__ == "__main__":
    main()
