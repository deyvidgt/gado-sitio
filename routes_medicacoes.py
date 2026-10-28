#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_medicacoes.py — Endpoints para Histórico de Medicações

Provides:
  GET  /medicacoes              — Dashboard de medicações
  GET  /medicacoes/animal/<id>  — Histórico de medicações por animal
  POST /medicacoes/registrar    — Form para novo registro
"""

from flask import render_template, request, jsonify, redirect, url_for
from extensions import app, login_required
import medicacoes
from datetime import datetime


@app.route('/medicacoes')
@login_required
def medicacoes_dashboard():
    """Dashboard de medicações — quarentena hoje e últimas 30 dias."""
    alertas = medicacoes.alertas_quarentena()
    recentes = medicacoes.medicacoes_recentes(dias=30)

    return render_template('medicacoes/dashboard.html',
                         alertas=alertas,
                         medicacoes_recentes=recentes)


@app.route('/animais/<animal_id>/medicacoes')
@login_required
def historico_medicacoes(animal_id):
    """Histórico de medicações de um animal."""
    historico = medicacoes.historico_animal(animal_id)
    relatorio = medicacoes.relatorio_medicacoes_animal(animal_id)

    return render_template('medicacoes/historico.html',
                         animal_id=animal_id,
                         historico=historico,
                         relatorio=relatorio)


@app.route('/medicacoes/registrar', methods=['GET', 'POST'])
@login_required
def registrar_medicacao():
    """Form para registrar medicação."""
    if request.method == 'POST':
        sucesso = medicacoes.registrar_medicacao(
            data=request.form.get('data'),
            brincos=request.form.get('brincos'),
            tipo=request.form.get('tipo'),
            principio=request.form.get('principio'),
            dosagem=request.form.get('dosagem'),
            via=request.form.get('via'),
            motivo=request.form.get('motivo'),
            quarentena_dias=int(request.form.get('quarentena_dias', 0)),
            custo=float(request.form.get('custo', 0)),
            observacoes=request.form.get('observacoes', ''),
        )

        if sucesso:
            return redirect(url_for('medicacoes_dashboard'))
        else:
            return render_template('medicacoes/registrar.html',
                                 erro="Erro ao registrar medicação")

    return render_template('medicacoes/registrar.html')


@app.route('/api/medicacoes/alertas')
@login_required
def api_alertas_medicacoes():
    """API JSON: alertas de quarentena."""
    alertas = medicacoes.alertas_quarentena()
    return jsonify(alertas)


@app.route('/api/medicacoes/animal/<animal_id>')
@login_required
def api_historico_animal(animal_id):
    """API JSON: histórico de um animal."""
    historico = medicacoes.historico_animal(animal_id)
    return jsonify(historico)
