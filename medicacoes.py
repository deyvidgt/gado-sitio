#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
medicacoes.py — Histórico de medicações por animal (Leite e Corte)

Rastreia qual medicação foi dada a qual animal, quando, e impacto em quarentena de leite.
Integra com Animais (brinco) e alertas de qualidade de leite.
"""

import pandas as pd
from datetime import datetime, timedelta
import db
from config import COLUNAS_MEDICACOES


def registrar_medicacao(data: str, brincos: str, tipo: str, principio: str,
                       dosagem: str, via: str, motivo: str, quarentena_dias: int,
                       custo: float = 0, observacoes: str = "") -> bool:
    """
    Registra medicação para um ou mais animais.

    Args:
        data: dd/mm/aaaa
        brincos: "Amarelo 01 #A0001; Azul 05 #A0003" (mesmo formato de Vendas)
        tipo: "Antibiótico IM", "Antiparasitário", "Antiinflamatório", etc.
        principio: "Penicilina benzatina", "Ivermectina", etc.
        dosagem: "20 mL", "1 comprimido"
        via: "IM", "IV", "Oral", "Tópico"
        motivo: "Mastite", "Metrite", "Ferida", "Controle parasitário"
        quarentena_dias: dias até liberação de leite (min 3 antibiótico, 0 outros)
        custo: R$ gasto
        observacoes: notas extras

    Returns:
        True se gravou, False se erro
    """
    try:
        # Validar data
        try:
            data_obj = pd.to_datetime(data, format='%d/%m/%Y')
        except:
            print(f"❌ Data inválida: {data}")
            return False

        # Validar brincos (existem?)
        if brincos.strip():
            brincos_lista = [b.strip() for b in brincos.split(';') if b.strip()]
        else:
            print("❌ Brincos obrigatórios")
            return False

        # Calcular data de liberação
        data_liberacao = (data_obj + timedelta(days=int(quarentena_dias))).strftime('%d/%m/%Y')

        # Montar linha
        linha = [
            data,
            brincos,
            tipo,
            principio,
            dosagem,
            via,
            motivo,
            str(quarentena_dias),
            data_liberacao,
            str(custo),
            "Sistema",  # Responsável (admin)
            observacoes,
        ]

        # Gravar
        db.salvar_linha("Medicações", linha)
        print(f"✅ Medicação registrada: {brincos} em {data}")
        return True

    except Exception as e:
        print(f"❌ Erro ao registrar medicação: {e}")
        return False


def historico_animal(brinco_id: str) -> list:
    """
    Retorna histórico de medicações de um animal.

    Args:
        brinco_id: Identificador único (ex: "A0001")

    Returns:
        Lista de dicts com medicações
    """
    try:
        df = db.ler_aba("Medicações")
        if df.empty:
            return []

        # Filtrar por brinco (buscar substring no formato "Amarelo 01 #A0001")
        df_filtrado = df[df['Brincos'].str.contains(brinco_id, na=False)]

        return df_filtrado.to_dict('records')

    except Exception as e:
        print(f"❌ Erro ao ler histórico: {e}")
        return []


def alertas_quarentena(hoje: str = None) -> dict:
    """
    Retorna animais em quarentena de leite HOJE.

    Args:
        hoje: dd/mm/aaaa (default: hoje)

    Returns:
        {
            "total": int,
            "por_liberar": [{"brinco": "", "liberacao": "", "dias_falta": int}, ...],
            "por_vencer_hoje": [...]
        }
    """
    if not hoje:
        hoje = datetime.now().strftime('%d/%m/%Y')

    try:
        data_obj = pd.to_datetime(hoje, format='%d/%m/%Y')
    except:
        return {"total": 0, "por_liberar": [], "por_vencer_hoje": []}

    try:
        df = db.ler_aba("Medicações")
        if df.empty:
            return {"total": 0, "por_liberar": [], "por_vencer_hoje": []}

        # Converter Data Liberação para datetime
        df['Data_Liberacao_obj'] = pd.to_datetime(df['Data Liberação'], format='%d/%m/%Y', errors='coerce')

        # Filtrar medicações que ainda estão em quarentena (Data_Liberacao >= hoje)
        df_quaren = df[df['Data_Liberacao_obj'] >= data_obj].copy()

        if df_quaren.empty:
            return {"total": 0, "por_liberar": [], "por_vencer_hoje": []}

        # Calcular dias faltantes
        df_quaren['dias_falta'] = (df_quaren['Data_Liberacao_obj'] - data_obj).dt.days

        # Separar por vencer hoje (dias_falta == 0) e ainda faltando
        por_vencer = df_quaren[df_quaren['dias_falta'] == 0].copy()
        por_liberar = df_quaren[df_quaren['dias_falta'] > 0].copy()

        return {
            "total": len(df_quaren),
            "por_liberar": [
                {
                    "brinco": row['Brincos'],
                    "liberacao": row['Data Liberação'],
                    "dias_falta": int(row['dias_falta']),
                    "motivo": row['Motivo'],
                } for _, row in por_liberar.iterrows()
            ],
            "por_vencer_hoje": [
                {
                    "brinco": row['Brincos'],
                    "liberacao": row['Data Liberação'],
                    "motivo": row['Motivo'],
                } for _, row in por_vencer.iterrows()
            ],
        }

    except Exception as e:
        print(f"❌ Erro ao calcular quarentena: {e}")
        return {"total": 0, "por_liberar": [], "por_vencer_hoje": []}


def medicacoes_recentes(dias: int = 30) -> list:
    """
    Retorna medicações dos últimos N dias.
    """
    try:
        df = db.ler_aba("Medicações")
        if df.empty:
            return []

        data_limite = pd.to_datetime(datetime.now() - timedelta(days=dias), format='%Y-%m-%d')
        df['Data_obj'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df_recentes = df[df['Data_obj'] >= data_limite].copy()

        return df_recentes.to_dict('records')

    except Exception as e:
        print(f"❌ Erro ao ler recentes: {e}")
        return []


def relatorio_medicacoes_animal(brinco_id: str, ano: int = None) -> dict:
    """
    Relatório de medicações de um animal em um ano.
    """
    if not ano:
        ano = datetime.now().year

    historico = historico_animal(brinco_id)

    if not historico:
        return {"animal": brinco_id, "ano": ano, "total": 0, "por_tipo": {}}

    df = pd.DataFrame(historico)
    df['ano'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.year
    df_ano = df[df['ano'] == ano]

    por_tipo = df_ano['Tipo Medicação'].value_counts().to_dict()

    return {
        "animal": brinco_id,
        "ano": ano,
        "total": len(df_ano),
        "por_tipo": por_tipo,
        "medicacoes": df_ano.to_dict('records'),
    }
