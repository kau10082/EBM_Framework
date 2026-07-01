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

import os

NCT_TRIAL = {}
PIVOTAL_LABALAMA_ARM = {}

ACR = re.compile(r"(?!x)x")  # Fallback empty matcher

def load_topic_config(path=None):
    global NCT_TRIAL, PIVOTAL_LABALAMA_ARM, ACR
    NCT_TRIAL = {}
    PIVOTAL_LABALAMA_ARM = {}
    ACR = re.compile(r"(?!x)x")  # Fallback empty matcher
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic_config.json")
    if os.path.exists(path):
        try:
            cfg = json.loads(Path(path).read_text(encoding="utf-8"))
            NCT_TRIAL = cfg.get("NCT_TRIAL", {})
            PIVOTAL_LABALAMA_ARM = cfg.get("PIVOTAL_LABALAMA_ARM", {})
            if PIVOTAL_LABALAMA_ARM:
                names = [re.escape(k) for k in PIVOTAL_LABALAMA_ARM.keys()]
                ACR = re.compile(rf"\b({'|'.join(names)})\b(?!\s+(?:of|on|study population)\b)", re.I)
        except Exception as e:
            sys.stderr.write(f"Failed to load topic config from {path}: {e}\n")
    else:
        sys.stderr.write(f"WARNING: Topic config file not found at {path}. PIVOTAL_LABALAMA_ARM will be empty and pivotal trial matching will fail.\n")

load_topic_config()

def _by_uid(items, src=""):
    """以 uid 建索引；缺 uid 者跳過並警示——單筆髒資料不可讓整批 ⑤b 以 KeyError 中止。"""
    out = {}; skipped = 0
    for r in items:
        u = r.get("uid") if isinstance(r, dict) else None
        if u is None:
            skipped += 1; continue
        out[u] = r
    if skipped:
        sys.stderr.write("⚠ %s 有 %d 筆缺 uid，已跳過（未入索引，請補 uid 後重跑）\n" % (src or "輸入", skipped))
    return out

def records_of(g7):
    """g7_units.json 統一讀取層（單一真值來源，防產出端/守門端契約飄移）：
    相容本檔輸出 {"rows":[{uid,unit,design,...}]}（無 role 鍵）、舊形狀 {"records":[{role,...}]} 與裸 list。
    回傳每筆帶 role∈{core,background,awaiting,""} 的 dict list；role 缺時由 unit/design 前綴推導
    （核心:→core、待評估→awaiting、其餘有分類文字→background）。gate_guard 與報告產生器一律經此讀取。"""
    if isinstance(g7, list):
        recs = g7
    elif isinstance(g7, dict):
        recs = g7.get("records") or g7.get("rows") or []
    else:
        return []
    out = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        if r.get("role"):
            out.append(r); continue
        u = str(r.get("unit") or ""); d = str(r.get("design") or "")
        role = ("core" if u.startswith("核心")
                else "awaiting" if u.startswith("待評估") or d.startswith("待評估")
                else "background" if (u or d) else "")
        rr = dict(r); rr["role"] = role; out.append(rr)
    return out

TRIALCTX = re.compile(r"\b(trial|study|randomi[sz]ed|cohort|programme|program)\b", re.I)
NCTRE = re.compile(r"NCT0?\d{6,8}", re.I)

