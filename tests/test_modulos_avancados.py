#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_modulos_avancados.py — Testes para os módulos avançados de corte e leite (v5.23-5.24)
"""
import pytest
import pandas as pd


def test_modulos_avancados_rotas(cliente):
    """Testa se as rotas de enfermaria, alertas de parto, controle leiteiro e curral respondem."""
    assert cliente.get("/animais/enfermaria").status_code in (200, 302)
    assert cliente.get("/reproducao/alertas-parto").status_code in (200, 302)
    assert cliente.get("/leite/controle").status_code in (200, 302)
    assert cliente.get("/curral").status_code in (200, 302)
