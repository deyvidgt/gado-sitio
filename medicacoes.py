#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
medicacoes.py — Histórico de medicações por animal + quarentena leite (v5.12 Onda 12.X)

Rastreia qual medicação foi dada a qual animal, quando, dosagem, e impacto em quarentena de leite.
Integra com Manejo (tipo "Medicação") e alertas de quarentena.

Dados: Aba Excel "Medicações" com colunas:
  Data, Brincos, Tipo Medicação, Princípio Ativo, Dosagem, Via, Motivo,
  Quarentena Leite (dias), Data Liberação, Responsável, ID Envio, Criado Em
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta

import animais as A

# ── Tipos de medicação ──────────────────────────────────────────────────────────
TIPOS_MEDICACAO = [
    "Antibiótico IM",
    "Antibiótico IV",
    "Antibiótico Oral",
    "Antiparasitário",
    "Anti-inflamatório",
    "Vitaminas",
    "Estimulante Rúmen",
    "Outro",
]

VIAS_APLICACAO = ["IM", "IV", "Oral", "Tópico", "Intra-mamária"]

# ── Quarentena padrão por tipo (dias) ──────────────────────────────────────────
QUARENTENA_PADRAO = {
    "Antibiótico IM": 3,
    "Antibiótico IV": 3,
    "Antibiótico Oral": 3,
    "Antiparasitário": 0,
    "Anti-inflamatório": 1,
    "Vitaminas": 0,
    "Estimulante Rúmen": 0,
    "Outro": 1,
}

MOTIVOS_MEDICACAO = [
    "Mastite",
    "Metrite",
    "Ferida/Abcesso",
    "Controle Parasitário",
    "Reposição Vitamínica",
    "Doença Respiratória",
    "Diarreia",
    "Outro",
]


