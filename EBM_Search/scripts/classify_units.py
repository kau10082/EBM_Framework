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
import sys, re, json, argparse, time, urllib.parse, urllib.request
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
# RCT 次級/事後分析（隨機化在母試驗，摘要常無 randomized 字樣）——屬該試驗的『報告』，仍歸 RCT/Study
R_RCT2ND= re.compile(r"post[\s\-]?hoc|responder analysis|pre[\s\-]?specified (analysis|subgroup|outcome)|subgroup analysis|exploratory (post|analysis|endpoint)|secondary (analysis|outcome analysis)|further analysis of|analysis of (the )?(impact|ethos|kronos|fulfil|trilogy|tribute|trinity|etwas)|analysis of (data from|pooled data from the)|of the (impact|ethos|kronos|fulfil|trilogy|tribute|trinity) (trial|study)", re.I)
# 其他原始臨床研究設計詞（非隨機/小型臨床比較/加成試驗等）——放寬以接住被誤丟未分型的真原始研究
R_PRIM2 = re.compile(r"open[\s\-]?label|cross[\s\-]?over|clinical (trial|comparison)|we compared|to compare the (effect|efficacy|safety)|comparative (trial|effectiveness of (the )?triple)|comparison of (the )?(dual|triple|effectiveness)|effect of triple therapy|triple therapy with.{0,40}versus|add[\s\-]?on (to|therapy|treatment)|combined with triple|versus (dual|tiotropium|placebo|ics)|phase (i{1,3}|[1-4])\b|single[\s\-]?(centre|center) (study|trial)|multi[\s\-]?(centre|center) (study|trial)|treatment-na[iï]ve.{0,30}(study|trial)|prospective.{0,20}(interventional|comparative)", re.I)
# 藥學/裝置/方法學（背景）
R_PHARM = re.compile(r"pulmonary deposition|lung deposition|in vitro|in-vitro|in silico|pharmacokinetic|pharmacodynamic|bioequivalence|bioavailability|aerosol|particle size|fine particle|device (performance|resistance|design|engineering)|dry powder inhaler (design|performance)|computational fluid|deposition (model|modeling|modelling)|usability|peak inspiratory flow|inhalation profile", re.I)
# 共識/調查/觀點（背景）
R_SURVEY= re.compile(r"delphi|consensus (project|panel|exercise|document|statement)|expert (opinion|panel|consensus|view)|perception|knowledge (and|of|on|gap)|attitude|questionnaire|cross-sectional survey|physician survey|survey of|inhaler technique|taste|quality improvement|implementation (of|science)|prescrib|practice pattern|unmet need", re.I)

def has(pt,*w): return any(x.lower() in (pt or "").lower() for x in w)

# 樞紐試驗『樣本數特徵』（無 NCT 的次級分析常只報藥名＋N＋作者）——保守連結用
PIV_N = {"IMPACT":[10355],"FULFIL":[1810,1811],"ETHOS":[8588,8509,8572],"KRONOS":[1896,1902],
         "TRILOGY":[1368,1367],"TRIBUTE":[1532],"TRINITY":[2691,2680]}
ACR_ANY = re.compile(r"\b(IMPACT|ETHOS|KRONOS|FULFIL|TRILOGY|TRIBUTE|TRINITY|TRIVERSYTI|TRISTAR|INTREPID|TRIFORCE)\b(?!\s+(?:of|on)\b)")
NUM_N = re.compile(r"(\d{1,2},?\d{3})\s*(?:patients|subjects|participants|were random|outpatients|symptomatic)", re.I)

def sig_link(text):
    """無 NCT 時，用『試驗縮寫(摘要全文)』或『樣本數特徵』保守連到母試驗；連不到回 None。"""
    t=text or ""
    m=ACR_ANY.search(t)
    if m and re.search(r"trial|study|copd|exacerbation|patients|randomi", t, re.I):
        return m.group(1).upper()
    for x in NUM_N.findall(t):
        try: n=int(x.replace(",",""))
        except Exception: continue
        for tr,Ns in PIV_N.items():
            if any(abs(n-N)<=max(5,int(N*0.005)) for N in Ns): return tr
    return None

