#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for ia_features.py — 25-feature extraction for ML models
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ia_features import extrair_features, preprocessar_batch


def test_extrair_features_shape():
    """Feature extraction returns dict with 25 normalized features."""
    df_animais = pd.DataFrame({
        'ID': ['A0001'],
        'Data Nascimento': ['01/01/2020'],
        'Sexo': ['F'],
        'Peso Estimado (kg)': [400.0],
    })
    df_manejo = pd.DataFrame()
    df_vendas = pd.DataFrame()

    features = extrair_features('A0001', df_animais, df_manejo, df_vendas)

    assert isinstance(features, dict)
    assert len(features) == 25, f"Expected 25 features, got {len(features)}"
    assert 'idade_dias_norm' in features


def test_extrair_features_normalized():
    """All features are normalized to [0, 1]."""
    df_animais = pd.DataFrame({
        'ID': ['A0001'],
        'Data Nascimento': ['01/01/2020'],
        'Sexo': ['F'],
        'Peso Estimado (kg)': [400.0],
    })

    features = extrair_features('A0001', df_animais, pd.DataFrame(), pd.DataFrame())

    for key, value in features.items():
        assert 0 <= value <= 1, f"Feature {key}={value} outside [0,1]"


def test_extrair_features_nan_handling():
    """Missing data (NaN) is imputed with median, not propagated."""
    df_animais = pd.DataFrame({
        'ID': ['A0001'],
        'Data Nascimento': [pd.NaT],
        'Sexo': [None],
        'Peso Estimado (kg)': [np.nan],
    })

    features = extrair_features('A0001', df_animais, pd.DataFrame(), pd.DataFrame())

    assert features is not None
    assert not any(pd.isna(v) for v in features.values()), "Features must not contain NaN"


def test_preprocessar_batch_returns_scaler():
    """Batch preprocessing returns DataFrame and StandardScaler."""
    features_list = [
        {'idade_dias_norm': 0.5, 'sexo': 1.0, 'num_tratamentos_90d_norm': 0.2},
        {'idade_dias_norm': 0.6, 'sexo': 0.0, 'num_tratamentos_90d_norm': 0.3},
    ]

    df, scaler = preprocessar_batch(features_list)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert df.shape[1] == 3
    assert scaler is not None


def test_extrair_features_reproducible():
    """Same input produces same features (seed consistency)."""
    df_animais = pd.DataFrame({
        'ID': ['A0001'],
        'Data Nascimento': ['01/01/2020'],
        'Sexo': ['F'],
        'Peso Estimado (kg)': [400.0],
    })

    f1 = extrair_features('A0001', df_animais, pd.DataFrame(), pd.DataFrame(), hoje='2026-11-01')
    f2 = extrair_features('A0001', df_animais, pd.DataFrame(), pd.DataFrame(), hoje='2026-11-01')

    assert f1 == f2
