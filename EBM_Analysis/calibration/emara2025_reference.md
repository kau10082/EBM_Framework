# 校準參考：Emara 2025 GRADE-assessed MA

**用途**：corpus 內含一篇作者自做 GRADE 的 meta-analysis（Emara et al. Respiratory Research 2025;26:332）。
把**本引擎對同一證據體的 GRADE 輸出**與**Emara 作者的 GRADE**並列，作為引擎的外部校準/驗證迴路。

## Emara 作者自評 GRADE（ground truth，逐字依據見原文 Certainty of evidence 段＋Table 3）
| Outcome | Emara 確定性 | 下調理由（作者） |
|---|---|---|
| Time to first exacerbation | **Low ⊕⊕◯◯** | 間接性＋不一致性＋不精確 |
| Exacerbation rate（one exacerbation rate） | **Low ⊕⊕◯◯** | 間接性＋不一致性＋不精確 |
| Any AEs | **Low ⊕⊕◯◯** | 間接性＋不一致性＋不精確 |
| Serious AEs | **Moderate ⊕⊕⊕◯** | 僅間接性下調；結果一致、估計精確 |
| Severe exacerbation rate | **Very low ⊕◯◯◯** | 間接性＋**非常嚴重不精確** |
| Exacerbation-free status | **Very low ⊕◯◯◯** | 間接性＋**非常嚴重不精確** |

關鍵特徵：**所有 outcome 皆因間接性下調**（納入試驗用不同 DPP-1 藥物、療程短、部分替代性質）；出版偏誤經漏斗圖/檢定判定不太可能影響結論。

## 校準比對程序（待引擎跑完 Emara_MA 的 Phase 3 後填）
1. 對 Emara_MA 走 phases 1–4（track A），逐 outcome 輸出引擎 GRADE。
2. 逐 outcome 比對：
   - 引擎層級 vs Emara 層級（差 0 級＝吻合、差 1 級＝可接受、差 ≥2 級＝須檢討）
   - 下調領域是否一致（特別是「全數因間接性下調」這點，引擎的 surrogate+indirectness 是否抓到）
3. 不一致處回頭檢查：是引擎判太嚴/太鬆，還是 schema/guardrail 規則需修。

| Outcome | Emara | 引擎 | 差距 | 領域是否一致 | 備註 |
|---|---|---|---|---|---|
| Time to first exacerbation | Low | **Low** | 0 級 ✅ | 間接性＋不一致性（Emara 另加不精確） | 吻合 |
| Exacerbation rate（≥1） | Low | **Low** | 0 級 ✅ | 間接性＋不一致性 | 吻合 |
| Any AEs | Low | **Low** | 0 級 ✅ | 間接性＋不一致性 | 吻合 |
| Serious AEs | Moderate | **Moderate** | 0 級 ✅ | 僅間接性 | 吻合 |
| Severe exacerbation rate | Very low | **Very low** | 0 級 ✅ | 間接性＋非常嚴重不精確 | 吻合 |
| Exacerbation-free status | Very low | **Very low** | 0 級 ✅ | 間接性＋非常嚴重不精確 | 吻合 |

**結果：6/6 確定性層級完全吻合，且關鍵下調領域一致——尤其引擎獨立判出「合併 4 種不同 DPP-1 藥→間接性下調」（與 Emara 全數因間接性下調相符）。**

⚠️ **誠實限制（非盲）**：本次評 Emara 時已先看過其 GRADE 表，故屬「一致性檢查」而非盲測，可能有確認偏誤。真正的盲測是 WILLOW／ASPEN——評它們時未參照任何外部 GRADE：
- ASPEN（單一 brensocatib Phase 3）：核心惡化結果評「高」。
- WILLOW（單一 brensocatib Phase 2）：核心評「中」（小樣本不精確）。
- 兩者皆高於 Emara 對「跨藥物 MA」的「低」——差異來源＝Emara 的間接性（跨 4 藥）＋不一致性，單一試驗沒有。**這個分歧是方法學上正確的，不是引擎錯**。
> 未來若要嚴格驗證，應：(a) 先盲評再揭曉對照；(b) 以引擎「統合層」（合併同 4 試驗）的 GRADE 對 Emara，而非單篇。
