# -*- coding: utf-8 -*-
"""unpaywall 測試：離線測 email 解析；network 標記測真 OA 查詢。"""
import pytest
import unpaywall


def test_mailto_resolves_non_placeholder():
    """_mailto 要從 config 取真 email（非 example.com 佔位）。"""
    m = unpaywall._mailto()
    assert "@" in m and "example.com" not in m


def test_lookup_empty_doi_returns_empty():
    assert unpaywall.lookup("") == {}
    assert unpaywall.oa_pdf("") == ""


@pytest.mark.network
def test_lookup_known_oa_article():
    """Emara(BMC Respir Res) 為 gold OA→is_oa 應為真、且有 PDF url。"""
    d = unpaywall.lookup("10.1186/s12931-025-03407-2")
    assert d.get("is_oa") is True
    assert d.get("pdf_url", "").lower().endswith(".pdf")


@pytest.mark.network
def test_lookup_paywalled_returns_doi_record():
    """付費刊也應回 dict（不報錯）；is_oa 可能 True(green 典藏)或 False。"""
    d = unpaywall.lookup("10.1056/NEJMoa2411664")
    assert isinstance(d, dict) and "is_oa" in d
