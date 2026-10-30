# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from calendar import monthrange, month_name

import pandas as pd
from flask import render_template, request, jsonify

from db import carregar_aba
from extensions import app, _get_dados_cache, login_required, _safe, _agora

# Tradução de meses para português
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# Tradução de dias da semana para português
DIAS_SEMANA_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _iso(ts):
    """Converte timestamp para string ISO (YYYY-MM-DD)."""
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%Y-%m-%d")
    return None


def _txt(v) -> str:
    """Texto de célula sem 'nan'/None."""
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def _urgencia(dias):
    """Retorna urgência por dias (eventos passados são 'normal')."""
    if dias is None or dias < 0:  # Passado ou sem data
        return "normal"
    if dias <= 3:
        return "urgente"
    if dias <= 7:
        return "aviso"
    return "normal"


def _eventos_mes(mes, ano, hoje=None):
    """Retorna {data: [eventos]} para o mês especificado, unificado com API manejo."""
    hoje = pd.Timestamp(_agora()) if hoje is None else pd.Timestamp(hoje)
    hoje_norm = hoje.normalize()

    inicio = pd.Timestamp(year=ano, month=mes, day=1)
    fim = pd.Timestamp(year=ano, month=mes, day=1) + pd.DateOffset(months=1) - timedelta(days=1)

    resultado = {}

    # ── Manejo ──────────────────────────────────────────────────────────────
    df_man = carregar_aba("Manejo")
    if not df_man.empty and "Data" in df_man.columns:
        for _, row in df_man[df_man["Data"].notna() & (df_man["Data"] >= inicio)].iterrows():
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            tipo = _txt(row.get("Tipo", "") or "")
            dias = (d - hoje_norm).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "categoria": "manejo",
                "tipo": tipo,
                "titulo": tipo or "Manejo",
                "detalhes": " · ".join(x for x in (
                    _txt(row.get("Produto")), _txt(row.get("Descrição"))) if x),
                "urgencia": urg,
                "cabecas": int(_safe(row.get("Qtd Cabeças"))),
            })

    # ── Visitas ──────────────────────────────────────────────────────────────
    df_vis = carregar_aba("Visitas")
    if not df_vis.empty and "Data" in df_vis.columns:
        for _, row in df_vis[df_vis["Data"].notna() & (df_vis["Data"] >= inicio)].iterrows():
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje_norm).days
            urg = _urgencia(dias)
            resp = _txt(row.get("Responsável", "") or "")
            resultado.setdefault(d.date(), []).append({
                "categoria": "visita",
                "tipo": "Visita",
                "titulo": f"Visita — {resp}" if resp else "Visita",
                "detalhes": resp,
                "urgencia": urg,
                "cabecas": int(_safe(row.get("Gado Contado"))),
            })

    # ── Compras ──────────────────────────────────────────────────────────────
    df_comp = carregar_aba("Compras")
    if not df_comp.empty and "Data" in df_comp.columns:
        for _, row in df_comp[df_comp["Data"].notna() & (df_comp["Data"] >= inicio)].iterrows():
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            qtd = int(_safe(row.get("Qtd Cabeças")))
            resultado.setdefault(d.date(), []).append({
                "categoria": "compra",
                "tipo": "Compra",
                "titulo": f"Compra — {qtd} cab.",
                "detalhes": _txt(row.get("Descrição", "") or ""),
                "urgencia": "normal",
                "cabecas": qtd,
            })

    # ── Vendas ───────────────────────────────────────────────────────────────
    df_vend = carregar_aba("Vendas")
    if not df_vend.empty and "Data" in df_vend.columns:
        for _, row in df_vend[df_vend["Data"].notna() & (df_vend["Data"] >= inicio)].iterrows():
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            qtd = int(_safe(row.get("Qtd Cabeças")))
            resultado.setdefault(d.date(), []).append({
                "categoria": "venda",
                "tipo": "Venda",
                "titulo": f"Venda — {qtd} cab.",
                "detalhes": _txt(row.get("Descrição", "") or ""),
                "urgencia": "normal",
                "cabecas": qtd,
            })

    # ── Gastos ───────────────────────────────────────────────────────────────
    df_gast = carregar_aba("Gastos")
    if not df_gast.empty and "Data" in df_gast.columns:
        for _, row in df_gast[df_gast["Data"].notna() & (df_gast["Data"] >= inicio)].iterrows():
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            tipo = _txt(row.get("Tipo", "") or "")
            desc = _txt(row.get("Descrição", "") or "")
            label = tipo or desc or "Gasto"
            resultado.setdefault(d.date(), []).append({
                "categoria": "gasto",
                "tipo": "Gasto",
                "titulo": label[:25],
                "detalhes": desc if desc and desc != tipo else "",
                "urgencia": "normal",
                "cabecas": 0,
            })

    # ── Tarefas (pendentes) ──────────────────────────────────────────────────
    df_tar = carregar_aba("Tarefas")
    if not df_tar.empty and "Data" in df_tar.columns:
        for _, row in df_tar[df_tar["Data"].notna() & (df_tar["Data"] >= inicio)].iterrows():
            # Pular tarefas já concluídas
            if _txt(row.get("Feito Em")):
                continue
            d = pd.Timestamp(row.get("Data")).normalize() if pd.notna(row.get("Data")) else pd.NaT
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje_norm).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "categoria": "tarefa",
                "tipo": "Tarefa",
                "titulo": _txt(row.get("Título")),
                "detalhes": _txt(row.get("Responsável", "") or ""),
                "urgencia": urg,
                "cabecas": 0,
            })

    return resultado


