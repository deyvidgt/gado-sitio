# -*- coding: utf-8 -*-
"""Testes para o módulo de previsão de tempo (tempo.py)."""
from datetime import datetime

import tempo


def test_alertas_tempo_chuva_forte():
    """Detecta chuva forte >20mm → risco de mastite."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 28, "umidade": 65, "vento_kmh": 10},
        "dias": [
            {"data": "2026-10-27", "maxima": 28, "minima": 20, "chuva_mm": 25, "chuva_probabilidade": 80},
            {"data": "2026-10-28", "maxima": 26, "minima": 18, "chuva_mm": 5, "chuva_probabilidade": 30},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "chuva_forte"
    assert alertas[0]["icone"] == "🌧️"
    assert "25" in alertas[0]["descricao"]


def test_alertas_tempo_calor_umidade():
    """Detecta calor >30°C + umidade >70% → estresse térmico."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 32, "umidade": 75, "vento_kmh": 10},
        "dias": [
            {"data": "2026-10-27", "maxima": 35, "minima": 25, "chuva_mm": 0, "chuva_probabilidade": 10},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "calor_umidade"
    assert alertas[0]["icone"] == "🔥"


def test_alertas_tempo_vento_forte():
    """Detecta vento forte >15 km/h → desconforto animal."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 28, "umidade": 60, "vento_kmh": 20},
        "dias": [
            {"data": "2026-10-27", "maxima": 28, "minima": 18, "chuva_mm": 0, "chuva_probabilidade": 5},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "vento_forte"
    assert alertas[0]["icone"] == "💨"


def test_alertas_tempo_queda_temperatura():
    """Detecta queda abrupta de temperatura >10°C."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 25, "umidade": 60, "vento_kmh": 10},
        "dias": [
            {"data": "2026-10-27", "maxima": 28, "minima": 20, "chuva_mm": 0, "chuva_probabilidade": 5},
            {"data": "2026-10-28", "maxima": 18, "minima": 8, "chuva_mm": 0, "chuva_probabilidade": 10},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "queda_temp"
    assert alertas[0]["icone"] == "❄️"


def test_alertas_tempo_multiplos():
    """Detecta múltiplos alertas simultaneamente."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 32, "umidade": 75, "vento_kmh": 18},
        "dias": [
            {"data": "2026-10-27", "maxima": 35, "minima": 25, "chuva_mm": 30, "chuva_probabilidade": 90},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    # Chuva forte + calor + umidade + vento
    assert len(alertas) >= 2
    tipos = {a["tipo"] for a in alertas}
    assert "chuva_forte" in tipos
    assert "calor_umidade" in tipos
    assert "vento_forte" in tipos


def test_alertas_tempo_condicoes_normais():
    """Sem alertas quando as condições são normais."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 22, "umidade": 55, "vento_kmh": 8},
        "dias": [
            {"data": "2026-10-27", "maxima": 25, "minima": 18, "chuva_mm": 5, "chuva_probabilidade": 10},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 0


def test_alertas_tempo_indisponivel():
    """Retorna lista vazia quando previsão está indisponível."""
    prev = {"status": "indisponível", "mensagem": "Previsão indisponível."}
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 0


def test_alertas_tempo_chuva_extrema():
    """Detecta chuva extrema >40mm como urgente."""
    prev = {
        "status": "atualizado",
        "atual": {"temperatura": 26, "umidade": 70, "vento_kmh": 12},
        "dias": [
            {"data": "2026-10-27", "maxima": 26, "minima": 20, "chuva_mm": 50, "chuva_probabilidade": 95},
        ],
    }
    alertas = tempo.alertas_tempo(prev)

    assert len(alertas) == 1
    assert alertas[0]["nivel"] == "urgente"


def test_previsao_extrai_vento_umidade_chuva_e_atualiza_cache_antigo(tmp_path, monkeypatch):
    agora = datetime(2026, 11, 4, 12)
    monkeypatch.setattr(tempo, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tempo, "_configuracao", lambda: {
        "latitude": -18.9, "longitude": -48.2,
    })
    tempo._salvar_cache(
        {"current": {}, "daily": {"time": ["2026-11-04"]}},
        datetime(2026, 11, 4, 10),
    )
    dados_api = {
        "current": {},
        "daily": {
            "time": ["2026-11-04"],
            "weather_code": [1],
            "temperature_2m_max": [29],
            "temperature_2m_min": [18],
            "precipitation_probability_max": [0],
            "precipitation_sum": [0],
            "wind_speed_10m_max": [17.5],
            "relative_humidity_2m_mean": [64],
        },
    }

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return dados_api

    chamada = {}

    def requisitar(url, **kwargs):
        chamada.update(kwargs)
        return Resposta()

    monkeypatch.setattr(tempo.requests, "get", requisitar)

    previsao = tempo.previsao(agora=agora)

    assert "wind_speed_10m_max" in chamada["params"]["daily"]
    assert "relative_humidity_2m_mean" in chamada["params"]["daily"]
    assert previsao["dias"][0]["vento_kmh"] == 17.5
    assert previsao["dias"][0]["umidade"] == 64
    assert previsao["dias"][0]["chuva_mm"] == 0


def test_tabela_tempo_formata_data_e_mostra_zero_e_dados_diarios(cliente, monkeypatch):
    previsao = {
        "status": "atualizado",
        "mensagem": "Previsão atualizada.",
        "consultado_em": "2026-11-04T12:00:00",
        "atual": {"temperatura": 25, "umidade": 0, "vento_kmh": 0, "condicao": "Céu limpo"},
        "dias": [{
            "data": "2026-11-04", "minima": 0, "maxima": 0, "chuva_mm": 0,
            "chuva_probabilidade": 0, "vento_kmh": 17.5, "umidade": 64,
        }],
    }
    monkeypatch.setattr(tempo, "previsao", lambda **kwargs: previsao)

    html = cliente.get("/tempo").get_data(as_text=True)

    assert "04/11/2026" in html
    assert "2026-11-04</strong>" not in html
    assert "17.5 km/h" in html
    assert "64%" in html
    assert "0mm" in html and "0%</span>" in html
    assert 'id="chartVentoUmidade"' in html
    assert "d.vento_kmh ?? null" in html
    assert "d.umidade ?? null" in html
