# -*- coding: utf-8 -*-
"""Previsão Open-Meteo com cache por sítio e degradação segura."""

import json
import os
from datetime import datetime

import requests

import db

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
NOME_CACHE = "tempo_cache.json"
CACHE_HORAS = 3
# Testes podem apontar para uma pasta temporária; em produção o sítio ativo é lido
# dinamicamente para não misturar caches entre sítios.
DATA_DIR = None


def _pasta_dados():
    return DATA_DIR or db.DATA_DIR

_CODIGOS = {
    0: "Céu limpo", 1: "Predominantemente limpo", 2: "Parcialmente nublado",
    3: "Nublado", 45: "Névoa", 48: "Névoa congelante", 51: "Chuvisco leve",
    53: "Chuvisco moderado", 55: "Chuvisco intenso", 61: "Chuva leve",
    63: "Chuva moderada", 65: "Chuva intensa", 71: "Neve leve",
    73: "Neve moderada", 75: "Neve intensa", 80: "Pancadas leves",
    81: "Pancadas moderadas", 82: "Pancadas intensas", 95: "Trovoada",
    96: "Trovoada com granizo leve", 99: "Trovoada com granizo intenso",
}


def _configuracao():
    caminho = os.path.join(_pasta_dados(), "sitio_config.json")
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo) or {}
    except (OSError, ValueError):
        return {}


def _cache_path():
    return os.path.join(_pasta_dados(), NOME_CACHE)


def _ler_cache():
    try:
        with open(_cache_path(), encoding="utf-8") as arquivo:
            valor = json.load(arquivo)
        if isinstance(valor, dict) and isinstance(valor.get("dados"), dict):
            return valor
    except (OSError, ValueError, TypeError):
        pass
    return None


def _salvar_cache(dados, agora):
    caminho = _cache_path()
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump({"salvo_em": agora.isoformat(), "dados": dados}, arquivo)
    os.replace(temporario, caminho)


def _coordenadas(cfg):
    try:
        latitude = float(str(cfg.get("latitude", "")).replace(",", "."))
        longitude = float(str(cfg.get("longitude", "")).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def _formatar(dados, cfg, salvo_em, desatualizado=False):
    atual = dados.get("current") or {}
    diario = dados.get("daily") or {}
    datas = diario.get("time") or []
    dias = []
    campos = (
        ("temperature_2m_max", "maxima"), ("temperature_2m_min", "minima"),
        ("precipitation_probability_max", "chuva_probabilidade"),
        ("precipitation_sum", "chuva_mm"), ("weather_code", "codigo"),
    )
    for i, data in enumerate(datas):
        item = {"data": data}
        for origem, destino in campos:
            valores = diario.get(origem) or []
            if i < len(valores):
                item[destino] = valores[i]
        item["condicao"] = _CODIGOS.get(item.get("codigo"), "Condição não informada")
        dias.append(item)
    return {
        "status": "cache" if desatualizado else "atualizado",
        "desatualizado": bool(desatualizado),
        "mensagem": "Previsão em cache." if desatualizado else "Previsão atualizada.",
        "local": str(cfg.get("nome") or "Região do sítio"),
        "consultado_em": salvo_em,
        "atual": {
            "temperatura": atual.get("temperature_2m"),
            "umidade": atual.get("relative_humidity_2m"),
            "vento_kmh": atual.get("wind_speed_10m"),
            "condicao": _CODIGOS.get(atual.get("weather_code"), "Condição não informada"),
        },
        "dias": dias,
    }


def previsao(*, agora=None):
    agora = agora or datetime.now()
    cfg = _configuracao()
    coordenadas = _coordenadas(cfg)
    cache = _ler_cache()
    if not coordenadas:
        return {"status": "indisponível", "mensagem": "Cadastre as coordenadas do sítio."}

    if cache:
        try:
            salvo = datetime.fromisoformat(cache["salvo_em"])
            if (agora - salvo).total_seconds() < CACHE_HORAS * 3600:
                return _formatar(cache["dados"], cfg, cache["salvo_em"])
        except (KeyError, TypeError, ValueError):
            cache = None

    # shortcut: a chamada roda com a trava do sítio segurada (um pedido por vez), então
    # a espera fica curta; quando o site ficar lento, buscar em segundo plano.
    try:
        resposta = requests.get(
            URL_OPEN_METEO,
            params={
                "latitude": coordenadas[0], "longitude": coordenadas[1],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                "timezone": "America/Sao_Paulo", "forecast_days": 5,
            },
            timeout=(2, 3),
            allow_redirects=False,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if not isinstance(dados, dict) or not isinstance(dados.get("daily"), dict):
            raise ValueError("resposta meteorológica incompleta")
        _salvar_cache(dados, agora)
        return _formatar(dados, cfg, agora.isoformat())
    except (requests.RequestException, ValueError, TypeError, OSError):
        if cache:
            return _formatar(cache["dados"], cfg, cache.get("salvo_em"), desatualizado=True)
        return {"status": "indisponível", "mensagem": "Previsão indisponível no momento."}
