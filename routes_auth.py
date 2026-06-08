#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_auth.py — Sítio Santo Antonio
Login, logout, favicon e proteção de sessão.
"""
from flask import render_template, request, redirect, url_for, flash, session
from extensions import (
    app, _agora, _validar_csrf, _gerar_csrf, login_required,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
    _carregar_usuarios, _salvar_usuarios,
    BASE_DIR, BUNDLE_DIR,
)
from config import MAX_TENTATIVAS_LOGIN
import os

def login():
    if session.get("logado"):
        return redirect(url_for("dashboard"))

    erro = None
    usuario_digitado = ""

    if request.method == "POST":
        _validar_csrf()
        usuario = request.form.get("usuario", "").strip().lower()
        senha   = request.form.get("senha",   "").strip()
        usuario_digitado = usuario

        tentativas = session.get("tentativas_login", 0)
        usuarios_db = _carregar_usuarios()

        if tentativas >= MAX_TENTATIVAS_LOGIN:
            erro = "Muitas tentativas. Feche e abra o programa para desbloquear."
        elif usuario in usuarios_db and _verificar_hash(senha, usuarios_db[usuario]["hash"]):
            # ✅ Login OK — migrar SHA-256 → bcrypt se possível
            if _bcrypt_disponivel():
                stored = usuarios_db[usuario]["hash"]
                if not (stored.startswith("$2b$") or stored.startswith("$2a$")):
                    dados = usuarios_db
                    dados[usuario]["hash"] = _hash_bcrypt(senha)
                    _salvar_usuarios(dados)
            session.clear()
            session["logado"]  = True
            session["usuario"] = usuario
            _gerar_csrf()   # novo token após login
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            session["tentativas_login"] = tentativas + 1
            restantes = MAX_TENTATIVAS_LOGIN - session["tentativas_login"]
            if restantes <= 0:
                erro = "Acesso bloqueado. Feche e abra o programa para tentar novamente."
            elif usuario and usuario not in usuarios_db:
                erro = f"Usuário '{usuario}' não encontrado."
            else:
                erro = "Usuário ou senha incorretos."

    tentativas_restantes = MAX_TENTATIVAS_LOGIN - session.get("tentativas_login", 0)
    return render_template("login.html", erro=erro,
                           usuario_digitado=usuario_digitado,
                           tentativas_restantes=tentativas_restantes)

@app.route("/logout", methods=["POST"])
def logout():
    _validar_csrf()
    usuario = session.get("usuario", "")
    session.clear()
    flash(f"Até logo, {usuario.capitalize()}! 👋", "success")
    return redirect(url_for("login"))

@app.route("/favicon.ico")
def favicon():
    from flask import send_from_directory
    static = os.path.join(BUNDLE_DIR, "static")
    if os.path.exists(os.path.join(static, "favicon.ico")):
        return send_from_directory(static, "favicon.ico")
    return "", 204

