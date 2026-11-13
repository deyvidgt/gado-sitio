#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_estimar_peso.py — Testes para o módulo de Estimação de Peso por Foto / Biometria Bovina (v5.20)
"""

import pytest
import pandas as pd
from flask import url_for


def test_estimar_peso_valida_medidas():
    import peso_foto as PF

    # Validação correta
    comp, prof, ref, bcs = PF.validar("140", "70", "100", "5")
    assert comp == 140.0
    assert prof == 70.0
    assert ref == 100.0
    assert bcs == 5


def test_estimar_peso_calculo_bruto():
    import peso_foto as PF

    # Fórmula Schaeffer
    bruto = PF.estimar_bruto(140.0, 70.0)
    assert bruto > 0
    assert isinstance(bruto, float)


def test_estimar_peso_rota_get(cliente):
    """Testa se a página de estimativa de peso carrega corretamente."""
    res = cliente.get("/animais/estimar_peso")
    # Redireciona para login se não autenticado, ou carrega se autenticado
    assert res.status_code in (200, 302)
