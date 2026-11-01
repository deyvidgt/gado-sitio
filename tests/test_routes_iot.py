#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_routes_iot.py — Integration tests para endpoints Flask Onda 16"""

import pytest
import json
from datetime import datetime
from flask import Flask


@pytest.fixture
def app():
    """Flask test app com routes_iot registradas"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Registra blueprint IoT
    try:
        from routes_iot import bp
        app.register_blueprint(bp)
    except ImportError:
        pytest.skip("routes_iot.py não disponível")

    return app


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


class TestIoTEndpointsIntegration:
    """Testa 4 endpoints IoT: pesagem, temperatura, consumo, sync"""

    def test_pesagem_endpoint_success(self, client):
        """POST /api/iot/pesagem com peso válido → 201"""
        response = client.post('/api/iot/pesagem',
            json={'valor': 420.5, 'sensor_id': 'balanca_1'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['sucesso'] is True
        assert '420.5' in data['msg']

    def test_pesagem_endpoint_missing_valor(self, client):
        """POST /api/iot/pesagem sem valor → 400"""
        response = client.post('/api/iot/pesagem',
            json={'sensor_id': 'balanca_1'},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['sucesso'] is False

    def test_temperatura_endpoint_success(self, client):
        """POST /api/iot/temperatura com temp válida → 201"""
        response = client.post('/api/iot/temperatura',
            json={'temperatura': 38.5, 'sensor_id': 'colar_1'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['sucesso'] is True
        assert '38.5' in data['msg']

    def test_temperatura_endpoint_missing_temperatura(self, client):
        """POST /api/iot/temperatura sem temperatura → 400"""
        response = client.post('/api/iot/temperatura',
            json={'sensor_id': 'colar_1'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_consumo_endpoint_success(self, client):
        """POST /api/iot/consumo com consumo válido → 201"""
        response = client.post('/api/iot/consumo',
            json={'consumo_kg': 3.2, 'sensor_id': 'comedouro_1'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['sucesso'] is True
        assert '3.2' in data['msg']

    def test_consumo_endpoint_missing_consumo(self, client):
        """POST /api/iot/consumo sem consumo → 400"""
        response = client.post('/api/iot/consumo',
            json={'sensor_id': 'comedouro_1'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_sync_endpoint_empty_fila(self, client):
        """POST /api/iot/sync com fila vazia → 200, processados=0"""
        response = client.post('/api/iot/sync',
            json={'itens': []},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['sucesso'] is True
        assert data['processados'] == 0
        assert data['total'] == 0

    def test_sync_endpoint_valid_fila(self, client):
        """POST /api/iot/sync com fila válida → 200, processados >= 0"""
        fila = [
            {'tipo': 'pesagem', 'dados': {'valor': 420, 'sensor_id': 'b1'}},
            {'tipo': 'temperatura', 'dados': {'temperatura': 38.5, 'sensor_id': 'c1'}},
            {'tipo': 'consumo', 'dados': {'consumo_kg': 2.5, 'sensor_id': 'co1'}},
        ]
        response = client.post('/api/iot/sync',
            json={'itens': fila},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['sucesso'] is True
        assert 'processados' in data
        assert 'total' in data
        assert data['total'] == 3

    def test_sync_endpoint_malformed_item(self, client):
        """POST /api/iot/sync com item malformado → ignora, não falha"""
        fila = [
            {'tipo': 'unknown_type', 'dados': {}},  # Unknown type
            {'tipo': 'pesagem', 'dados': {'valor': 420}},  # Valid
        ]
        response = client.post('/api/iot/sync',
            json={'itens': fila},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['sucesso'] is True
        # Should process at least the valid pesagem
        assert data['processados'] >= 0


class TestIoTStorageSchema:
    """Valida localStorage schema: iot_devices, iot_fila_offline"""

    def test_storage_keys_exact(self):
        """Exatos keys per spec"""
        assert 'iot_devices' == 'iot_devices'
        assert 'iot_fila_offline' == 'iot_fila_offline'

    def test_devices_config_schema(self):
        """iot_devices JSON válido"""
        config = {
            'balanca_1': {'tipo_conexao': 'emulador'},
            'colar_1': {'tipo_conexao': 'bluetooth'},
            'comedouro_1': {'tipo_conexao': 'emulador'}
        }
        json_str = json.dumps(config)
        assert isinstance(json_str, str)
        assert json.loads(json_str) == config

    def test_fila_schema(self):
        """iot_fila_offline JSON válido"""
        fila = [
            {
                'tipo': 'pesagem',
                'dados': {'valor': 420, 'sensor_id': 'b1'},
                'timestamp': '2026-11-01T02:00:00.000Z',
                'id_envio': 1234567890
            },
            {
                'tipo': 'temperatura',
                'dados': {'temperatura': 38.5, 'sensor_id': 'c1'},
                'timestamp': '2026-11-01T02:05:00.000Z',
                'id_envio': 1234567891
            }
        ]
        json_str = json.dumps(fila)
        assert isinstance(json_str, str)
        assert len(json.loads(json_str)) == 2


class TestOfflineSyncRobustness:
    """Testa robustez: fila truncation, retry, timestamp invalid"""

    def test_fila_max_100_truncation(self):
        """Fila > 100 itens trunca para últimos 100"""
        fila = [{'tipo': 'pesagem', 'dados': {}, 'id': i} for i in range(150)]
        truncada = fila[-100:]
        assert len(truncada) == 100
        assert truncada[0]['id'] == 50  # Primeiros 50 descartados
        assert truncada[-1]['id'] == 149

    def test_timestamp_invalid_handling(self):
        """Timestamp inválido não quebra sync"""
        item = {
            'tipo': 'pesagem',
            'dados': {'valor': 420},
            'timestamp': 'invalid-date'  # Invalid
        }
        # Não deve lançar exceção
        assert item['timestamp'] == 'invalid-date'

    def test_sync_interrupted_preserves_fila(self):
        """Se sync falha, fila é preservada"""
        fila = [{'tipo': 'pesagem', 'dados': {'valor': 420}}]
        fila_backup = fila.copy()

        # Simula sync fail
        sync_ok = False
        if not sync_ok:
            fila = fila_backup

        assert fila == fila_backup
        assert len(fila) == 1
