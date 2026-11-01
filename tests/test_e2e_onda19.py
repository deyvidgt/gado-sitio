#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E + smoke test: full Onda 19 pipeline on real gado_familia.xlsx"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from ia_sintetico import gerar_sintetico
from ia_features import extrair_features, preprocessar_batch
from ia_modelos import ModeloMorte, ModeloCio, calcular_inbreeding_avk
from reproducao_avancada_ia import alertas_ia_preditiva


def test_full_pipeline_synthetic():
    """Full synthetic pipeline: gen → features → models → predict → alerts."""
    # Step 1: Generate
    df = gerar_sintetico(n_animais=200, anos=2, seed=42)
    assert len(df) == 200
    assert 'animal_id' in df.columns

    # Step 2: Extract features
    features_list = []
    for _, row in df.iterrows():
        f = extrair_features(row['animal_id'], df, pd.DataFrame(), pd.DataFrame())
        if f:
            features_list.append(f)
    assert len(features_list) > 150  # >75% coverage

    # Step 3: Predict
    X, scaler = preprocessar_batch(features_list)
    modelo_morte = ModeloMorte()
    modelo_morte.treinar(X.values, np.random.randint(0, 2, len(X)))

    result = modelo_morte.prever(features_list[0])
    assert 'prob_morte' in result
    assert 0 <= result['prob_morte'] <= 100

    # Step 4: Alerts
    ia_result = alertas_ia_preditiva(df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert 'urgentes' in ia_result
    assert 'avisos' in ia_result
    assert 'total' in ia_result


def test_smoke_real_data():
    """Smoke test on real gado_familia.xlsx if available."""
    try:
        from db import ler_aba
        df_animais = ler_aba('Animais')
        df_manejo = ler_aba('Manejo')
        df_compras = ler_aba('Compras')
        df_vendas = ler_aba('Vendas')

        if df_animais is None or df_animais.empty:
            pytest.skip("No real data available")

        # Call IA pipeline
        ia_result = alertas_ia_preditiva(df_animais, df_manejo, df_compras, df_vendas)

        # Verify structure
        assert isinstance(ia_result, dict)
        assert 'urgentes' in ia_result
        assert 'avisos' in ia_result
        assert isinstance(ia_result['urgentes'], list)
        assert isinstance(ia_result['avisos'], list)

        # Verify items have expected fields
        for item in ia_result['urgentes'] + ia_result['avisos']:
            assert 'tipo' in item
            assert 'animal' in item
    except ImportError:
        pytest.skip("db module not available")


def test_integration_alertas_with_ia():
    """Verify alertas.todos() accepts IA parameters."""
    import alertas
    df = gerar_sintetico(n_animais=50, seed=42)

    # Should not raise
    resultado = alertas.todos(
        animais=df,
        df_manejo=pd.DataFrame(),
        df_compras=pd.DataFrame(),
        df_vendas=pd.DataFrame()
    )

    assert isinstance(resultado, list)
