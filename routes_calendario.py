# -*- coding: utf-8 -*-
from datetime import date, datetime
from calendar import monthrange, month_name

from flask import render_template, request, jsonify

from extensions import app, _get_dados_cache, login_required
import calendario


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
    eventos_por_dia = calendario.eventos_mes(dados, mes, ano)

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

    return render_template(
        "calendario.html",
        mes=mes, ano=ano, mes_nome=month_name[mes],
        semanas=semanas,
        mes_ant=mes_ant, ano_ant=ano_ant,
        mes_prox=mes_prox, ano_prox=ano_prox,
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
    eventos_por_dia = calendario.eventos_mes(dados, d.month, d.year)
    eventos = eventos_por_dia.get(d, [])

    return jsonify({"data": str(d), "eventos": eventos})
