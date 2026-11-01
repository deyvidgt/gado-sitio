#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for ia_modelos.py — ML model classes for death, estrus, inbreeding prediction
"""

import pytest
import pandas as pd
import numpy as np
from ia_modelos import ModeloMorte, ModeloCio, calcular_inbreeding_avk


def test_modelo_morte_treina():
    """ModeloMorte trains on X, y without error."""
    X = np.random.randn(100, 25)
    y = np.random.randint(0, 2, 100)

    modelo = ModeloMorte()
    modelo.treinar(X, y)

    assert modelo.modelo is not None
    assert modelo.scaler is not None


def test_modelo_morte_prever_range():
    """ModeloMorte.prever() returns dict with prob in [0,100], urgencia in {URGENTE, AVISO, OK}."""
    X = np.random.randn(100, 25)
    y = np.random.randint(0, 2, 100)
    modelo = ModeloMorte()
    modelo.treinar(X, y)

    features = {f'f{i}': np.random.rand() for i in range(25)}
    result = modelo.prever(features)

    assert isinstance(result, dict)
    assert 0 <= result['prob_morte'] <= 100
    assert result['urgencia'] in ['URGENTE', 'AVISO', 'OK']
    assert isinstance(result['motivos'], list)
    assert 'acao' in result


def test_modelo_cio_treina():
    """ModeloCio trains on X, y (regression) without error."""
    X = np.random.randn(100, 25)
    y = np.random.uniform(1, 25, 100)  # Days to estrus

    modelo = ModeloCio()
    modelo.treinar(X, y)

    assert modelo.modelo is not None
    assert modelo.scaler is not None


def test_modelo_cio_prever_range():
    """ModeloCio.prever() returns dias in [1,25], data_prevista is future date."""
    X = np.random.randn(100, 25)
    y = np.random.uniform(1, 25, 100)
    modelo = ModeloCio()
    modelo.treinar(X, y)

    features = {f'f{i}': np.random.rand() for i in range(25)}
    result = modelo.prever(features)

    assert isinstance(result, dict)
    assert 1 <= result['dias_ate_cio'] <= 25
    assert 0 <= result['confianca'] <= 1
    assert result['alertar'] in [True, False]
    assert result['data_prevista'] is not None


def test_calcular_avk_missing_pedigree():
    """AVK calculation handles missing Pai/Mãe without crashing; returns 0.0."""
    df = pd.DataFrame({
        'ID': ['A0001'],
        'Pai': [None],
        'Mãe': [None],
    })
    avk = calcular_inbreeding_avk('A0001', df)
    assert avk == 0.0


def test_calcular_avk_known_pedigree():
    """AVK calculation > 0 when animal has pedigree."""
    df = pd.DataFrame({
        'ID': ['A0001', 'A0002', 'A0003'],
        'Pai': ['A0002', None, None],
        'Mãe': ['A0003', None, None],
    })
    avk = calcular_inbreeding_avk('A0001', df)
    assert avk > 0.0
    assert avk <= 1.0
