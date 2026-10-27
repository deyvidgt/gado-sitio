#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_pesagem.py — Gráficos de crescimento e GMD do animal (v5.6)
"""
import pandas as pd
from flask import render_template, request, jsonify

import animais as A
import pesagem as P
from extensions import app, login_required, _agora, _get_dados_cache, fmt_data


@app.route("/animais/crescimento")
@login_required
def crescimento():
    """Página com gráfico de peso vs tempo + GMD do animal."""
    id_animal = request.args.get("id", "").strip()
    if not id_animal:
        return "Animal não especificado", 400

    dados = _get_dados_cache()
    df_animais = A.carregar()
    df_manejo = dados["Manejo"] if "Manejo" in dados else pd.DataFrame()

    animal = A.por_id(df_animais, id_animal)
    if animal is None:
        return "Animal não encontrado", 404

    hist = P.todas(df_manejo).get(id_animal, [])
    pesagens = P.gmd_por_periodo(hist)
    tendencia = P.tendencia_gmd(hist)

    if pesagens:
        peso_inicial = pesagens[0]["peso_kg"]
        peso_atual = pesagens[-1]["peso_kg"]
        gmd_geral = None
        if len(pesagens) >= 2:
            dias_totais = pesagens[-1]["dias_desde_primeira"]
            if dias_totais > 0:
                gmd_geral = round((peso_atual - peso_inicial) / dias_totais * 1000, 0)
    else:
        peso_inicial = peso_atual = gmd_geral = None

    return render_template("crescimento.html",
                          animal=animal,
                          id_animal=id_animal,
                          pesagens=pesagens,
                          tendencia=tendencia,
                          peso_inicial=peso_inicial,
                          peso_atual=peso_atual,
                          gmd_geral=gmd_geral,
                          fmt_brinco=A.fmt_brinco,
                          COR_HEX=A.COR_HEX)


@app.route("/api/animais/crescimento")
@login_required
def api_crescimento():
    """JSON com todas as pesagens + GMD do animal."""
    id_animal = request.args.get("id", "").strip()
    if not id_animal:
        return jsonify({"erro": "id obrigatório"}), 400

    dados = _get_dados_cache()
    df_animais = A.carregar()
    df_manejo = dados["Manejo"] if "Manejo" in dados else pd.DataFrame()

    animal = A.por_id(df_animais, id_animal)
    if animal is None:
        return jsonify({"erro": "Animal não encontrado"}), 404

    hist = P.todas(df_manejo).get(id_animal, [])
    pesagens = P.gmd_por_periodo(hist)
    tendencia = P.tendencia_gmd(hist)

    return jsonify({
        "id": id_animal,
        "brinco": A.fmt_brinco(animal["Brinco Cor"], animal["Brinco Nº"]),
        "pesagens": pesagens,
        "tendencia": tendencia,
    })
