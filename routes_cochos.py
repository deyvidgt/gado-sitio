#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Cochos (comedouros) — Integração com Visitas e Edição/Exclusão Robustas (v5.19)
"""

from flask import render_template, request, redirect, url_for, flash, abort
from datetime import datetime
import uuid

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
    from models import Insumo
    dados = _get_dados_cache()
    df_cochos = CO.carregar()
    df_visitas = dados.get("Visitas")
    if df_visitas is None:
        df_visitas = __import__("db").carregar_aba("Visitas")

    movimentos = CO.carregar_movimentos()
    sit = CO.calcular_situacao_cochos(df_cochos, df_visitas, movimentos)
    resumo = CO.resumo_cochos(df_cochos, df_visitas, movimentos)

    insumos_db = Insumo.query.all()
    lista_insumos = [{
        "id": i.id,
        "nome": i.nome,
        "peso_saco": i.peso_saco or 25.0,
        "quantidade": i.quantidade or 0.0
    } for i in insumos_db]

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

    return render_template("cochos.html", cochos=lista, resumo=resumo, insumos_estoque=lista_insumos, hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/cochos/novo", methods=["POST"])
@login_required
def novo_cocho():
    """Cria novo cocho."""
    _validar_csrf()
    try:
        from db import carregar_aba, reescrever_aba, salvar_linha
        cocho_id = request.form.get("id", "").strip()
        if not cocho_id:
            flash("Informe um ID para o cocho.", "error")
            return redirect(url_for("cochos"))

        df_original = carregar_aba("Cochos")
        df_cochos = CO.normalizar_cochos(df_original)
        if len(df_cochos) != len(df_original):
            fazer_backup_seguro()
            reescrever_aba("Cochos", _preparar_para_editar(df_cochos))

        if (
            "ID" in df_cochos.columns
            and df_cochos["ID"].fillna("").astype(str).str.strip().eq(cocho_id).any()
        ):
            flash(f"Já existe um cocho com o ID {cocho_id}. Edite o registro existente.", "error")
            return redirect(url_for("cochos"))

        linha = [
            cocho_id,  # ID
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
    except Exception as e:
        app.logger.exception("Falha ao cadastrar cocho")
        flash(f"Erro ao cadastrar cocho: {e}", "error")
    return redirect(url_for("cochos"))


@app.route("/cochos/salgar/<cocho_id>", methods=["POST"])
@login_required
def salgar_cocho(cocho_id):
    """Registra salga (reposição) do cocho com dados do modal e baixa no estoque de insumos."""
    _validar_csrf()
    try:
        from db import salvar_linha
        import math
        from models import Insumo
        from extensions import db as db_sqla, parse_valor

        df = CO.carregar()
        cocho = df[df["ID"].astype(str).str.strip() == str(cocho_id).strip()]
        if cocho.empty:
            abort(404)
        data_str = request.form.get("data", "").strip()
        try:
            data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Informe uma data válida para a reposição.")

        insumo_id = request.form.get("insumo_id")
        qtd_sacos = parse_valor(request.form.get("quantidade_sacos", 0))
        volume_kg = parse_valor(request.form.get("volume", 0))

        peso_saco = 25.0
        insumo_nome = ""
        if insumo_id:
            ins = Insumo.query.get(insumo_id)
            if ins:
                insumo_nome = ins.nome
                peso_saco = ins.peso_saco or 25.0

        if qtd_sacos > 0:
            quantidade = qtd_sacos * peso_saco
        else:
            quantidade = volume_kg

        if not math.isfinite(quantidade) or quantidade <= 0:
            raise ValueError("A quantidade reposta deve ser maior que zero.")

        dados = _get_dados_cache()
        situacao = CO.calcular_situacao_cochos(
            df, dados.get("Visitas"), CO.carregar_movimentos()
        ).get(str(cocho_id), {})
        capacidade = CO._normalizar_numero(cocho.iloc[0].get("Capacidade (kg)")) or 500
        saldo = situacao.get("volume_kg", 0)
        if quantidade + saldo > capacidade + 1e-9:
            raise ValueError(f"A reposição excede a capacidade: cabem {max(0, capacidade - saldo):g} kg.")

        fazer_backup_seguro()

        # Dar baixa no estoque do insumo selecionado
        if insumo_id:
            ins = Insumo.query.get(insumo_id)
            if ins:
                ins.quantidade = max(0.0, (ins.quantidade or 0.0) - quantidade)
                db_sqla.session.commit()

        obs_texto = f"Insumo: {insumo_nome} ({qtd_sacos:g} sacos)" if insumo_nome else ""

        salvar_linha("Movimentos Cocho", [
            uuid.uuid4().hex[:12].upper(), data_obj.strftime("%d/%m/%Y"),
            str(cocho_id), "Reposição", quantidade, "", obs_texto,
            _membro_logado(),
        ])
        flash(f"✨ Reposição de {quantidade:g} kg ({insumo_nome or 'Salga'}) registrada e baixada do estoque com sucesso!", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao registrar reposição no cocho %s", cocho_id)
        flash(f"Erro ao registrar reposição: {e}", "error")

    return redirect(url_for("cochos"))


@app.route("/cochos/leitura/<cocho_id>", methods=["POST"])
@login_required
def registrar_leitura_cocho(cocho_id):
    """Registra a sobra e o número de cabeças para medir consumo/cabeça/dia."""
    _validar_csrf()
    try:
        import math
        from db import salvar_linha
        df = CO.carregar()
        cocho = df[df["ID"].astype(str).str.strip() == str(cocho_id).strip()]
        if cocho.empty:
            abort(404)
        data_str = request.form.get("data", "").strip()
        try:
            data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Informe uma data válida para a leitura.")
        sobra = float(request.form.get("sobra", "").replace(",", "."))
        cabecas = int(request.form.get("cabecas", "0"))
        capacidade = CO._normalizar_numero(cocho.iloc[0].get("Capacidade (kg)")) or 500
        if not math.isfinite(sobra) or sobra < 0 or sobra > capacidade:
            raise ValueError(f"A sobra deve estar entre 0 e {capacidade:g} kg.")
        if cabecas <= 0:
            raise ValueError("Informe o número de cabeças atendidas pelo cocho.")
        fazer_backup_seguro()
        salvar_linha("Movimentos Cocho", [
            uuid.uuid4().hex[:12].upper(), data_obj.strftime("%d/%m/%Y"),
            str(cocho_id), "Leitura", sobra, cabecas,
            request.form.get("observacoes", "").strip(), _membro_logado(),
        ])
        flash("Leitura do cocho registrada; o consumo/cabeça/dia será calculado quando houver duas leituras.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao registrar leitura do cocho %s", cocho_id)
        flash(f"Erro ao registrar leitura: {e}", "error")
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
    """Remove definitivamente o cocho da aba persistida."""
    if request.method == "GET":
        return redirect(url_for("cochos"))
    _validar_csrf()
    try:
        from db import reescrever_aba
        df = _preparar_para_editar(CO.carregar())
        if df.empty or "ID" not in df.columns:
            flash("Cocho não encontrado.", "error")
            return redirect(url_for("cochos"))

        ids = df["ID"].fillna("").astype(str).str.strip()
        alvo = str(cocho_id).strip()
        if not ids.eq(alvo).any():
            flash("Cocho não encontrado.", "error")
            return redirect(url_for("cochos"))

        df = df.loc[~ids.eq(alvo)].reset_index(drop=True)
        fazer_backup_seguro()
        reescrever_aba("Cochos", df)
        flash("🗑️ Cocho removido com sucesso!", "success")
    except Exception as e:
        app.logger.exception("Falha ao excluir cocho %s", cocho_id)
        flash(f"Erro ao remover cocho: {e}", "error")

    return redirect(url_for("cochos"))
