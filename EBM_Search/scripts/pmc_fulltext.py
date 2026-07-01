#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pmc_fulltext.py — ③ Tier 3 全文取得『正規』PMC 全文擷取器（committed, portable）
================================================================================
把『如何抓 PMC 全文正文』與『NCBI E-utilities 速率限制』從**靠記性**改成
**committed 程式碼**——不再依賴個人 auto-memory（auto-memory 不隨 repo、別人 clone 拿不到，
見 SEARCH_SPEC「可攜可靠性」鐵律）。

定版兩鐵律（2026-06 使用者糾正後落地）
------------------------------------------------
1. **全文路徑＝NCBI efetch `db=pmc`（解析 <body> 正文），不用 EuropePMC `fullTextXML`。**
   （EuropePMC fullTextXML 對本流程不穩/常空；efetch db=pmc 對 PMC OA subset 穩定回 JATS XML。
   非 OA-subset 的 PMC 文章 efetch 只回 front matter（無 <body>）→ 視為『PMC 無全文』、續走 Tier 4 Unpaywall。）
2. **NCBI E-utilities 速率限制必遵守**：無 API key ＝ **3 req/s**；有 key（settings `pubmed.ncbi_api_key`
   或 env `NCBI_API_KEY`）＝ **10 req/s**。超速會被 429 節流→整批靜默失敗（本框架實測：
   Tier 3 一度 sleep 0.2s＝5 req/s→全部 efetch 回 None→0 篇全文。本器內建節流，杜絕此復發）。

零相依（純 stdlib）。可 import，也可 CLI 自測。
  from pmc_fulltext import NcbiClient
  cli = NcbiClient(mailto, api_key)
  pmcids = cli.idconv_pmcids(["35486828", ...])      # {pmid: 'PMC...'}
  text   = cli.fetch_pmc_body("PMC9046468")          # str 正文 或 None
CLI:
  python pmc_fulltext.py --pmids 35486828,41914528    # 解析並印出每篇正文長度
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
UA = "ebm-framework-pmc/1.0 (mailto:%s)"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from xref_verify import load_settings, default_settings_path  # noqa: E402
except Exception:  # noqa: BLE001
    def load_settings(path):
        return {}

    def default_settings_path():
        return os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "settings.yaml"))


def resolve_credentials(settings_path=None):
    """回 (mailto, api_key)。優先序：env > settings.yaml > 預設。api_key 可為 ''（＝無 key→3 req/s）。"""
    s = {}
    try:
        s = load_settings(settings_path or default_settings_path()) or {}
    except Exception:  # noqa: BLE001
        s = {}
    mailto = (os.environ.get("CROSSREF_MAILTO")
              or (s.get("crossref", {}) or {}).get("mailto", "")
              or "anon@example.com")
    api_key = (os.environ.get("NCBI_API_KEY")
               or (s.get("pubmed", {}) or {}).get("ncbi_api_key", "")
               or "")
    return mailto, api_key


class _RateLimiter:
    """強制 E-utilities 最小請求間隔：無 key 3 req/s（0.34s）、有 key 10 req/s（0.11s）。
    留 10% 安全邊際避免邊界 429。"""
    def __init__(self, has_key):
        self.min_interval = (1.0 / 10.0 if has_key else 1.0 / 3.0) * 1.10
        self._last = 0.0

    def wait(self):
        now = time.monotonic()
        gap = now - self._last
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
        self._last = time.monotonic()