R_SRMA  = re.compile(r"meta-?analys|systematic review|we searched (pubmed|embase|medline|cochrane|databases|the)|prospero|pooled (analysis|data|estimate)|network meta|random-?effects model|fixed-?effects model|cochrane (central|library|database)|search strategy|inclusion criteria were", re.I)
# 指引：只認 pubtype 與『標題』訊號（abstract 內 recommendation/management of 太常見會誤併，故不掃 abstract）
R_GUIDE_TITLE = re.compile(r"guideline|gold (report|science committee|20\d\d|strategy document)|recommendations for the (diagnosis|management|treatment|pharmacolog)|consensus (statement|document)|position (paper|statement)|practice parameter|clinical practice recommendation", re.I)
R_PROTO = re.compile(r"study protocol|protocol for|rationale and design|^design of|methods? (paper|of a)|statistical analysis plan", re.I)
R_RCT   = re.compile(r"randomi[sz]ed|randomly (assigned|allocated)|double-?blind|placebo-?controlled|active-?controlled|parallel-?group|1:1 (randomi|ratio)|were assigned to receive", re.I)
R_OBS   = re.compile(r"real-?world|observational|retrospective (cohort|study|analysis)|prospective cohort|propensity|claims (data|database)|electronic (health|medical) record|nationwide|population-?based|registry-?based|new-?user (cohort|design)|target trial emulation|pharmacoepidemiolog|probabilistic bias analysis|before[\s\-]?after (study|design|comparison)|pre[\s\-]?post (study|design)|whose treatment was changed (from|to)|we included patients whose", re.I)
# 真正的隨機化證據（用來把關『其他原始臨床研究』回退路徑——只認確有隨機化者，避免綜述描述他人試驗誤判 RCT）
R_RAND  = re.compile(r"randomi[sz]ed|randomly (assigned|allocated)|double-?blind|placebo-?controlled (trial|study)|1:1 (randomi|ratio)|were (randomly )?assigned to receive|cross-?over (trial|study)|open-?label.{0,20}randomi", re.I)
# 明確的綜述/藥物簡介訊號（review 描述他人試驗時常含 randomized/placebo-controlled 字樣 → 會誤觸 R_RCT；
# 故先擋下這些『綜述體』再判 RCT）。2026-06 使用者逐筆核對 24 篇獨立核心 RCT 後立：誤拉入綜述/藥動 8+ 篇。
R_REVIEW_STRONG = re.compile(r"narrative (review|paper)|this (review|article|paper) (review|summari[sz]|explore|discuss|present|offer)|to review (current|the) (evidence|literature|role|use)|we (used pubmed|conducted (a|the) literature search|searched (pubmed|medline|the literature))|literature search (from|was conducted|using)|areas covered\b|this article (review|explore|present)|overview of (the )?(heterogeneity|current)|drug (profile|review)|reviews the role", re.I)
R_PK_STRONG = re.compile(r"population pharmacokinetic|pharmacokinetic (analysis|profile|model|characteri)|pharmacodynamic (analysis|profile)|bioequivalence|gas trapping|residual volume", re.I)
# 會議摘要偵測（DOI/標題訊號）：依 Cochrane/MECIR，會議摘要＝『待評估研究(studies awaiting classification)』，
# 未經完整同行評審、數據不完整 → **不得當核心可分析 RCT**（除非是已納入完整論文試驗的子報告）。
# 2026-06 使用者糾正：一篇 ERS congress-2020 摘要(無 PMID)被誤判為獨立核心 RCT。
R_CONF_DOI = re.compile(r"congress-\d|/conference|meetingabstract|ajrccm-conference|\.congress\.|abstract-\d", re.I)
R_CONF_TITLE = re.compile(r"\bposter\b|\bP\d{2,4}\b|congress abstract|conference abstract|^synopsis:", re.I)
# 研究計畫書（無結果）強訊號：protocol 描述會含 randomized/double-blind→會誤觸 R_RCT；故須能蓋過 RCT。
# 2026-06 使用者(外部 Claude)逐筆核對立：ANTES B+、日本 RCT 皆為 protocol(無 outcome)，誤入核心。
R_PROTO_STRONG = re.compile(r"\bstudy protocol\b|\bprotocol for a\b|\btrial protocol\b|rationale and design|"
    r"results (are |will be )?(expected|anticipated|pending|reported (in|by|during))|"
    r"will be (randomi[sz]ed|enrolled|recruited|assigned|conducted)|recruitment (began|will begin|started|commenced|is ongoing|is expected)|"
    r"first (patient|participant|subject)\b.{0,50}(20[2-9]\d)|enrol(l)?ment (began|will|is expected|started)|"
    r"this (study|trial) (will|aims to|is designed to) (enrol|recruit|randomi|assess|investigate|evaluate)", re.I)
# ICS 退階/移除設計（回答『能否撤 ICS』≠『起始三合一 vs 雙支擴』）→ 核心但須打 design=ICS-withdrawal 標籤，
# 避免下游 meta 把『退階』與『起始』方向性混算。2026-06 使用者(外部 Claude)核對 SUNSET/WISDOM 立。
R_ICS_WD = re.compile(r"withdrawal of (inhaled )?(gluco)?cortico-?steroid|\bics withdrawal\b|withdrawal of fluticasone|"
    r"de-?escalat|step(ping)?[\s\-]?down|stepwise (withdrawal|removal)|discontinu(e|ation|ing) (of )?(the )?(ics|inhaled cortico)|"
    r"removing (the )?inhaled cortico|direct (de-escalation|change) from (long-term )?triple", re.I)
# ★ ICS 退階『核心』嚴格訊號：撤除/退階字眼須與 ICS／吸入糖皮質素鄰近共現（或明寫『triple→雙支擴 de-escalation』）。
#   避免泛『step-up/step-down 管理策略』試驗（如 symptom-based management）被 R_ICS_WD 的裸『step-down』誤判為核心。
ICS_WD_STRICT = re.compile(
    r"withdrawal of (inhaled )?(gluco)?cortico-?steroid|\bics withdrawal\b|withdrawal of (inhaled )?glucocorticoid|"
    r"(withdraw\w*|de-?escalat\w*|discontinu\w*|remov\w*|step(ping)?[\s\-]?down)[^.;]{0,40}\b(ics|inhaled cortico\w*|inhaled glucocortico\w*|inhaled steroid|fluticasone|budesonide|beclomet\w*)\b|"
    r"\b(ics|inhaled cortico\w*|inhaled glucocortico\w*)\b[^.;]{0,40}(withdraw\w*|de-?escalat\w*|discontinu\w*|remov\w*|step(ping)?[\s\-]?down)|"
    r"de-?escalat\w*[^.;]{0,40}(from )?(long-term )?triple|triple[^.;]{0,40}de-?escalat", re.I)
