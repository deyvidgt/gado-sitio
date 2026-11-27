from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Endpoints de leituras IoT e sincronização offline idempotente."""
import logging
import threading
from datetime import datetime

from flask import jsonify, request, session

from extensions import app, login_required, db
from models import SyncRegistro

logger = logging.getLogger(__name__)
_SYNC_LOCK = threading.Lock()
_TIPOS_IOT = {'pesagem': 'Pesagem', 'temperatura': 'Temperatura', 'consumo': 'Consumo', 'agua': 'Água', 'cocho': 'Consumo Cocho', 'rfid': 'Leitura RFID'}


def _animal_por_rfid(tag_id):
    import animais as A
    df = A.carregar()
    for coluna in ('RFID', 'Tag RFID', 'Chip', 'Brinco RFID'):
        if coluna in df.columns:
            encontrados = df[df[coluna].astype(str).str.strip() == str(tag_id).strip()]
            if not encontrados.empty:
                return str(encontrados.iloc[0].get('ID', encontrados.index[0]))
    return None


def _numero_valido(valor, minimo=0, maximo=100000):
    try:
        valor = float(valor)
        return minimo <= valor <= maximo
    except (TypeError, ValueError):
        return False


def _salvar_manejo(tipo, dados, brincos=''):
    nome_tipo = _TIPOS_IOT.get(tipo)
    if not nome_tipo:
        return False
    try:
        import animais as A
        import db as dados_db
        from routes_animais import _membro_logado
        data = dados.get('timestamp') or agora().strftime('%d/%m/%Y %H:%M')
        descricao = f"IoT {dados.get('sensor_id', '')}: {dados}".strip()
        dados_db.salvar_linha('Manejo', A._linha_manejo(data, nome_tipo, 1, descricao, _membro_logado(), brincos=brincos))
        return True
    except Exception as exc:
        logger.error('Erro ao salvar leitura IoT em Manejo: %s', exc)
        return False


def _receber(campo, tipo):
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
    return _receber('valor', 'pesagem')


@app.route('/api/iot/temperatura', methods=['POST'])
@login_required
def iot_temperatura():
    return _receber('temperatura', 'temperatura')


@app.route('/api/iot/consumo', methods=['POST'])
@login_required
def iot_consumo():
    return _receber('consumo_kg', 'consumo')


def _processar_sync(itens):
    resultados = []
    usuario = str(session.get('usuario') or '')
    sitio = str(session.get('sitio') or 'default')
    with _SYNC_LOCK:
      for item in itens:
        if not isinstance(item, dict) or not item.get('id_envio'):
            resultados.append({'id_envio': '', 'status': 'invalido', 'msg': 'id_envio obrigatório'})
            continue
        envio = str(item['id_envio'])
        if (item.get('usuario') and str(item['usuario']) != usuario) or (item.get('sitio') and str(item['sitio']) != sitio):
            resultados.append({'id_envio': envio, 'status': 'invalido', 'msg': 'Sessão incompatível'})
            continue
        if db.session.query(SyncRegistro).filter_by(id_envio=envio).first():
            resultados.append({'id_envio': envio, 'status': 'duplicado', 'msg': 'Já processado'})
            continue
        tipo, dados = item.get('tipo'), item.get('dados') or {}
        if tipo not in _TIPOS_IOT or not isinstance(dados, dict):
            resultados.append({'id_envio': envio, 'status': 'invalido', 'msg': 'Tipo ou dados inválidos'})
            continue
        try:
            if not _salvar_manejo(tipo, dados, brincos=str(dados.get('brincos') or '')):
                raise ValueError('Falha ao gravar leitura')
            db.session.add(SyncRegistro(id_envio=envio, usuario=usuario, sitio=sitio, tipo=str(tipo)))
            db.session.commit()
            resultados.append({'id_envio': envio, 'status': 'processado', 'msg': 'OK'})
        except Exception as exc:
            db.session.rollback()
            logger.error('Erro no item offline %s: %s', envio, exc)
            resultados.append({'id_envio': envio, 'status': 'erro_transitorio', 'msg': 'Falha transitória'})
    return resultados


@app.route('/api/sync', methods=['POST'])
@login_required
def sync_geral():
    dados = request.get_json(silent=True) or {}
    return jsonify({'sucesso': True, 'resultados': _processar_sync(dados.get('itens') or [])}), 200


@app.route('/api/iot/rfid', methods=['POST'])
@login_required
def iot_rfid():
    dados = request.get_json(silent=True) or {}
    animal_id = _animal_por_rfid(dados.get('tag_id')) if dados.get('tag_id') else None
    if not animal_id:
        return jsonify({'status': 'invalido', 'msg': 'RFID desconhecido'}), 422
    dados['brincos'] = animal_id
    if not _salvar_manejo('rfid', dados, brincos=animal_id):
        return jsonify({'status': 'erro_transitorio', 'msg': 'Falha ao registrar leitura'}), 500
    return jsonify({'status': 'processado', 'animal_id': animal_id}), 201


@app.route('/api/iot/agua', methods=['POST'])
@login_required
def iot_agua():
    dados = request.get_json(silent=True) or {}
    if dados.get('unidade') not in ('L', 'l', 'm3') or not _numero_valido(dados.get('valor'), 0, 100000):
        return jsonify({'sucesso': False, 'status': 'invalido', 'msg': 'Valor/unidade inválidos'}), 400
    return (_receber('valor', 'agua')[0] | {'status': 'processado'}, 201) if _salvar_manejo('agua', dados) else (jsonify({'sucesso': False}), 500)


@app.route('/api/iot/cocho', methods=['POST'])
@login_required
def iot_cocho():
    dados = request.get_json(silent=True) or {}
    if dados.get('unidade') not in ('kg', 'g') or not _numero_valido(dados.get('consumo_kg'), 0, 100000):
        return jsonify({'sucesso': False, 'status': 'invalido', 'msg': 'Consumo/unidade inválidos'}), 400
    if dados['unidade'] == 'g':
        dados['consumo_kg'] = float(dados['consumo_kg']) / 1000
        dados['unidade'] = 'kg'
    return jsonify({'sucesso': True, 'status': 'processado', 'msg': 'cocho registrado'}) if _salvar_manejo('cocho', dados) else (jsonify({'sucesso': False}), 500)


@app.route('/api/iot/sync', methods=['POST'])
@login_required
def iot_sync():
    dados = request.get_json(silent=True) or {}
    itens = dados.get('itens') or []
    if any(isinstance(item, dict) and item.get('id_envio') for item in itens):
        resultados = _processar_sync(itens)
        processados = sum(r['status'] in ('processado', 'duplicado') for r in resultados)
    else:
        processados = sum(1 for item in itens if isinstance(item, dict) and _salvar_manejo(item.get('tipo'), item.get('dados') or {}, brincos=str((item.get('dados') or {}).get('brincos') or '')))
    return jsonify({'sucesso': True, 'processados': processados, 'total': len(itens)}), 200
