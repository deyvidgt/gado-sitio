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