R_ECON  = re.compile(r"cost-?(effectiveness|utility|benefit|saving|minimi)|budget impact|economic (evaluation|model|analysis)|\bqaly|pharmacoeconomic|incremental cost", re.I)
R_REVIEW= re.compile(r"\breview\b|narrative|reappraisal|perspective|editorial|commentary|update on|state of the art|in (the )?management of|pharmacotherap|expert opinion|where are we", re.I)
# 對照臂：三合一 vs 雙支擴 LABA/LAMA（讀摘要方法學；此處允許 umec/vil 等藥對作為『對照臂』訊號）
R_DUAL  = re.compile(r"\blaba[\s/\-]?lama\b|\blama[\s/\-]?laba\b|dual bronchodilat|dual (long-acting )?bronchodilator|umeclidinium[\s/\-]?vilanterol|glycopyrr\w+[\s/\-]?formoterol|formoterol[\s/\-]?glycopyrr|indacaterol[\s/\-]?glycopyrr|tiotropium[\s/\-]?olodaterol|aclidinium[\s/\-]?formoterol|anoro|ultibro|stiolto|spiolto|duaklir|bevespi|two long-acting bronchodilator", re.I)
R_TRIP  = re.compile(r"triple|ics[\s/\-]?laba[\s/\-]?lama|single[\s\-]?inhaler triple|trelegy|trimbow|breztri|trixeo|fostair|fluticasone furoate[\s/\-]?umeclidinium[\s/\-]?vilanterol|budesonide[\s/\-]?glycopyrr\w+[\s/\-]?formoterol|beclomet\w*[\s/\-]?formoterol[\s/\-]?glycopyrron|ff[\s/\-]?umec[\s/\-]?vi\b|\bbgf\b|\bbdp[\s/\-]?ff[\s/\-]?g\b", re.I)
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
    content=_by_uid(json.loads((cache/"g2c_FINAL_content.json").read_text(encoding="utf-8")), "g2c_FINAL_content")
    union=_by_uid(json.loads((cache/"g1_raw_union.json").read_text(encoding="utf-8")), "g1_raw_union")
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
    # CT.gov 逐成分臂資料（resolve_arms 產）：nct→{has_triple,has_dual_ll,acronym}；及標題補回的 uid→nct
    nct_arms={}; uid_resolved={}
    pa=cache/"nct_arms.json"
    if pa.exists():
        try: nct_arms=json.loads(pa.read_text(encoding="utf-8"))
        except Exception: pass
    pu=cache/"uid_resolved.json"
    if pu.exists():
        try: uid_resolved=json.loads(pu.read_text(encoding="utf-8"))
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
        # pubtype 是否明確標 RCT（最可靠；有此旗標則不被『綜述體』訊號擋下）
        is_rct_pt = has(pt,"Randomized Controlled Trial","Controlled Clinical Trial")
        if is_ct: design="進行中/登錄試驗(CT.gov)"  # ★ 登錄腿記錄＝登錄試驗（不論有無合成摘要；修『給了合成摘要後 is_ct&not ab 失效→落未分型』）
        elif has(pt,"Meta-Analysis","Systematic Review") or R_SRMA.search(text): design="背景:SR/MA/network-meta"
        elif has(pt,"Guideline","Practice Guideline") or R_GUIDE_TITLE.search(title): design="背景:指引"
        # ★ 即使帶 RCT pubtype 也非『核心效力 RCT』者，先擋下（群體藥動次分析、基因/生物標記關聯、純方法學工具）：
        elif re.search(r"population pharmacokinetic|poppk|bioequivalence", text, re.I): design="背景:藥學/裝置/方法學"
        elif re.search(r"\b(snp|single[- ]nucleotide|polymorphism|genetic variant|pharmacogenomic|\brs\d{4,}\b|gene[a-z ]{0,18}associated with)\b", text, re.I): design="背景:觀察性/真實世界"
        elif re.search(r"composite (tool|index|measure)|is a (promising )?(composite )?(concept|tool)", title, re.I): design="背景:綜述/其他次級"
        elif re.search(r"real[- ]life", text, re.I) and not has(pt,"Randomized Controlled Trial"): design="背景:觀察性/真實世界"
        # ★ 先擋『綜述體/藥動』再判 RCT（2026-06 使用者逐筆核對立）：綜述描述他人試驗常含 randomized/placebo-controlled
        #   字樣→會誤觸 R_RCT；故無 RCT pubtype 而命中強綜述/PK 訊號者先歸背景，避免把綜述/藥動誤拉成 RCT。
        elif (not is_rct_pt) and R_REVIEW_STRONG.search(text): design="背景:綜述/其他次級"
        elif (not is_rct_pt) and R_PK_STRONG.search(text) and not R_RAND.search(ab): design="背景:藥學/裝置/方法學"
        # 研究計畫書(無結果)優先於 RCT：protocol 含 randomized 字樣會誤觸 R_RCT，故強訊號須能蓋過。
        elif R_PROTO_STRONG.search(text) or R_PROTO.search(title) or (R_PROTO.search(text) and not R_RCT.search(ab)): design="進行中/試驗計畫書"
        elif is_rct_pt or (R_RCT.search(text) and not R_OBS.search(text)): design="原始研究:RCT"
        elif trip_ctx and R_RCT2ND.search(text) and not R_OBS.search(text): design="原始研究:RCT"  # 試驗事後/次級分析＝該試驗報告
        elif has(pt,"Observational Study") or R_OBS.search(text): design="背景:觀察性/真實世界"
        # ★ 其他原始臨床研究回退：須『確有隨機化證據(R_RAND)』才當 RCT，否則綜述『we compared/clinical trial』會誤判
        elif trip_ctx and R_PRIM2.search(text) and R_RAND.search(text) and not R_OBS.search(text): design="原始研究:RCT"
        elif R_ECON.search(text): design="背景:經濟評估"
        elif R_PHARM.search(text): design="背景:藥學/裝置/方法學"
        elif R_SURVEY.search(text): design="背景:共識/調查/觀點"
        elif R_REVIEW.search(text): design="背景:綜述/其他次級"
        else: design="背景:其他次級文獻(社論/會議短摘/討論等)"
        row={"uid":uid,"title":title,"pmid":v.get("pmid",""),"doi":v.get("doi",""),
             "arm":v.get("arm"),"design":design,"abstract_available":bool(ab)}
        if design=="原始研究:RCT":
            # 對照軸(C=LABA/LAMA)偵測校正（2026-06 使用者糾正核心/非核心誤判）：
            #  (1) 先正規化分隔符 en/em-dash→hyphen、β→b——否則 ETHOS/KRONOS 的
            #      `glycopyrrolate–formoterol`(en-dash) 漏判 → 假陰(該核心被丟非核心)。
            #  (2) 再『遮蔽三合一藥名跨度』(R_TRIP.sub) 才掃 R_DUAL——否則三合一名 `FF/UMEC/VI`
            #      內含 `UMEC/VI`=umeclidinium/vilanterol(一個雙支擴對) → 假陽(FULFIL/TRILOGY 對照其實
            #      是 ICS/LABA 卻被當核心)。真正獨立的雙支擴對照臂(如 IMPACT 的 UMEC/VI 比較組)遮蔽後仍在。
            dtext=text.replace("–","-").replace("—","-").replace("β","b")
            trip=bool(R_TRIP.search(dtext))
            dual=bool(R_DUAL.search(R_TRIP.sub(" ", dtext)))
            trial,key=detect_trial(text,nct,names)
            if not key and uid_resolved.get(uid):   # 摘要無 NCT → CT.gov 標題搜尋補回
                key=uid_resolved[uid]
                if not trial: trial=names.get(key, key)
                row["linked_by"]="ctgov_title_search"
            if not trial:  # 無 NCT/縮寫上下文 → 試『縮寫(摘要)＋樣本數特徵』保守連結
                sl=sig_link(text)
                if sl: trial=sl; row["linked_by"]="signature"
            arm=nct_arms.get(key or "")  # CT.gov 逐成分臂資料
            if arm and not trial: trial=arm.get("acronym") or key
            # ★ 不留『(未辨識)』：未連到試驗名者一律以 NCT 或 PMID 當穩定識別（每筆自成一 Study）。
            row["trial"]=trial or key or ("研究-PMID" + str(v.get("pmid") or "?")); row["nct"]=key
            row["comparator_LABA_LAMA"]=dual
            doi_l=str(v.get("doi") or "").lower()
            is_conf = bool(R_CONF_DOI.search(doi_l)) or bool(R_CONF_TITLE.search(title))
            # 決策優先序（★ 定版：每筆 RCT 一律給出確定核心/背景，不留『待確認』灰色地帶）：
            #   樞紐權威表 → ICS 退階設計 → CT.gov 雙支擴對照臂(has_dual_ll，可靠) → CT.gov 無三合一臂 →
            #   會議摘要 → 其餘三合一 RCT 一律背景(具體理由：對照非雙支擴/未經權威確認)。
            #   核心『只』由 樞紐表／ICS退階／CT.gov has_dual_ll 三條正向確認來源背書；
            #   CT.gov has_triple=True 不採（跨臂/安慰劑描述污染假陽，如 ILLUMINATE/POWER）。
            # ★ 對照臂判定優先序（2026-06 使用者定版）：**人工核對的樞紐權威表為主**（known trials 最準），
            #   CT.gov 登錄各臂作『交叉核對 tripwire』——不一致時**記 table_discrepancy 攤出待人工核對、不靜默覆蓋**。
            #   （理由：CT.gov 逐臂 regex 兩種噪音都會發生——假陽：arm 描述跨臂提及三類藥→has_triple 誤 True(如 ILLUMINATE)；
            #    假陰：三合一以品牌/開發代號命名未被成分庫命中→has_triple 誤 False(如 TRIBUTE 的 extrafine BDP/FF/G)。
            #    故 CT.gov 不可凌駕表、只能當不一致告警；表 curation 錯(如前案 TRIVERSYTI)由此 tripwire＋摘要矛盾偵測雙重surface。）
            def _ctgov_crosscheck(in_table_value):
                # 在表內試驗：表值(是否核心) vs CT.gov has_dual_ll 不一致 → 記 discrepancy（不覆蓋）
                if arm and (arm.get("has_dual_ll") is not None) and (bool(in_table_value) != bool(arm.get("has_dual_ll"))):
                    row["table_discrepancy"]=(f"PIVOTAL表={in_table_value} 但 CT.gov 各臂 has_dual_ll={arm.get('has_dual_ll')}"
                        f"（has_triple={arm.get('has_triple')}；二者不一致→請人工核對對照臂事實，注意 CT.gov 逐臂 regex 也可能假陽/假陰）")
            if trial in PIVOTAL_LABALAMA_ARM:
                row["unit"]="核心:三合一 vs LABA/LAMA" if PIVOTAL_LABALAMA_ARM[trial] else "三合一 vs ICS/LABA或安慰劑(非LABA/LAMA對照)"
                row["core_basis"]="pivotal_trial_design"
                _ctgov_crosscheck(PIVOTAL_LABALAMA_ARM[trial])
            elif trip and ICS_WD_STRICT.search(dtext):
                # ICS 退階/移除設計（三合一→雙支擴，如 WISDOM/SUNSET）＝核心子型；下游 meta 不與起始混算。
                row["unit"]="核心:ICS 退階試驗(三合一→LABA/LAMA)"; row["core_basis"]="ICS_withdrawal"
                row["design_subtype"]="ICS-withdrawal"
            elif arm and not arm.get("has_triple"):
                design="背景:對照側RCT(無三合一臂)"; row["design"]=design; row["unit"]=""
                row["core_basis"]="ctgov_arms(no_triple)"; row["nct"]=key
                buckets[design]+=1; rows.append(row); continue
            elif is_conf:
                row["unit"]="待評估:會議摘要(未完整發表)"; row["design"]="背景:會議摘要(待評估)"
                row["core_basis"]="conference_abstract_awaiting"
            elif trip:
                # 三合一 RCT 但對照臂未經 樞紐表/ICS退階/CT.gov has_dual_ll 任一正向確認為雙支擴
                # → 確定歸背景(本題非核心)，具體理由標明；不留『待覆核』灰色桶。
                design="背景:三合一RCT(對照非雙支擴或未確認,本題非核心)"; row["design"]=design; row["unit"]=""
                row["core_basis"]="not_confirmed_dual_comparator"
                buckets[design]+=1; rows.append(row); continue
            else:
                design="背景:對照側RCT(無三合一臂)"; row["design"]=design; row["unit"]=""
                buckets[design]+=1; rows.append(row); continue
            # ★ ICS 退階/移除設計標記：非樞紐核心若命中 ICS-withdrawal 訊號→改記獨立子型（樞紐試驗為起始設計，
            #   其子報告即使摘要提及 withdrawal 亦不得改判，避免如 IMPACT 死亡率報告被誤標退階）。
            if (str(row.get("unit","")).startswith("核心") and row.get("core_basis")!="pivotal_trial_design"
                    and row.get("design_subtype")!="ICS-withdrawal" and R_ICS_WD.search(dtext)):
                row["unit"]="核心:ICS 退階試驗(三合一→LABA/LAMA)"; row["design_subtype"]="ICS-withdrawal"
            studies[trial or ("研究-PMID"+str(v.get("pmid") or "?"))].append(row)
            buckets[row["unit"]]+=1
        else:
            buckets[design]+=1
        rows.append(row)
    core=[r for r in rows if r.get("unit","").startswith("核心")]
    out_obj={"n":len(rows),"title_only_no_abstract":title_only,"buckets":dict(buckets),
             "rct_studies":{k:len(v) for k,v in studies.items()},
             "core_rct_studies":sorted({r["trial"] for r in core if r["trial"]!="(未辨識)"}),
             "rows":rows}
    # ★ 主動覆核防線（2026-06 使用者『避免下次再犯』）：把『不確定/高風險的核心判定』攤出來逼人工覆核，
    #   不要等下游才被抓。核心列只要落入下列任一風險即列入待覆核，寫 g7_review_flags.json 並在 main 警示：
    #   (1) 非樞紐核心(無權威表背書,純 regex)；(2) 無 PMID(疑會議摘要/未完整發表)；(3) DOI 像會議摘要；
    #   (4) 帶 ICS-withdrawal 子型(設計不同,需確認方向)；(5) 摘要含 protocol 字樣(疑無結果)。
    review_flags=[]
    for r in rows:
        if not str(r.get("unit","")).startswith("核心"): continue
        reasons=[]
        if r.get("trial") not in PIVOTAL_LABALAMA_ARM: reasons.append("非樞紐核心(regex判定,須覆核對照臂)")
        if not r.get("pmid"): reasons.append("無PMID(疑會議摘要/未完整發表)")
        if R_CONF_DOI.search(str(r.get("doi") or "").lower()): reasons.append("DOI疑會議摘要")
        if r.get("design_subtype")=="ICS-withdrawal": reasons.append("ICS退階設計(勿與起始混算)")
        if R_PROTO_STRONG.search((r.get("title") or "")): reasons.append("標題含protocol訊號(疑無結果)")
        # ★ 矛盾偵測(2026-06 使用者抓出 TRIVERSYTI 誤標核心)：樞紐表標核心，但摘要對照疑為 ICS/LABA(非雙支擴)
        #   → 表項可能curation錯誤(如 TRIVERSYTI＝BDP/FF/G vs BDP/FF＝ICS/LABA)。攤出逼人工核對權威表。
        if r.get("core_basis")=="pivotal_trial_design":
            ab=(content.get(r.get("uid"),{}).get("abstract") or "").lower().replace("–","-").replace("—","-")
            ics_laba_comp=bool(re.search(r"versus inhaled corticosteroid|vs\.? inhaled corticosteroid|inhaled corticosteroid (plus|and|/) long-acting (beta|b2)|versus ics[ /\-]laba|\bics[ /\-]laba\b", ab))
            has_dual=bool(r.get("comparator_LABA_LAMA")) or bool(R_DUAL.search(R_TRIP.sub(" ", ab)))
            if ics_laba_comp and not has_dual:
                reasons.append("樞紐表標核心但摘要對照疑為ICS/LABA非雙支擴(須核對PIVOTAL_LABALAMA_ARM權威表)")
        if r.get("table_discrepancy"):
            reasons.append("CT.gov交叉核對不一致："+r["table_discrepancy"])
        if reasons:
            review_flags.append({"uid":r.get("uid"),"pmid":r.get("pmid"),"title":(r.get("title") or "")[:90],
                                 "trial":r.get("trial"),"unit":r.get("unit"),"flags":reasons})
    out_obj["core_review_flags"]=review_flags
    (cache/"g7_review_flags.json").write_text(json.dumps(review_flags,ensure_ascii=False,indent=1),encoding="utf-8")
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
    axes=g0.get("axes",{})
    # ★ 介入軸不一定鍵名叫 "I"（可能是 I_triple、I_intervention…）：穩健地依鍵名/role 找出介入軸，
    #   否則 enrich 會靜默拿到空 isyn → 所有 NCT 介入判為不在範圍 → 全部 RCT 誤丟背景（2026-06 使用者糾正）。
    I=axes.get("I")
    if not isinstance(I,dict) or not I.get("synonyms"):
        for k,v in axes.items():
            if not isinstance(v,dict): continue
            if k=="I" or k.upper().startswith("I_") or "intervention" in str(v.get("role","")).lower():
                I=v; break
    I=I if isinstance(I,dict) else {}
    isyn=[_norm(s) for s in (I.get("synonyms") or []) if s and len(s)>3]
    # 四軸展開的成分清單（若有）：用『各類別成分各命中≥1』作為組合介入(如三合一)的通用判準
    fae=g0.get("four_axis_expansion",{}).get("axisC_class_INN_devcode_brand",{})
    comp_groups=[v for k,v in fae.items() if k.endswith("_components") and isinstance(v,list)]
    comp_groups=[[_norm(x) for x in grp] for grp in comp_groups]
    content=_by_uid(json.loads((cache/"g2c_FINAL_content.json").read_text(encoding="utf-8")), "g2c_FINAL_content")
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

