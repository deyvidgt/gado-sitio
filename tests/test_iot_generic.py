import pandas as pd


def test_rfid_requires_known_animal(cliente, monkeypatch):
    monkeypatch.setattr('routes_iot._animal_por_rfid', lambda tag: None)
    response = cliente.post('/api/iot/rfid', json={'tag_id': 'RF-404', 'sensor_id': 'r1'})
    assert response.status_code == 422
    assert response.json['status'] == 'invalido'


def test_water_and_feeder_validate_units_and_ranges(cliente, monkeypatch):
    monkeypatch.setattr('routes_iot._salvar_manejo', lambda *args, **kwargs: True)
    water = cliente.post('/api/iot/agua', json={'valor': 12, 'unidade': 'L', 'sensor_id': 'w1', 'lote_id': 'L1'})
    bad = cliente.post('/api/iot/cocho', json={'consumo_kg': -1, 'unidade': 'kg', 'sensor_id': 'c1'})
    assert water.status_code == 201
    assert water.json['sucesso'] is True
    assert bad.status_code == 400


def test_generic_frontend_has_manual_readings():
    from pathlib import Path
    source = Path('static/js/iot_sensores.js').read_text(encoding='utf-8')
    assert 'RfidManual' in source
    assert 'AguaManual' in source
    assert 'CochoManual' in source
