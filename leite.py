# -*- coding: utf-8 -*-
"""
Módulo de suporte para o sistema de gestão de leite.

Funções para cálculos, processamento de dados e validações.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import pandas as pd


def _data(valor) -> Optional[date]:
    """Converte string para data; retorna None se inválida."""
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        if isinstance(valor, str):
            # Tenta formato dd/mm/aaaa
            partes = valor.replace("-", "/").split("/")
            if len(partes) == 3:
                d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
                return date(a, m, d)
        return pd.to_datetime(valor, dayfirst=True).date()
    except (ValueError, TypeError, AttributeError):
        return None


def _numero(valor) -> Optional[float]:
    """Converte string em número; retorna None se inválida."""
    if not valor and valor != 0:
        return None
    try:
        s = str(valor).replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return None


def acumulados(df: pd.DataFrame, hoje: date) -> Dict:
    """
    Calcula totais acumulados de produção de leite do mês até hoje.

    Args:
        df: DataFrame da aba "Leite Produção"
        hoje: Data atual (date object)

    Returns:
        Dict com: total_litros, dias_com_registro, media_diaria
    """
    if df.empty:
        return {"total_litros": 0.0, "dias_com_registro": 0, "media_diaria": 0.0}

    inicio_mes = hoje.replace(day=1)
    df_mes = df.copy()

    # Converte coluna Data para date
    df_mes["Data_converted"] = df_mes.get("Data", []).apply(_data)
    df_mes = df_mes[(df_mes["Data_converted"] >= inicio_mes) & (df_mes["Data_converted"] <= hoje)]

    if df_mes.empty:
        return {"total_litros": 0.0, "dias_com_registro": 0, "media_diaria": 0.0}

    # Converte Litros para número
    df_mes["Litros_num"] = df_mes.get("Litros", []).apply(_numero)
    total = df_mes["Litros_num"].sum() or 0.0
    dias = len(df_mes)
    media = total / dias if dias > 0 else 0.0

    return {
        "total_litros": round(total, 2),
        "dias_com_registro": dias,
        "media_diaria": round(media, 2),
    }


def contagens_rebanho(df_animais: pd.DataFrame) -> Dict[str, int]:
    """
    Conta vacas em lactação, secas, novilhas e total de fêmeas.

    Args:
        df_animais: DataFrame da aba "Animais"

    Returns:
        Dict com contagens por categoria
    """
    if df_animais.empty:
        return {
            "vacas_lactacao": 0,
            "vacas_secas": 0,
            "novilhas": 0,
            "total_femeas": 0,
        }

    # Filtra vivas
    vivas = df_animais[df_animais.get("Status", "").astype(str).str.lower().isin({"vivo", "ativo"})]

    # Filtra fêmeas
    femeas = vivas[vivas.get("Sexo", "").astype(str).str.upper() == "F"]

    # Conta por situação leite (se houver coluna)
    lactacao = len(femeas[femeas.get("Situação Leite", "").astype(str).str.lower() == "em lactação"])
    secas = len(femeas[femeas.get("Situação Leite", "").astype(str).str.lower() == "seca"])
    novilhas = len(femeas[femeas.get("Categoria", "").astype(str).str.lower() == "novilha"])

    # Se não houver coluna Situação Leite, aprox. pela categoria
    if lactacao == 0 and secas == 0:
        vacas = len(femeas[femeas.get("Categoria", "").astype(str).str.lower() == "vaca"])
        lactacao = max(1, vacas - novilhas // 2)
        secas = vacas - lactacao

    return {
        "vacas_lactacao": lactacao,
        "vacas_secas": secas,
        "novilhas": novilhas,
        "total_femeas": len(femeas),
    }


def dias_em_lactacao(data_parto: str, hoje: date) -> Optional[int]:
    """Calcula dias desde o parto até hoje."""
    parto = _data(data_parto)
    if not parto:
        return None
    return (hoje - parto).days


def medias_periodo(
    df: pd.DataFrame,
    inicio: date,
    fim: date,
    animais_lactacao: int = 1,
) -> Dict[str, float]:
    """
    Calcula médias de produção no período.

    Args:
        df: DataFrame da aba "Leite Produção"
        inicio: Data inicial
        fim: Data final
        animais_lactacao: Número de vacas em lactação (para média por vaca)

    Returns:
        Dict com: media_diaria, media_por_vaca, producao_total
    """
    if df.empty:
        return {"media_diaria": 0.0, "media_por_vaca": 0.0, "producao_total": 0.0}

    df_p = df.copy()
    df_p["Data_converted"] = df_p.get("Data", []).apply(_data)
    df_p = df_p[(df_p["Data_converted"] >= inicio) & (df_p["Data_converted"] <= fim)]

    if df_p.empty:
        return {"media_diaria": 0.0, "media_por_vaca": 0.0, "producao_total": 0.0}

    df_p["Litros_num"] = df_p.get("Litros", []).apply(_numero)
    total = df_p["Litros_num"].sum() or 0.0
    dias = len(df_p)

    media_dia = total / dias if dias > 0 else 0.0
    media_vaca = media_dia / animais_lactacao if animais_lactacao > 0 else 0.0

    return {
        "media_diaria": round(media_dia, 2),
        "media_por_vaca": round(media_vaca, 2),
        "producao_total": round(total, 2),
    }


def producao_por_animal(df: pd.DataFrame, inicio: date, fim: date) -> List[Dict]:
    """
    Agrupa produção por animal.

    Returns:
        Lista de dicts com: id, brinco, total_litros, dias, media
    """
    if df.empty:
        return []

    df_p = df.copy()
    df_p["Data_converted"] = df_p.get("Data", []).apply(_data)
    df_p = df_p[(df_p["Data_converted"] >= inicio) & (df_p["Data_converted"] <= fim)]

    if df_p.empty:
        return []

    df_p["Litros_num"] = df_p.get("Litros", []).apply(_numero)

    # Agrupa por Vaca ID ou Brinco
    agrupado = []
    for vaca_id in df_p.get("Vaca ID", []).unique():
        if not vaca_id or str(vaca_id).strip() == "":
            continue
        registros = df_p[df_p.get("Vaca ID", "") == vaca_id]
        total = registros["Litros_num"].sum() or 0.0
        dias = len(registros)
        media = total / dias if dias > 0 else 0.0

        agrupado.append({
            "id": str(vaca_id),
            "brinco": registros.iloc[0].get("Brinco", "") if len(registros) > 0 else "",
            "total_litros": round(total, 2),
            "dias": dias,
            "media": round(media, 2),
        })

    return sorted(agrupado, key=lambda x: x["total_litros"], reverse=True)


def serie_diaria(df: pd.DataFrame, inicio: date, fim: date) -> List[Tuple[date, float]]:
    """
    Cria série diária de produção.

    Returns:
        Lista de tuplas (data, total_litros_dia)
    """
    if df.empty:
        return []

    df_p = df.copy()
    df_p["Data_converted"] = df_p.get("Data", []).apply(_data)
    df_p = df_p[(df_p["Data_converted"] >= inicio) & (df_p["Data_converted"] <= fim)]

    if df_p.empty:
        return []

    df_p["Litros_num"] = df_p.get("Litros", []).apply(_numero)

    # Agrupa por dia
    diarios = {}
    for _, linha in df_p.iterrows():
        data = linha["Data_converted"]
        litros = linha["Litros_num"] or 0.0
        if data not in diarios:
            diarios[data] = 0.0
        diarios[data] += litros

    # Retorna série ordenada
    return sorted([(d, round(l, 2)) for d, l in diarios.items()])


def validar_producao(dados: Dict) -> Optional[str]:
    """
    Valida dados de um registro de ordenha.

    Args:
        dados: Dict com Data, Vaca ID (opcional), Modo Registro, Litros

    Returns:
        Mensagem de erro se inválido, None se OK
    """
    data = _data(dados.get("Data"))
    if not data:
        return "Data inválida."

    modo = str(dados.get("Modo Registro", "")).strip().lower()
    if modo not in ("individual", "rebanho"):
        return "Modo de registro inválido (individual ou rebanho)."

    if modo == "individual":
        vaca_id = str(dados.get("Vaca ID", "")).strip()
        if not vaca_id:
            return "Vaca ID é obrigatório no modo individual."

    litros = _numero(dados.get("Litros"))
    if litros is None or litros < 0:
        return "Litros deve ser um número positivo."

    return None
