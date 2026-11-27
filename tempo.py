from agora import agora
# -*- coding: utf-8 -*-
"""Previsão Open-Meteo com cache por sítio e degradação segura."""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

import db

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
NOME_CACHE = "tempo_cache.json"
CACHE_HORAS = 3
VARIAVEIS_DIARIAS = (
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "precipitation_probability_max", "precipitation_sum",
    "wind_speed_10m_max", "relative_humidity_2m_mean",
)
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


def _coordenadas_do_mapa():
    """Extrai coordenadas do centro do mapa de pastos (média dos contornos GeoJSON)."""
    try:
        from pastos import carregar as carregar_pastos
        df_pastos = carregar_pastos()
        if df_pastos.empty:
            return None

        coords = []
        for _, row in df_pastos.iterrows():
            geojson_str = row.get("Contorno GeoJSON")
            if not geojson_str:
                continue
            try:
                import json
                geojson = json.loads(str(geojson_str))
                if geojson.get("type") == "Polygon":
                    # Poligono: pega coordenadas (longitude, latitude)
                    pontos = geojson.get("coordinates", [[]])[0]
                    coords.extend(pontos)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        if coords:
            # Média das coordenadas (longitude, latitude)
            lon_media = sum(c[0] for c in coords) / len(coords)
            lat_media = sum(c[1] for c in coords) / len(coords)
            return lat_media, lon_media
    except Exception:
        pass
    return None


def _coordenadas(cfg):
    """Coordenadas do sítio: preferência (1) sitio_config.json, (2) mapa de pastos."""
    try:
        latitude = float(str(cfg.get("latitude", "")).replace(",", "."))
        longitude = float(str(cfg.get("longitude", "")).replace(",", "."))
    except (TypeError, ValueError):
        latitude = longitude = None

    if latitude is not None and longitude is not None:
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude

    # Fallback: tenta extrair do mapa de pastos
    return _coordenadas_do_mapa()


def _formatar(dados, cfg, salvo_em, desatualizado=False):
    atual = dados.get("current") or {}
    diario = dados.get("daily") or {}
    datas = diario.get("time") or []
    dias = []
    campos = (
        ("temperature_2m_max", "maxima"), ("temperature_2m_min", "minima"),
        ("precipitation_probability_max", "chuva_probabilidade"),
        ("precipitation_sum", "chuva_mm"), ("wind_speed_10m_max", "vento_kmh"),
        ("relative_humidity_2m_mean", "umidade"), ("weather_code", "codigo"),
    )
    for i, data in enumerate(datas):
        item = {"data": data}
        for origem, destino in campos:
            valores = diario.get(origem) or []
            if i < len(valores):
                item[destino] = valores[i]
        item["condicao"] = _CODIGOS.get(item.get("codigo"), "Condição não informada")
        dias.append(item)

    # Monta localização: nome do sítio ou "Município, Estado"
    local = str(cfg.get("nome") or "Região do sítio")
    municipio = cfg.get("municipio")
    estado = cfg.get("estado")
    if municipio and estado:
        local = f"{municipio}, {estado}"
    elif municipio:
        local = municipio

    return {
        "status": "cache" if desatualizado else "atualizado",
        "desatualizado": bool(desatualizado),
        "mensagem": "Previsão em cache." if desatualizado else "Previsão atualizada.",
        "local": local,
        "municipio": municipio or None,
        "estado": estado or None,
        "consultado_em": salvo_em,
        "atual": {
            "temperatura": atual.get("temperature_2m"),
            "umidade": atual.get("relative_humidity_2m"),
            "vento_kmh": atual.get("wind_speed_10m"),
            "condicao": _CODIGOS.get(atual.get("weather_code"), "Condição não informada"),
        },
        "dias": dias,
    }


