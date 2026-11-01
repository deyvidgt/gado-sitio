#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""routes_iot.py — 4 endpoints IoT: pesagem, temperatura, consumo, sync.

Grava na aba Manejo pelo helper A._linha_manejo (posicional, ordem de COLUNAS_MANEJO).
"""
import logging
from datetime import datetime

from flask import jsonify, request

from extensions import app, login_required

logger = logging.getLogger(__name__)

# Tipos de manejo aceitos pelo módulo IoT (existem em config.TIPOS_MANEJO).
_TIPOS_IOT = {
    'pesagem': 'Pesagem',
    'temperatura': 'Temperatura',
    'consumo': 'Consumo',
}


def _salvar_manejo(tipo, dados, brincos=''):
    """Grava a leitura em Manejo. Devolve True/False."""
    nome_tipo = _TIPOS_IOT.get(tipo)
    if not nome_tipo:
        return False
    try:
        import animais as A
        import db
        from extensions import _membro_logado

        data = dados.get('timestamp') or datetime.now().strftime('%d/%m/%Y %H:%M')
        descricao = f"IoT {dados.get('sensor_id', '')}: {dados}".strip()
        db.salvar_linha("Manejo", A._linha_manejo(
            data, nome_tipo, 1, descricao, _membro_logado(), brincos=brincos))
        return True
    except Exception as e:
        logger.error("Erro ao salvar leitura IoT em Manejo: %s", e)
        return False


def _receber(campo, tipo):
    """POST comum: valida o campo e grava. Devolve (json, status)."""
    dados = request.get_json(silent=True) or {}
    valor = dados.get(campo)
    if valor is None:
        return {'sucesso': False, 'msg': f'Falta o campo {campo}'}, 400
    if _salvar_manejo(tipo, dados, brincos=str(dados.get('brincos') or '')):
        return {'sucesso': True, 'msg': f'{tipo} registrado ({valor})'}, 201
    return {'sucesso': False, 'msg': 'Falha ao gravar no Manejo'}, 500


@app.route('/api/iot/pesagem', methods=['POST'])
@login_required
def iot_pesagem():
    """Peso da balança. Body: {valor, sensor_id, brincos?, timestamp?}"""
    return _receber('valor', 'pesagem')


@app.route('/api/iot/temperatura', methods=['POST'])
@login_required
def iot_temperatura():
    """Temperatura do colar. Body: {temperatura, sensor_id, brincos?, timestamp?}"""
    return _receber('temperatura', 'temperatura')


@app.route('/api/iot/consumo', methods=['POST'])
@login_required
def iot_consumo():
    """Consumo do comedouro. Body: {consumo_kg, sensor_id, brincos?, timestamp?}"""
    return _receber('consumo_kg', 'consumo')


@app.route('/api/iot/sync', methods=['POST'])
@login_required
def iot_sync():
    """Sincroniza a fila offline do celular. Body: {itens: [{tipo, dados}]}"""
    dados = request.get_json(silent=True) or {}
    itens = dados.get('itens') or []
    processados = sum(
        1 for item in itens
        if isinstance(item, dict) and _salvar_manejo(
            item.get('tipo'), item.get('dados') or {},
            brincos=str((item.get('dados') or {}).get('brincos') or ''))
    )
    return jsonify({'sucesso': True, 'processados': processados, 'total': len(itens)}), 200
