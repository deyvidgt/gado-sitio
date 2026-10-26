#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas da Reprodução — Sítio Santo Antonio v5.3
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import db
import reproducao as R
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


@app.route("/reproducao")
@login_required
def reproducao():
    hoje = pd.Timestamp(_agora()).normalize()
    df_an = A.carregar()
    sit = R.situacao(db.carregar_aba("Manejo"), df_an, hoje)
    vacas = [A.ref(r) for _, r in A.vivos(df_an).iterrows()
             if A._txt(r.get("Sexo")).upper().startswith("F")]
    return render_template("reproducao.html", situacoes=sit,
                           ind=R.indicadores(sit, df_an),
                           alertas=R.alertas(sit, hoje), vacas=vacas,
                           hoje=f"{hoje:%Y-%m-%d}", resultados=R.RESULTADOS)


@app.route("/reproducao/registrar", methods=["POST"])
@login_required
def registrar_reproducao():
    _validar_csrf()
    f = request.form
    tipo = R.TIPO_DIAGNOSTICO if f.get("tipo") == "diagnostico" else R.TIPO_COBERTURA
    try:
        R.registrar(tipo, f.get("vaca", ""), f.get("data"), f.get("touro", ""),
                    f.get("resultado", ""), _membro_logado())
        fazer_backup_seguro()
        flash("🐮 Anotado!" if tipo == R.TIPO_COBERTURA else "🩺 Resultado anotado!",
              "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("reproducao"))