# ── CT.gov 逐成分臂分類（取代舊 enrich 的『整串三合一名比對』，修核心試驗被誤丟背景）──
ICS_DRUGS  = ("budesonide","fluticasone","beclomet","beclometh","mometasone","ciclesonide")
LABA_DRUGS = ("formoterol","vilanterol","salmeterol","olodaterol","indacaterol","arformoterol")
LAMA_DRUGS = ("umeclidinium","glycopyrron","glycopyrrol","tiotropium","aclidinium","revefenacin")
# 品牌→類別（CT.gov 介入常只給品牌/代號）
BRAND_CLASS = {
    "trelegy":{"ICS","LABA","LAMA"},"trimbow":{"ICS","LABA","LAMA"},"breztri":{"ICS","LABA","LAMA"},
    "enerzair":{"ICS","LABA","LAMA"},"bgf":{"ICS","LABA","LAMA"},
    "anoro":{"LABA","LAMA"},"ultibro":{"LABA","LAMA"},"stiolto":{"LABA","LAMA"},"spiolto":{"LABA","LAMA"},
    "duaklir":{"LABA","LAMA"},"bevespi":{"LABA","LAMA"},"gff":{"LABA","LAMA"},"umec/vi":{"LABA","LAMA"},
    "symbicort":{"ICS","LABA"},"breo":{"ICS","LABA"},"relvar":{"ICS","LABA"},"seretide":{"ICS","LABA"},
    "advair":{"ICS","LABA"},"foster":{"ICS","LABA"},"bff":{"ICS","LABA"},"ff/vi":{"ICS","LABA"},
    "spiriva":{"LAMA"},"incruse":{"LAMA"},"seebri":{"LAMA"},"tudorza":{"LAMA"},
}
def _drug_classes(text):
    t=_norm(text); cl=set()
    if any(d in t for d in ICS_DRUGS):  cl.add("ICS")
    if any(d in t for d in LABA_DRUGS): cl.add("LABA")
    if any(d in t for d in LAMA_DRUGS): cl.add("LAMA")
    for b,cs in BRAND_CLASS.items():
        if b in t: cl|=cs
    return cl

