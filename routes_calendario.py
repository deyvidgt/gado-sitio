# -*- coding: utf-8 -*-
from datetime import date

from flask import render_template, request

from extensions import app, _get_dados_cache, login_required
import calendario


@app.route("/calendario")
@login_required
def calendario_pagina():
    tipo = request.args.get("tipo", "")
    eventos = calendario.eventos(_get_dados_cache(), tipo=tipo or None)
    return render_template("calendario.html", eventos=eventos, tipo=tipo)
