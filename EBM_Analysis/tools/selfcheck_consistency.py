# -*- coding: utf-8 -*-
"""
selfcheck_consistency.py — Phase 4 統合報告的『自我一致性硬 gate』
=================================================================
把 Gemini 稽核抓到的內部矛盾編成確定性檢查（非靠模型自律）：
  C1  RoB2 整體＝最不利子領域（Cochrane Ch8 §8.2.2）。overall≠worst → FAIL。
  C2  RoB2『選擇性報告』領域若判 some_concerns/high，rationale 不得僅以
      『廠商資助/registry 未驗證』為由——須有 outcome switching 證據；
      贊助者偏誤應歸 GRADE publication_bias，不放 RoB2 domain5。
  C3  SoF 任一 relative_effect 出現『合併/pooled/池化』字樣，必須標明來源
      （具名 MA、或『自行池化 N=…』），否則 FAIL（避免偷挪背景 MA 數據）。
退出碼非 0 表示有矛盾，供 CI / 渲染前擋關。
"""
import json, sys, re
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import workdir; CACHE = Path(workdir.cache_dir())
except Exception:
    CACHE = Path(__file__).resolve().parent.parent / "cache"

ORDER = {"low": 0, "some_concerns": 1, "high": 2}
DOMS = ["randomization", "deviations", "missing_data", "measurement", "selective_reporting"]
SRC_MARK = ["MA", "meta", "Emara", "Carvalhal", "自行池化", "N=", "取自", "pooled from"]