def registrar_medicacao(data: str, brincos_str: str, tipo: str, principio: str,
                       dosagem: str, via: str, motivo: str, quarentena_leite: int,
                       responsavel: str = "") -> dict:
    """Registra nova medicação por animal.

    Retorna: {"sucesso": bool, "msg": str, "data_liberacao": str}

    shortcut: não valida tipo/princípio/motivo contra enum (dados do usuário variam)
    """
    try:
        data_obj = pd.Timestamp(data).normalize()
        if data_obj > pd.Timestamp.now().normalize():
            raise ValueError("Data não pode ser futura")

        # Validar brincos (devem existir em Animais)
        ids_animais = A.ids_de(brincos_str)
        if not ids_animais:
            raise ValueError("Nenhum animal encontrado nos brincos informados")

        # Quarentena deve ser >= 0
        if not isinstance(quarentena_leite, int) or quarentena_leite < 0:
            raise ValueError("Quarentena deve ser número não-negativo")

        data_liberacao = data_obj + timedelta(days=quarentena_leite)

        return {
            "sucesso": True,
            "msg": f"✅ Medicação registrada para {len(ids_animais)} animal(is)",
            "data_liberacao": str(data_liberacao.date()),
            "ids_animais": ids_animais,
            "data_liberacao_obj": data_liberacao,
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def historico_animal(df_medicacoes, animal_id: str) -> list[dict]:
    """Retorna todas as medicações de um animal (por brinco ID).

    Retorna: [{"data": "2026-10-31", "tipo": "Mastite", "via": "IM", "quarentena": 3, ...}]
    """
    if df_medicacoes is None or df_medicacoes.empty:
        return []

    registros = []
    for _, row in df_medicacoes.iterrows():
        brincos_str = A._txt(row.get("Brincos", ""))
        if animal_id not in A.ids_de(brincos_str):
            continue

        registros.append({
            "data": A._txt(row.get("Data", "")),
            "tipo_medicacao": A._txt(row.get("Tipo Medicação", "")),
            "principio_ativo": A._txt(row.get("Princípio Ativo", "")),
            "dosagem": A._txt(row.get("Dosagem", "")),
            "via": A._txt(row.get("Via", "")),
            "motivo": A._txt(row.get("Motivo", "")),
            "quarentena_leite": row.get("Quarentena Leite (dias)", 0),
            "data_liberacao": A._txt(row.get("Data Liberação", "")),
            "responsavel": A._txt(row.get("Responsável", "")),
        })

    # Ordenar por data (descendente — mais recente primeiro)
    registros.sort(key=lambda x: x["data"], reverse=True)
    return registros


def animais_em_quarentena(df_medicacoes, df_animais, hoje=None) -> list[dict]:
    """Retorna animais com leite em quarentena HOJE.

    Retorna: [{"animal_ref": "Preta 23 #A0042", "data_liberacao": "2026-11-02", "dias_restantes": 1}]
    """
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()

    if df_medicacoes is None or df_medicacoes.empty:
        return []

    em_quarentena = {}  # animal_id → (data_liberacao mais recente, dias_restantes)

    for _, row in df_medicacoes.iterrows():
        try:
            data_lib = pd.Timestamp(row.get("Data Liberação", "")).normalize()
            if pd.isna(data_lib) or data_lib < hoje:
                continue  # liberação já passou

            brincos_str = A._txt(row.get("Brincos", ""))
            for animal_id in A.ids_de(brincos_str):
                dias_restantes = (data_lib - hoje).days
                # Manter a liberação mais próxima (a que libera por último)
                if animal_id not in em_quarentena or data_lib > em_quarentena[animal_id][0]:
                    em_quarentena[animal_id] = (data_lib, dias_restantes)
        except (ValueError, TypeError):
            continue

    # Montar resposta com referência do animal
    nomes = {}
    if df_animais is not None and not df_animais.empty:
        nomes = {r["ID"]: A.ref(r) for _, r in df_animais.iterrows()}

    alertas = []
    for animal_id, (data_lib, dias_restantes) in em_quarentena.items():
        alertas.append({
            "animal_id": animal_id,
            "animal_ref": nomes.get(animal_id, animal_id),
            "data_liberacao": str(data_lib.date()),
            "dias_restantes": dias_restantes,
            "urgencia": "urgente" if dias_restantes <= 1 else "aviso",
        })

    # Ordenar por dias restantes (mais urgentes primeiro)
    alertas.sort(key=lambda x: x["dias_restantes"])
    return alertas


def alertas_quarentena(df_medicacoes, df_animais, hoje=None) -> list[dict]:
    """Gera alertas de quarentena leite para WhatsApp/dashboard.

    Retorna: [{"animal_ref": "Preta 23", "mensagem": "🚫 Leite em quarentena até 02/11"}]
    """
    em_quarentena = animais_em_quarentena(df_medicacoes, df_animais, hoje)

    alertas = []
    for q in em_quarentena:
        if q["urgencia"] == "urgente":
            icone = "🚫"
            msg = f"LEITE LIBERADO AMANHÃ ({q['data_liberacao']})"
        else:
            icone = "⏰"
            msg = f"Leite em quarentena até {q['data_liberacao']} ({q['dias_restantes']} dias)"

        alertas.append({
            "animal_ref": q["animal_ref"],
            "animal_id": q["animal_id"],
            "mensagem": f"{icone} {q['animal_ref']}: {msg}",
            "urgencia": q["urgencia"],
            "data_liberacao": q["data_liberacao"],
        })

    return alertas


def dashboard_medicacoes(df_medicacoes, df_animais, hoje=None) -> dict:
    """Resumo para dashboard: total medicações este mês, em quarentena, etc.

    Retorna: {
        "total_mes": int,
        "em_quarentena_hoje": int,
        "liberando_amanha": int,
        "tipos_mais_comuns": [...],
    }
    """
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    mes_inicio = hoje.replace(day=1)

    if df_medicacoes is None or df_medicacoes.empty:
        return {
            "total_mes": 0,
            "em_quarentena_hoje": 0,
            "liberando_amanha": 0,
            "tipos_mais_comuns": [],
        }

    # Total este mês
    df_mes = df_medicacoes[
        (pd.to_datetime(df_medicacoes["Data"], errors="coerce") >= mes_inicio) &
        (pd.to_datetime(df_medicacoes["Data"], errors="coerce") <= hoje)
    ]
    total_mes = len(df_mes) if not df_mes.empty else 0

    # Em quarentena hoje
    quarentena = animais_em_quarentena(df_medicacoes, df_animais, hoje)
    em_quarentena_hoje = len(quarentena)

    # Liberando amanhã
    amanha = hoje + timedelta(days=1)
    liberando_amanha = sum(1 for q in quarentena if pd.Timestamp(q["data_liberacao"]).normalize() == amanha)

    # Tipos mais comuns
    tipos_cont = {}
    for _, row in df_medicacoes.iterrows():
        tipo = A._txt(row.get("Tipo Medicação", "Outro"))
        tipos_cont[tipo] = tipos_cont.get(tipo, 0) + 1

    tipos_mais_comuns = sorted(tipos_cont.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_mes": total_mes,
        "em_quarentena_hoje": em_quarentena_hoje,
        "liberando_amanha": liberando_amanha,
        "tipos_mais_comuns": [{"tipo": t, "count": c} for t, c in tipos_mais_comuns],
    }
