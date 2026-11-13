#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_indicadores_embrapa.py — Rotas para Indicadores Zootécnicos ANCP / Embrapa (Taxa de Desmama e Natalidade)
"""
from flask import render_template
import indicadores_embrapa as IE
import animais as A
import db
from extensions import app, login_required, _get_dados_cache

@app.route("/indicadores/embrapa")
@login_required
def indicadores_embrapa():
    """Painel de Indicadores Zootécnicos Embrapa / ANCP (Taxa de Desmama e Natalidade)."""
    dados = _get_dados_cache()
    df_animais = A.carregar()
    df_man = dados.get("Manejo", pd.DataFrame())

    natalidade = IE.calcular_taxa_natalidade(df_animais, df_man)
    desmama = IE.calcular_taxa_desmama(df_animais, df_man)

    return render_template(
        "indicadores_embrapa.html",
        natalidade=natalidade,
        desmama=desmama,
    )
