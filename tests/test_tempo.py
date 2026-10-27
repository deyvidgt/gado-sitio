# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

import tempo


def _resposta_tempo():
    return {
        "current": {
            "temperature_2m": 28.4,
            "relative_humidity_2m": 61,
            "wind_speed_10m": 12.3,
            "weather_code": 1,
        },
        "daily": {
            "time": ["2026-10-26", "2026-10-27"],
            "temperature_2m_max": [31.0, 30.0],
            "temperature_2m_min": [20.0, 19.0],
            "precipitation_probability_max": [20, 65],
            "precipitation_sum": [0.0, 8.2],
            "weather_code": [1, 61],
        },
    }


def test_previsao_consulta_open_meteo_e_formata_resposta(tmp_path, monkeypatch):
    chamadas = []

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return _resposta_tempo()

    def get(url, **kwargs):
        chamadas.append((url, kwargs))
        return Resposta()

    monkeypatch.setattr(tempo.requests, "get", get)
    monkeypatch.setattr(tempo, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tempo, "_configuracao", lambda: {
        "nome": "Sítio Teste",
        "latitude": -18.9186,
        "longitude": -48.2772,
    })

    resultado = tempo.previsao(agora=datetime(2026, 10, 26, 8, 0))

    assert resultado["status"] == "atualizado"
    assert resultado["local"] == "Sítio Teste"
    assert resultado["atual"]["temperatura"] == 28.4
    assert resultado["dias"][1]["chuva_mm"] == 8.2
    assert chamadas[0][0] == tempo.URL_OPEN_METEO
    assert chamadas[0][1]["timeout"] == (2, 3)  # conectar em 2s, resposta em 3s
    assert chamadas[0][1]["allow_redirects"] is False


def test_previsao_usa_cache_quando_servico_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(tempo, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tempo, "_configuracao", lambda: {
        "nome": "Sítio Teste", "latitude": -18.9, "longitude": -48.2,
    })
    cache = tmp_path / tempo.NOME_CACHE
    cache.write_text(json.dumps({
        "salvo_em": "2026-10-26T02:00:00",
        "dados": _resposta_tempo(),
    }), encoding="utf-8")

    def falha(*args, **kwargs):
        raise tempo.requests.RequestException("offline")

    monkeypatch.setattr(tempo.requests, "get", falha)
    resultado = tempo.previsao(agora=datetime(2026, 10, 26, 8, 0))

    assert resultado["status"] == "cache"
    assert resultado["desatualizado"] is True
    assert resultado["atual"]["temperatura"] == 28.4


def test_previsao_indisponivel_sem_coordenadas(tmp_path, monkeypatch):
    monkeypatch.setattr(tempo, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tempo, "_configuracao", lambda: {"nome": "Sítio Teste"})

    resultado = tempo.previsao(agora=datetime(2026, 10, 26, 8, 0))

    assert resultado["status"] == "indisponível"
    assert "coordenadas" in resultado["mensagem"].lower()