def _ct_get(url, mailto):
    try: return urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":f"EBM/0.22 (mailto:{mailto})"}),timeout=25).read()
    except Exception: return None

def _ct_arms(nct, mailto):
    """回傳 {acronym, has_triple, has_dual_ll, interventions:[...]}：逐 intervention(名＋說明)判類別組合。"""
    raw=_ct_get(f"https://clinicaltrials.gov/api/v2/studies/{nct}", mailto)
    if not raw: return None
    try: ps=json.loads(raw).get("protocolSection",{})
    except Exception: return None
    idm=ps.get("identificationModule",{}); aim=ps.get("armsInterventionsModule",{})
    ivs=aim.get("interventions",[]) or []
    intervention_classes=[]
    for iv in ivs:
        blob=(iv.get("name","") or "")+" "+(iv.get("description","") or "")
        intervention_classes.append(_drug_classes(blob))
    # 也看 armGroups（有時成分寫在 arm 描述）
    for ag in (aim.get("armGroups",[]) or []):
        blob=(ag.get("label","") or "")+" "+(ag.get("description","") or "")+" "+" ".join(ag.get("interventionNames",[]) or [])
        c=_drug_classes(blob)
        if c: intervention_classes.append(c)
    has_triple = any({"ICS","LABA","LAMA"}<=c for c in intervention_classes)
    has_dual_ll= any(c=={"LABA","LAMA"} for c in intervention_classes)
    return {"acronym":idm.get("acronym","") or idm.get("briefTitle","")[:40],
            "has_triple":has_triple,"has_dual_ll":has_dual_ll,
            "classes":[sorted(c) for c in intervention_classes]}

