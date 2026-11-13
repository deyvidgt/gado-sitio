#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_alertas_parto.py — Alertas de Parto e Controle Reprodutivo (v5.23)
"""
from flask import render_template
import pandas as pd
import db
import animais as A
import reproducao as R
from extensions import app, login_required, _agora

@app.route("/reproducao/alertas-parto")
@login_required
def alertas_parto():
    """Painel de Matrizes Próximas ao Parto."""
    hoje = pd.Timestamp(_agora()).normalize()
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    sit = R.situacao(df_man, df_an, hoje)

    return render_template("alertas_parto.html", situacoes=sit)
