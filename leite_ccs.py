#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
leite_ccs.py — Contagem de células somáticas (CCS) e contaminação bacteriana (CPP)

Painel do leite (v5.4): rastreamento de qualidade de leite por animal.
"""

import pandas as pd
from db import carregar_aba


def carregar():
    """Carrega aba 'Leite Produção' do Excel."""
    try:
        df = carregar_aba("Leite Produção")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
