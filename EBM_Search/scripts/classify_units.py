# -*- coding: utf-8 -*-
"""
classify_units.py — ⑦ 決定納入單位：以『標題＋摘要(方法學內容)』精確分類，非只靠標題/pubtype。
================================================================================
讀 ⑥ 乾淨候選(g6_verified.json, verdict=VERIFIED) ＋ ②c 摘要(g2c_FINAL_content.json) ＋
聯集(g1_raw_union.json, 取 NCT/sources)。對每筆以『標題＋摘要』判：
  • 研究設計（SR/MA → 指引 → 試驗計畫書 → RCT → 觀察性 → 經濟 → 綜述/其他）——優先序見下。
  • 若 RCT：偵測 NCT 號／試驗縮寫（word-boundary，且排除『IMPACT of/on』這類常用字誤併），
    並判**對照臂是否含 LABA/LAMA 雙支擴**（讀摘要方法學，可用 umeclidinium/vilanterol 等
    『在比較情境出現』的藥對）→ 區分『核心:三合一 vs LABA/LAMA』與『三合一 vs ICS/LABA 或安慰劑』。
  • RCT 依 NCT/試驗名歸併為 Study、報告數對帳。
背景(SR/MA/指引/觀察/經濟/綜述)＝不計入原始研究納入數，作引文追蹤種子與討論對照。

定位：rapid-review 輔助（單一 AI、未達 MECIR 雙人獨立）；最終納入/精確報告連結建議人工覆核。
用法：python classify_units.py --cache <dir> [--out g7_units.json]
"""
import sys, re, json, argparse
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# 已知樞紐三合一試驗 NCT → 試驗名（abstract 常附 NCT，最可靠的歸併鍵）
NCT_TRIAL = {
    "NCT02164513":"IMPACT","NCT02465567":"ETHOS","NCT02497001":"KRONOS","NCT02345161":"FULFIL",
    "NCT01917331":"TRILOGY","NCT02579850":"TRIBUTE","NCT01911364":"TRINITY","NCT03478683":"ETHOS-ext",
    "NCT03142362":"FULFIL-ext","NCT04636437":"TRIVERSYTI",
}
ACR = re.compile(r"\b(IMPACT|ETHOS|KRONOS|FULFIL|TRILOGY|TRIBUTE|TRINITY|TRIVERSYTI|TRISTAR)\b(?!\s+(?:of|on|study population)\b)")
TRIALCTX = re.compile(r"\b(trial|study|randomi[sz]ed|cohort|programme|program)\b", re.I)
NCTRE = re.compile(r"NCT0?\d{6,8}", re.I)

R_SRMA  = re.compile(r"meta-?analys|systematic review|we searched (pubmed|embase|medline|cochrane|databases|the)|prospero|pooled (analysis|data|estimate)|network meta|random-?effects model|fixed-?effects model|cochrane (central|library|database)|search strategy|inclusion criteria were", re.I)
# 指引：只認 pubtype 與『標題』訊號（abstract 內 recommendation/management of 太常見會誤併，故不掃 abstract）
R_GUIDE_TITLE = re.compile(r"guideline|gold (report|science committee|20\d\d|strategy document)|recommendations for the (diagnosis|management|treatment|pharmacolog)|consensus (statement|document)|position (paper|statement)|practice parameter|clinical practice recommendation", re.I)
R_PROTO = re.compile(r"study protocol|protocol for|rationale and design|^design of|methods? (paper|of a)|statistical analysis plan", re.I)
R_RCT   = re.compile(r"randomi[sz]ed|randomly (assigned|allocated)|double-?blind|placebo-?controlled|active-?controlled|parallel-?group|1:1 (randomi|ratio)|were assigned to receive", re.I)
R_OBS   = re.compile(r"real-?world|observational|retrospective (cohort|study|analysis)|prospective cohort|propensity|claims (data|database)|electronic (health|medical) record|nationwide|population-?based|registry-?based|new-?user (cohort|design)|target trial emulation", re.I)
R_ECON  = re.compile(r"cost-?(effectiveness|utility|benefit|saving|minimi)|budget impact|economic (evaluation|model|analysis)|\bqaly|pharmacoeconomic|incremental cost", re.I)
R_REVIEW= re.compile(r"\breview\b|narrative|reappraisal|perspective|editorial|commentary|update on|state of the art|in (the )?management of|pharmacotherap|expert opinion|where are we", re.I)
# 對照臂：三合一 vs 雙支擴 LABA/LAMA（讀摘要方法學；此處允許 umec/vil 等藥對作為『對照臂』訊號）
R_DUAL  = re.compile(r"\blaba[\s/\-]?lama\b|\blama[\s/\-]?laba\b|dual bronchodilat|dual (long-acting )?bronchodilator|umeclidinium[\s/\-]?vilanterol|glycopyrr\w+[\s/\-]?formoterol|formoterol[\s/\-]?glycopyrr|indacaterol[\s/\-]?glycopyrr|tiotropium[\s/\-]?olodaterol|aclidinium[\s/\-]?formoterol|anoro|ultibro|stiolto|spiolto|duaklir|bevespi|two long-acting bronchodilator", re.I)
R_TRIP  = re.compile(r"triple|ics[\s/\-]?laba[\s/\-]?lama|single[\s\-]?inhaler triple|trelegy|trimbow|breztri|trixeo|fostair|fluticasone furoate[\s/\-]?umeclidinium[\s/\-]?vilanterol|budesonide[\s/\-]?glycopyrr\w+[\s/\-]?formoterol|beclomet\w*[\s/\-]?formoterol[\s/\-]?glycopyrron", re.I)