def detect_trial(text, nct_field, names=None):
    """以 NCT 為最可靠的 Study 鍵：任何出現的 NCT 都當一個 Study（已知樞紐→正式名；其餘→CT.gov 名或 NCT 本身）。
    無 NCT 才退回 word-boundary 試驗縮寫。names＝{NCT:顯示名}（NCT_TRIAL ＋ CT.gov 抓回的 nct_names）。"""
    names = names or NCT_TRIAL
    ncts=["NCT"+re.sub(r"\D","",m) for m in NCTRE.findall(text or "")]
    if nct_field: ncts.append("NCT"+re.sub(r"\D","",nct_field))
    # 已知樞紐試驗優先（給穩定正式名）
    for k in ncts:
        if k in NCT_TRIAL: return NCT_TRIAL[k], k
    # 其餘任何 NCT → 自成一個 Study（鍵＝NCT，顯示名取 CT.gov 名或 NCT）
    for k in ncts:
        return names.get(k, k), k
    m=ACR.search(text or "")
    if m and TRIALCTX.search(text or ""): return m.group(1).upper(), ""
    return None, ""

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
    # NCT→顯示名（CT.gov 抓回的 nct_names.json）＋已知樞紐，供 detect_trial 將任何 NCT 歸為 Study
    names=dict(NCT_TRIAL)
    pn=cache/"nct_names.json"
    if pn.exists():
        try: names.update({k:v for k,v in json.loads(pn.read_text(encoding="utf-8")).items() if k not in NCT_TRIAL})
        except Exception: pass
    # 以 CT.gov 介入判定的『非三合一試驗』NCT 集合：這些 NCT 的 RCT 報告＝介入非三合一→剔出核心
    nontriple=set()
    pt2=cache/"nct_triple.json"
    if pt2.exists():
        try: nontriple=set(json.loads(pt2.read_text(encoding="utf-8")).get("nontriple_nct",[]))
        except Exception: pass
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
        trip_ctx = bool(R_TRIP.search(text))  # 與本題相關（含三合一）才把次級分析當試驗報告
        if is_ct: design="進行中/登錄試驗(CT.gov)"  # ★ 登錄腿記錄＝登錄試驗（不論有無合成摘要；修『給了合成摘要後 is_ct&not ab 失效→落未分型』）
        elif has(pt,"Meta-Analysis","Systematic Review") or R_SRMA.search(text): design="背景:SR/MA/network-meta"
        elif has(pt,"Guideline","Practice Guideline") or R_GUIDE_TITLE.search(title): design="背景:指引"
        elif R_PROTO.search(text) and not R_RCT.search(ab): design="進行中/試驗計畫書"
        elif has(pt,"Randomized Controlled Trial","Controlled Clinical Trial") or (R_RCT.search(text) and not R_OBS.search(text)): design="原始研究:RCT"
        elif trip_ctx and R_RCT2ND.search(text) and not R_OBS.search(text): design="原始研究:RCT"  # 試驗事後/次級分析＝該試驗報告
        elif has(pt,"Observational Study") or R_OBS.search(text): design="背景:觀察性/真實世界"
        elif trip_ctx and R_PRIM2.search(text) and not R_OBS.search(text): design="原始研究:RCT"  # 其他原始臨床研究設計
        elif R_ECON.search(text): design="背景:經濟評估"
        elif R_PHARM.search(text): design="背景:藥學/裝置/方法學"
        elif R_SURVEY.search(text): design="背景:共識/調查/觀點"
        elif R_REVIEW.search(text): design="背景:綜述/其他次級"
        else: design="背景:其他次級文獻(社論/會議短摘/討論等)"
        row={"uid":uid,"title":title,"pmid":v.get("pmid",""),"doi":v.get("doi",""),
             "arm":v.get("arm"),"design":design,"abstract_available":bool(ab)}
        if design=="原始研究:RCT":
            trip=bool(R_TRIP.search(text)); dual=bool(R_DUAL.search(text))
            trial,key=detect_trial(text,nct,names)
            if key and key in nontriple:   # 該 NCT 經 CT.gov 介入判定為非三合一（他藥/雙合一）→ 歸背景（非核心），不丟棄
                design="背景:非核心RCT(非三合一vs雙合一介入)"; row["design"]=design
                row["trial"]=trial; row["nct"]=key; buckets[design]+=1; rows.append(row); continue
            if not trial:  # 無 NCT/縮寫上下文 → 試『縮寫(摘要)＋樣本數特徵』保守連結
                sl=sig_link(text)
                if sl: trial=sl; row["linked_by"]="signature"
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

def _norm(s): return re.sub(r"[\s/\-–—,;]+"," ",(s or "").lower())

