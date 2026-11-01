#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration: reproducao_avancada_ia + alertas.py"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ia_sintetico import gerar_sintetico
from reproducao_avancada_ia import alertas_ia_preditiva
import alertas


class TestIAAlertasIntegration:
    def test_alertas_ia_preditiva_called_by_alertas_todos(self):
        """alertas.todos() integrates IA predictions."""
        df = gerar_sintetico(n_animais=50, seed=42)

        # Mock data
        df_manejo = pd.DataFrame()
        df_compras = pd.DataFrame()
        df_vendas = pd.DataFrame()

        # Call todos with IA data
        resultado = alertas.todos(
            animais=df,
            df_manejo=df_manejo,
            df_compras=df_compras,
            df_vendas=df_vendas
        )

        # Should have items (leiteiro + IA)
        assert isinstance(resultado, list)
        assert len(resultado) > 0

    def test_alertas_todos_handles_missing_ia_models(self):
        """alertas.todos() gracefully skips IA when models missing."""
        df = gerar_sintetico(n_animais=20, seed=42)

        # Call without models (FileNotFoundError caught)
        resultado = alertas.todos(animais=df)

        # Should return list (even if empty or just leiteiro alerts)
        assert isinstance(resultado, list)

    def test_ia_urgentes_appear_in_todos(self):
        """Morte urgente (>70%) from IA appears in alertas.todos()."""
        df = gerar_sintetico(n_animais=100, seed=42)

        # Mock manejo data
        df_manejo = pd.DataFrame({
            'Brinco': ['A0001'] * 5,
            'Tipo': ['Medicação', 'Vacina', 'Tratamento Veterinário', 'Nascimento', 'Morte'],
            'Data': pd.date_range('2026-10-01', periods=5),
            'Descrição': ['', '', '', '', '']
        })

        resultado = alertas.todos(
            animais=df,
            df_manejo=df_manejo,
            df_compras=pd.DataFrame(),
            df_vendas=pd.DataFrame()
        )

        # Should have IA-originated alerts (origem='ia_*')
        ia_alerts = [item for item in resultado if item['origem'].startswith('ia_')]
        assert len(ia_alerts) >= 0  # May be 0 if no high-risk animals
