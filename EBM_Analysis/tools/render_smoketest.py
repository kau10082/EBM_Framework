# -*- coding: utf-8 -*-
"""
render_smoketest.py — 渲染煙霧測試（把人工校對升級成機器 gate）
=================================================================
專守「視覺/完整性」這類無數據/算術 gate 能抓、過去只能靠人眼的破圖：
  V1 磚塊字形殘留（msjh/msyh 缺字形→□）
  V2 章節跳號（如 4→6，代表某段被條件式整段跳過）
  V3 空表破圖（資料層：會渲染成表的『選填陣列』卻是空的→標題+表頭+0列）
  V4 SoF 必要結局缺漏（GRADE 鐵則：須含全因死亡＋SAE）
  V5 SoF 行數 vs 資料層 sof 筆數一致（PDF 是否吞了列）

用法：
  python render_smoketest.py <報告.pdf> [--data <_synthesis.json 或 _search_report.json>]
  不給 --data 時自動依 run_state.paths 找 _synthesis.json。
退場碼：0＝全綠；1＝有破圖（列出每條）。供 verify_all 併入。
"""
import sys, os, re, json
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

TOFU = "≈≥≤−◯↔⇔⇄⟷▸►™✅✓✔∧≠"  # 高風險缺字形符號（任一渲染器淨化漏掉就會變磚塊）
# 資料層「會渲染成表、空了就破圖」的選填陣列（GRADE 報告 synthesis）
RENDER_ARRAYS = ["sof", "body_of_evidence", "study_characteristics", "rob_summary",
                 "baseline_risk_strata", "literature_status"]

def _pdf_text(p):
    try:
        import pypdf
        return "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages)
    except Exception as e:
        return ""

def _find_data():
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    try:
        import run_state, workdir
        st = run_state.load() or {}
        for c in (st.get("paths", {}).get("synthesis"),
                  os.path.join(workdir.cache_dir(), "_synthesis.json")):
            if c and os.path.exists(c): return c
    except Exception:
        pass
    return None

def checks_on(txt, data):
    """純邏輯：給 PDF 文字＋資料(synthesis dict 或 None)，回 fails[]。可單元測試。"""
    fails = []
    # V1 磚塊
    bad = sorted({c for c in TOFU if c in txt})
    if bad:
        fails.append("V1 磚塊字形殘留：%s（渲染器 safe() 漏淨化）" % " ".join(bad))

    # V2 章節跳號（抓「N、」或「N.」開頭的中/英章節號）
    nums = [int(n) for n in re.findall(r"(?:^|\n)\s*(\d{1,2})[、.][^\d]", txt)]
    seen = sorted(set(n for n in nums if 1 <= n <= 20))
    if seen:
        gaps = [n for n in range(seen[0], seen[-1] + 1) if n not in seen]
        if gaps:
            fails.append("V2 章節跳號：缺第 %s 節（某段可能空資料被整段跳過）" % "、".join(map(str, gaps)))

    if data is not None:
        is_grade = "sof" in data or "body_of_evidence" in data
        if is_grade:
            # V3 會渲染成表卻空
            for k in RENDER_ARRAYS:
                if k in data and isinstance(data[k], list) and len(data[k]) == 0:
                    fails.append("V3 空表破圖：synthesis.%s 為空陣列（報告會印標題+表頭卻 0 資料列）" % k)
            # V4 SoF 必含死亡＋SAE
            sof = data.get("sof", []) or []
            names = " ".join((s.get("outcome", "") for s in sof))
            if sof:
                if not re.search(r"死亡|mortalit", names, re.I):
                    fails.append("V4 SoF 缺『全因死亡』（GRADE 鐵則 C11：SoF 須含死亡）")
                if not re.search(r"SAE|嚴重不良|serious adverse", names, re.I):
                    fails.append("V4 SoF 缺『嚴重不良事件 SAE』（C11）")
                # V5 SoF 行數 vs PDF
                # PDF 中每個 outcome 名稱前幾字應出現
                missing = [s.get("outcome", "")[:6] for s in sof if s.get("outcome", "")[:6] and s.get("outcome", "")[:6] not in txt]
                if missing:
                    fails.append("V5 SoF 列疑遭吞：PDF 找不到 %d/%d outcome（%s）" % (len(missing), len(sof), "、".join(missing[:3])))
            # V6 渲染器一致性：資料有的關鍵欄位、PDF 必須渲得出來（防兩個 renderer 分歧，
            #    如 clinical_one_liner 進了 md 卻漏進 pdf）。取去空白後的特徵片段比對。
            _nz = re.sub(r"\s+", "", txt)
            PARITY = [("clinical_one_liner", "給臨床的一句話"), ("report_title", "報告標題")]
            for key, label in PARITY:
                v = data.get(key)
                if isinstance(v, str) and len(v.strip()) >= 12:
                    snip = re.sub(r"\s+", "", v.strip())[:14]
                    if snip and snip not in _nz:
                        fails.append("V6 渲染器漏渲：synthesis.%s（%s）資料有、PDF 卻找不到（兩 renderer 分歧）" % (key, label))
    return fails

def check(pdf, data_path):
    """讀 PDF 文字＋載入資料檔，再交給純邏輯 checks_on。"""
    txt = _pdf_text(pdf)
    if not txt:
        return ["無法讀取 PDF 文字（pypdf 失敗或檔不存在）：%s" % pdf]
    data = None
    if data_path and os.path.exists(data_path):
        try:
            d = json.load(open(data_path, encoding="utf-8"))
            data = d.get("synthesis", d)  # 兼容 {synthesis:..}／純 synthesis／檢索報告
        except Exception as e:
            return checks_on(txt, None) + ["V3-5 資料檔無法解析：%s" % str(e)[:60]]
    return checks_on(txt, data)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_path = None
    if "--data" in sys.argv:
        i = sys.argv.index("--data")
        if i + 1 < len(sys.argv): data_path = sys.argv[i + 1]
    if not args:
        print("用法：python render_smoketest.py <報告.pdf> [--data <_synthesis.json>]"); raise SystemExit(2)
    pdf = args[0]
    if not data_path: data_path = _find_data()
    fails = check(pdf, data_path)
    print("== 渲染煙霧測試：%s ==" % os.path.basename(pdf))
    if fails:
        for f in fails: print("  ❌", f)
        print("共 %d 處破圖（定稿前須清零）" % len(fails)); raise SystemExit(1)
    print("  ✅ 無磚塊／章節連續／無空表／SoF 含死亡+SAE／SoF 列數一致")

if __name__ == "__main__":
    main()
