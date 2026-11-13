#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_precisao.py — Módulos Avançados de Zootecnia de Precisão (v5.30)
1. Indicadores de Nutrição e Lotes (Ruminação, Ócio, Refeições, Comportamento)
2. Estoque de Animais e Lotação por UA/ha
3. Alertas Avançados (Cio, Parto, Enfermaria com Gravidade)
4. Calendário Sanitário e Histórico
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
import db
import animais as A
import pastos as PA
import reproducao as R
import enfermaria as ENF
from extensions import app, login_required, _agora

@app.route("/nutricao/indicadores")
@login_required
def nutricao_indicadores():
    """Painel de Indicadores de Nutrição e Lotes (Comportamento e Bem-estar)."""
    return render_template("nutricao_indicadores.html")


@app.route("/animais/estoque")
@login_required
def animais_estoque_lotacao():
    """Painel de Estoque de Animais e Lotação por UA/ha."""
    df_animais = A.carregar()
    df_pastos = PA.carregar()
    df_man = db.carregar_aba("Manejo")

    # Categorias para gráfico de pizza/rosca
    categorias = {}
    faixas_etarias = {"Até 12 meses": 0, "12 a 24 meses": 0, "Mais de 24 meses": 0}

    if not df_animais.empty:
        vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"]
        for _, r in vivos.iterrows():
            cat = str(r.get("Categoria", "Outros")).strip() or "Outros"
            categorias[cat] = categorias.get(cat, 0) + 1

            # Faixa etária estimada por nascimento
            nasc = pd.to_datetime(r.get("Nascimento"), dayfirst=True, errors="coerce")
            if pd.notna(nasc):
                meses = (_agora() - nasc).days / 30.44
                if meses <= 12:
                    faixas_etarias["Até 12 meses"] += 1
                elif meses <= 24:
                    faixas_etarias["12 a 24 meses"] += 1
                else:
                    faixas_etarias["Mais de 24 meses"] += 1
            else:
                faixas_etarias["Mais de 24 meses"] += 1

    # Lotação por piquete
    sit_pastos = PA.situacao(df_pastos, df_animais, df_man, 0, 0)

    return render_template(
        "animais_estoque.html",
        categorias=categorias,
        faixas_etarias=faixas_etarias,
        sit_pastos=sit_pastos,
    )


@app.route("/reproducao/cio-parto")
@login_required
def reproducao_cio_parto():
    """Painel unificado de Alertas de Cio, Parto e Enfermaria Avançada."""
    hoje = pd.Timestamp(_agora()).normalize()
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    sit = R.situacao(df_man, df_an, hoje)
    
    # Próximos partos (nos próximos 45 dias)
    partos_proximos = []
    for s in sit:
        if s.get("status") == "prenha" and s.get("parto_previsto"):
            dt = pd.to_datetime(s["parto_previsto"]).date()
            dias = (dt - hoje.date()).days
            if 0 <= dias <= 45:
                partos_proximos.append({**s, "dias_restantes": dias})

    tratamento = ENF.animais_em_tratamento()

    return render_template(
        "cio_parto_enfermaria.html",
        partos_proximos=partos_proximos,
        tratamento=tratamento,
        situacoes=sit,
    )


@app.route("/sanitario/calendario")
@login_required
def calendario_sanitario():
    """Calendário Sanitário Mensal com código de cores."""
    df_man = db.carregar_aba("Manejo")
    hoje = _agora().date()

    eventos = []
    if not df_man.empty and "Data" in df_man.columns:
        for _, r in df_man.iterrows():
            tipo = str(r.get("Tipo", ""))
            if "Sanitário" in tipo or "Vacina" in tipo or "Tratamento" in tipo:
                dt = pd.to_datetime(r.get("Data"), dayfirst=True, errors="coerce")
                if pd.notna(dt):
                    dias = (dt.date() - hoje).days
                    status = "atrasado" if dias < 0 else ("proximo" if dias <= 7 else "ok")
                    eventos.append({
                        "data": dt.strftime("%d/%m/%Y"),
                        "tipo": tipo,
                        "descricao": r.get("Descrição"),
                        "status": status,
                    })

    return render_template("calendario_sanitario.html", eventos=eventos)
