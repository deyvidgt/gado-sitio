#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_agenda_unificada.py — Agenda Unificada (Calendário + Tarefas) v5.10
"""

from flask import render_template, request
from extensions import app, login_required, _get_dados_cache, fmt_data
from tarefas import carregar as tarefas_carregar, pendentes as tarefas_pendentes
from routes_calendario import _eventos_mes
from config import REPETICOES_TAREFA, NOMES_MEMBROS, MEMBROS
from datetime import date, datetime, timedelta
from calendar import monthrange
import pandas as pd


def _agora():
    return datetime.now()


@app.route("/agenda")
@login_required
def agenda_unificada():
    """Página unificada: calendário + tarefas + eventos operacionais."""
    dados = _get_dados_cache()

    # Pega mês/ano dos parâmetros
    mes = request.args.get("mes", type=int, default=date.today().month)
    ano = request.args.get("ano", type=int, default=date.today().year)

    mes = max(1, min(12, mes))
    ano = max(2020, min(2100, ano))

    hoje = date.today()

    # Eventos do mês
    eventos_por_dia = _eventos_mes(dados, mes, ano)

    # Gera grid de calendário
    primeiro_dia, dias_mes = monthrange(ano, mes)
    semanas = []
    semana_atual = [None] * primeiro_dia

    for dia in range(1, dias_mes + 1):
        d = date(ano, mes, dia)
        info = {
            "dia": dia,
            "data": d,
            "eventos": eventos_por_dia.get(d, []),
            "hoje": d == hoje,
        }
        semana_atual.append(info)
        if len(semana_atual) == 7:
            semanas.append(semana_atual)
            semana_atual = []

    if semana_atual:
        semana_atual.extend([None] * (7 - len(semana_atual)))
        semanas.append(semana_atual)

    # Tarefas
    df_tarefas = tarefas_carregar()
    hoje_ts = pd.Timestamp(_agora()).normalize()
    tarefas_pend = tarefas_pendentes(df_tarefas, hoje_ts, limite_dias=365)

    # Próximos 14 dias
    proximos = []
    para_data = hoje
    for _ in range(14):
        if para_data in eventos_por_dia:
            for evt in eventos_por_dia[para_data]:
                proximos.append({
                    "data": para_data,
                    "tipo": "evento",
                    "titulo": evt.get("titulo"),
                    "icon": evt.get("icon", "📌"),
                    "status": evt.get("status")
                })
        para_data += timedelta(days=1)

    # Adiciona tarefas
    for tarefa in tarefas_pend[:20]:
        try:
            data_tar = pd.Timestamp(tarefa.get("data")).date() if tarefa.get("data") else None
            if data_tar and 0 <= (data_tar - hoje).days <= 14:
                proximos.append({
                    "data": data_tar,
                    "tipo": "tarefa",
                    "titulo": tarefa.get("titulo"),
                    "id": tarefa.get("id"),
                    "icon": "📋",
                    "responsavel": tarefa.get("responsavel")
                })
        except:
            pass

    proximos.sort(key=lambda x: x["data"])

    return render_template("agenda_unificada.html",
                          mes=mes, ano=ano, hoje=hoje,
                          semanas=semanas,
                          tarefas_pendentes=tarefas_pend[:10],
                          proximos_14_dias=proximos[:20],
                          fmt_data=fmt_data)