class NcbiClient:
    """E-utilities 用戶端：內建速率限制＋重試。專責 PMID→PMCID 與 PMC 全文正文擷取。"""
    def __init__(self, mailto, api_key="", timeout=90):
        self.mailto = mailto
        self.api_key = api_key or ""
        self.timeout = timeout
        self.rl = _RateLimiter(bool(self.api_key))

    def _key_param(self):
        return ("&api_key=" + urllib.parse.quote(self.api_key)) if self.api_key else ""

    def _http(self, url, tries=4):
        for i in range(tries):
            self.rl.wait()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA % self.mailto})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return r.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001（含 429 HTTPError）→ 退避重試
                time.sleep(1.0 + i)
        return None

    def idconv_pmcids(self, pmids, batch=190):
        """PMID 清單 → {pmid(str): 'PMCxxxx'}（只含有 PMC 版者）。批次走 idconv。"""
        out = {}
        pmids = [str(p) for p in pmids if p]
        for i in range(0, len(pmids), batch):
            chunk = pmids[i:i + batch]
            url = "%s?ids=%s&format=json&tool=ebm-framework&email=%s%s" % (
                IDCONV, urllib.parse.quote(",".join(chunk)),
                urllib.parse.quote(self.mailto), self._key_param())
            d = self._http(url)
            if not d:
                sys.stderr.write("⚠ idconv batch %d–%d 抓取失敗：%d 筆 PMID 無法判定有無 PMC 版"
                                 "（抓取失敗≠無 PMC 版，覆蓋率會無聲下降；請重跑）\n" % (i, i + batch, len(chunk)))
                continue
            try:
                for rec in json.loads(d).get("records", []):
                    if rec.get("pmcid"):
                        out[str(rec.get("pmid"))] = rec["pmcid"]
            except Exception as e:  # noqa: BLE001
                sys.stderr.write("⚠ idconv batch %d 回應解析失敗（%s）：該批 %d 筆視同未判定\n"
                                 % (i, str(e)[:40], len(chunk)))
        return out

    def fetch_pmc_body(self, pmcid, min_len=1500):
        """PMCID → 全文正文純文字（解析 JATS <body>）。
        回 None＝非 OA-subset（無 <body>，只有 front matter）或抓取失敗 → 呼叫端續走 Tier 4。"""
        if not pmcid:
            return None
        num = str(pmcid).replace("PMC", "")
        url = "%s/efetch.fcgi?db=pmc&id=%s&retmode=xml%s" % (EUTILS, urllib.parse.quote(num), self._key_param())
        xml = self._http(url)
        if not xml:
            sys.stderr.write("⚠ efetch db=pmc %s 抓取失敗（≠非 OA subset）\n" % pmcid)
            return None
        m = re.search(r"<body[ >].*?</body>", xml, re.S)
        if not m:
            return None  # 無 <body>＝非 OA 全文（front matter only）→ 不是真全文
        txt = re.sub(r"<[^>]+>", " ", m.group(0))
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt if len(txt) >= min_len else None

    def fulltext_for_pmids(self, pmids):
        """便利包裝：PMID 清單 → {pmid: text}（僅含成功取到正文者）。"""
        pmcids = self.idconv_pmcids(pmids)
        out = {}
        for pmid, pmcid in pmcids.items():
            t = self.fetch_pmc_body(pmcid)
            if t:
                out[pmid] = t
        return out


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="PMC 全文擷取器（efetch db=pmc，內建 NCBI 速率限制）")
    ap.add_argument("--pmids", help="逗號分隔 PMID")
    ap.add_argument("--config", help="settings.yaml 路徑")
    a = ap.parse_args(argv)
    mailto, api_key = resolve_credentials(a.config)
    cli = NcbiClient(mailto, api_key)
    print("rate: %s（min interval %.3fs）｜ mailto=%s" % (
        "10 req/s (api_key)" if api_key else "3 req/s (no key)", cli.rl.min_interval, mailto))
    if a.pmids:
        pmids = [x.strip() for x in a.pmids.split(",") if x.strip()]
        pmcids = cli.idconv_pmcids(pmids)
        print("PMCIDs:", pmcids)
        for pmid, pmcid in pmcids.items():
            t = cli.fetch_pmc_body(pmcid)
            print("  PMID %s → %s → %s" % (pmid, pmcid, ("%d chars" % len(t)) if t else "no <body> (non-OA)→Tier4"))


if __name__ == "__main__":
    main()
