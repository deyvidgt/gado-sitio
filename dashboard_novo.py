#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_novo.py — Funções para o novo dashboard mobile-first (v5.8)

Inclui:
- chuvas_mes(): Gráfico de chuvas do mês
- cotacao_mercado(): Cotação de boi e leite
- alertas_consolidados(): Consolidação de avisos
"""

import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from extensions import _agora


def chuvas_mes(ano: int = None, mes: int = None) -> dict:
    """
    Retorna dados de chuvas do mês para gráfico.

    Args:
        ano: Ano (se None, usa atual)
        mes: Mês 1-12 (se None, usa atual)

    Returns:
        {
            "total": 120,        # mm acumulado
            "media": 90,         # mm média histórica (simplificado)
            "semanas": [
                {"num": 1, "mm": 30},
                {"num": 2, "mm": 45},
                ...
            ]
        }
    """
    agora = _agora()
    if ano is None:
        ano = agora.year
    if mes is None:
        mes = agora.month

    # Ler visitas
    try:
        visitas = carregar_aba("Visitas")
    except:
        return {"total": 0, "media": 90, "semanas": []}

    if visitas.empty or "Chuva mm" not in visitas.columns:
        return {"total": 0, "media": 90, "semanas": []}

    # Filtrar mês
    visitas["Data"] = pd.to_datetime(visitas["Data"], dayfirst=True, errors="coerce")
    visitas_mes = visitas[
        (visitas["Data"].dt.year == ano) &
        (visitas["Data"].dt.month == mes)
    ]

    # Chuva total
    chuva_col = visitas_mes.get("Chuva mm") or visitas_mes.get("Chuva (mm)")
    if chuva_col is None:
        return {"total": 0, "media": 90, "semanas": []}

    total = float(chuva_col.sum() or 0)

    # Separar por semana (aproximado: semana 1 = dias 1-7, etc)
    semanas = {}
    for _, row in visitas_mes.iterrows():
        if pd.isna(row.get("Data")) or pd.isna(row.get("Chuva mm")):
            continue
        dia = row["Data"].day
        semana = (dia - 1) // 7 + 1
        mm = float(row.get("Chuva mm") or 0)
        semanas[semana] = semanas.get(semana, 0) + mm

    semanas_list = [{"num": i, "mm": round(semanas.get(i, 0), 1)} for i in range(1, 5)]

    # Média histórica (simplificada: valor fixo por região)
    media_historica = 90  # mm/mês (média Triângulo Mineiro)

    return {
        "total": round(total, 1),
        "media": media_historica,
        "semanas": semanas_list,
    }


def cotacao_mercado() -> list:
    """
    Retorna cotações de boi e leite.

    Returns:
        [
            {
                "nome": "Boi",
                "preco": 30.50,
                "variacao": 2.5,        # % vs ontem
                "variacao_symbol": "↑"
            },
            ...
        ]
    """
    # TODO: Integrar com API real (ex: BeefPoint, QuotaLab)
    # Por enquanto, retorna valores simulados

    # Tentar ler de arquivo manual (sitio_config.json)
    try:
        from extensions import _ler_sitio_config_disco
        cfg = _ler_sitio_config_disco()
        cotacoes = cfg.get("cotacoes", {})

        resultado = []
        if cotacoes.get("boi_preco"):
            resultado.append({
                "nome": "Boi (R$/kg)",
                "preco": float(cotacoes["boi_preco"]),
                "variacao": float(cotacoes.get("boi_variacao", 0)),
                "variacao_symbol": "↑" if float(cotacoes.get("boi_variacao", 0)) >= 0 else "↓",
                "icon": "📈",
            })

        if cotacoes.get("leite_preco"):
            resultado.append({
                "nome": "Leite (R$/L)",
                "preco": float(cotacoes["leite_preco"]),
                "variacao": float(cotacoes.get("leite_variacao", 0)),
                "variacao_symbol": "↑" if float(cotacoes.get("leite_variacao", 0)) >= 0 else "↓",
                "icon": "🥛",
            })

        if resultado:
            return resultado
    except:
        pass

    # Valores padrão (simulado)
    return [
        {
            "nome": "Boi (R$/kg)",
            "preco": 30.50,
            "variacao": 2.5,
            "variacao_symbol": "↑",
        },
        {
            "nome": "Leite (R$/L)",
            "preco": 1.82,
            "variacao": -1.0,
            "variacao_symbol": "↓",
        },
    ]


def alertas_consolidados(dados: dict) -> list:
    """
    Consolida todos os alertas: quarentena, CCS, mastite, CPP, pastos.

    Args:
        dados: Dict com abas (Medicações, Leite Produção, etc)

    Returns:
        [
            {
                "icon": "🚨",
                "msg": "Vaca 05 em quarentena até 10/11",
                "status": "urgente",  # urgente | aviso | ok
            },
            ...
        ]
    """
    alertas = []

    # Quarentena de medicações (v5.7)
    try:
        medicacoes = dados.get("Medicações") or carregar_aba("Medicações")
        agora = _agora().date()

        for _, row in medicacoes.iterrows():
            data_lib = row.get("Data Liberação")
            if pd.isna(data_lib):
                continue

            data_lib = pd.to_datetime(data_lib, dayfirst=True, errors="coerce")
            if pd.isna(data_lib):
                continue

            if data_lib.date() > agora:
                brinco = row.get("Brincos", "")
                dias = (data_lib.date() - agora).days
                alertas.append({
                    "icon": "🚫",
                    "msg": f"Quarentena: {brinco} ({dias}d)",
                    "status": "urgente" if dias <= 3 else "aviso",
                })
    except Exception as e:
        pass

    # CCS e mastite (v5.4)
    try:
        leite_prod = dados.get("Leite Produção") or carregar_aba("Leite Produção")
        if not leite_prod.empty and "CCS" in leite_prod.columns:
            altos_ccs = leite_prod[
                (leite_prod["CCS"] > 200000) |
                (leite_prod["CPP"] > 100000)
            ].tail(5)

            for _, row in altos_ccs.iterrows():
                vaca = row.get("Vaca", "")
                ccs = row.get("CCS", 0)
                if ccs > 400000:
                    alertas.append({
                        "icon": "⚠️",
                        "msg": f"CCS alto: {vaca} ({int(ccs/1000)}k)",
                        "status": "urgente",
                    })
                elif ccs > 200000:
                    alertas.append({
                        "icon": "⚡",
                        "msg": f"CCS elevado: {vaca}",
                        "status": "aviso",
                    })
    except Exception as e:
        pass

    # Pastos lotados (v5.2)
    try:
        import pastos
        situacao = pastos.situacao(dados.get("Manejo") or carregar_aba("Manejo"),
                                   dados.get("Pastos") or carregar_aba("Pastos"))

        for pasto_id, info in situacao.items():
            ua_ha = info.get("ua_ha", 0)
            capacidade = info.get("capacidade_ua_ha", 0)

            if capacidade > 0 and ua_ha > capacidade:
                pasto_nome = info.get("nome", pasto_id)
                alertas.append({
                    "icon": "🌾",
                    "msg": f"Lotação crítica: {pasto_nome}",
                    "status": "aviso",
                })
    except Exception as e:
        pass

    # Reprodução: atrasados (v5.3)
    try:
        import reproducao
        reprodutivas = reproducao.situacao(
            dados.get("Manejo") or carregar_aba("Manejo")
        )

        atrasadas = [a for a in reprodutivas.values() if a.get("status") == "atrasada"]
        if atrasadas:
            alertas.append({
                "icon": "🐮",
                "msg": f"{len(atrasadas)} vaca(s) atrasada(s)",
                "status": "urgente",
            })
    except Exception as e:
        pass

    return alertas[:5]  # Máx 5 alertas no resumo


def tarefas_pendentes(dados: dict = None) -> list:
    """
    Retorna tarefas pendentes/atrasadas para o resumo.

    Returns:
        [
            {
                "titulo": "Pesagem geral",
                "status_label": "Hoje",
                "dias_atraso": 0,
                "dias_ate": 0,
            },
            ...
        ]
    """
    try:
        import tarefas
        from extensions import _agora

        tarefas_obj = tarefas.pendentes(_agora().date())
        resultado = []

        for t in tarefas_obj[:5]:
            dias_atraso = max(0, (datetime.now().date() - t.get("data_vencimento", datetime.now().date())).days)
            dias_ate = (t.get("data_vencimento", datetime.now().date()) - datetime.now().date()).days

            if dias_atraso > 0:
                status_label = f"⏰ {dias_atraso}d atrasada"
            elif dias_ate == 0:
                status_label = "🔴 Hoje"
            else:
                status_label = f"📅 +{dias_ate}d"

            resultado.append({
                "titulo": t.get("titulo", ""),
                "status_label": status_label,
                "dias_atraso": dias_atraso,
                "dias_ate": dias_ate,
            })

        return resultado
    except Exception as e:
        return []
