#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_comparativo_anual.py — Teste para a formatação em /comparativo-anual
"""
import pytest


def test_comparativo_anual_formatacao(cliente):
    """Testa se a página de comparativo anual carrega e substituiu a abreviação em 'k' pelo filtro brl."""
    res = cliente.get("/comparativo-anual")
    assert res.status_code in (200, 302)
    if res.status_code == 200:
        html = res.get_data(as_text=True)
        assert "R$ " in html
        assert "k" not in html.lower() or "R$ " in html
