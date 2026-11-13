#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_modulos_zootecnicos_financeiros.py — Testes para os módulos avançados zootécnicos e financeiros (v5.25)
"""
import pytest
import pandas as pd


def test_rotas_zootecnicas_financeiras(cliente):
    """Testa se as rotas de calculador de ração avançado, relatórios gráficos e financeiro respondem."""
    assert cliente.get("/racao/calculador").status_code in (200, 302)
    assert cliente.get("/relatorios/graficos-rebanho").status_code in (200, 302)
    assert cliente.get("/financeiro").status_code in (200, 302)