def _resolve_nct_by_title(title, mailto):
    """CT.gov 以標題詞搜尋找回 NCT（給摘要無 NCT 的 RCT 報告用）。回傳最佳 NCT 或 ''。"""
    if not title or len(title)<12: return ""
    q=re.sub(r"[^a-zA-Z0-9 ]"," ",title)[:160]
    raw=_ct_get("https://clinicaltrials.gov/api/v2/studies?pageSize=5&fields=NCTId,BriefTitle,OfficialTitle&query.term="+urllib.parse.quote(q+" COPD"), mailto)
    if not raw: return ""
    try: studies=json.loads(raw).get("studies",[])
    except Exception: return ""
    tnorm=_norm(title)
    best=""; bestov=0
    tw=set(w for w in tnorm.split() if len(w)>3)
    for s in studies:
        idm=s.get("protocolSection",{}).get("identificationModule",{})
        ct_t=_norm((idm.get("briefTitle","") or "")+" "+(idm.get("officialTitle","") or ""))
        ov=len(tw & set(ct_t.split()))
        if ov>bestov and ov>=max(3,int(0.45*len(tw))): bestov=ov; best=idm.get("nctId","")
    return best

def resolve_arms(cache, mailto="test@example.com"):
    """⑤b CT.gov 臂解析（逐成分）：對候選中的 RCT 報告，(1) 摘要無 NCT 者以標題搜 CT.gov 補 NCT，
    (2) 對每個 NCT 抓臂/介入逐成分判 has_triple/has_dual_ll。寫 nct_arms.json、uid_resolved.json、nct_names.json。
    取代舊 enrich『整串三合一名比對』（CT.gov 介入多為成分藥分項→整串比對全部誤判非三合一）。"""
    cache=Path(cache)
    content=_by_uid(json.loads((cache/"g2c_FINAL_content.json").read_text(encoding="utf-8")), "g2c_FINAL_content")
    g4ab=json.loads((cache/"g4_abstracts.json").read_text(encoding="utf-8")) if (cache/"g4_abstracts.json").exists() else {}
    ver=json.loads((cache/"g6_verified.json").read_text(encoding="utf-8"))
    union=_by_uid(json.loads((cache/"g1_raw_union.json").read_text(encoding="utf-8")), "g1_raw_union")
    ncts=set(); uid_resolved={}; rct_uids=[]
    for v in ver:
        if v.get("verdict")!="VERIFIED": continue
        uid=v.get("uid"); ab=(content.get(uid,{}).get("abstract") or "") or (g4ab.get(uid) or ""); title=v.get("title") or ""
        text=title+" "+ab; pt=v.get("pubtype_full","") or ""
        found=[ "NCT"+re.sub(r"\D","",m) for m in NCTRE.findall(text)]
        u=union.get(uid,{})
        if u.get("nct"): found.append(u["nct"])
        for n in found: ncts.add(n)
        # RCT-ish 報告且無 NCT → 記下待標題搜尋
        is_rct = has(pt,"Randomized Controlled Trial","Controlled Clinical Trial") or (R_RCT.search(text) and not R_OBS.search(text))
        if is_rct and not found:
            rct_uids.append((uid,title))
    # 標題搜尋補 NCT（限 RCT 無 NCT 者）
    for uid,title in rct_uids:
        n=_resolve_nct_by_title(title, mailto)
        if n: uid_resolved[uid]=n; ncts.add(n)
        time.sleep(0.05)
    names={}; arms={}
    for k in sorted(ncts):
        a=_ct_arms(k, mailto)
        if not a: continue
        names[k]=a["acronym"] or k; arms[k]=a
        time.sleep(0.05)
    json.dump(names,open(cache/"nct_names.json","w",encoding="utf-8"),ensure_ascii=False)
    json.dump(arms,open(cache/"nct_arms.json","w",encoding="utf-8"),ensure_ascii=False)
    json.dump(uid_resolved,open(cache/"uid_resolved.json","w",encoding="utf-8"),ensure_ascii=False)
    nt=[k for k,a in arms.items() if a["has_triple"]]
    print(f"⑤b CT.gov 臂解析：NCT {len(ncts)}｜抓到臂 {len(arms)}｜含三合一臂 {len(nt)}｜"
          f"三合一∧雙支擴對照(核心) {sum(1 for a in arms.values() if a['has_triple'] and a['has_dual_ll'])}｜"
          f"標題補回 NCT {len(uid_resolved)}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cache", dest="cache_dir", required=True)
    ap.add_argument("--out", dest="outfile", default="g7_units.json")
    ap.add_argument("--topic-config", help="Path to topic_config.json")
    ap.add_argument("--enrich",action="store_true",help="先線上 CT.gov 逐成分臂解析(寫 nct_arms/uid_resolved/nct_names)")
    a = ap.parse_args()
    if a.topic_config:
        load_topic_config(a.topic_config)
    if a.enrich: resolve_arms(a.cache_dir)
    o=classify(a.cache_dir, a.outfile)
    print(f"⑦ 精確分類（n={o['n']}，其中無摘要僅標題 {o['title_only_no_abstract']}）：")
    for k,v in sorted(o["buckets"].items(),key=lambda x:-x[1]): print(f"  {v:>5}  {k}")
    print("\nRCT 依 NCT/試驗名歸併為 Study：")
    for k,v in sorted(o["rct_studies"].items(),key=lambda x:-x[1]): print(f"  ● {k}: {v} 報告")
    print("\n核心『三合一 vs LABA/LAMA』Study：", ", ".join(o["core_rct_studies"]))
    rf=o.get("core_review_flags") or []
    if rf:
        print(f"\n⚠️  核心待人工覆核 {len(rf)} 筆（rapid-review 不可逕信，須逐筆核對；明細 g7_review_flags.json）：")
        for x in rf[:30]:
            print(f"   - [{x.get('pmid') or '無PMID'}] {x['title']} ｜ {'、'.join(x['flags'])}")
        print("   → 非樞紐核心/無PMID/會議摘要/ICS退階/protocol 訊號者，務必人工或 Phase 0 覆核後才當核心證據。")

if __name__=="__main__":
    main()