@app.route("/calendario")
@login_required
def calendario_pagina():
    """Mostra grid de calendário com eventos do mês."""
    # Pega mês/ano dos parâmetros ou usa hoje
    mes = request.args.get("mes", type=int, default=_agora().date().month)
    ano = request.args.get("ano", type=int, default=_agora().date().year)

    # Valida mês/ano
    mes = max(1, min(12, mes))
    ano = max(2020, min(2100, ano))

    # Busca eventos do mês (unificado com API manejo)
    eventos_por_dia = _eventos_mes(mes, ano)

    # Monta grid: semanas com dias da semana
    hoje = _agora().date()
    primeiro_dia, dias_mes = monthrange(ano, mes)

    # Cria lista de semanas [0-6], sendo 0=seg, 6=dom
    semanas = []
    semana_atual = [None] * primeiro_dia  # preenche os dias antes do 1º

    for dia in range(1, dias_mes + 1):
        d = date(ano, mes, dia)
        info = {
            "dia": dia,
            "data": d,
            "eventos": eventos_por_dia.get(d, []),
            "hoje": d == hoje,
            "proxima_data": d > hoje,
            "passada_data": d < hoje
        }
        semana_atual.append(info)
        if len(semana_atual) == 7:
            semanas.append(semana_atual)
            semana_atual = []

    # Completa última semana se houver dias
    if semana_atual:
        while len(semana_atual) < 7:
            semana_atual.append(None)
        semanas.append(semana_atual)

    # Nav mês anterior/próximo
    if mes == 1:
        mes_ant = 12
        ano_ant = ano - 1
    else:
        mes_ant = mes - 1
        ano_ant = ano

    if mes == 12:
        mes_prox = 1
        ano_prox = ano + 1
    else:
        mes_prox = mes + 1
        ano_prox = ano

    # Todos os eventos do mês (ordenados por data)
    todos_eventos = []
    for d, evts in sorted(eventos_por_dia.items()):
        for evt in evts:
            todos_eventos.append({
                "tipo": evt.get("tipo", ""),
                "titulo": evt.get("titulo", ""),
                "data": d,
                "urgencia": evt.get("urgencia", "normal")
            })

    # Próximos 7 dias
    proximos_7_dias = []
    data_inicio = _agora().date()
    data_fim = data_inicio + timedelta(days=7)
    for d in sorted(eventos_por_dia.keys()):
        if data_inicio <= d < data_fim:
            for evt in eventos_por_dia[d]:
                proximos_7_dias.append({
                    "tipo": evt.get("tipo", ""),
                    "titulo": evt.get("titulo", ""),
                    "data": d,
                    "urgencia": evt.get("urgencia", "normal")
                })

    return render_template(
        "calendario.html",
        mes=mes, ano=ano, mes_nome=MESES_PT.get(mes, month_name[mes]),
        semanas=semanas,
        mes_ant=mes_ant, ano_ant=ano_ant,
        mes_prox=mes_prox, ano_prox=ano_prox,
        todos_eventos=todos_eventos,
        proximos_7_dias=proximos_7_dias,
        tipo=""
    )


@app.route("/api/calendario/eventos")
@login_required
def api_calendario_eventos():
    """Retorna eventos de um dia em JSON (unificado com API manejo)."""
    data_str = request.args.get("data", "")
    try:
        d = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"erro": "Data inválida"}), 400

    eventos_por_dia = _eventos_mes(d.month, d.year)
    eventos = eventos_por_dia.get(d, [])

    return jsonify({"data": str(d), "eventos": eventos})
