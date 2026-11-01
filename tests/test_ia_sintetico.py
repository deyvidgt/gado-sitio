#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for ia_sintetico.py — synthetic data generation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ia_sintetico import gerar_sintetico


def test_gerar_sintetico_shape():
    """Synthetic data has expected shape and required columns."""
    df = gerar_sintetico(n_animais=100, anos=1, seed=42)
    assert len(df) == 100
    assert 'animal_id' in df.columns
    assert 'evento_tipo' in df.columns
    assert 'sexo' in df.columns
    assert 'dono' in df.columns
    assert 'inbreeding_avk_pct' in df.columns


def test_gerar_sintetico_morte_rate():
    """Death rate in synthetic data is 2-5% per year (cumulative)."""
    df = gerar_sintetico(n_animais=5000, anos=3, seed=42)
    mortes = (df['evento_tipo'] == 'MORTE').sum()
    taxa_anual = mortes / len(df) / 3
    assert 0.02 < taxa_anual < 0.05, f"Death rate {taxa_anual} outside 2-5% range"


def test_gerar_sintetico_reproducible():
    """Same seed produces identical data."""
    df1 = gerar_sintetico(n_animais=500, anos=2, seed=42)
    df2 = gerar_sintetico(n_animais=500, anos=2, seed=42)
    assert df1['animal_id'].equals(df2['animal_id'])
    assert df1['evento_tipo'].equals(df2['evento_tipo'])


def test_gerar_sintetico_sexo_distribution():
    """Sex ratio is approximately 55% F, 45% M."""
    df = gerar_sintetico(n_animais=2000, seed=42)
    f_pct = (df['sexo'] == 'F').sum() / len(df)
    m_pct = (df['sexo'] == 'M').sum() / len(df)
    assert 0.50 < f_pct < 0.60, f"F ratio {f_pct} outside 50-60% range"
    assert 0.40 < m_pct < 0.50, f"M ratio {m_pct} outside 40-50% range"


def test_gerar_sintetico_pedigree_coverage():
    """~80% of animals have known pai_id and mae_id."""
    df = gerar_sintetico(n_animais=1000, seed=42)
    pai_known = (df['pai_id'].notna()).sum() / len(df)
    mae_known = (df['mae_id'].notna()).sum() / len(df)
    assert 0.75 < pai_known < 0.85, f"Pai coverage {pai_known} outside 75-85%"
    assert 0.75 < mae_known < 0.85, f"Mae coverage {mae_known} outside 75-85%"
