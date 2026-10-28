#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_conversao_alimentar.py — Rotas de conversão alimentar (v5.10 Onda 5)
"""
from flask import render_template, jsonify, request
from extensions import app, login_required
from conversao_alimentar import (
    calcular_conversao_alimentar,
    gerar_alertas_conversao,
    resumo_conversao_alimentar
)


@app.route("/nutrição/conversão", methods=["GET"])
@login_required
def dashboard_conversao():
    """Dashboard de eficiência alimentar com alertas e recomendações."""
    resumo = resumo_conversao_alimentar()
    alertas = gerar_alertas_conversao()

    # Separa por tipo de alerta
    criticos = [a for a in alertas if a['tipo'] == 'critico']
    avisos = [a for a in alertas if a['tipo'] == 'aviso']

    return render_template("nutrição_conversão.html",
                          resumo=resumo,
                          alertas_criticos=criticos,
                          alertas_avisos=avisos,
                          total_alertas=len(alertas))


@app.route("/nutrição/conversão/<animal_id>", methods=["GET"])
@login_required
def analise_conversao_animal(animal_id):
    """Análise detalhada de conversão alimentar de um animal."""
    resultado = calcular_conversao_alimentar(animal_id)

    # Busca dados do animal para exibição
    try:
        import animais
        df_animais = animais.carregar()
        animal = df_animais[df_animais['ID'].astype(str) == str(animal_id)].iloc[0]
        animal_desc = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')} #{animal_id}"
    except Exception:
        animal_desc = f"ID {animal_id}"

    return render_template("nutrição_analise_animal.html",
                          animal_id=animal_id,
                          animal_desc=animal_desc,
                          resultado=resultado)


@app.route("/api/conversão/resumo", methods=["GET"])
@login_required
def api_conversao_resumo():
    """API: resumo de eficiência alimentar do rebanho."""
    resumo = resumo_conversao_alimentar()
    alertas = gerar_alertas_conversao()

    return jsonify({
        "resumo": resumo,
        "total_alertas": len(alertas),
        "criticos": len([a for a in alertas if a['tipo'] == 'critico']),
        "avisos": len([a for a in alertas if a['tipo'] == 'aviso'])
    })


@app.route("/api/conversão/<animal_id>", methods=["GET"])
@login_required
def api_conversao_animal(animal_id):
    """API: conversão alimentar de um animal."""
    resultado = calcular_conversao_alimentar(animal_id)

    return jsonify({
        "animal_id": animal_id,
        "categoria": resultado['categoria'],
        "conversao_alimentar": resultado['conversao_alimentar'],
        "padrao_conversao": resultado['padrao_conversao'],
        "desvio_percent": resultado['desvio_percent'],
        "tipo_alerta": resultado['tipo_alerta'],
        "motivo": resultado['motivo'],
        "recomendacao": resultado.get('recomendacao', ''),
        "consumo_total_kg": resultado['consumo_total_kg'],
        "ganho_total_kg": resultado['ganho_total_kg'],
        "peso_inicial_kg": resultado['peso_inicial_kg'],
        "peso_final_kg": resultado['peso_final_kg'],
        "dias_com_dados": resultado['dias_com_dados']
    })
