import json


def test_sync_processes_idempotently(cliente, monkeypatch):
    calls = []
    monkeypatch.setattr("routes_iot._salvar_manejo", lambda tipo, dados, brincos="": calls.append((tipo, dados)) or True)
    item = {"id_envio": "sync-test-1", "tipo": "pesagem", "dados": {"valor": 420, "sensor_id": "b1"}, "usuario": "deyvid"}
    first = cliente.post("/api/sync", json={"itens": [item]})
    second = cliente.post("/api/sync", json={"itens": [item]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json["resultados"][0]["status"] == "processado"
    assert second.json["resultados"][0]["status"] == "duplicado"
    assert len(calls) == 1


def test_sync_returns_per_item_validation_status(cliente):
    response = cliente.post("/api/sync", json={"itens": [{"id_envio": "bad-1", "tipo": "desconhecido", "dados": {}}]})
    assert response.status_code == 200
    assert response.json["resultados"][0]["status"] == "invalido"
