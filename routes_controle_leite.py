#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_controle_leite.py — Rotas do Módulo de Controle Leiteiro (v5.24)
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
import db
import animais as A
from extensions import app, login_required, _agora, _validar_csrf
from routes_animais import _membro_logado, fazer_backup_seguro

@app.route("/leite/controle", methods=["GET", "POST"])
@login_required
def controle_leite():
    """Painel de Controle Leiteiro e produção diária."""
    df_animais = A.carregar()
    df_prod = db.carregar_aba("Leite Produção")
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    recentes = []
    if not df_prod.empty and "Data" in df_prod.columns:
        for _, row in df_prod.tail(20).iterrows():
            d = row.to_dict()
            dt = d.get("Data")
            if pd.notna(dt):
                d["Data"] = pd.to_datetime(dt).strftime("%d/%m/%Y")
            recentes.append(d)

    return render_template(
        "controle_leite.html",
        vacas=vivos,
        registros=recentes,
        hoje=_agora().strftime("%Y-%m-%d"),
    )


@app.route("/leite/controle/salvar", methods=["POST"])
@login_required
def salvar_controle_leiteiro():
    _validar_csrf()
    f = request.form
    vaca = f.get("vaca_id", "").strip()
    litros = f.get("litros", "").strip()
    ordenha = f.get("ordenha", "Total Dia").strip()
    data = f.get("data", _agora().strftime("%d/%m/%Y"))

    try:
        if not vaca or not litros:
            raise ValueError("Preencha a vaca/lote e os litros produzidos.")
        
        litros_val = float(str(litros).replace(",", "."))
        fazer_backup_seguro()

        linha = [
            data,
            vaca,
            "Individual",
            ordenha,
            litros_val,
            "", "", "", "",
            _agora().isoformat(),
        ]
        db.salvar_linha("Leite Produção", linha)
        flash(f"🥛 Registrado {litros_val} L para {vaca}!", "success")
    except ValueError as e:
        flash(f"❌ {e}", "error")

    return redirect(url_for("controle_leite"))
