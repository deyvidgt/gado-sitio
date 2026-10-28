#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_confinamento_genetica.py — Rotas para confinamento e genética (v5.10)

Rotas simples:
- /confinamento — lista lotes ativos
- /confinamento/novo — formulário novo lote
- /genetica — avisos de endogamia
- /genetica/compatibilidade — simulador de acasalamento
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from extensions import app, login_required, _get_dados_cache
import confinamento as CONF
import genetica as GEN
from db import salvar_linha, carregar_aba
from extensions import _agora, fmt_data, fmt_brl
from datetime import datetime
import pandas as pd


@app.route("/confinamento")
@login_required
def confinamento():
    """Página de lotes em confinamento."""
    dados = _get_dados_cache()
    ativos = CONF.lotes_ativos(dados)

    # Preparar dados para template
    lotes_list = []
    if not ativos.empty:
        for _, lote in ativos.iterrows():
            lotes_list.append({
                "lote_id": lote.get("Lote ID", "—"),
                "quantidade": int(pd.to_numeric(lote.get("Quantidade", 0), errors="coerce") or 0),
                "peso_inicial": pd.to_numeric(lote.get("Peso Inicial (kg)", 0), errors="coerce") or 0,
                "peso_final": pd.to_numeric(lote.get("Peso Final (kg)", 0), errors="coerce") or 0,
                "gmd": pd.to_numeric(lote.get("GMD (kg/dia)", 0), errors="coerce") or 0,
                "dias": int(pd.to_numeric(lote.get("Dias Confinado", 0), errors="coerce") or 0),
            })

    alertas = CONF.alertas_confinamento(dados)

    return render_template(
        "confinamento.html",
        lotes=lotes_list,
        alertas=alertas,
    )


@app.route("/confinamento/novo", methods=["GET", "POST"])
@login_required
def novo_lote_confinamento():
    """Formulário para novo lote."""
    if request.method == "POST":
        try:
            conf = carregar_aba("Confinamento Lotes")

            linha = [
                request.form.get("data_entrada", _agora().strftime("%d/%m/%Y")),
                "",  # Data Saída
                request.form.get("lote_id", ""),
                request.form.get("brincos", ""),
                int(request.form.get("quantidade", 0)) or 0,
                float(request.form.get("peso_inicial", 0)) or 0,
                0,  # Peso Final
                0,  # Dias Confinado
                0,  # GMD
                "Ativo",
                request.form.get("observacao", ""),
                session.get("user_id", "—"),
                "",  # ID Envio
                _agora().isoformat(),
            ]

            from db import salvar_linha
            salvar_linha("Confinamento Lotes", linha)
            flash("✅ Lote criado com sucesso!", "success")
            return redirect(url_for("confinamento"))
        except Exception as e:
            flash(f"❌ Erro ao criar lote: {e}", "error")

    return render_template("novo_lote.html")


@app.route("/genetica")
@login_required
def genetica():
    """Página de genética e avisos de endogamia."""
    dados = _get_dados_cache()
    avisos = GEN.avisos_genetica(dados)

    return render_template(
        "genetica.html",
        avisos=avisos,
        num_avisos=len(avisos),
    )


@app.route("/genetica/compatibilidade", methods=["GET", "POST"])
@login_required
def compatibilidade_acasalamento():
    """Simulador de compatibilidade de acasalamento."""
    resultado = None
    touro_id = ""
    vaca_id = ""

    if request.method == "POST":
        touro_id = request.form.get("touro_id", "").strip()
        vaca_id = request.form.get("vaca_id", "").strip()

        dados = _get_dados_cache()
        resultado = GEN.compatibilidade_acasalamento(touro_id, vaca_id, dados)

    return render_template(
        "compatibilidade_acasalamento.html",
        resultado=resultado,
        touro_id=touro_id,
        vaca_id=vaca_id,
    )


# API para autocomplete de animal ID
@app.route("/api/animais/search")
@login_required
def api_animais_search():
    """Autocomplete para animal ID."""
    q = request.args.get("q", "").upper()
    dados = _get_dados_cache()
    animais = dados.get("Animais", pd.DataFrame())

    if animais.empty:
        return jsonify([])

    # Filtrar por ID ou Brinco
    resultado = animais[
        (animais.get("ID", "").str.contains(q, na=False)) |
        (animais.get("Brinco Cor", "").str.contains(q, na=False))
    ]["ID"].head(10).tolist()

    return jsonify(resultado)
