#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Usuários e Configurações — Sítio Santo Antonio
"""
import os
import json
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, session
from db import DATA_DIR
from config import USUARIOS
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
)


# ── Helpers locais (lêem/gravam em DATA_DIR, fora do repo Git) ────────────────

def _usuarios_path():
    return os.path.join(DATA_DIR, "usuarios.json")


def _carregar_usuarios_local():
    caminho = _usuarios_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback: criar a partir de config.py
    dados = {
        u: {"hash": h, "criado": _agora().strftime("%d/%m/%Y")}
        for u, h in USUARIOS.items()
    }
    _salvar_usuarios_local(dados)
    return dados


def _salvar_usuarios_local(dados):
    with open(_usuarios_path(), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _verificar_senha(usuario, senha):
    usuarios = _carregar_usuarios_local()
    if usuario not in usuarios:
        return False
    return _verificar_hash(senha, usuarios[usuario]["hash"])


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/configuracoes")
@login_required
def configuracoes():
    usuarios = _carregar_usuarios_local()
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

    dados = _carregar_usuarios_local()
    dados[usuario]["hash"] = _hash_bcrypt(nova) if _bcrypt_disponivel() else _sha256(nova)
    _salvar_usuarios_local(dados)
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

    dados = _carregar_usuarios_local()
    if novo_user in dados:
        flash(f"Usuário '{novo_user}' já existe.", "error")
        return redirect(url_for("configuracoes"))

    dados[novo_user] = {
        "hash":   _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha),
        "criado": _agora().strftime("%d/%m/%Y"),
    }
    _salvar_usuarios_local(dados)
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

    dados = _carregar_usuarios_local()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))

    del dados[alvo]
    _salvar_usuarios_local(dados)
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

    dados = _carregar_usuarios_local()
    if alvo not in dados:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("configuracoes"))

    dados[alvo]["hash"] = _hash_bcrypt(senha) if _bcrypt_disponivel() else _sha256(senha)
    _salvar_usuarios_local(dados)
    flash(f"✅ Senha de '{alvo.capitalize()}' redefinida!", "success")
    return redirect(url_for("configuracoes"))