def check(syn=None):
    """回傳矛盾清單（空＝通過）。供 build_reports 渲染前呼叫，不自行 exit。"""
    if syn is None:
        syn = json.loads((CACHE / "_synthesis.json").read_text(encoding="utf-8")).get("synthesis", {})
    fails = []
    # C1: RoB2 overall == worst
    for r in (syn.get("rob_summary") or []):
        worst = max((r[d] for d in DOMS), key=lambda v: ORDER.get(v, 0))
        if r.get("overall") != worst:
            fails.append(f"C1 [{r.get('trial')}] overall={r.get('overall')} ≠ 最不利領域={worst}")
    # C2: sponsorship/registry 不得當 selective_reporting 的下調理由（此檔僅有等級，理由查 pub bias 是否承接）
    pb = (syn.get("publication_bias") or "")
    if syn.get("rob_summary") and not re.search(r"廠商|贊助|sponsor|資助|發表偏誤", pb):
        fails.append("C2 廠商資助之偏誤未在 publication_bias 聲明（應歸此處，非 RoB2 domain5）")
    # C3: SoF 合併效應須標來源
    for o in (syn.get("sof") or []):
        rel = o.get("relative_effect") or ""
        if re.search(r"合併|pooled|池化", rel) and not any(m in rel + (o.get("comment") or "") for m in SRC_MARK):
            fails.append(f"C3 SoF「{o.get('outcome')[:20]}」relative_effect 標『合併』但未註來源：{rel}")
    # C4: RoB2『全文依賴性』——僅摘要/AI 合成抽取者，overall 不得 low（最高 some_concerns）
    for r in (syn.get("rob_summary") or []):
        basis = (r.get("evidence_basis") or "full_text")
        if basis in ("abstract", "ai_synthesis") and r.get("overall") == "low":
            fails.append(f"C4 [{r.get('trial')}] 證據來源={basis}（非全文）卻判 RoB2 overall=low；無資訊不得提議 low，最高 some_concerns（MECIR C54/C55）")
    # C5: 危害結果用詞——須用 NNTH，禁用 NNH（Cochrane 強烈建議）
    harm_kw = re.compile(r"不良|危害|harm|過度角化|hyperkeratosis|牙周|感染|AE")
    for o in (syn.get("sof") or []):
        ae = (o.get("absolute_effect") or "")
        if harm_kw.search(o.get("outcome") or "") and re.search(r"\bNNH\b", ae):
            fails.append(f"C5 SoF「{o.get('outcome')[:20]}」危害結果用了 NNH，應改用 NNTH（指明方向、避免誤解）")
    # C6: 二分類 SoF（相對效應為 RR/OR）之絕對效應若給 NNT 類，須附 95% CI
    for o in (syn.get("sof") or []):
        rel = o.get("relative_effect") or ""; ae = o.get("absolute_effect") or ""
        if re.search(r"\b(RR|OR)\b", rel) and re.search(r"NNT[BH]?", ae) and not re.search(r"CI|到|—|–", ae):
            fails.append(f"C6 SoF「{o.get('outcome')[:20]}」二分類絕對效應給了 NNT 但缺 95% CI（須由相對效應 CI 代入 ACR 回推）")
    # C7: 運算覆驗——由相對效應＋ACR 重算 RD/NNT/CI，與報告所寫比對（不再只信手抄）
    try:
        import absrisk
        def _f(pat, s):
            m = re.search(pat, s or ""); return float(m.group(1)) if m else None
        def _pct(s):
            m = re.search(r'([\d.]+)\s*%', s or ""); return float(m.group(1)) / 100 if m else None
        for o in (syn.get("sof") or []):
            rel, ae = o.get("relative_effect") or "", o.get("absolute_effect") or ""
            if "率" in (o.get("assumed_control_risk") or "") or "/人年" in ae:
                continue  # 率結果不套 NNT
            acr = _pct(o.get("assumed_control_risk")); corr_pct = _pct(o.get("corresponding_risk"))
            rr = _f(r'\bRR\s*([\d.]+)', rel); orr = _f(r'\bOR\s*([\d.]+)', rel)
            stated_nnt = _f(r'NNT[BH]?\s*[≈≒=]?\s*([\d.]+)', ae)
            stated_rd = _f(r'([+-]?[\d.]+)\s*個百分點', ae)
            if (rr or orr) and acr is not None:
                rd = absrisk._corr("rr" if rr else "or", rr or orr, acr) - acr
            elif acr is not None and corr_pct is not None:
                rd = corr_pct - acr
            else:
                continue
            if stated_rd is not None and abs(rd * 100 - stated_rd) > 0.6:
                fails.append(f"C7 SoF「{o['outcome'][:16]}」風險差重算 {rd*100:+.1f}pp ≠ 報告 {stated_rd:+.1f}pp")
            if stated_nnt is not None and abs(rd) > 1e-9 and abs(1/abs(rd) - stated_nnt) > 1.0:
                fails.append(f"C7 SoF「{o['outcome'][:16]}」NNT 重算 {1/abs(rd):.0f} ≠ 報告 {stated_nnt:.0f}")
            # NNT CI 覆驗
            # CI 分隔符統一支援 –／-／到／to，避免「0.52 to 0.78」「0.52 到 0.78」讓 NNT CI 覆驗靜默跳過
            relci = re.search(r'(?:RR|OR)\s*[\d.]+.{0,14}CI\s*([\d.]+)\s*(?:[–\-到]|\bto\b)\s*([\d.]+)', rel)
            aeci = re.search(r'CI\s*([\d.]+)\s*(?:[–\-到]|\bto\b)\s*([\d.]+)', ae)
            if (rr or orr) and acr is not None and relci and aeci:
                diffs = [abs(absrisk._corr("rr" if rr else "or", float(b), acr) - acr) for b in relci.groups()]
                if all(d > 1e-9 for d in diffs):   # CI 觸無效線(diff≈0→NNT 無限大)時略過數值覆驗，避免 1/0 ZeroDivisionError 把整段 C7 靜默中斷
                    ns = sorted(1/d for d in diffs)
                    es = sorted(float(x) for x in aeci.groups())
                    if abs(ns[0]-es[0]) > 1.0 or abs(ns[1]-es[1]) > 1.0:
                        fails.append(f"C7 SoF「{o['outcome'][:16]}」NNT CI 重算 {ns[0]:.0f}-{ns[1]:.0f} ≠ 報告 {es[0]:.0f}-{es[1]:.0f}")
    except Exception as e:
        # 不靜默吞：C7 是數值覆驗，靜默跳過會放走絕對/相對效應不一致。失敗關閉——
        # 回報為一條 fail 請人工核對（確需略過由 build_reports --skip-consistency 統一處理）。
        fails.append(f"C7 覆驗中止（{str(e)[:80]}）——請人工核對 SoF 絕對效應與相對效應一致性")
    # C8: 連續結果 SoF 須附 MID 或可解讀再表達（Ch14 §14.1.6.2、Ch15 §15.5）
    for o in (syn.get("sof") or []):
        rel = o.get("relative_effect") or ""; ae = o.get("absolute_effect") or ""
        is_cont = re.search(r"\bMD\b|平均差|mL|percentage|百分點變化|分數", ae) and not re.search(r"\b(RR|OR|HR)\b|率比|風險差|NNT", ae)
        if is_cont and not (o.get("mid") or o.get("continuous_reexpression")):
            fails.append(f"C8 SoF「{o.get('outcome','')[:18]}」為連續結果但缺 MID/可解讀再表達")
    # C9: 時間事件(HR)結果 SoF 須有絕對欄（Ch14 §14.1.5.2）
    for o in (syn.get("sof") or []):
        rel = o.get("relative_effect") or ""; ae = o.get("absolute_effect") or ""
        if re.search(r"\bHR\b", rel) and not re.search(r"%|NNT|風險|存活|事件|百分點", ae):
            fails.append(f"C9 SoF「{o.get('outcome','')[:18]}」為 HR 結果但缺絕對效應欄（須由 absrisk hr 換算）")
    # C10: ≥2 試驗時須有證據體 GRADE（Ch14 §14.2.1，非逐篇取均/取最差）
    if len((syn.get("rob_summary") or [])) >= 2 and not syn.get("body_of_evidence"):
        fails.append("C10 證據體 GRADE 缺失：≥2 試驗時 synthesis 須含 body_of_evidence（跨研究逐 outcome 確定性）")
    # C11: critical outcomes 必列 SoF（全因死亡＋SAE，即使罕見/不顯著/不可統合；Ch14 §14.1.6.1，防結果報告偏誤）
    if syn.get("sof"):
        sof_text = " ".join(o.get("outcome", "") for o in syn["sof"])
        if not re.search(r"死亡|mortalit", sof_text, re.I):
            fails.append("C11 SoF 缺『全因死亡』critical outcome（即使罕見/不顯著也須列，給低/極低確定性）")
        if not re.search(r"嚴重不良|\bSAE\b|serious adverse", sof_text, re.I):
            fails.append("C11 SoF 缺『嚴重不良事件 SAE』critical outcome（須列）")
    # C12: 借用他人 MA 合併值卻宣稱『不池化』且未明示採用理由＝自我矛盾（Emara paradox 防呆）
    borrowed = any(re.search(r"取自.{0,6}MA|Emara.{0,6}合併|pooled", (o.get("relative_effect") or "") + (o.get("comment") or "")) for o in (syn.get("sof") or []))
    nopool = re.search(r"不池化|未自行(統計)?池化", (syn.get("vote_counting_check") or "") + (syn.get("conflict_analysis") or ""))
    adopt = re.search(r"採用|特例|明示|adopt", (syn.get("conflict_analysis") or "") + (syn.get("vote_counting_check") or "") + "".join((o.get("comment") or "") for o in (syn.get("sof") or [])))
    if borrowed and nopool and not adopt:
        fails.append("C12 借用他人 MA 合併值但宣稱『不池化』且未明示採用理由（自我矛盾，須標明特例採用 MA 合併估計）")
    # C13: 跨呈現確定性一致——body_of_evidence 與 SoF 同 outcome 確定性須相符（防手改一處飄移）
    def _kw(s): return set(re.findall(r"[一-鿿A-Za-z0-9]{2,}", re.sub(r"[（）()／/、，,。.；;]", " ", s or "")))
    def _cln(s): return re.sub(r"[\s（）()／/、，,。.；;]", "", s or "")
    sof = (syn.get("sof") or [])
    for b in (syn.get("body_of_evidence") or []):
        bk = _kw(b.get("outcome", ""))
        best = None; bestov = 0
        for o in sof:
            ov = len(bk & _kw(o.get("outcome", "")))
            if ov > bestov: bestov, best = ov, o
        # 中文整詞無 token 重疊時的子字串後援（如「死亡」⊂「全因死亡」），避免 C13 漏檢一致性
        if not best or bestov < 2:
            bc = _cln(b.get("outcome", ""))
            for o in sof:
                oc = _cln(o.get("outcome", ""))
                if len(bc) >= 2 and len(oc) >= 2 and (bc in oc or oc in bc):
                    best, bestov = o, 2; break
        if best and bestov >= 2 and b.get("certainty") != best.get("certainty"):
            fails.append(f"C13 證據體 GRADE「{b.get('outcome','')[:14]}」確定性={b.get('certainty')} ≠ SoF「{best.get('outcome','')[:14]}」={best.get('certainty')}（跨呈現飄移）")
    # C14: SoF 任何 NNTB/NNTH 點估計必附 CI 或不確定標記（含危害；防假性精確，Ch15 §15.4.4）
    for o in (syn.get("sof") or []):
        ae = (o.get("absolute_effect") or "") + (o.get("dose_response") or "")
        if re.search(r"NNT[BH]\s*[≈≒=]?\s*\d", ae) and not re.search(r"CI|到|[–-]\s*\d|無限大|不顯著|跨", ae):
            fails.append(f"C14 SoF「{o.get('outcome','')[:16]}」NNT 點估計缺 CI/不確定標記（假性精確；事件少時 CI 常含無限大）")
    # C15: SoF 受試者數一致性（防『每次報告 N 飄移』）——所有「跨 N 個 RCT 合併」列須用同一個受試者總數；
    #      子比較列(單試驗單劑量 vs 安慰劑)允許不同，但其 N 須等於兩臂和。
    def _ints(s):
        # 受試者數提取：數字後若緊接劑量/單位(mg/µg/週/%…)則排除，避免把劑量(150mg/300mg)誤當 N 觸發 C15 假性阻擋
        out = []
        # 排除單位用多字元安全寫法（days?/months?/天，不用裸 d|m|mo——否則會誤排除「1200 deaths/died」這種真 N）
        for m in re.finditer(r"(\d[\d,]*)\s*(mg|µg|μg|ug|mcg|kg|m[lL]|%|週|周|wk|week|days?|months?|天|歲|year|yr|mmHg|nmol|mmol)?", s or "", re.I):
            if not m.group(2):
                out.append(int(m.group(1).replace(",", "")))
        return out
    pooled_totals = {}
    for o in (syn.get("sof") or []):
        nps = o.get("n_participants_studies") or ""
        nums = [n for n in _ints(nps) if n >= 100]            # 忽略研究數/小數
        if re.search(r"RCT|試驗", nps) and not re.search(r"vs|＋|\+|臂|單試驗|單劑量", nps):
            # 視為「跨 RCT 合併」列：取其最大數為該列宣稱的合併總數
            if nums:
                pooled_totals.setdefault(max(nums), []).append(o.get("outcome", "")[:14])
    if len(pooled_totals) > 1:
        desc = "；".join(f"{n}（{'/'.join(v)}）" for n, v in sorted(pooled_totals.items()))
        fails.append(f"C15 SoF 跨-RCT 合併列出現 {len(pooled_totals)} 個不同受試者總數：{desc} → 須統一(隨機分配總數)，MA分析集差異只在敘述explain、勿混入 SoF 欄")
    # C16: RoB2 整體非「低」者，須在 note 說明 some concerns/high 之來源（PDF 末欄「some concerns 原因」要填，
    #      防報告出現未解釋的 concern。2026-06 因 RoB 表 concern 無說明而立）。
    for r in (syn.get("rob_summary") or []):
        ov = str(r.get("overall") or "")
        if ov and not re.search(r"^低$|low", ov, re.I):
            if not str(r.get("note") or "").strip():
                fails.append(f"C16 [{r.get('trial')}] RoB2 整體={ov} 但未填 note 說明來源（concern/high 須註明哪個領域、為何）")
    return fails

def warnings(syn=None):
    """非阻擋的提醒（soft）：缺了會降可讀性/完整性、但不擋定稿者。回提醒清單。"""
    if syn is None:
        try:
            syn = json.loads((CACHE / "_synthesis.json").read_text(encoding="utf-8")).get("synthesis", {})
        except Exception:
            return []
    warns = []
    # W1: 有 SoF 卻沒寫白話總結 plain_summary（通勤可讀開頭；schema 允許 null→不會被硬擋）
    if syn.get("sof") and not (syn.get("plain_summary") or "").strip():
        warns.append("W1 缺 plain_summary（白話『一分鐘讀懂』開頭）——報告少了通勤可讀的總結；建議補上（口語、術語就地白話化）")
    return warns


def main():
    fails = check()
    if fails:
        print("❌ 自我一致性檢查未過（%d）：" % len(fails))
        for f in fails: print("  -", f)
        sys.exit(1)
    print("✅ 自我一致性檢查通過：RoB2 overall=最不利領域、贊助者偏誤歸發表偏誤、SoF 合併效應已註來源。")

if __name__ == "__main__":
    main()
