#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_pastos_ocupacao.py — Rotas de ocupação de pastos (v5.10 Onda 6)
"""
from flask import render_template, jsonify, request
from extensions import app, login_required
from pastos_ocupacao import (
    gerar_alertas_lotacao,
    estimar_dias_ocupacao,
    recomendar_rotacao,
    resumo_ocupacao_pastos
)


@app.route("/pastos/ocupação", methods=["GET"])
@login_required
def dashboard_ocupacao_pastos():
    """Dashboard de ocupação e rotação de pastos."""
    resumo = resumo_ocupacao_pastos()
    alertas = gerar_alertas_lotacao()

    # Separa por tipo de alerta
    criticos = [a for a in alertas if a['tipo'] == 'critico']
    avisos = [a for a in alertas if a['tipo'] == 'aviso']
    alertas_info = [a for a in alertas if a['tipo'] == 'alerta']
    subutilizados = [a for a in alertas if a['tipo'] == 'subutilizacao']

    return render_template("pastos_ocupação.html",
                          resumo=resumo,
                          alertas_criticos=criticos,
                          alertas_avisos=avisos,
                          alertas_info=alertas_info,
                          pastos_subutilizados=subutilizados,
                          total_alertas=len(alertas))


@app.route("/pastos/<pasto_id>/rotação", methods=["GET"])
@login_required
def plano_rotacao_pasto(pasto_id):
    """Plano de rotação detalhado para um pasto."""
    estimativa = estimar_dias_ocupacao(pasto_id)
    rotacao = recomendar_rotacao(pasto_id)

    # Busca dados do pasto para exibição
    try:
        import pastos
        situacao = pastos.situacao(pasto_id)
        nome_pasto = situacao.get('nome', f'Pasto {pasto_id}')
    except Exception:
        nome_pasto = f'Pasto {pasto_id}'

    return render_template("pastos_rotação.html",
                          pasto_id=pasto_id,
                          nome_pasto=nome_pasto,
                          estimativa=estimativa,
                          rotacao=rotacao)


@app.route("/api/pastos/ocupação/resumo", methods=["GET"])
@login_required
def api_ocupacao_resumo():
    """API: resumo de ocupação de pastos."""
    resumo = resumo_ocupacao_pastos()
    alertas = gerar_alertas_lotacao()

    return jsonify({
        "resumo": resumo,
        "total_alertas": len(alertas),
        "criticos": len([a for a in alertas if a['tipo'] == 'critico']),
        "avisos": len([a for a in alertas if a['tipo'] == 'aviso']),
        "subutilizados": len([a for a in alertas if a['tipo'] == 'subutilizacao'])
    })


@app.route("/api/pastos/<pasto_id>/ocupação", methods=["GET"])
@login_required
def api_ocupacao_pasto(pasto_id):
    """API: detalhes de ocupação de um pasto."""
    estimativa = estimar_dias_ocupacao(pasto_id)

    return jsonify({
        "pasto_id": pasto_id,
        "ua_ha_atual": estimativa.get('ua_ha_atual'),
        "capacidade_ua_ha": estimativa.get('capacidade_ua_ha'),
        "taxa_ocupacao_percent": estimativa.get('taxa_ocupacao_percent'),
        "dias_ocupacao_recomendado": estimativa.get('dias_ocupacao_recomendado'),
        "dias_descanso_recomendado": estimativa.get('dias_descanso_recomendado')
    })


@app.route("/api/pastos/<pasto_id>/rotação", methods=["GET"])
@login_required
def api_rotacao_pasto(pasto_id):
    """API: plano de rotação para um pasto."""
    rotacao = recomendar_rotacao(pasto_id)

@app.route("/cron/verificar-alertas")
@login_required
def disparar_alertas():
    from cron_alertas import executar_alertas_diarios
    executar_alertas_diarios()
    return "Alertas processados.", 200