def enrich(cache, mailto="test@example.com"):
    """⑦ 線上補強（通用、由 g0 軸驅動）：對候選摘要中出現的所有 NCT，查 CT.gov 取
    名稱＋InterventionName，並用 **g0_strategy 的 I 軸同義詞／四軸展開成分** 判該試驗介入是否在範圍內，
    寫 nct_names.json（NCT→名）＋ nct_triple.json（in-scope=triple_nct／out=nontriple_nct）。
    換主題時自動依該主題 g0 的 I 軸判定，不必改碼。"""
    cache=Path(cache)
    g0=json.loads((cache/"g0_strategy.json").read_text(encoding="utf-8"))
    axes=g0.get("axes",{}); I=axes.get("I",{})
    isyn=[_norm(s) for s in (I.get("synonyms") or []) if s and len(s)>3]
    # 四軸展開的成分清單（若有）：用『各類別成分各命中≥1』作為組合介入(如三合一)的通用判準
    fae=g0.get("four_axis_expansion",{}).get("axisC_class_INN_devcode_brand",{})
    comp_groups=[v for k,v in fae.items() if k.endswith("_components") and isinstance(v,list)]
    comp_groups=[[_norm(x) for x in grp] for grp in comp_groups]
    content={c["uid"]:c for c in json.loads((cache/"g2c_FINAL_content.json").read_text(encoding="utf-8"))}
    g4ab=json.loads((cache/"g4_abstracts.json").read_text(encoding="utf-8")) if (cache/"g4_abstracts.json").exists() else {}
    ver=json.loads((cache/"g6_verified.json").read_text(encoding="utf-8"))
    ncts=set()
    for v in ver:
        uid=v.get("uid"); ab=(content.get(uid,{}).get("abstract") or "") or (g4ab.get(uid) or "")
        for m in NCTRE.findall((v.get("title") or "")+" "+ab): ncts.add("NCT"+re.sub(r"\D","",m))
    def get(url):
        try: return urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":f"EBM/0.21 (mailto:{mailto})"}),timeout=20).read()
        except Exception: return None
    names={}; triple=[]; nontrip=[]
    for k in sorted(ncts):
        raw=get(f"https://clinicaltrials.gov/api/v2/studies/{k}?fields=InterventionName,BriefTitle,Acronym")
        if not raw: continue
        try:
            ps=json.loads(raw).get("protocolSection",{})
            acr=ps.get("identificationModule",{}).get("acronym","")
            bt=ps.get("identificationModule",{}).get("briefTitle","")
            iv=";".join(i.get("name","") for i in ps.get("armsInterventionsModule",{}).get("interventions",[]))
        except Exception: acr="";bt="";iv=""
        names[k]=acr or (bt[:40] if bt else k)
        blob=_norm(iv+" "+bt)
        in_scope = any(s in blob for s in isyn)  # 介入命中 I 軸同義詞
        if not in_scope and comp_groups:         # 或：各成分類別各命中≥1（通用組合介入判準）
            in_scope = all(any(c in blob for c in grp) for grp in comp_groups if grp)
        (triple if in_scope else nontrip).append(k)
        time.sleep(0.04)
    json.dump(names,open(cache/"nct_names.json","w",encoding="utf-8"),ensure_ascii=False)
    json.dump({"triple_nct":triple,"nontriple_nct":nontrip},open(cache/"nct_triple.json","w",encoding="utf-8"),ensure_ascii=False)
    print(f"⑦ enrich：NCT 共 {len(ncts)}→ 命名 {len(names)}｜介入在範圍(I 軸) {len(triple)}｜不在範圍 {len(nontrip)}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--cache",required=True); ap.add_argument("--out",default="g7_units.json")
    ap.add_argument("--enrich",action="store_true",help="先線上查 CT.gov 補 NCT 名＋以 g0 I 軸判介入範圍(寫 nct_names/nct_triple)")
    a=ap.parse_args()
    if a.enrich: enrich(a.cache)
    o=classify(a.cache,a.out)
    from collections import Counter
    print(f"⑦ 精確分類（n={o['n']}，其中無摘要僅標題 {o['title_only_no_abstract']}）：")
    for k,v in sorted(o["buckets"].items(),key=lambda x:-x[1]): print(f"  {v:>5}  {k}")
    print("\nRCT 依 NCT/試驗名歸併為 Study：")
    for k,v in sorted(o["rct_studies"].items(),key=lambda x:-x[1]): print(f"  ● {k}: {v} 報告")
    print("\n核心『三合一 vs LABA/LAMA』Study：", ", ".join(o["core_rct_studies"]))

if __name__=="__main__":
    main()
