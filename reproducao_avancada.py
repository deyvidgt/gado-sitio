#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproducao_avancada.py — IATF, sincronização de cio, IEP otimizado (v5.12 Onda 12)

Estende reproducao.py com:
  • Protocolo IATF (GnRH → progesterona → PGF2α → inseminação)
  • Detecção de cio automática (observação manual + análise histórica)
  • Agendamento automático de coberturas
  • IEP (Intervalo Entre Partos) otimizado
  • Sugestões de descarte (culling) por IEP/taxa prenhez

Dados: Manejo tipos "Sincronização IATF", "Observação de Cio"
"""

from __future__ import annotations
from agora import agora

import pandas as pd
from datetime import datetime, timedelta
import logging

import reproducao as R
import animais as A

# ── Fases IATF (dias relativos ao dia 0 da sincronização) ──────────────────────
IATF_PROTOCOLO = {
    "GnRH_inicial": 0,           # Dia 0: aplicar GnRH
    "inserir_p4": 0,             # Dia 0: inserir progesterona
    "pgf2a": 7,                  # Dia 7: aplicar PGF2α
    "remover_p4": 8,             # Dia 8: remover progesterona
    "gnrh_final": 9,             # Dia 9: GnRH final
    "inseminacao": 9,            # Dia 9: inseminar (~16-20h após GnRH)
}

# ── Limites para alertas ────────────────────────────────────────────────────────
IEP_EXCELENTE = 365             # dias
IEP_BOM = 400                   # dias
IEP_RUIM = 420                  # dias (candidata culling)
TAXA_PRENHEZ_BOA = 0.75         # >= 75% em 3 tentativas
DIAS_CICLO_NORMAL = 21          # ciclo reprodutivo normal


def _eventos_iatf(df_man) -> list[tuple[pd.Timestamp, str, str]]:
    """[(data, id_animal, fase)] de todas as sincronizações IATF."""
    if df_man is None or df_man.empty or "Tipo" not in df_man.columns:
        return []

    df = df_man[(df_man["Tipo"] == "Sincronização IATF") & df_man["Data"].notna()]
    out = []
    for _, r in df.iterrows():
        d = pd.Timestamp(r["Data"]).normalize()
        fase = A._txt(r.get("Descrição", "")).strip() or "GnRH inicial"
        for i in A.ids_de(r.get("Brincos")):
            out.append((d, i, fase))
    out.sort(key=lambda e: e[0])
    return out


def _eventos_cio(df_man) -> list[tuple[pd.Timestamp, str, int]]:
    """[(data, id_animal, intensidade 1-5)] de observações de cio."""
    if df_man is None or df_man.empty or "Tipo" not in df_man.columns:
        return []

    df = df_man[(df_man["Tipo"] == "Observação de Cio") & df_man["Data"].notna()]
    out = []
    for _, r in df.iterrows():
        d = pd.Timestamp(r["Data"]).normalize()
        # Intensidade: tentar extrair número 1-5 da descrição
        desc = A._txt(r.get("Descrição", ""))
        intensidade = 3  # padrão
        for i in range(1, 6):
            if str(i) in desc:
                intensidade = i
                break
        for id_animal in A.ids_de(r.get("Brincos")):
            out.append((d, id_animal, intensidade))
    out.sort(key=lambda e: e[0])
    return out


def alertas_iatf(df_man, df_animais, hoje=None) -> list[dict]:
    """Alertas de IATF: "fazer GnRH hoje", "inseminar amanhã", etc.

    Retorna lista com:
    {
        "animal_id": "A0001",
        "animal_ref": "Amarelo 21 #A0001",
        "tipo_alerta": "gnrh_hoje" | "pgf2a_hoje" | "inseminacao_hoje" | "inseminacao_amanha",
        "mensagem": "Fazer GnRH hoje em Amarelo 21",
        "urgencia": "urgente" | "aviso",
        "data_acao": "2026-11-01",
    }
    """
    hoje = pd.Timestamp(hoje or pd.Timestamp(agora())).normalize()
    amanha = hoje + timedelta(days=1)
    alertas = []

    eventos = _eventos_iatf(df_man)
    nomes = {}
    if df_animais is not None and not df_animais.empty:
        nomes = {r["ID"]: A.ref(r) for _, r in df_animais.iterrows()}

    # Buscar sincronizações IATF ativas (iniciadas nos últimos 14 dias, próximas de inseminação)
    for data_inicio, animal_id, fase_inicial in eventos:
        if data_inicio > hoje:
            continue  # ainda não começou

        dias_desde_inicio = (hoje - data_inicio).days

        # Se iniciou há < 10 dias, pode ainda estar no protocolo
        if dias_desde_inicio <= 10:
            dias_até_fase = {}
            for fase, dia_relativo in IATF_PROTOCOLO.items():
                dias_até_fase[fase] = dia_relativo - dias_desde_inicio

            # Alertas para hoje
            for fase, dias_até in dias_até_fase.items():
                if dias_até == 0:
                    alertas.append({
                        "animal_id": animal_id,
                        "animal_ref": nomes.get(animal_id, animal_id),
                        "tipo_alerta": f"{fase}_hoje",
                        "mensagem": f"🩺 {nomes.get(animal_id, animal_id)}: fazer {_nome_fase_iatf(fase)} HOJE",
                        "urgencia": "urgente",
                        "data_acao": str(hoje.date()),
                    })

            # Alertas para amanhã
            for fase, dias_até in dias_até_fase.items():
                if dias_até == 1:
                    alertas.append({
                        "animal_id": animal_id,
                        "animal_ref": nomes.get(animal_id, animal_id),
                        "tipo_alerta": f"{fase}_amanha",
                        "mensagem": f"⏰ {nomes.get(animal_id, animal_id)}: preparar {_nome_fase_iatf(fase)} para amanhã",
                        "urgencia": "aviso",
                        "data_acao": str(amanha.date()),
                    })

    return alertas


def _nome_fase_iatf(fase: str) -> str:
    """Traduz nome da fase IATF para português amigável."""
    nomes = {
        "GnRH_inicial": "GnRH inicial",
        "inserir_p4": "inserir progesterona (P4)",
        "pgf2a": "aplicar PGF2α",
        "remover_p4": "remover progesterona",
        "gnrh_final": "GnRH final",
        "inseminacao": "inseminação",
    }
    return nomes.get(fase, fase)


def detectar_cios_proximos(df_man, df_animais, hoje=None, dias_proximos=7) -> list[dict]:
    """Detecta animais em cio nos próximos N dias baseado em histórico + ciclo normal.

    Retorna:
    {
        "animal_id": "A0001",
        "animal_ref": "Amarelo 21 #A0001",
        "tipo_alerta": "cio_observado" | "cio_previsto",
        "data_cio": "2026-11-02",
        "dias_desde_parto": 45,
        "intensidade_observada": 4,  # 1-5, None se previsto
        "mensagem": "Cio observado em Amarelo 21",
        "urgencia": "urgente" | "aviso",
    }
    """
    hoje = pd.Timestamp(hoje or pd.Timestamp(agora())).normalize()
    proxima_data = hoje + timedelta(days=dias_proximos)
    alertas = []

    cios_observados = _eventos_cio(df_man)
    nomes = {}
    if df_animais is not None and not df_animais.empty:
        nomes = {r["ID"]: A.ref(r) for _, r in df_animais.iterrows()}

    # 1. Cios já observados
    cios_por_animal = {}
    for data, animal_id, intensidade in cios_observados:
        if hoje <= data <= proxima_data:
            if animal_id not in cios_por_animal or data > cios_por_animal[animal_id][0]:
                cios_por_animal[animal_id] = (data, intensidade)

    for animal_id, (data, intensidade) in cios_por_animal.items():
        alertas.append({
            "animal_id": animal_id,
            "animal_ref": nomes.get(animal_id, animal_id),
            "tipo_alerta": "cio_observado",
            "data_cio": str(data.date()),
            "intensidade_observada": intensidade,
            "mensagem": f"🔥 Cio observado em {nomes.get(animal_id, animal_id)} (intensidade {intensidade}/5)",
            "urgencia": "urgente" if intensidade >= 4 else "aviso",
        })

    # 2. Cios previstos (ciclo de 21 dias)
    ultimo_cio = {}
    for data, animal_id, intensidade in reversed(cios_observados):
        if animal_id not in ultimo_cio and data <= hoje:
            ultimo_cio[animal_id] = data

    for animal_id, data_ultimo_cio in ultimo_cio.items():
        dias_desde = (hoje - data_ultimo_cio).days
        # Se passou 15-28 dias, próximo cio deve estar próximo
        if 15 <= dias_desde <= 28:
            dias_até_proximo = DIAS_CICLO_NORMAL - (dias_desde % DIAS_CICLO_NORMAL)
            data_proximo_cio = hoje + timedelta(days=dias_até_proximo)
            if data_proximo_cio <= proxima_data:
                alertas.append({
                    "animal_id": animal_id,
                    "animal_ref": nomes.get(animal_id, animal_id),
                    "tipo_alerta": "cio_previsto",
                    "data_cio": str(data_proximo_cio.date()),
                    "dias_desde_parto": dias_desde,
                    "intensidade_observada": None,
                    "mensagem": f"⏰ Próximo cio previsto em {nomes.get(animal_id, animal_id)} ({data_proximo_cio.strftime('%d/%m')})",
                    "urgencia": "aviso",
                })

    return sorted(alertas, key=lambda x: x["data_cio"])


def iep_por_vaca(df_man, df_animais) -> dict[str, dict]:
    """Calcula IEP (Intervalo Entre Partos) por vaca.

    Retorna:
    {
        "A0001": {
            "animal_ref": "Amarelo 21 #A0001",
            "partos": [data1, data2, ...],  # datas de parto (em ordem)
            "iep_dias": [dias_entre_1_2, dias_entre_2_3, ...],
            "iep_media": 385,
            "iep_status": "excelente" | "bom" | "ruim",
            "recomendacao": "manter" | "investigar" | "culling",
        }
    }
    """
    partos = R._partos(df_animais)
    nomes = {}
    if df_animais is not None and not df_animais.empty:
        nomes = {r["ID"]: A.ref(r) for _, r in df_animais.iterrows()}

    out = {}
    for vaca_id, datas_parto in partos.items():
        if not datas_parto or len(datas_parto) < 2:
            continue  # precisa de 2+ partos para calcular IEP

        datas_parto = sorted(datas_parto)
        ieps = []
        for i in range(1, len(datas_parto)):
            dias = (datas_parto[i] - datas_parto[i-1]).days
            ieps.append(dias)

        media_iep = sum(ieps) / len(ieps) if ieps else 0

        # Status baseado na média
        if media_iep <= IEP_EXCELENTE:
            status = "excelente"
            recomendacao = "manter"
        elif media_iep <= IEP_BOM:
            status = "bom"
            recomendacao = "manter"
        elif media_iep < IEP_RUIM:
            status = "ruim"
            recomendacao = "investigar"
        else:
            status = "crítico"
            recomendacao = "culling"

        out[vaca_id] = {
            "animal_ref": nomes.get(vaca_id, vaca_id),
            "partos": datas_parto,
            "iep_dias": ieps,
            "iep_media": round(media_iep, 1),
            "iep_status": status,
            "recomendacao": recomendacao,
        }

    return out


def taxa_prenhez(df_man, animal_id: str, ultimas_coberturas=3) -> dict:
    """Taxa de prenhez: quantos diagnósticos "Prenha" em N coberturas recentes.

    Retorna:
    {
        "animal_id": "A0001",
        "coberturas_analisadas": 3,
        "prenhas": 2,
        "taxa": 0.67,  # 67%
        "status": "boa" | "média" | "ruim",
    }
    """
    eventos_cobertura = R._eventos(df_man, R.TIPO_COBERTURA)
    eventos_diagnostico = R._eventos(df_man, R.TIPO_DIAGNOSTICO)

    # Filtra coberturas do animal
    coberturas_animal = [(d, prod) for d, i, _, prod in eventos_cobertura if i == animal_id]

    if not coberturas_animal:
        return {
            "animal_id": animal_id,
            "coberturas_analisadas": 0,
            "prenhas": 0,
            "taxa": 0,
            "status": "sem_dados",
        }

    # Pega últimas N coberturas
    coberturas_analisadas = coberturas_animal[-ultimas_coberturas:]
    prenhas = 0

    for data_cobertura, _ in coberturas_analisadas:
        # Busca diagnóstico APÓS essa cobertura
        for d, i, desc, _ in eventos_diagnostico:
            if i == animal_id and d > data_cobertura:
                if R._resultado(desc) == "Prenha":
                    prenhas += 1
                break  # só conta o primeiro diagnóstico após essa cobertura

    taxa = prenhas / len(coberturas_analisadas) if coberturas_analisadas else 0

    if taxa >= TAXA_PRENHEZ_BOA:
        status = "boa"
    elif taxa >= 0.5:
        status = "média"
    else:
        status = "ruim"

    return {
        "animal_id": animal_id,
        "coberturas_analisadas": len(coberturas_analisadas),
        "prenhas": prenhas,
        "taxa": round(taxa, 2),
        "status": status,
    }


def sugestoes_culling(df_man, df_animais) -> list[dict]:
    """Sugere vacas para descarte (culling) baseado em IEP + taxa prenhez.

    Retorna:
    [
        {
            "animal_id": "A0001",
            "animal_ref": "Amarelo 21 #A0001",
            "motivo": "IEP crítico (450 dias)",
            "score_culling": 85,  # 0-100, quanto maior mais urgente
            "dados": {...},  # IEP, taxa prenhez, etc
        }
    ]
    """
    ieps = iep_por_vaca(df_man, df_animais)
    sugestoes = []

    for vaca_id, dados_iep in ieps.items():
        if dados_iep["recomendacao"] != "culling":
            continue

        taxa = taxa_prenhez(df_man, vaca_id)

        score = 0
        motivos = []

        # IEP crítico = +50 pontos
        if dados_iep["iep_media"] > IEP_RUIM:
            score += 50
            motivos.append(f"IEP crítico ({dados_iep['iep_media']} dias, meta < 400)")

        # Taxa prenhez ruim = +40 pontos
        if taxa["taxa"] < 0.5:
            score += 40
            motivos.append(f"Taxa prenhez baixa ({int(taxa['taxa']*100)}% em {taxa['coberturas_analisadas']} coberturas)")

        # Capricharam demais = +10 pontos (quanto mais coberturas sem resultar em prenhez)
        if taxa["coberturas_analisadas"] >= 3 and taxa["taxa"] == 0:
            score += 10
            motivos.append("Histórico negativo (3+ coberturas sem prenhez)")

        sugestoes.append({
            "animal_id": vaca_id,
            "animal_ref": dados_iep["animal_ref"],
            "motivo": " + ".join(motivos),
            "score_culling": min(score, 100),
            "dados": {**dados_iep, **taxa},
        })

    return sorted(sugestoes, key=lambda x: x["score_culling"], reverse=True)


