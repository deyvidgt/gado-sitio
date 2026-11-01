#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cochos.py — Gestão de comedouros/bebedouros por pasto (v5.12 Onda 11 expandida)

Cadastro, manutenção, alertas de reposição (ração/água/sal).
Dados: aba Excel "Cochos" com colunas:
  ID, Pasto, Tipo, Localização GPS, Data Instalação, Última Manutenção,
  Frequência Limpeza (dias), Status, Observações, Criado Em
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta

import animais as A

TIPOS_COCHO = ["Cocho (ração)", "Bebedouro (água)", "Saleiro (sal)"]

STATUS_COCHO = ["Ativo", "Manutenção", "Danificado", "Fora de Serviço"]


def registrar_cocho(pasto_id: str, tipo: str, lat: float, lng: float,
                   freq_limpeza: int = 7, observacoes: str = "") -> dict:
    """Registra novo cocho/bebedouro."""
    try:
        if tipo not in TIPOS_COCHO:
            return {"sucesso": False, "msg": f"Tipo inválido: {tipo}"}

        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return {"sucesso": False, "msg": "Coordenadas GPS inválidas"}

        cocho_id = f"C{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "sucesso": True,
            "msg": f"✅ Cocho registrado: {cocho_id}",
            "cocho_id": cocho_id,
            "pasto_id": pasto_id,
            "tipo": tipo,
            "coordenadas": {"lat": lat, "lng": lng},
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def historico_manutencoes(df_cochos, cocho_id: str) -> list[dict]:
    """Retorna manutenções de um cocho."""
    if df_cochos is None or df_cochos.empty:
        return []

    manutencoes = []
    for _, row in df_cochos.iterrows():
        if A._txt(row.get("ID")) != cocho_id:
            continue

        data_ult_manut = A._txt(row.get("Última Manutenção", ""))
        if data_ult_manut:
            manutencoes.append({
                "data": data_ult_manut,
                "tipo": "Limpeza/Manutenção",
                "observacoes": A._txt(row.get("Observações", "")),
            })

    return sorted(manutencoes, key=lambda x: x["data"], reverse=True)


def alertas_manutencao(df_cochos, hoje=None) -> list[dict]:
    """Alertas de cochos pendentes manutenção."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()

    if df_cochos is None or df_cochos.empty:
        return []

    alertas = []
    for _, row in df_cochos.iterrows():
        try:
            freq = int(row.get("Frequência Limpeza (dias)", 7))
            data_ult = pd.Timestamp(row.get("Última Manutenção", ""))

            if pd.isna(data_ult):
                data_ult = pd.Timestamp(row.get("Data Instalação", hoje))

            dias_desde = (hoje - data_ult).days

            if dias_desde >= freq:
                cocho_id = A._txt(row.get("ID"))
                tipo = A._txt(row.get("Tipo"))
                pasto = A._txt(row.get("Pasto"))

                alertas.append({
                    "cocho_id": cocho_id,
                    "tipo": tipo,
                    "pasto": pasto,
                    "dias_atraso": dias_desde - freq,
                    "mensagem": f"🚨 {tipo} em {pasto} pendente limpeza ({dias_desde} dias)",
                    "urgencia": "urgente" if dias_desde >= freq * 1.5 else "aviso",
                })
        except (ValueError, TypeError):
            continue

    return sorted(alertas, key=lambda x: x["dias_atraso"], reverse=True)


def alertas_reposicao(df_cochos, insumo_type: str = "ração") -> list[dict]:
    """Alertas de reposição (ração/água/sal) baseado em tipo de cocho."""
    if df_cochos is None or df_cochos.empty:
        return []

    alertas = []
    tipo_mapa = {
        "ração": "Cocho (ração)",
        "água": "Bebedouro (água)",
        "sal": "Saleiro (sal)",
    }
    tipo_buscado = tipo_mapa.get(insumo_type, "Cocho (ração)")

    for _, row in df_cochos.iterrows():
        tipo = A._txt(row.get("Tipo"))
        if tipo != tipo_buscado:
            continue

        status = A._txt(row.get("Status", "Ativo"))
        if status != "Ativo":
            continue

        cocho_id = A._txt(row.get("ID"))
        pasto = A._txt(row.get("Pasto"))

        alertas.append({
            "cocho_id": cocho_id,
            "pasto": pasto,
            "tipo": insumo_type.upper(),
            "mensagem": f"🔔 Reposição de {insumo_type} em {pasto} ({cocho_id})",
        })

    return alertas


def dashboard_cochos(df_cochos) -> dict:
    """Resumo para dashboard."""
    if df_cochos is None or df_cochos.empty:
        return {"total": 0, "por_tipo": {}, "em_manutencao": 0}

    por_tipo = {}
    em_manutencao = 0

    for _, row in df_cochos.iterrows():
        tipo = A._txt(row.get("Tipo", "Outro"))
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        status = A._txt(row.get("Status", "Ativo"))
        if status == "Manutenção":
            em_manutencao += 1

    return {
        "total": len(df_cochos),
        "por_tipo": por_tipo,
        "em_manutencao": em_manutencao,
    }


def cochos_por_pasto(df_cochos, pasto_id: str) -> list[dict]:
    """Lista cochos de um pasto específico com coordenadas para mapa."""
    if df_cochos is None or df_cochos.empty:
        return []

    cochos = []
    for _, row in df_cochos.iterrows():
        if A._txt(row.get("Pasto")) != pasto_id:
            continue

        try:
            lat = float(row.get("Localização GPS", "").split(",")[0])
            lng = float(row.get("Localização GPS", "").split(",")[1])
        except (ValueError, IndexError, AttributeError):
            lat, lng = 0, 0

        cochos.append({
            "id": A._txt(row.get("ID")),
            "tipo": A._txt(row.get("Tipo")),
            "status": A._txt(row.get("Status", "Ativo")),
            "lat": lat,
            "lng": lng,
            "frequencia_limpeza": int(row.get("Frequência Limpeza (dias)", 7)),
            "observacoes": A._txt(row.get("Observações", "")),
        })

    return cochos
