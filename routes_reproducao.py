#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas da Reprodução — Sítio Santo Antonio v5.3 + Onda 8.4 gráficos
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import db
import reproducao as R
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


def _grafico_composicao_reprodutivo(sit, df_animais):
    """Pizza: Composição (Coberta/Prenha/Vazia/Pariu). Onda 8.4.3"""
    try:
        if not sit:
            return None

        labels = ["Coberta", "Prenha", "Vazia", "Pariu"]
        data = [
            sum(1 for s in sit if s.get("status") == "coberta"),
            sum(1 for s in sit if s.get("status") == "prenha"),
            sum(1 for s in sit if s.get("status") == "vazia"),
            sum(1 for s in sit if s.get("status") == "pariu"),
        ]

        if sum(data) == 0:
            return None

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico composição reprodutivo falhou: {e}")
        return None


def _grafico_timeline_partos(sit):
    """Timeline: Próximos partos nos 285 dias (com foco próximos 90). Onda 8.4.4"""
    try:
        if not sit:
            return None

        hoje = _agora().date()

        # Agrupa prenhas por data prevista
        partos_por_data = {}
        for s in sit:
            if s.get("status") == "prenha" and s.get("parto_previsto"):
                data = pd.to_datetime(s["parto_previsto"]).date()
                dias_restantes = (data - hoje).days
                if 0 <= dias_restantes <= 285:
                    data_str = data.isoformat()
                    partos_por_data[data_str] = partos_por_data.get(data_str, 0) + 1

        if not partos_por_data:
            return None

        datas = sorted(partos_por_data.keys())
        labels = [pd.to_datetime(d).strftime("%d/%m") for d in datas]
        data = [partos_por_data[d] for d in datas]

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico timeline partos falhou: {e}")
        return None


@app.route("/reproducao")
@login_required
def reproducao():
    hoje = pd.Timestamp(_agora()).normalize()
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    sit = R.situacao(df_man, df_an, hoje)
    vacas = [A.ref(r) for _, r in A.vivos(df_an).iterrows()
             if A._txt(r.get("Sexo")).upper().startswith("F")]

    # Gráficos Onda 8.4
    grafico_composicao = _grafico_composicao_reprodutivo(sit, df_an)
    grafico_partos = _grafico_timeline_partos(sit)

    return render_template("reproducao.html", situacoes=sit,
                           ind=R.indicadores(sit, df_an),
                           alertas=R.alertas(sit, hoje), vacas=vacas,
                           grafico_composicao=grafico_composicao,
                           grafico_partos=grafico_partos,
                           hoje=f"{hoje:%Y-%m-%d}", resultados=R.RESULTADOS)


@app.route("/reproducao/registrar", methods=["POST"])
@login_required
def registrar_reproducao():
    _validar_csrf()
    f = request.form
    tipo = R.TIPO_DIAGNOSTICO if f.get("tipo") == "diagnostico" else R.TIPO_COBERTURA
    try:
        R.registrar(tipo, f.get("vaca", ""), f.get("data"), f.get("touro", ""),
                    f.get("resultado", ""), _membro_logado())
        fazer_backup_seguro()
        flash("🐮 Anotado!" if tipo == R.TIPO_COBERTURA else "🩺 Resultado anotado!",
              "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("reproducao"))
