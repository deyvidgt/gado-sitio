#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas dos Pastos com mapa — Sítio Santo Antonio v5.2
"""
import json

import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import pastos as PA
import pesagem as P
from calculos import calcular_estoque
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache,
                        _ler_sitio_config_disco)
from routes_animais import _membro_logado, fazer_backup_seguro


def _peso_medio(df_animais, df_man) -> float:
    """Pesados → Configurações → 0 (o pastos.situacao usa 450 kg)."""
    medio = P.peso_medio_vivos(df_animais, df_man)[0]
    if medio > 0:
        return medio
    try:
        return float(_ler_sitio_config_disco().get("peso_medio", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


@app.route("/pastos")
@login_required
def pastos():
    dados = _get_dados_cache()
    df_p, df_a = PA.carregar(), A.carregar()
    sit = PA.situacao(df_p, df_a, dados["Manejo"],
                      calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"]),
                      _peso_medio(df_a, dados["Manejo"]), hoje=_agora())
    lista = [{"id": p["ID"], "nome": p["Nome"], "area": float(p["Área (ha)"]), "cor": p["Cor"],
              "geo": json.loads(p["Contorno"]), **sit[p["ID"]]}
             for _, p in PA.ativos(df_p).iterrows()]
    return render_template("pastos.html", pastos=lista, sem_pasto=sit[None],
                           hoje=pd.Timestamp(_agora()).strftime("%Y-%m-%d"))


@app.route("/pastos/novo", methods=["POST"])
@login_required
def novo_pasto():
    _validar_csrf()
    try:
        PA.criar(request.form.get("nome"), request.form.get("contorno", ""), _membro_logado())
        flash("🗺️ Pasto salvo!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/<id_>/editar", methods=["POST"])
@login_required
def editar_pasto(id_):
    _validar_csrf()
    f = request.form
    try:
        fazer_backup_seguro()
        PA.editar(id_, nome=f.get("nome"), contorno_json=f.get("contorno") or None)
        flash("Pasto atualizado.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/<id_>/excluir", methods=["POST"])
@login_required
def excluir_pasto(id_):
    _validar_csrf()
    try:
        fazer_backup_seguro()
        PA.excluir(id_)
        flash("Pasto excluído do mapa (o histórico continua no Manejo).", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/mover", methods=["POST"])
@login_required
def mover_gado():
    _validar_csrf()
    f = request.form
    dados = _get_dados_cache()
    refs = None
    if f.get("quem") != "todos":
        refs, erros = A.resolver_texto(f.get("brincos", ""))
        if erros or not refs:
            flash("; ".join(erros) or "Diga quais brincos vão mudar de pasto.", "error")
            return redirect(url_for("pastos"))
    try:
        PA.mover(f.get("pasto"), f.get("data"), refs,
                 calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"]),
                 _membro_logado())
        flash("🐄 Gado movido!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))
