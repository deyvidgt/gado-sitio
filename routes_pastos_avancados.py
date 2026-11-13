#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_pastos_avancados.py — Rotas para Controle Físico e Sanitário de Pastagens (Rotativo x Descanso)
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
import pastos as PA
import pastos_avancados as PAV
import animais as A
import db
from extensions import app, login_required, _get_dados_cache

@app.route("/pastos/rotativo")
@login_required
def pastos_rotativo():
    """Painel de Pastoreio Rotativo, Altura de Pastejo, Descanso e UA/ha."""
    dados = _get_dados_cache()
    df_pastos = PA.carregar()
    df_animais = A.carregar()
    df_man = dados.get("Manejo", pd.DataFrame())

    relatorio = PAV.relatorio_geral_pastagens(df_pastos, df_animais, df_man)

    return render_template(
        "pastos_rotativo.html",
        relatorio=relatorio,
    )
