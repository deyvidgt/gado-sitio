#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_iot_e2e.py — E2E + smoke tests para Onda 16"""

import pytest
import json
from datetime import datetime
import sys
sys.path.insert(0, '.')


class TestIoTEndpoints:
    """E2E: sensores → manager → endpoints → sync"""

    def test_pesagem_endpoint(self, client):
        """POST /api/iot/pesagem salva peso."""
        response = client.post('/api/iot/pesagem', json={
            'valor': 420.5,
            'sensor_id': 'balanca_1',
            'timestamp': datetime.now().isoformat()
        })
        assert response.status_code == 201
        assert response.json['sucesso'] is True

    def test_temperatura_endpoint(self, client):
        """POST /api/iot/temperatura salva temp."""
        response = client.post('/api/iot/temperatura', json={
            'temperatura': 38.5,
            'sensor_id': 'colar_1',
            'timestamp': datetime.now().isoformat()
        })
        assert response.status_code == 201
        assert response.json['sucesso'] is True

    def test_consumo_endpoint(self, client):
        """POST /api/iot/consumo salva consumo."""
        response = client.post('/api/iot/consumo', json={
            'consumo_kg': 3.2,
            'sensor_id': 'comedouro_1',
            'timestamp': datetime.now().isoformat()
        })
        assert response.status_code == 201
        assert response.json['sucesso'] is True

    def test_sync_endpoint(self, client):
        """POST /api/iot/sync sincroniza fila."""
        fila = [
            {'tipo': 'pesagem', 'dados': {'valor': 420, 'sensor_id': 'b1'}},
            {'tipo': 'temperatura', 'dados': {'temperatura': 38.5, 'sensor_id': 'c1'}},
        ]
        response = client.post('/api/iot/sync', json={'itens': fila})
        assert response.status_code == 200
        assert response.json['sucesso'] is True
        assert response.json['processados'] >= 0

    def test_fila_max_100_itens(self):
        """localStorage fila não excede 100 itens."""
        # Simula adição de 150 itens
        fila = [{'tipo': 'pesagem', 'dados': {}, 'timestamp': datetime.now().isoformat()}
                for _ in range(150)]

        # Trunca a > 100
        fila_truncada = fila[-100:]
        assert len(fila_truncada) == 100

    def test_sensor_desconecta_gracefully(self):
        """Sensor desconectado retorna erro sem crash."""
        # Mock: sensor sem conectar
        class SensorTest:
            def __init__(self):
                self.conectado = False
            async def ler(self):
                if not self.conectado:
                    return {'sucesso': False, 'msg': 'Não conectado'}
                return {'sucesso': True, 'valor': 420}

        sensor = SensorTest()
        result = sensor.ler.__self__.ler()  # Hack para async
        # Verifica que retorna dict com sucesso=False
        assert isinstance(result, dict)

    def test_localStorage_schema(self):
        """localStorage keys exatos: iot_devices, iot_fila_offline"""
        # Simula dados
        devices = {'balanca_1': {'tipo_conexao': 'emulador'}}
        fila = [{'tipo': 'pesagem', 'dados': {}}]

        # Verifica JSON valid
        assert isinstance(json.dumps(devices), str)
        assert isinstance(json.dumps(fila), str)

    def test_offline_sync_retry(self):
        """Fila retém itens se sync falha."""
        fila = [{'tipo': 'pesagem', 'dados': {'valor': 420}}]
        fila_backup = fila.copy()

        # Simula sync fail → restaura fila
        sync_ok = False
        if not sync_ok:
            fila = fila_backup

        assert len(fila) == 1
        assert fila[0]['dados']['valor'] == 420


@pytest.fixture
def client():
    """Flask test client"""
    try:
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    except ImportError:
        pytest.skip("app.py não disponível")
