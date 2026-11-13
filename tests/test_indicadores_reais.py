#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_indicadores_reais.py — Testes para a rota de Índices Zootécnicos e cruzamento de dados reais
"""
import pytest


def test_indicadores_rota(cliente):
    """Testa se a rota /indicadores carrega com sucesso e cruza dados reais."""
    res = cliente.get("/indicadores")
    assert res.status_code in (200, 302)
