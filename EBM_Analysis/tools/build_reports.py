# -*- coding: utf-8 -*-
"""無 API：把 cache/ 裡「我（Claude）逐階段產出並驗證過的 JSON」渲染成人讀報告。
報告永遠由結構化 JSON 渲染，不與判定漂移。

  python tools/build_reports.py
產出：outputs/{paper}.report.md、outputs/synthesis.md、outputs/ledger.csv
"""
import sys
import csv
import json
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir  # noqa: E402  執行期資料導向工作夾（見 workdir.py）
CACHE = Path(workdir.cache_dir())
OUTPUTS = Path(workdir.outputs_dir())
# 確定性符號：用 ○(U+25CB，CJK 字型有字形) 而非 ◯(U+25EF，msjh 缺字形)，避免 .md 轉 PDF 出磚塊
SYM = {"high": "⊕⊕⊕⊕", "moderate": "⊕⊕⊕○", "low": "⊕⊕○○", "very_low": "⊕○○○"}
AMSTAR2_SYM = {"high": "高信心", "moderate": "中等信心", "low": "低信心", "critically_low": "極低信心"}
ORDER = ["very_low", "low", "moderate", "high"]
# ledger.csv 固定欄位（單一真相）：所有列照此建，不依資料動態決定欄位（AGENTS.md 資料表硬規則）
LEDGER_COLS = ["paper_id", "status", "track", "grade_start", "worst_outcome_certainty", "flags", "updated"]


def load(pid, ph):
    p = CACHE / f"{pid}.{ph}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def paper_ids():
    return sorted({p.name.split(".")[0] for p in CACHE.glob("*.p1.json")})


