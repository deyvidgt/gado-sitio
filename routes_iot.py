#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""routes_iot.py — 4 endpoints IoT: pesagem, temperatura, consumo, sync"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('iot', __name__, url_prefix='/api/iot')


def _salvar_manejo(tipo, dados, brinco='IoT'):
    """Salva leitura em Manejo aba."""
    try:
        from db import ler_aba, salvar_linha
        df = ler_aba('Manejo')
        if df is None:
            df = pd.DataFrame()

        nova_linha = {
            'Tipo': tipo,
            'Data': dados.get('timestamp', datetime.now().isoformat()),
            'Brincos': brinco,
            'Descrição': f"IoT: {dados}",
        }
        salvar_linha('Manejo', list(nova_linha.values()))
        return True
    except Exception as e:
        logger.error(f"Erro salvar Manejo: {e}")
        return False


@bp.route('/pesagem', methods=['POST'])
def iot_pesagem():
    """POST /api/iot/pesagem — salva peso do animal."""
    try:
        data = request.get_json()
        peso = data.get('valor')
        sensor_id = data.get('sensor_id', 'balanca_1')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if peso is None:
            return jsonify({'sucesso': False, 'msg': 'Falta valor peso'}), 400

        # Salva em Manejo com tipo "Pesagem"
        _salvar_manejo('Pesagem', {
            'peso_kg': peso,
            'sensor_id': sensor_id,
            'timestamp': timestamp
        })

        return jsonify({'sucesso': True, 'msg': f'Peso {peso}kg salvo'}), 201
    except Exception as e:
        logger.error(f"Erro pesagem: {e}")
        return jsonify({'sucesso': False, 'msg': str(e)}), 500


@bp.route('/temperatura', methods=['POST'])
def iot_temperatura():
    """POST /api/iot/temperatura — salva temperatura do colar."""
    try:
        data = request.get_json()
        temp = data.get('temperatura')
        sensor_id = data.get('sensor_id', 'colar_1')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if temp is None:
            return jsonify({'sucesso': False, 'msg': 'Falta valor temperatura'}), 400

        _salvar_manejo('Temperatura', {
            'temp_c': temp,
            'sensor_id': sensor_id,
            'timestamp': timestamp
        })

        return jsonify({'sucesso': True, 'msg': f'Temp {temp}°C salva'}), 201
    except Exception as e:
        logger.error(f"Erro temperatura: {e}")
        return jsonify({'sucesso': False, 'msg': str(e)}), 500


@bp.route('/consumo', methods=['POST'])
def iot_consumo():
    """POST /api/iot/consumo — salva consumo do comedouro."""
    try:
        data = request.get_json()
        consumo = data.get('consumo_kg')
        sensor_id = data.get('sensor_id', 'comedouro_1')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if consumo is None:
            return jsonify({'sucesso': False, 'msg': 'Falta valor consumo'}), 400

        _salvar_manejo('Consumo', {
            'consumo_kg': consumo,
            'sensor_id': sensor_id,
            'timestamp': timestamp
        })

        return jsonify({'sucesso': True, 'msg': f'Consumo {consumo}kg salvo'}), 201
    except Exception as e:
        logger.error(f"Erro consumo: {e}")
        return jsonify({'sucesso': False, 'msg': str(e)}), 500


@bp.route('/sync', methods=['POST'])
def iot_sync():
    """POST /api/iot/sync — sincroniza fila offline."""
    try:
        data = request.get_json()
        itens = data.get('itens', [])

        processados = 0
        for item in itens:
            tipo = item.get('tipo')
            dados = item.get('dados')
            if tipo in ['pesagem', 'temperatura', 'consumo']:
                if _salvar_manejo(tipo, dados):
                    processados += 1

        return jsonify({
            'sucesso': True,
            'processados': processados,
            'total': len(itens)
        }), 200
    except Exception as e:
        logger.error(f"Erro sync: {e}")
        return jsonify({'sucesso': False, 'msg': str(e)}), 500
