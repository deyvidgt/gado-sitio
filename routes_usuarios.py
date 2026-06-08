#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Usuários e Configurações — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
import os, tempfile
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, carregar_todas, inicializar, fazer_backup
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS,
                    EMOJIS_MEMBROS, OPCOES_VISITA)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _fazer_backup_inteligente, _limpar_backups_antigos,
    _carregar_usuarios, _salvar_usuarios,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
    fmt_brl, fmt_data, parse_valor,
    _gerar_alertas, _calc_anual, BASE_DIR,
)

#  USUÁRIOS E CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

def _usuarios_path():
    from db import DATA_DIR
    return os.path.join(DATA_DIR, "usuarios.json")

def _carregar_usuarios():
    import json
    caminho = _usuarios_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    dados = {u: {"hash": h, "criado": _agora().strftime("%d/%m/%Y")}
             for u, h in USUARIOS.items()}
    _salvar_usuarios(dados)
    return dados

def _salvar_usuarios(dados):
    import json
    with open(_usuarios_path(), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def _verificar_senha(usuario, senha):
    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return False
    return _verificar_hash(senha, usuarios[usuario]["hash"])

@app.route("/configuracoes")
@login_required
def configuracoes():
    usuarios = _carregar_usuarios()
    return render_template("configuracoes.html", usuarios=usuarios)

@app.route("/configuracoes/trocar-senha", methods=["POST"])
@login_required
def trocar_senha():
    _validar_csrf()
    usuario = session["usuario"]
    atual   = request.form.get("senha_atual", "").strip()
    nova    = request.form.get("senha_nova",  "").strip()
    conf    = request.form.get("senha_conf",  "").strip()
    if not _verificar_senha(usuario, atual):
        flash("Senha atual incorreta.", "error")
        return redirect(url_for("configuracoes"))
    if len(nova) < 4:
        flash("A nova senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    if nova != conf:
        flash("As senhas não coincidem.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    dados[usuario]["hash"] = _hash_bcrypt(nova) if _bcrypt_disponivel() else _sha256(nova)
    _salvar_usuarios(dados)
    flash("✅ Senha alterada com sucesso!", "success")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/adicionar-usuario", methods=["POST"])
@login_required
def adicionar_usuario():
    _validar_csrf()
    import re
    novo_user = request.form.get("usuario", "").strip().lower()
    senha     = request.form.get("senha",   "").strip()
    if not re.match(r"^[a-z]{2,20}$", novo_user):
        flash("Nome de usuário inválido (apenas letras, 2–20 caracteres).", "error")
        return redirect(url_for("configuracoes"))
    if len(senha) < 4:
        flash("A senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if novo_user in dados:
        flash(f"Usuário '{novo_user}' já existe.", "error")
        return redirect(url_for("configuracoes"))
    dados[novo_user] = {
        "hash":   _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha),
        "criado": _agora().strftime("%d/%m/%Y"),
    }
    _salvar_usuarios(dados)
    flash(f"✅ Usuário '{novo_user.capitalize()}' criado!", "success")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/excluir-usuario", methods=["POST"])
@login_required
def excluir_usuario():
    _validar_csrf()
    alvo = request.form.get("usuario", "").strip().lower()
    if alvo == session["usuario"]:
        flash("Você não pode excluir sua própria conta.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))
    del dados[alvo]
    _salvar_usuarios(dados)
    flash(f"Usuário '{alvo.capitalize()}' excluído.", "warning")
    return redirect(url_for("configuracoes"))

@app.route("/configuracoes/resetar-senha", methods=["POST"])
@login_required
def resetar_senha():
    _validar_csrf()
    alvo  = request.form.get("usuario",    "").strip().lower()
    senha = request.form.get("senha_nova", "").strip()
    if len(senha) < 4:
        flash("A senha precisa ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("configuracoes"))
    dados = _carregar_usuarios()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))
    dados[alvo]["hash"] = _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha)
    _salvar_usuarios(dados)
    flash(f"✅ Senha de '{alvo.capitalize()}' redefinida!", "success")
    return redirect(url_for("configuracoes"))


# ══════════════════════════════════════════════════════════════════════════════
