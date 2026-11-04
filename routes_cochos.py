#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Cochos (comedouros) — Integração com Visitas e Edição/Exclusão Robustas (v5.19)
"""

from flask import render_template, request, redirect, url_for, flash, abort
from datetime import datetime

import cochos as CO
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache)
from routes_animais import _membro_logado, fazer_backup_seguro


def _preparar_para_editar(df):
    # carregar_aba infere float64 em colunas de texto vazias; gravar string
    # nela dispara FutureWarning (vira erro em pandas futuro). Força object.
    return df.astype(object)


@app.route("/cochos")
@login_required
def cochos():
    """Dashboard visual dos cochos: volume, consumo, próxima salga."""
    dados = _get_dados_cache()
    df_cochos = CO.carregar()
    df_visitas = dados.get("Visitas")
    if df_visitas is None:
        df_visitas = __import__("db").carregar_aba("Visitas")

    sit = CO.calcular_situacao_cochos(df_cochos, df_visitas)
    resumo = CO.resumo_cochos(df_cochos, df_visitas)

    # Prepara lista para template (ordenada por dias restantes)
    lista = []
    for _, cocho in df_cochos.iterrows():
        cocho_id = str(cocho.get("ID", "")).strip()
        if cocho_id not in sit:
            continue

        info = sit.get(cocho_id, {})
        lista.append({
            "id": cocho_id,
            "nome": str(cocho.get("Nome", "")),
            "tipo": str(cocho.get("Tipo", "")),
            "local": str(cocho.get("Local", "")),
            "capacidade": cocho.get("Capacidade (kg)", 0),
            "volume_atual": cocho.get("Volume Atual (kg)", 0),
            "observacoes": str(cocho.get("Observações", "")),
            "ativo": str(cocho.get("Ativo", "Sim")),
            **info
        })

    # Ordena por dias restantes
    lista.sort(key=lambda x: (x.get("dias_restantes") or 999))

    return render_template("cochos.html", cochos=lista, resumo=resumo, hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/cochos/novo", methods=["POST"])
@login_required
def novo_cocho():
    """Cria novo cocho."""
    _validar_csrf()
    try:
        from db import salvar_linha
        linha = [
            request.form.get("id", "").strip(),  # ID
            request.form.get("nome", "").strip(),  # Nome
            request.form.get("tipo", "").strip(),  # Tipo
            request.form.get("local", "").strip(),  # Local
            request.form.get("capacidade", ""),  # Capacidade (kg)
            request.form.get("volume_atual", ""),  # Volume Atual (kg)
            request.form.get("ultima_salga", ""),  # Última Salga
            request.form.get("observacoes", ""),  # Observações
            "Sim",  # Ativo
            _membro_logado(),  # Criado Por
        ]
        salvar_linha("Cochos", linha)
        flash("🍽️ Cocho registrado!", "success")
        fazer_backup_seguro()
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("cochos"))


@app.route("/cochos/salgar/<cocho_id>", methods=["POST"])
@login_required
def salgar_cocho(cocho_id):
    """Registra salga (reposição) do cocho com dados do modal."""
    _validar_csrf()
    try:
        from db import reescrever_aba
        df = _preparar_para_editar(CO.carregar())

        cocho = df[df["ID"].astype(str) == str(cocho_id)]
        if cocho.empty:
            abort(404)

        cocho_idx = df[df["ID"].astype(str) == str(cocho_id)].index[0]

        data_str = request.form.get("data", "").strip()
        if data_str and "-" in data_str:
            try:
                dt_obj = datetime.strptime(data_str, "%Y-%m-%d")
                data_str = dt_obj.strftime("%d/%m/%Y")
            except ValueError:
                data_str = _agora().strftime("%d/%m/%Y")
        else:
            data_str = _agora().strftime("%d/%m/%Y")

        volume_recarregado = request.form.get("volume", "")

        df.at[cocho_idx, "Última Salga"] = data_str
        df.at[cocho_idx, "Volume Atual (kg)"] = volume_recarregado

        reescrever_aba("Cochos", df)
        flash(f"✨ Cocho salgado com sucesso em {data_str}!", "success")
        fazer_backup_seguro()
    except Exception as e:
        flash(f"Erro ao registrar salga: {e}", "error")

    return redirect(url_for("cochos"))


@app.route("/cochos/editar/<cocho_id>", methods=["POST", "GET"])
@login_required
def editar_cocho(cocho_id):
    """Edita dados do cocho."""
    if request.method == "GET":
        return redirect(url_for("cochos"))
    _validar_csrf()
    try:
        from db import reescrever_aba
        df = _preparar_para_editar(CO.carregar())

        cocho = df[df["ID"].astype(str) == str(cocho_id)]
        if cocho.empty:
            abort(404)

        cocho_idx = cocho.index[0]
        df.at[cocho_idx, "Nome"] = request.form.get("nome", "").strip()
        df.at[cocho_idx, "Tipo"] = request.form.get("tipo", "").strip()
        df.at[cocho_idx, "Local"] = request.form.get("local", "").strip()
        df.at[cocho_idx, "Capacidade (kg)"] = request.form.get("capacidade", "")
        df.at[cocho_idx, "Volume Atual (kg)"] = request.form.get("volume_atual", "")
        df.at[cocho_idx, "Observações"] = request.form.get("observacoes", "")
        df.at[cocho_idx, "Ativo"] = request.form.get("ativo", "Sim")

        reescrever_aba("Cochos", df)
        flash("✏️ Cocho atualizado com sucesso!", "success")
        fazer_backup_seguro()
    except Exception as e:
        flash(f"Erro ao editar cocho: {e}", "error")

    return redirect(url_for("cochos"))


@app.route("/cochos/deletar/<cocho_id>", methods=["POST", "GET"])
@app.route("/cochos/excluir/<cocho_id>", methods=["POST", "GET"])
@login_required
def deletar_cocho(cocho_id):
    """Marca cocho como inativo (soft delete) ou remove definitivamente."""
    if request.method == "GET":
        return redirect(url_for("cochos"))
    _validar_csrf()
    try:
        from db import reescrever_aba
        df = _preparar_para_editar(CO.carregar())

        cocho = df[df["ID"].astype(str) == str(cocho_id)]
        if cocho.empty:
            abort(404)

        cocho_idx = cocho.index[0]
        # Remove fisicamente ou marca como Inativo
        df.at[cocho_idx, "Ativo"] = "Não"

        reescrever_aba("Cochos", df)
        flash("🗑️ Cocho removido com sucesso!", "success")
        fazer_backup_seguro()
    except Exception as e:
        flash(f"Erro ao remover cocho: {e}", "error")

    return redirect(url_for("cochos"))
