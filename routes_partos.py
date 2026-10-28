#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_partos.py — Rotas de previsão de partos (v5.10 Onda 3)
"""
from flask import render_template, jsonify
from extensions import app, login_required
from partos_predicao import gerar_alertas_partos, calcular_datas_parto
import animais


@app.route("/partos", methods=["GET"])
@login_required
def calendario_partos():
    """Dashboard de previsão de partos."""
    alertas = gerar_alertas_partos()

    urgentes = [a for a in alertas if a['tipo'] == 'urgente']
    avisos = [a for a in alertas if a['tipo'] == 'aviso']

    return render_template("partos_calendario.html",
                          alertas_urgentes=urgentes,
                          alertas_aviso=avisos,
                          total_alertas=len(alertas))


@app.route("/api/partos/resumo", methods=["GET"])
@login_required
def api_resumo_partos():
    """API: resumo de partos próximos."""
    alertas = gerar_alertas_partos()

    return jsonify({
        "total": len(alertas),
        "urgentes": len([a for a in alertas if a['tipo'] == 'urgente']),
        "avisos": len([a for a in alertas if a['tipo'] == 'aviso']),
        "alertas": [
            {
                "animal": a['animal_desc'],
                "tipo": a['tipo'],
                "dias": a['dias_ate_parto'],
                "data_parto": a['data_parto'].isoformat() if a['data_parto'] else None,
                "acao": a['acao']
            }
            for a in alertas[:10]
        ]
    })
