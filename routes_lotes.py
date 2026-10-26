#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas do painel por lote — Sítio Santo Antonio v5.3
"""
from flask import render_template

import lotes as L
from extensions import app, _agora, _get_dados_cache, login_required


@app.route("/lotes")
@login_required
def lotes():
    d = _get_dados_cache()
    r = L.calcular(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"], hoje=_agora())
    return render_template("lotes.html", **r)
