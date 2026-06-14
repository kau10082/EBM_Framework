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
CACHE = ROOT / "cache"
OUTPUTS = ROOT / "outputs"
SYM = {"high": "⊕⊕⊕⊕", "moderate": "⊕⊕⊕◯", "low": "⊕⊕◯◯", "very_low": "⊕◯◯◯"}
AMSTAR2_SYM = {"high": "高信心", "moderate": "中等信心", "low": "低信心", "critically_low": "極低信心"}
ORDER = ["very_low", "low", "moderate", "high"]


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
        cs = [o["certainty_final"] for o in (p3 or {}).get("outcomes", [])]
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
    cols = ["paper_id", "status", "track", "grade_start", "worst_outcome_certainty", "flags", "updated"]
    with open(OUTPUTS / "ledger.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
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
    if rq.get("statement"):
        L += [f"**臨床問題**：{rq['statement']}", ""]
    sc = syn.get("study_characteristics", [])
    if sc:
        drugs = "、".join(dict.fromkeys(r["drug"] for r in sc))
        L += [f"**證據基礎**：{len(sc)} 項隨機對照試驗，涵蓋 {drugs}。詳見各 `*.report.md` 與 `synthesis.md`。", ""]
    L += ["---", ""]

    # 一、總結
    L += ["## 一、總結（Bottom Line）", ""]
    L += [f"- {b}" for b in syn.get("bottom_line", [])]
    L.append("")

    # 二、SoF
    sof = syn.get("sof", [])
    if sof:
        L += ["## 二、Summary of Findings（重要結果總覽表）", ""]
        if rq:
            L += [f"**表頭宣告（適用對象）**　族群（P）：{rq.get('P','')}；介入（I）：{rq.get('I','')}；對照（C）：{rq.get('C','')}", ""]
        L += [_row(["結果", "對照組風險", "介入組對應風險", "絕對效應", "相對效應", "參與者(研究)", "確定性", "評論"]),
              _row(["---"] * 8)]
        for r in sof:
            L.append(_row([r.get("outcome", ""), r.get("assumed_control_risk", ""), r.get("corresponding_risk", ""),
                           r.get("absolute_effect", ""), r.get("relative_effect", ""), r.get("n_participants_studies", ""),
                           SYM.get(r.get("certainty", ""), r.get("certainty", "")), r.get("comment") or ""]))
        L += ["", "> 解讀提醒：相對效應（RR/HR）須搭配絕對數字才完整；連續型結果（FEV1、生活品質）沒有比值，效益以「平均差」呈現。", ""]

    # 三、證據品質與完整度
    if sc or syn.get("rob_summary") or syn.get("publication_bias"):
        L += ["## 三、證據品質與完整度", ""]
        if sc:
            L += ["### 1. 納入研究特徵表", "",
                  _row(["試驗", "藥物", "期別", "N", "劑量(每日一次)", "療程", "對照", "主要終點"]), _row(["---"] * 8)]
            for r in sc:
                L.append(_row([r["trial"], r["drug"], r["phase"], r["n"], r["dose"], r["duration"], r["comparator"], r["primary_outcome"]]))
            L.append("")
        rs = syn.get("rob_summary", [])
        if rs:
            L += ["### 2. 偏誤風險（RoB 2）逐領域摘要", "",
                  _row(["試驗", "隨機化", "偏離介入", "缺失資料", "結果測量", "選擇性報告", "整體"]), _row(["---"] * 7)]
            for r in rs:
                L.append(_row([r["trial"], r["randomization"], r["deviations"], r["missing_data"], r["measurement"], r["selective_reporting"], f"**{r['overall']}**"]))
            L.append("")
        if syn.get("publication_bias"):
            L += ["### 3. 發表偏誤／缺失證據聲明", "", syn["publication_bias"], ""]
        if syn.get("subgroup_implications"):
            L += ["### 4. 次群組與對研究的意涵", "", syn["subgroup_implications"], ""]
        strata = syn.get("baseline_risk_strata", [])
        if strata:
            L += ["### 5. 基準風險分層的絕對效應", "",
                  _row(["基準惡化風險（對照組）", "對應介入率", "每人每年絕對減少"]), _row(["---"] * 3)]
            for r in strata:
                L.append(_row([r["baseline_risk"], r["corresponding"], r["absolute_reduction"]]))
            L += ["", "> 頻繁惡化（高 BSI）患者的絕對獲益最大、NNTB 最小；輕度患者獲益較小。", ""]
        rr = syn.get("related_reviews", [])
        if rr:
            L += ["### 6. 相關系統性回顧／統合分析（AMSTAR 2 品質）", "",
                  "> 與上方 4 個 RCT「納入研究特徵表」分離（study vs review 單位區分）；去重後不與個別 RCT 結論疊加。", "",
                  _row(["回顧（類型）", "涵蓋範圍", "納入試驗", "AMSTAR 2 信心", "角色"]), _row(["---"] * 5)]
            for r in rr:
                L.append(_row([r["review"], r["scope"], r["trials_covered"],
                               f"**{AMSTAR2_SYM.get(r['amstar2_rating'], r['amstar2_rating'])}**", r["role"]]))
            L.append("")
            for r in rr:
                if r.get("amstar2_basis"):
                    L += [f"- **{r['review']}** 評級依據：{r['amstar2_basis']}"]
            L.append("")

    # 四、跨篇統合與結論
    L += ["## 四、跨篇統合與結論", ""]
    for k, t in [("consistency", "數據一致性"), ("conflict_analysis", "證據對抗（為何單藥 vs 類別確定性不同）"),
                 ("weight_adjudication", "權重裁決與整體結論")]:
        if syn.get(k):
            L += [f"### {t}", "", syn[k], ""]

    # 五、限制
    lim = syn.get("limitations", [])
    if lim:
        L += ["## 五、限制與尚待釐清", ""] + [f"- {x}" for x in lim] + [""]

    # 六、給臨床
    if syn.get("clinical_one_liner"):
        L += ["## 六、給臨床的一句話", "", f"> **{syn['clinical_one_liner']}**", ""]

    L += ["---", "",
          "> 附註：本報告由 EBM_Analysis 評讀引擎自動產出（運算由 Claude 直接執行、無外部 API）；"
          "內容由結構化 JSON（`cache/_synthesis.json` 等）渲染、不與判定漂移。逐篇判定見各 `*.report.md`。"]
    (OUTPUTS / "FINAL_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return True


def main():
    OUTPUTS.mkdir(exist_ok=True)
    for pid in paper_ids():
        report(pid)
    synthesis()
    fr = final_report()
    n = ledger()
    extra = " / FINAL_REPORT.md" if fr else ""
    print(f"✅ {n} papers → outputs/（report.md / synthesis.md{extra} / ledger.csv）")


if __name__ == "__main__":
    main()
