#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_relatorios_graficos.py — Relatórios gráficos de rebanho e vacinação (v5.25)
- Gráficos de rosca/pizza (rebanho por categoria, gênero, status reprodutivo)
- Relatório de vacinação organizado em Atraso (Overdue), Próxima Semana (Next Week) e Próximo Mês (Next Month)
"""
from flask import render_template
import pandas as pd
from datetime import datetime, timedelta
import db
import animais as A
from extensions import app, login_required, _agora

@app.route("/relatorios/graficos-rebanho")
@login_required
def relatorios_graficos_rebanho():
    """Painel de relatórios gráficos do rebanho e vacinação."""
    df_animais = A.carregar()
    df_man = db.carregar_aba("Manejo")
    hoje = _agora().date()

    # Contagens por categoria
    categorias = {}
    generos = {"Macho": 0, "Fêmea": 0}
    status_repro = {"Prenha": 0, "Vazia/Aberta": 0, "Outros": 0}

    if not df_animais.empty:
        vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"]
        for _, r in vivos.iterrows():
            cat = str(r.get("Categoria", "Outros")).strip() or "Outros"
            categorias[cat] = categorias.get(cat, 0) + 1

            sexo = str(r.get("Sexo", "")).strip().upper()
            if sexo.startswith("F"):
                generos["Fêmea"] += 1
            else:
                generos["Macho"] += 1

    # Vacinação / Manejos: Overdue, Next Week, Next Month
    vacinacao_atrasada = []
    vacinacao_proxima_semana = []
    vacinacao_proximo_mes = []

    if not df_man.empty and "Data" in df_man.columns:
        for _, r in df_man.iterrows():
            if "Sanitário" in str(r.get("Tipo", "")) or "Vacina" in str(r.get("Descrição", "")):
                dt = pd.to_datetime(r.get("Data"), dayfirst=True, errors="coerce")
                if pd.notna(dt):
                    dias_diff = (dt.date() - hoje).days
                    item = {
                        "data": dt.strftime("%d/%m/%Y"),
                        "tipo": r.get("Tipo"),
                        "descricao": r.get("Descrição"),
                    }
                    if dias_diff < 0:
                        vacinacao_atrasada.append(item)
                    elif 0 <= dias_diff <= 7:
                        vacinacao_proxima_semana.append(item)
                    elif 8 <= dias_diff <= 30:
                        vacinacao_proximo_mes.append(item)

    return render_template(
        "relatorios_graficos.html",
        categorias=categorias,
        generos=generos,
        vacinacao_atrasada=vacinacao_atrasada,
        vacinacao_proxima_semana=vacinacao_proxima_semana,
        vacinacao_proximo_mes=vacinacao_proximo_mes,
    )
