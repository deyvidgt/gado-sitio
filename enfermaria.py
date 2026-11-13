#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enfermaria.py — Módulo de Enfermaria e Saúde Animal (v5.23)
Níveis de gravidade (Observação, Crítico/Grave), monitoramento de sintomas, tratamentos e histórico de curas.
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime
import db
import animais as A

ABA_ENFERMARIA = "Enfermaria"


def carregar_enfermaria() -> pd.DataFrame:
    df = db.carregar_aba(ABA_ENFERMARIA)
    colunas_padrao = ["ID", "Data Entrada", "Animal ID", "Gravidade", "Sintomas", "Diagnostico", "Tratamento", "Status", "Data Cura", "Observacoes"]
    for c in colunas_padrao:
        if c not in df.columns:
            df[c] = None
    return df[colunas_padrao].copy()


def animais_em_tratamento() -> list[dict]:
    df = carregar_enfermaria()
    if df.empty:
        return []
    ativos = df[df["Status"].astype(str).str.lower().isin(["observacao", "critico", "grave", "ativo", "em tratamento"])]
    return ativos.to_dict("records")
