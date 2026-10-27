# -*- coding: utf-8 -*-
"""Rotas do módulo de volumosos (feno, silo, etc)."""

from flask import render_template, request, redirect, url_for, flash
import volumosos as V
from db import carregar_aba, salvar_linha
from extensions import _agora, _validar_csrf, app, login_required


@app.route("/volumosos")
@login_required
def painel_volumosos():
    """Painel de volumosos com estoque, dias faltam e alertas."""
    hoje = _agora().date()
    situacao = V.situacao_volumosos(hoje=hoje)

    # Ordena por alerta (aviso primeiro)
    volumosos_ordenados = sorted(
        situacao.items(),
        key=lambda x: ({"aviso": 0, "ok": 1}.get(x[1]["alerta"], 2), x[0])
    )

    return render_template("volumosos.html", volumosos=volumosos_ordenados, hoje=hoje)


@app.route("/volumosos/lançar", methods=["GET", "POST"])
@login_required
def lancar_volumoso():
    """Formulário para lançar entrada de volumoso."""
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        tipo = str(f.get("tipo", "")).strip()
        data = f.get("data", "").strip()
        quantidade = str(f.get("quantidade", "")).strip()
        qualidade = str(f.get("qualidade", "")).strip()
        origem = str(f.get("origem", "")).strip()
        custo = str(f.get("custo", "")).strip()
        observacao = str(f.get("observacao", "")).strip()

        if not tipo or not data or not quantidade:
            flash("Preencha Tipo, Data e Quantidade.", "error")
            return redirect(url_for("lancar_volumoso"))

        linha = [
            data, tipo, quantidade, qualidade, origem, custo, observacao,
            "", _agora().isoformat()
        ]
        salvar_linha("Volumosos", linha)
        flash(f"{tipo} lançado com sucesso.", "success")
        return redirect(url_for("painel_volumosos"))

    return render_template("volumosos_lancar.html", hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/volumosos/consumo", methods=["GET", "POST"])
@login_required
def registrar_consumo():
    """Registrar consumo diário de volumoso."""
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        tipo = str(f.get("tipo", "")).strip()
        data = f.get("data", "").strip()
        quantidade = str(f.get("quantidade", "")).strip()
        local = str(f.get("local", "")).strip()
        observacao = str(f.get("observacao", "")).strip()

        if not tipo or not data or not quantidade:
            flash("Preencha Tipo, Data e Quantidade consumida.", "error")
            return redirect(url_for("registrar_consumo"))

        linha = [
            data, tipo, quantidade, local, observacao, "", _agora().isoformat()
        ]
        salvar_linha("Consumo Volumosos", linha)
        flash(f"Consumo de {tipo} registrado.", "success")
        return redirect(url_for("painel_volumosos"))

    # Tipos já usados (para sugestão)
    df_vol = carregar_aba("Volumosos")
    tipos_sugeridos = []
    if df_vol is not None and not df_vol.empty:
        tipos = df_vol.get("Tipo", []).dropna().unique()
        tipos_sugeridos = sorted([str(t).strip() for t in tipos if str(t).strip()])

    return render_template(
        "volumosos_consumo.html",
        tipos_sugeridos=tipos_sugeridos,
        hoje=_agora().strftime("%Y-%m-%d")
    )
