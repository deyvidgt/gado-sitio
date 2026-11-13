#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_precisao.py — Testes para os módulos de zootecnia de precisão e indicadores (v5.30)
"""
import pytest


def test_rotas_precisao(cliente):
    """Testa se as rotas de precisão respondem com sucesso."""
    assert cliente.get("/nutricao/indicadores").status_code in (200, 302)
    assert cliente.get("/animais/estoque").status_code in (200, 302)
    assert cliente.get("/reproducao/cio-parto").status_code in (200, 302)
    assert cliente.get("/sanitario/calendario").status_code in (200, 302)
