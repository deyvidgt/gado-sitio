#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_culling.py — Testes para Gestão de Culling (Descarte Estratégico de Fêmeas)
"""
import pytest
import pandas as pd


def test_reproducao_culling_vazio():
    import reproducao_avancada as RA

    df_m = pd.DataFrame()
    df_a = pd.DataFrame()

    culling = RA.sugestoes_culling(df_m, df_a)
    assert isinstance(culling, list)
    assert len(culling) == 0
