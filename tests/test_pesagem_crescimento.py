# -*- coding: utf-8 -*-
"""
Testes para GMD e gráfico de crescimento do animal (v5.6).
"""
import pandas as pd
import pytest
import pesagem as P


def test_gmd_por_periodo_basico():
    """gmd_por_periodo com duas pesagens."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-11"), 110.0),
    ]
    pontos = P.gmd_por_periodo(hist)

    assert len(pontos) == 2
    assert pontos[0]["peso_kg"] == 100.0
    assert pontos[0]["dias_desde_primeira"] == 0
    assert pontos[0]["gmd_g_dia"] is None

    assert pontos[1]["peso_kg"] == 110.0
    assert pontos[1]["dias_desde_primeira"] == 10
    assert pontos[1]["gmd_g_dia"] == 1000  # 10 kg / 10 dias * 1000


def test_gmd_por_periodo_varias():
    """gmd_por_periodo com múltiplas pesagens."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-06"), 105.0),
        (pd.Timestamp("2026-01-16"), 120.0),
    ]
    pontos = P.gmd_por_periodo(hist)

    assert len(pontos) == 3
    assert pontos[1]["gmd_g_dia"] == 1000  # 5 kg / 5 dias * 1000
    assert pontos[2]["gmd_g_dia"] == 1500  # 15 kg / 10 dias * 1000


def test_gmd_por_periodo_vazio():
    """gmd_por_periodo com lista vazia."""
    pontos = P.gmd_por_periodo([])
    assert pontos == []


def test_gmd_por_periodo_uma_pesagem():
    """gmd_por_periodo com uma pesagem só."""
    hist = [(pd.Timestamp("2026-01-01"), 100.0)]
    pontos = P.gmd_por_periodo(hist)
    assert pontos == []


def test_gmd_por_periodo_com_filtro_data():
    """gmd_por_periodo filtra por intervalo de datas."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-10"), 110.0),
        (pd.Timestamp("2026-01-20"), 125.0),
    ]
    pontos = P.gmd_por_periodo(hist,
                               inicio=pd.Timestamp("2026-01-10"),
                               fim=pd.Timestamp("2026-01-20"))

    assert len(pontos) == 2
    assert pontos[0]["peso_kg"] == 110.0
    assert pontos[1]["peso_kg"] == 125.0


def test_tendencia_gmd_basico():
    """tendencia_gmd com histórico simples."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-31"), 130.0),
    ]
    tend = P.tendencia_gmd(hist, ultimos_dias=30)

    assert tend is not None
    assert tend["dias"] == 30
    assert tend["n"] == 2
    assert tend["media_g_dia"] == 1000  # 30 kg / 30 dias * 1000


def test_tendencia_gmd_vazio():
    """tendencia_gmd com lista vazia."""
    tend = P.tendencia_gmd([])
    assert tend is None


def test_tendencia_gmd_uma_pesagem():
    """tendencia_gmd com uma pesagem só."""
    hist = [(pd.Timestamp("2026-01-01"), 100.0)]
    tend = P.tendencia_gmd(hist)
    assert tend is None


def test_tendencia_gmd_acelerando():
    """tendencia_gmd detecta aceleração."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-10"), 105.0),  # 1ª metade: +5 kg em 9 dias
        (pd.Timestamp("2026-01-20"), 120.0),  # 2ª metade: +15 kg em 10 dias
    ]
    tend = P.tendencia_gmd(hist, ultimos_dias=30)

    assert tend is not None
    assert tend["tendencia"] == "acelerando"


def test_tendencia_gmd_desacelerando():
    """tendencia_gmd detecta desaceleração."""
    hist = [
        (pd.Timestamp("2026-01-01"), 100.0),
        (pd.Timestamp("2026-01-10"), 120.0),  # 1ª metade: +20 kg em 9 dias
        (pd.Timestamp("2026-01-20"), 125.0),  # 2ª metade: +5 kg em 10 dias
    ]
    tend = P.tendencia_gmd(hist, ultimos_dias=30)

    assert tend is not None
    assert tend["tendencia"] == "desacelerando"


def test_api_crescimento_animal_inexistente(cliente):
    """GET /api/animais/crescimento com animal inexistente."""
    resp = cliente.get("/api/animais/crescimento?id=A9999")
    assert resp.status_code == 404
    assert resp.get_json()["erro"] == "Animal não encontrado"


def test_api_crescimento_sem_id(cliente):
    """GET /api/animais/crescimento sem id."""
    resp = cliente.get("/api/animais/crescimento")
    assert resp.status_code == 400
    assert "id obrigatório" in resp.get_json()["erro"]
