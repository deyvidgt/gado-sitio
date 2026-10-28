#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_genetica.py — Rotas de análise genética e consanguinidade (v5.10 Onda 4)
"""
from flask import render_template, jsonify, request
from extensions import app, login_required
from consanguinidade import (
    gerar_alertas_consanguinidade,
    calcular_coeficiente_endogamia,
    analisar_progenie,
    sugerir_acasalamentos
)
import animais


@app.route("/genetica", methods=["GET"])
@login_required
def dashboard_genetica():
    """Dashboard de genética com alertas de endogamia."""
    alertas = gerar_alertas_consanguinidade()

    urgentes = [a for a in alertas if a['tipo'] == 'urgente']
    avisos = [a for a in alertas if a['tipo'] == 'aviso']

    return render_template("genetica_consanguinidade.html",
                          alertas_urgentes=urgentes,
                          alertas_aviso=avisos,
                          total_alertas=len(alertas))


@app.route("/genetica/<animal_id>", methods=["GET"])
@login_required
def analise_animal(animal_id):
    """Análise detalhada de um animal: endogamia, progênie, sugestões."""
    f = calcular_coeficiente_endogamia(animal_id)
    progenie = analisar_progenie(animal_id)
    sugestoes = sugerir_acasalamentos(animal_id)

    try:
        df_animais = animais.carregar()
        animal = df_animais[df_animais['ID'].astype(str) == str(animal_id)].iloc[0]
        animal_desc = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')} #{animal_id}"
    except Exception:
        animal_desc = f"ID {animal_id}"

    return render_template("genetica_analise.html",
                          animal_id=animal_id,
                          animal_desc=animal_desc,
                          coeficiente_endogamia=round(f, 2),
                          progenie=progenie,
                          sugestoes_acasalamento=sugestoes)


@app.route("/api/genetica/consanguinidade/<animal_id>", methods=["GET"])
@login_required
def api_consanguinidade(animal_id):
    """API: coeficiente de endogamia."""
    f = calcular_coeficiente_endogamia(animal_id)

    tipo_alerta = None
    if f > 6.25:
        tipo_alerta = "urgente"
    elif f > 3.13:
        tipo_alerta = "aviso"

    return jsonify({
        "animal_id": animal_id,
        "coeficiente": round(f, 2),
        "alerta": tipo_alerta,
        "limite_seguro": 6.25,
        "recomendacao": 3.13
    })
