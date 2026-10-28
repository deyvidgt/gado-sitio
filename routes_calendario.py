# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from calendar import monthrange, month_name

import pandas as pd
from flask import render_template, request, jsonify

from extensions import app, _get_dados_cache, login_required


def _data(valor):
    """Converte para timestamp, normalized."""
    d = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    return pd.NaT if pd.isna(d) else d.normalize()


def _texto(valor):
    """Converte para string segura."""
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def _tipo_manejo(tipo):
    """Classifica tipo de manejo."""
    t = _texto(tipo).lower()
    if "vacina" in t or "vermif" in t or "brucelose" in t:
        return "saude"
    if t in {"cobertura", "diagnóstico de gestação"}:
        return "reproducao"
    return "manejo"


def _urgencia(dias):
    """Retorna urgência por dias."""
    if dias is None:
        return "normal"
    if dias <= 3:
        return "urgente"
    if dias <= 7:
        return "aviso"
    return "normal"


def _eventos_mes(dados, mes, ano, hoje=None):
    """Retorna {data: [eventos]} para o mês especificado."""
    hoje = pd.Timestamp(hoje or date.today()).normalize()
    inicio = pd.Timestamp(year=ano, month=mes, day=1)
    fim = pd.Timestamp(year=ano, month=mes, day=1) + pd.DateOffset(months=1) - timedelta(days=1)

    resultado = {}

    # Manejo (saúde, reprodução)
    df_man = dados.get("Manejo", pd.DataFrame()) if dados else pd.DataFrame()
    if df_man is not None and not df_man.empty:
        for _, row in df_man.iterrows():
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            tipo = _tipo_manejo(row.get("Tipo"))
            titulo = _texto(row.get("Tipo")) or "Manejo"
            detalhe = _texto(row.get("Descrição")) or _texto(row.get("Produto"))
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": tipo, "titulo": titulo, "detalhes": detalhe,
                "urgencia": urg, "origem": "Manejo"
            })

    # Visitas
    df_vis = dados.get("Visitas", pd.DataFrame()) if dados else pd.DataFrame()
    if df_vis is not None and not df_vis.empty:
        for _, row in df_vis.iterrows():
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": "visita", "titulo": "Visita", "detalhes": _texto(row.get("Responsável")),
                "urgencia": urg, "origem": "Visitas"
            })

    # Tarefas
    df_tar = dados.get("Tarefas", pd.DataFrame()) if dados else pd.DataFrame()
    if df_tar is not None and not df_tar.empty:
        for _, row in df_tar.iterrows():
            if _texto(row.get("Feito Em")):
                continue
            d = _data(row.get("Data"))
            if pd.isna(d) or not (inicio <= d <= fim):
                continue
            dias = (d - hoje).days
            urg = _urgencia(dias)
            resultado.setdefault(d.date(), []).append({
                "tipo": "tarefa", "titulo": _texto(row.get("Título")),
                "detalhes": _texto(row.get("Responsável")),
                "urgencia": urg, "origem": "Tarefas"
            })

    return resultado


@app.route("/calendario")
@login_required
def calendario_pagina():
    """Mostra grid de calendário com eventos do mês."""
    # Pega mês/ano dos parâmetros ou usa hoje
    mes = request.args.get("mes", type=int, default=date.today().month)
    ano = request.args.get("ano", type=int, default=date.today().year)

    # Valida mês/ano
    mes = max(1, min(12, mes))
    ano = max(2020, min(2100, ano))

    dados = _get_dados_cache()

    # Busca eventos do mês
    eventos_por_dia = _eventos_mes(dados, mes, ano)

    # Monta grid: semanas com dias da semana
    hoje = date.today()
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
    data_inicio = date.today()
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
        mes=mes, ano=ano, mes_nome=month_name[mes],
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
    """Retorna eventos de um dia em JSON."""
    data_str = request.args.get("data", "")
    try:
        d = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"erro": "Data inválida"}), 400

    dados = _get_dados_cache()
    eventos_por_dia = _eventos_mes(dados, d.month, d.year)
    eventos = eventos_por_dia.get(d, [])

    return jsonify({"data": str(d), "eventos": eventos})
