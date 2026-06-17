# -*- coding: utf-8 -*-
"""unpaywall 測試：離線測 email 解析；network 標記測真 OA 查詢。"""
import pytest
import unpaywall


def test_mailto_returns_valid_email():
    """_mailto 一定回可用 email（含 @）；fresh-clone 無 settings.yaml 時退回 anonymous@example.com 亦屬合法。"""
    m = unpaywall._mailto()
    assert "@" in m


def test_mailto_prefers_env_override(monkeypatch):
    """有 env CROSSREF_MAILTO 時優先採用、且非佔位（不依賴本機被 gitignore 的 settings.yaml）。"""
    monkeypatch.setenv("CROSSREF_MAILTO", "real.user@hospital.org")
    m = unpaywall._mailto()
    assert m == "real.user@hospital.org" and "example.com" not in m


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