def has(pt,*w): return any(x.lower() in (pt or "").lower() for x in w)

def detect_trial(text, nct_field):
    for m in NCTRE.findall(text or ""):
        key=m.upper().replace("NCT0","NCT") if False else m.upper()
        key="NCT"+re.sub(r"\D","",key)
        if key in NCT_TRIAL: return NCT_TRIAL[key], key
    if nct_field:
        key="NCT"+re.sub(r"\D","",nct_field)
        if key in NCT_TRIAL: return NCT_TRIAL[key], key
    m=ACR.search(text or "")
    if m and TRIALCTX.search(text or ""): return m.group(1).upper(), ""
    return None, (("NCT"+re.sub(r"\D","",nct_field)) if nct_field else "")

def classify(cache, out="g7_units.json"):
    cache=Path(cache)
    ver=json.loads((cache/"g6_verified.json").read_text(encoding="utf-8"))
    content={c["uid"]:c for c in json.loads((cache/"g2c_FINAL_content.json").read_text(encoding="utf-8"))}
    union={r["uid"]:r for r in json.loads((cache/"g1_raw_union.json").read_text(encoding="utf-8"))}
    # 引文追蹤臂(citation-arm)的摘要不在 g2c（屬另一 PRISMA 臂）→ 由 g4_abstracts.json 補，避免被當 title-only
    g4ab={}
    p4=cache/"g4_abstracts.json"
    if p4.exists():
        try: g4ab=json.loads(p4.read_text(encoding="utf-8"))
        except Exception: g4ab={}
    from collections import Counter, defaultdict
    buckets=Counter(); studies=defaultdict(list); rows=[]; title_only=0
    for v in ver:
        if v.get("verdict")!="VERIFIED": continue
        uid=v.get("uid"); c=content.get(uid,{}); u=union.get(uid,{})
        ab=(c.get("abstract") or "").strip() or (g4ab.get(uid) or "").strip(); title=v.get("title") or c.get("title") or ""
        if not ab: title_only+=1
        text=title+" \n "+ab; pt=v.get("pubtype_full","") or ""
        nct=u.get("nct","") or ""
        is_ct = ("ClinicalTrials.gov" in (u.get("sources") or [])) or bool(nct)
        # 設計判別（優先序）
        if has(pt,"Meta-Analysis","Systematic Review") or R_SRMA.search(text): design="背景:SR/MA/network-meta"
        elif has(pt,"Guideline","Practice Guideline") or R_GUIDE_TITLE.search(title): design="背景:指引"
        elif R_PROTO.search(text) and not R_RCT.search(ab): design="進行中/試驗計畫書"
        elif has(pt,"Randomized Controlled Trial","Controlled Clinical Trial") or (R_RCT.search(text) and not R_OBS.search(text)): design="原始研究:RCT"
        elif is_ct and not ab: design="進行中/登錄試驗(CT.gov)"
        elif has(pt,"Observational Study") or R_OBS.search(text): design="背景:觀察性/真實世界"
        elif R_ECON.search(text): design="背景:經濟評估"
        elif R_REVIEW.search(text): design="背景:綜述/其他次級"
        else: design="背景:其他(未分型,待人工)"
        row={"uid":uid,"title":title,"pmid":v.get("pmid",""),"doi":v.get("doi",""),
             "arm":v.get("arm"),"design":design,"abstract_available":bool(ab)}
        if design=="原始研究:RCT":
            trip=bool(R_TRIP.search(text)); dual=bool(R_DUAL.search(text))
            trial,key=detect_trial(text,nct)
            row["trial"]=trial or "(未辨識)"; row["nct"]=key
            row["comparator_LABA_LAMA"]=dual
            row["unit"]= "核心:三合一 vs LABA/LAMA" if (trip and dual) else ("三合一 vs ICS/LABA或安慰劑(非LABA/LAMA對照)" if trip else "RCT(待人工確認介入)")
            studies[trial or "(未辨識試驗)"].append(row)
            buckets[row["unit"]]+=1
        else:
            buckets[design]+=1
        rows.append(row)
    core=[r for r in rows if r.get("unit","").startswith("核心")]
    out_obj={"n":len(rows),"title_only_no_abstract":title_only,"buckets":dict(buckets),
             "rct_studies":{k:len(v) for k,v in studies.items()},
             "core_rct_studies":sorted({r["trial"] for r in core if r["trial"]!="(未辨識)"}),
             "rows":rows}
    (cache/out).write_text(json.dumps(out_obj,ensure_ascii=False),encoding="utf-8")
    return out_obj

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--cache",required=True); ap.add_argument("--out",default="g7_units.json")
    a=ap.parse_args(); o=classify(a.cache,a.out)
    from collections import Counter
    print(f"⑦ 精確分類（n={o['n']}，其中無摘要僅標題 {o['title_only_no_abstract']}）：")
    for k,v in sorted(o["buckets"].items(),key=lambda x:-x[1]): print(f"  {v:>5}  {k}")
    print("\nRCT 依 NCT/試驗名歸併為 Study：")
    for k,v in sorted(o["rct_studies"].items(),key=lambda x:-x[1]): print(f"  ● {k}: {v} 報告")
    print("\n核心『三合一 vs LABA/LAMA』Study：", ", ".join(o["core_rct_studies"]))

if __name__=="__main__":
    main()
