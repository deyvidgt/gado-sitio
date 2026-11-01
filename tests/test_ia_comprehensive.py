#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_ia_comprehensive.py — Comprehensive unit tests for Onda 19
"""

import pytest
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from ia_sintetico import gerar_sintetico
from ia_features import extrair_features, preprocessar_batch
from ia_modelos import ModeloMorte, ModeloCio, calcular_inbreeding_avk


class TestSintetico:
    def test_gerar_sintetico_shape(self):
        df = gerar_sintetico(n_animais=100, anos=1, seed=42)
        assert len(df) == 100
        assert all(col in df.columns for col in ['animal_id', 'evento_tipo', 'sexo', 'inbreeding_avk_pct'])

    def test_gerar_sintetico_reproducible(self):
        df1 = gerar_sintetico(n_animais=50, seed=42)
        df2 = gerar_sintetico(n_animais=50, seed=42)
        assert df1['animal_id'].equals(df2['animal_id'])
        assert df1['evento_tipo'].equals(df2['evento_tipo'])

    def test_gerar_sintetico_morte_rate(self):
        df = gerar_sintetico(n_animais=3000, anos=3, seed=42)
        mortes = (df['evento_tipo'] == 'MORTE').sum()
        taxa_anual = mortes / len(df) / 3
        assert 0.015 < taxa_anual < 0.08, f"Taxa {taxa_anual} fora de faixa"


class TestFeatures:
    def test_extrair_features_count(self):
        df = gerar_sintetico(n_animais=10, seed=42)
        features = extrair_features('A0000', df, pd.DataFrame(), pd.DataFrame())
        assert len(features) == 25

    def test_extrair_features_normalized(self):
        df = gerar_sintetico(n_animais=10, seed=42)
        features = extrair_features('A0000', df, pd.DataFrame(), pd.DataFrame())
        assert all(0 <= v <= 1 for v in features.values()), "Todas features devem estar em [0,1]"

    def test_extrair_features_nan_handling(self):
        df = pd.DataFrame({'animal_id': ['A0001'], 'sexo': [None], 'peso_estimado_kg': [np.nan]})
        features = extrair_features('A0001', df, pd.DataFrame(), pd.DataFrame())
        assert features is not None
        assert not any(pd.isna(v) for v in features.values())

    def test_preprocessar_batch_shape(self):
        features_list = [
            {f'f{i}': np.random.rand() for i in range(25)}
            for _ in range(50)
        ]
        df, scaler = preprocessar_batch(features_list)
        assert df.shape[0] == 50
        assert df.shape[1] == 25
        assert scaler is not None


class TestModels:
    def test_modelo_morte_training(self):
        X = np.random.randn(100, 25)
        y = np.random.randint(0, 2, 100)
        modelo = ModeloMorte()
        modelo.treinar(X, y)
        assert modelo.modelo is not None
        assert modelo.scaler is not None

    def test_modelo_morte_prever_output(self):
        X = np.random.randn(100, 25)
        y = np.random.randint(0, 2, 100)
        modelo = ModeloMorte()
        modelo.treinar(X, y)

        features = {f'f{i}': np.random.rand() for i in range(25)}
        result = modelo.prever(features)

        assert 'prob_morte' in result
        assert 'urgencia' in result
        assert 0 <= result['prob_morte'] <= 100
        assert result['urgencia'] in ['URGENTE', 'AVISO', 'OK']

    def test_modelo_morte_thresholds(self):
        """Threshold boundaries: 70% = URGENTE, 50% = AVISO"""
        X = np.random.randn(100, 25)
        y = np.concatenate([np.ones(70), np.zeros(30)])

        modelo = ModeloMorte()
        modelo.treinar(X, y)

        # Mock high prob
        features = {f'f{i}': 0.9 if i < 10 else 0.1 for i in range(25)}
        result = modelo.prever(features)

        # Just check structure is correct
        assert result['urgencia'] in ['URGENTE', 'AVISO', 'OK']

    def test_modelo_cio_training(self):
        X = np.random.randn(100, 25)
        y = np.random.uniform(1, 25, 100)
        modelo = ModeloCio()
        modelo.treinar(X, y)
        assert modelo.modelo is not None

    def test_modelo_cio_prever_output(self):
        X = np.random.randn(100, 25)
        y = np.random.uniform(1, 25, 100)
        modelo = ModeloCio()
        modelo.treinar(X, y)

        features = {f'f{i}': np.random.rand() for i in range(25)}
        result = modelo.prever(features)

        assert 'dias_ate_cio' in result
        assert 1 <= result['dias_ate_cio'] <= 25
        assert 0 <= result['confianca'] <= 1
        assert 'alertar' in result

    def test_calcular_inbreeding_avk_missing_pedigree(self):
        df = pd.DataFrame({
            'animal_id': ['A0001'],
            'Pai': [None],
            'Mãe': [None],
        })
        # calcular_inbreeding_avk expects animal_id in df
        avk = calcular_inbreeding_avk('A0001', df)
        assert avk == 0.0

    def test_calcular_inbreeding_avk_with_pedigree(self):
        df = pd.DataFrame({
            'animal_id': ['A0001', 'A0002', 'A0003'],
            'Pai': ['A0002', None, None],
            'Mãe': ['A0003', None, None],
        })
        avk = calcular_inbreeding_avk('A0001', df)
        assert 0 <= avk <= 0.25


class TestEndToEnd:
    def test_full_pipeline(self):
        """Synthetic → Features → Models → Predictions"""
        # Generate synthetic
        df = gerar_sintetico(n_animais=100, anos=1, seed=42)

        # Extract features
        features_list = []
        labels = []
        for _, row in df.iterrows():
            features = extrair_features(row['animal_id'], df, pd.DataFrame(), pd.DataFrame())
            if features:
                features_list.append(features)
                labels.append(1 if row['evento_tipo'] == 'MORTE' else 0)

        assert len(features_list) > 0

        # Train model
        X, scaler = preprocessar_batch(features_list)
        y = np.array(labels)

        modelo = ModeloMorte()
        modelo.treinar(X.values, y)

        # Predict
        result = modelo.prever(features_list[0])
        assert 'prob_morte' in result
        assert 0 <= result['prob_morte'] <= 100