def report(pid):
    p1, p3, pp = load(pid, "p1"), load(pid, "p3"), load(pid, "p4")
    if not (p1 and p3 and pp):
        return
    L = [f"# EBM 評讀：{pp.get('paper_id', pid)}", "", "## PICO", pp.get("pico", ""), ""]
    bl = pp.get("bottom_line", {})
    L += ["## 🎯 核心結論", bl.get("text", ""), "",
          f"> 確定性：{SYM.get(bl.get('certainty',''), bl.get('certainty',''))}"
          f"　措辭層級：{bl.get('wording_tier','')}", "", "## GRADE 逐結果"]
    for o in p3.get("outcomes", []):
        L.append(f"- **{o['outcome_name']}**：{SYM.get(o['certainty_final'], o['certainty_final'])}"
                 f"（起始 {o.get('certainty_start','')}）")
    L += ["", "## ⚖️ 證據強度儀表板", pp.get("dashboard", ""), "", "## ⚠️ 臨床限制"]
    cav = pp.get("caveats", {}) or {}
    labels = {"surrogate": "替代結果", "harms": "不良反應覆蓋", "coi": "利益衝突",
              "imprecision": "不精確", "nma": "NMA", "nonreporting": "非報告偏誤"}
    hit = [f"- **{labels[k]}**：{cav[k]}" for k in labels if cav.get(k)]
    L += hit if hit else ["（無觸發護欄）"]
    (OUTPUTS / f"{pid}.report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def synthesis():
    p = CACHE / "_synthesis.json"
    if not p.exists():
        return
    syn = json.loads(p.read_text(encoding="utf-8"))
    syn = syn.get("synthesis", syn)
    if not syn:
        return
    L = ["# 統合報告 (Synthesis)", ""]

    # Summary of Findings 表（若有）
    sof = syn.get("sof")
    if sof:
        sym = {"high": "高 ⊕⊕⊕⊕", "moderate": "中 ⊕⊕⊕◯", "low": "低 ⊕⊕◯◯", "very_low": "極低 ⊕◯◯◯"}
        L += ["## Summary of Findings（SoF 表）", ""]
        cp = CACHE / "_corpus.json"
        if cp.exists():
            rq = json.loads(cp.read_text(encoding="utf-8")).get("review_question", {})
            L += ["**表頭宣告**　"
                  f"族群（P）：{rq.get('P','')}；介入（I）：{rq.get('I','')}；對照（C）：{rq.get('C','')}", ""]
        L += [
              "| 結果 | 對照組風險 | 介入組對應風險 | 絕對效應 | 相對效應 | 參與者(研究) | 確定性 | 評論 |",
              "|---|---|---|---|---|---|---|---|"]
        for r in sof:
            L.append("| " + " | ".join([
                r.get("outcome", ""), r.get("assumed_control_risk", ""),
                r.get("corresponding_risk", ""), r.get("absolute_effect", ""),
                r.get("relative_effect", ""), r.get("n_participants_studies", ""),
                sym.get(r.get("certainty", ""), r.get("certainty", "")),
                (r.get("comment") or "")]) + " |")
        L.append("")

    order = [("consistency", "數據一致性分析"), ("vote_counting_check", "計票準則查核"),
             ("swim_check", "SWiM／無 MA 綜整查核"), ("overlap_check", "多來源重疊／間接比較查核"),
             ("nma_check", "NMA 查核"), ("conflict_analysis", "證據對抗"),
             ("weight_adjudication", "終極權重裁決")]
    for k, t in order:
        if syn.get(k):
            L += [f"## {t}", syn[k], ""]
    (OUTPUTS / "synthesis.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def ledger():
    rows = []
    for pid in paper_ids():
        p2 = load(pid, "p2") or {}
        p3 = load(pid, "p3")
        p4 = load(pid, "p4") or {}
        cs = [o.get("certainty_final") for o in (p3 or {}).get("outcomes", [])]
        cs = [c for c in cs if c in ORDER]  # 濾掉非法/缺值，避免 ORDER.index 對非列舉值拋 ValueError 連帶整份渲染中止
        worst = min(cs, key=ORDER.index) if cs else ""
        flags = []
        ic = p2.get("integrity_check", {})
        if ic.get("retraction"):
            flags.append("retraction")
        if ic.get("erratum_or_eoc"):
            flags.append("erratum/EoC")
        for k in ("coi", "nonreporting", "surrogate", "harms"):
            if (p4.get("caveats", {}) or {}).get(k):
                flags.append(k)
        status = "ok" if p3 else ("in_progress" if load(pid, "p1") else "pending")
        rows.append({"paper_id": pid, "status": status, "track": p2.get("track", ""),
                     "grade_start": p2.get("grade_start", ""), "worst_outcome_certainty": worst,
                     "flags": ";".join(flags), "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    # 寫檔前 shape 驗證：每列鍵集合必須等於固定欄位，不靜默寫出殘缺表（AGENTS.md 資料表硬規則）
    for r in rows:
        assert set(r) == set(LEDGER_COLS), f"ledger 列欄位不符 EXPECTED：{set(r) ^ set(LEDGER_COLS)}（paper_id={r.get('paper_id')}）"
    with open(OUTPUTS / "ledger.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def _row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def final_report():
    """從 cache/_synthesis.json（＋_corpus.json）自動組出 FINAL_REPORT.md（單一真相來源）。"""
    p = CACHE / "_synthesis.json"
    if not p.exists():
        return False
    syn = json.loads(p.read_text(encoding="utf-8"))
    syn = syn.get("synthesis", syn)
    cp = CACHE / "_corpus.json"
    rq = json.loads(cp.read_text(encoding="utf-8")).get("review_question", {}) if cp.exists() else {}

    L = [f"# {syn.get('report_title', '實證評讀總報告')}", ""]
    if syn.get("plain_summary"):                       # 白話 lead 段（通勤可讀，30 秒看完）
        L += ["> 📋 **一分鐘讀懂**", ">", "> " + str(syn["plain_summary"]).replace("\n", "\n> "), ""]
    if rq.get("statement"):
        L += [f"**臨床問題**：{rq['statement']}", ""]
    sc = syn.get("study_characteristics", [])
    if sc:
        drugs = "、".join(dict.fromkeys(r["drug"] for r in sc))
        # 設計感知：證據體標籤由 syn.evidence_base_label 決定（NRSI 不得誤稱『隨機對照試驗』）。
        _eb = syn.get("evidence_base_label") or "項隨機對照試驗"
        L += [f"**證據基礎**：{len(sc)} {_eb}，涵蓋 {drugs}。詳見各 `*.report.md` 與 `synthesis.md`。", ""]
    L += ["---", ""]

    # ★ 標準版型＝Cochrane 後半段 6 段（與 PDF build_grade_pdf --layout cochrane5 同步；
    #   2026-06 使用者定為 analysis 階段 PDF/MD 統一格式）。
    # 〇、文獻篩選流程（PRISMA-style；2026-06 使用者要求新增於最前）
    flow = syn.get("screening_flow", [])
    if flow:
        L += ["## 〇、文獻篩選流程（Study Selection Flow，PRISMA-style）", "",
              "> 從多源廣蒐到最終納入分析的逐階段識別／排除／留存（檢索→篩選→收斂）。", "",
              _row(["階段", "流入", "排除（理由）", "留存／結果", "說明"]), _row(["---"] * 5)]
        for f in flow:
            L.append(_row([f.get("stage", ""), f.get("start", ""), f.get("excluded", ""),
                           f.get("remain", ""), f.get("note", "") or ""]))
        L.append("")

    # 一、納入研究特徵摘要表
    if sc:
        L += ["## 一、納入研究特徵摘要表（Characteristics of Included Studies）", "",
              "> 證明各試驗臨床上可比（Cochrane Ch9）：設計／基準風險／介入·對照精確內容／追蹤。", "",
              _row(["試驗", "研究設計", "N／族群", "介入臂", "對照臂", "追蹤", "主要終點"]), _row(["---"] * 7)]
        for r in sc:
            # 設計感知：有 design_detail 用之（NRSI），否則回退 RCT 預設描述。
            _dd = r.get("design_detail") or ((r.get("phase", "") + "；多中心雙盲平行"))
            L.append(_row([r["trial"], _dd, r["n"],
                           f'{r["drug"]}（{r["dose"]}）', r["comparator"], r["duration"], r["primary_outcome"]]))
        L.append("")
        for st in syn.get("baseline_risk_strata", []):
            L.append(f"- 基準風險分層：{st['baseline_risk']} → {st['absolute_reduction']}")
        L.append("")

    # 二、個別試驗偏誤風險評估
    rs = syn.get("rob_summary", [])
    if rs:
        _rsec = syn.get("rob_section") or {}
        _rtitle = _rsec.get("title") or "個別試驗偏誤風險評估（Risk of Bias 2）"
        _rintro = _rsec.get("intro") or "逐篇逐領域 RoB 2（Cochrane Ch8）；對 some concerns/high 具體點出瑕疵來源。"
        _rdef = ["試驗", "隨機化", "偏離介入", "缺失資料", "結果測量", "選擇性報告", "整體", "瑕疵說明（concern 來源）"]
        _rcols = ((_rsec.get("columns") or _rdef) + _rdef[len(_rsec.get("columns") or _rdef):])[:8]
        L += [f"## 二、{_rtitle}", "", f"> {_rintro}", "",
              _row(_rcols), _row(["---"] * 8)]
        for r in rs:
            L.append(_row([r["trial"], r["randomization"], r["deviations"], r["missing_data"], r["measurement"],
                           r["selective_reporting"], f"**{r['overall']}**",
                           (r.get("evidence_basis", "") + "：" + (r.get("note", "") or ""))]))
        L.append("")

    # 三、數據綜整與統合分析（Meta-Analysis）
    ma = syn.get("meta_analysis", [])
    if ma:
        L += ["## 三、數據綜整與統合分析（Data Synthesis／Meta-Analysis）", "",
              "> 逐核心結局之池化合併效應＋異質性 I²（Cochrane Ch10）；未池化者說明理由。", "",
              _row(["核心結局", "模型", "合併效應（95% CI）", "I²", "逐試驗效應", "絕對效應換算", "異質性判讀／理由"]), _row(["---"] * 7)]
        _mdl = {"fixed": "固定效應", "random": "隨機效應", "not_pooled": "未池化"}
        for m in ma:
            eff = m.get("pooled_effect", "") + (f'（{m.get("ci","")}）' if m.get("ci") else "")
            L.append(_row([m["outcome"], _mdl.get(m["model"], m["model"]), eff, m.get("i2") or "—",
                           m.get("per_study") or "", m.get("absolute") or "", m["heterogeneity"]]))
        L.append("")
    for k, t in [("consistency", "數據一致性"), ("conflict_analysis", "證據對抗"),
                 ("weight_adjudication", "權重裁決與整體判讀")]:
        if syn.get(k):
            L += [f"**{t}**：{syn[k]}", ""]

    # 四、GRADE 證據確定性評級
    boe = syn.get("body_of_evidence", [])
    if boe:
        L += ["## 四、GRADE 證據確定性評級（Evidence Profile）", "",
              "> 逐核心結局自 RCT 起始『高』，跑 5 大下調領域結算（Cochrane Ch14）。", "",
              _row(["核心結局", "確定性", "下調領域結算（依據）"]), _row(["---"] * 3)]
        for b in boe:
            L.append(_row([b["outcome"], SYM.get(b["certainty"], b["certainty"]) + " " + b["certainty"], b["basis"]]))
        L.append("")

    # 五、發現摘要表（SoF）與臨床建議
    sof = syn.get("sof", [])
    if sof:
        L += ["## 五、發現摘要表（SoF）與臨床決策建議", ""]
        if rq:
            L += [f"**適用對象**　P：{rq.get('P','')}；I：{rq.get('I','')}；C：{rq.get('C','')}", ""]
        L += ["> 相對＋絕對並列（每 1000 人）＋NNTB/NNTH＋95% CI；跨無效線/資料不足者不計 NNT（Cochrane Ch14·15）。", "",
              _row(["臨床結局（時框）", "假設對照風險", "對應介入風險", "絕對效應差（每 1000 人）＋NNT", "相對效應（95% CI）", "N（研究）", "確定性", "降級腳註"]), _row(["---"] * 8)]
        for r in sof:
            L.append(_row([r.get("outcome", ""), r.get("assumed_control_risk", ""), r.get("corresponding_risk", ""),
                           r.get("absolute_effect", ""), r.get("relative_effect", ""), r.get("n_participants_studies", ""),
                           SYM.get(r.get("certainty", ""), r.get("certainty", "")), r.get("comment") or ""]))
        L.append("")
        for fn in syn.get("sof_footnotes", []):
            L.append(f"- {fn}")
        L.append("")
        L += ["### 臨床建議底線（Authors' Conclusions）", ""]
        L += [f"- {b}" for b in syn.get("bottom_line", [])]
        if syn.get("subgroup_implications"):
            L += ["", f"**利弊平衡與次群組**：{syn['subgroup_implications']}"]
        L += ["", "> 【Cochrane Ch15 規範】提供利弊平衡與決策指引，但不下強制醫囑（不寫『必須全面改用』）；"
              "最終決策須納入個別病患價值觀、偏好與在地資源。", ""]
        if syn.get("publication_bias"):
            L += [f"**發表偏誤／利益衝突**：{syn['publication_bias']}", ""]
        lim = syn.get("limitations", [])
        if lim:
            L += ["**限制與尚待釐清**："] + [f"- {x}" for x in lim] + [""]

    # 六、給臨床的一句話
    if syn.get("clinical_one_liner"):
        L += ["## 六、給臨床的一句話（Clinical Bottom Line）", "", f"> **{syn['clinical_one_liner']}**", ""]

    L += ["---", "",
          "> 附註：本報告由 EBM_Analysis 評讀引擎自動產出（運算由 Claude 直接執行、無外部 API）；"
          "內容由結構化 JSON（`cache/_synthesis.json` 等）渲染、不與判定漂移。逐篇判定見各 `*.report.md`。"]
    (OUTPUTS / "FINAL_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return True


def main():
    # 渲染前：自動補 screening_flow（PRISMA 篩選流程）——自 _search_report.flow＋corpus 衍生，免手填防漂移
    # （Antigravity 第十輪 🟡c）。僅當 _synthesis.json 缺 screening_flow 才寫（手填值保留；--refresh-flow 強制重建）。
    if (CACHE / "_synthesis.json").exists():
        try:
            import build_screening_flow as _bsf
            _flow = _bsf.build(str(CACHE))
            _w, _r = _bsf.merge_into_synthesis(str(CACHE), _flow, force=("--refresh-flow" in sys.argv))
            if _w:
                sys.stderr.write(f"· screening_flow 自動帶入：{_r}\n")
        except Exception as _e:
            sys.stderr.write(f"· screening_flow 自動帶入略過（{_e}）\n")
    # 渲染前硬 gate：統合自我一致性（RoB2 overall=最不利／贊助偏誤歸發表偏誤／SoF 合併效應註來源）
    if (CACHE / "_synthesis.json").exists() and "--skip-consistency" not in sys.argv:
        try:
            import selfcheck_consistency as _sc
            _fails = _sc.check()
        except Exception as e:
            # 失敗關閉（fail-closed）：一致性硬 gate 無法執行時，不可當作通過而靜默出報告；
            # 中止渲染，要人修環境，或明確以 --skip-consistency 略過。
            sys.stderr.write(f"❌ 渲染中止：一致性 gate 無法執行（{e}）。修好後重跑，確需略過用 --skip-consistency。\n")
            sys.exit(1)
        if _fails:
            sys.stderr.write("❌ 渲染中止：統合報告未通過自我一致性檢查（%d）——\n" % len(_fails))
            for f in _fails:
                sys.stderr.write("  - " + f + "\n")
            sys.stderr.write("  修正 cache/_synthesis.json 後重跑；確需略過用 --skip-consistency。\n")
            sys.exit(1)
    OUTPUTS.mkdir(exist_ok=True)
    for pid in paper_ids():
        report(pid)
    synthesis()
    fr = final_report()
    n = ledger()
    extra = " / FINAL_REPORT.md" if fr else ""
    # 標準成品＝MD＋PDF 同格式（Cochrane 6 段）：MD 寫完即連帶產 PDF，確保兩者同步、不漏 PDF。
    pdf_made = ""
    if fr and "--no-pdf" not in sys.argv:
        try:
            import build_grade_pdf
            build_grade_pdf.build(str(CACHE / "_synthesis.json"), str(OUTPUTS / "FINAL_REPORT.pdf"), layout="cochrane5")
            pdf_made = " / FINAL_REPORT.pdf"
        except SystemExit:
            sys.stderr.write("⚠️ 缺 reportlab，未產 PDF（pip install reportlab 後重跑，或 build_grade_pdf.py 單獨產）。\n")
        except Exception as e:
            sys.stderr.write(f"⚠️ PDF 產生失敗（{str(e)[:80]}）；MD 已產出，可單獨跑 build_grade_pdf.py。\n")
    # 自動更新 run-state 指標檔（成品位置＋階段），避免座標檔走舊
    try:
        import run_state
        run_state.update(stage="phase4_rendered",
                         artifacts={"final_report_md": str(OUTPUTS / "FINAL_REPORT.md"),
                                    "synthesis_md": str(OUTPUTS / "synthesis.md"),
                                    "ledger_csv": str(OUTPUTS / "ledger.csv")})
        run_state.autofill()
    except Exception:
        pass
    print(f"✅ {n} papers → outputs/（report.md / synthesis.md{extra}{pdf_made} / ledger.csv）")


if __name__ == "__main__":
    main()
