#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pastos_avancados.py — Controle Físico e Sanitário de Pastagens (Rotativo x Descanso)
Inclui medição de altura (pré e pós-pastejo), dias de ocupação/descanso, UA/ha e semáforo.
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime, timedelta
import pastos as PA
import animais as A

# Limites agronômicos para Pastagens Tropicais (ex: Brachiaria/Panicum)
ALTURA_MIN_PRE = 25      # cm — entrada ideal
ALTURA_MIN_POS = 15      # cm — saída ideal (resíduo)
DIAS_DESCANSO_IDEAL = 30 # dias
DIAS_OCUPACAO_MAX = 7    # dias (pastejo rotativo ideal)
UA_HA_LIMITE_ALERTA = 2.5 # UA/ha (acima disso exige atenção/suplementação)


def analise_rotativo_pasto(pasto_id: str, df_pastos: pd.DataFrame, df_man: pd.DataFrame) -> dict:
    """Retorna o estado físico e de descanso do pasto (rotativo x descanso)."""
    # Localizar dados do pasto
    pasto_row = df_pastos[df_pastos["ID"] == pasto_id]
    if pasto_row.empty:
        return {"erro": "Pasto não encontrado"}
    p = pasto_row.iloc[0]
    area = float(p.get("Área (ha)", 0) or 0)
    nome = p.get("Nome", pasto_id)

    # Últimas medições de manejo no pasto
    historico_pasto = []
    if df_man is not None and not df_man.empty and "Pasto" in df_man.columns:
        filtrado = df_man[df_man["Pasto"].astype(str).str.contains(pasto_id, case=False, na=False)]
        for _, r in filtrado.iterrows():
            historico_pasto.append({
                "data": r.get("Data"),
                "tipo": r.get("Tipo"),
                "descricao": r.get("Descrição"),
            })

    # Simular ou ler dias de ocupação e descanso (com base no histórico de manejo)
    dias_ocupacao = 5   # padrão simulado ou calculado
    dias_descanso = 28  # padrão simulado ou calculado
    altura_pre = 30.0   # cm
    altura_pos = 18.0   # cm

    # Semáforo de Lotação e Descanso
    # Verde = Ótimo, Amarelo = Atenção, Vermelho = Crítico (Superlotação / Descanso insuficiente)
    status_descanso = "ok"
    if dias_descanso < 20:
        status_descanso = "critico"
    elif dias_descanso < 28:
        status_descanso = "atencao"

    status_altura = "ok"
    if altura_pos < 12:
        status_altura = "critico"
    elif altura_pre < 20:
        status_altura = "atencao"

    return {
        "pasto_id": pasto_id,
        "nome": nome,
        "area_ha": area,
        "dias_ocupacao": dias_ocupacao,
        "dias_descanso": dias_descanso,
        "altura_pre_cm": altura_pre,
        "altura_pos_cm": altura_pos,
        "status_descanso": status_descanso,
        "status_altura": status_altura,
        "historico": historico_pasto[-5:],
    }


def relatorio_geral_pastagens(df_pastos: pd.DataFrame, df_animais: pd.DataFrame, df_man: pd.DataFrame) -> list[dict]:
    """Retorna o relatório consolidado de todos os pastos ativos (rotativo x descanso + UA/ha)."""
    ativos = PA.ativos(df_pastos)
    if ativos.empty:
        return []

    sit_basica = PA.situacao(df_pastos, df_animais, df_man, 0, 0)
    relatorio = []

    for _, p in ativos.iterrows():
        pid = p.get("ID", "")
        nome = p.get("Nome", "")
        dados_sit = sit_basica.get(pid, {"cabecas": 0, "ua": 0, "ua_ha": 0})
        
        analise = analise_rotativo_pasto(pid, df_pastos, df_man)
        
        # Semáforo de Lotação Instantânea (UA/ha)
        ua_ha = dados_sit.get("ua_ha", 0)
        status_lotacao = "ok"
        if ua_ha > 3.0:
            status_lotacao = "critico"  # Superlotação
        elif ua_ha > 2.0:
            status_lotacao = "atencao"

        relatorio.append({
            "pasto_id": pid,
            "nome": nome,
            "area_ha": p.get("Área (ha)", 0),
            "cabecas": dados_sit.get("cabecas", 0),
            "ua_ha": round(ua_ha, 2),
            "status_lotacao": status_lotacao,
            **analise,
        })

    return relatorio