def alertas_tempo(prev):
    """Detecta alertas sobre as condições meteorológicas (chuva, calor, vento, temperatura).
    Retorna lista de alertas com tipo, descrição e ícone para leite/corte/volumosos."""
    alertas = []
    if not prev or prev.get("status") == "indisponível":
        return alertas

    atual = prev.get("atual", {})
    dias = prev.get("dias", [])

    # Verifica hoje (primeiro dia da previsão)
    hoje = dias[0] if dias else {}
    chuva_hoje = hoje.get("chuva_mm", 0) or 0
    temp_max = hoje.get("maxima", 0) or 0
    umidade = atual.get("umidade", 0) or 0
    vento = atual.get("vento_kmh", 0) or 0

    # Chuva forte: >20mm → risco de mastite/higiene
    if chuva_hoje > 20:
        alertas.append({
            "tipo": "chuva_forte",
            "alerta": "Chuva forte",
            "descricao": f"Precipitação de {chuva_hoje:.0f}mm — risco de mastite, higiene da ordenha crítica.",
            "icone": "🌧️",
            "nivel": "aviso" if chuva_hoje <= 40 else "urgente",
        })

    # Calor + umidade alta: >30°C + >70% umidade → estresse térmico
    if temp_max > 30 and umidade > 70:
        alertas.append({
            "tipo": "calor_umidade",
            "alerta": "Calor extremo",
            "descricao": f"{temp_max:.0f}°C + {umidade}% umidade — estresse térmico alto.",
            "icone": "🔥",
            "nivel": "aviso",
        })

    # Queda abrupta de temperatura (comparar com amanhã)
    if len(dias) > 1:
        amanha = dias[1]
        temp_amanha = amanha.get("minima", 0) or 0
        temp_min_hoje = hoje.get("minima", 0) or 0
        queda = temp_min_hoje - temp_amanha
        if queda > 10:
            alertas.append({
                "tipo": "queda_temp",
                "alerta": "Queda de temperatura",
                "descricao": f"Queda de {queda:.0f}°C — verificar abrigo dos animais.",
                "icone": "❄️",
                "nivel": "aviso",
            })

    # Vento forte: >15 km/h → desconforto animal
    if vento > 15:
        alertas.append({
            "tipo": "vento_forte",
            "alerta": "Vento forte",
            "descricao": f"Vento de {vento:.0f} km/h — desconforto animal e risco de disseminação de doenças.",
            "icone": "💨",
            "nivel": "aviso",
        })

    return alertas


def previsao(*, agora=None, latitude=None, longitude=None):
    """Previsão com suporte para geolocalização do navegador.

    Se latitude/longitude não forem dados, tenta usar as coordenadas do sitio_config.json.
    Se nenhuma coordenada existir, avisa para permitir geolocalização no celular.
    """
    agora = agora or agora()
    cfg = _configuracao()

    # Permite sobrescrever com coordenadas do navegador
    if latitude is not None and longitude is not None:
        try:
            coordenadas = (float(latitude), float(longitude))
            if not (-90 <= coordenadas[0] <= 90 and -180 <= coordenadas[1] <= 180):
                coordenadas = None
        except (TypeError, ValueError):
            coordenadas = None
    else:
        coordenadas = _coordenadas(cfg)

    cache = _ler_cache()
    if not coordenadas:
        return {"status": "indisponível",
                "mensagem": "Permita geolocalização para previsão automática.",
                "pede_geo": True}

    if cache:
        try:
            salvo = datetime.fromisoformat(cache["salvo_em"])
            diario_cache = cache["dados"].get("daily") or {}
            cache_diario_completo = all(
                isinstance(diario_cache.get(campo), list)
                and len(diario_cache[campo]) >= len(diario_cache.get("time") or [])
                for campo in VARIAVEIS_DIARIAS
            )
            if (cache_diario_completo
                    and (agora - salvo).total_seconds() < CACHE_HORAS * 3600):
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
                "daily": ",".join(VARIAVEIS_DIARIAS),
                "timezone": "America/Sao_Paulo", "forecast_days": 7,
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


def analise_secas_e_chuvas(df_visitas, hoje=None):
    """Analisa o histórico de chuvas das visitas (ano atual vs ano anterior)
    e gera alerta automático de estiagem / necessidade de antecipar volumoso."""
    hoje = hoje or agora().date()
    ano_atual = hoje.year
    ano_anterior = ano_atual - 1

    mensal_atual = {m: 0.0 for m in range(1, 13)}
    mensal_anterior = {m: 0.0 for m in range(1, 13)}
    chuva_ultimos_60d = 0.0
    limite_60d = hoje - timedelta(days=60)

    if df_visitas is not None and not df_visitas.empty and "Data" in df_visitas.columns and "Chuva mm" in df_visitas.columns:
        for _, row in df_visitas.iterrows():
            dt = pd.to_datetime(row.get("Data"), dayfirst=True, errors="coerce")
            if pd.isna(dt):
                continue
            d = dt.date()
            try:
                mm = float(str(row.get("Chuva mm", 0) or 0).replace(",", "."))
            except (TypeError, ValueError):
                mm = 0.0
            
            if d.year == ano_atual:
                mensal_atual[d.month] += mm
            elif d.year == ano_anterior:
                mensal_anterior[d.month] += mm

            if limite_60d <= d <= hoje:
                chuva_ultimos_60d += mm

    alerta_estiagem = None
    if chuva_ultimos_60d < 30.0 and hoje.month in (4, 5, 6, 7, 8, 9, 10):
        alerta_estiagem = {
            "nivel": "urgente",
            "titulo": "⚠️ Alerta de Estiagem Prolongada",
            "descricao": f"Acumulado de apenas {chuva_ultimos_60d:.1f}mm nos últimos 60 dias. Recomenda-se antecipar a reserva de volumoso (silagem/feno) para evitar escassez de pastagem."
        }

    return {
        "ano_atual": ano_atual,
        "ano_anterior": ano_anterior,
        "mensal_atual": mensal_atual,
        "mensal_anterior": mensal_anterior,
        "chuva_ultimos_60d": chuva_ultimos_60d,
        "alerta_estiagem": alerta_estiagem,
    }
