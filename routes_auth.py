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
from datetime import datetime, timedelta
import json
import os
import threading

# Minutos de bloqueio após exceder as tentativas (desbloqueio automático).
BLOQUEIO_MINUTOS = 15

# ── Bloqueio de login NO SERVIDOR ─────────────────────────────────────────────
# Antes o contador ficava no cookie da sessão: bastava apagar o cookie (ou abrir
# aba anônima) para ganhar mais 5 tentativas. Agora fica num arquivo na pasta de
# dados, por usuário — vale para qualquer navegador/IP e sobrevive a reinícios
# e a mais de um processo do servidor (o arquivo é a fonte da verdade).
_bloqueio_lock = threading.Lock()


def _bloqueios_path() -> str:
    from db import DATA_DIR
    return os.path.join(DATA_DIR, "login_bloqueios.json")


def _ler_bloqueios() -> dict:
    try:
        with open(_bloqueios_path(), encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def _gravar_bloqueios(dados: dict):
    caminho = _bloqueios_path()
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)   # troca atômica: nunca deixa o arquivo pela metade


def _estado_login(usuario: str) -> dict:
    """{'falhas': n, 'bloqueio_ate': iso|None} do usuário; expira bloqueios vencidos."""
    reg = _ler_bloqueios().get(usuario) or {}
    ate = reg.get("bloqueio_ate")
    if ate:
        try:
            if _agora() >= datetime.fromisoformat(ate):
                return {"falhas": 0, "bloqueio_ate": None}
        except ValueError:
            return {"falhas": 0, "bloqueio_ate": None}
    return {"falhas": int(reg.get("falhas", 0) or 0), "bloqueio_ate": ate}


def _registrar_falha(usuario: str) -> dict:
    with _bloqueio_lock:
        dados = _ler_bloqueios()
        est = _estado_login(usuario)
        est["falhas"] += 1
        if est["falhas"] >= MAX_TENTATIVAS_LOGIN:
            est["bloqueio_ate"] = (_agora() + timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat()
        dados[usuario] = est
        # Limpa registros vencidos para o arquivo não crescer com nomes digitados errado.
        agora = _agora()
        for u in [u for u, r in dados.items() if u != usuario
                  and (r.get("bloqueio_ate") or "") < agora.isoformat()
                  and (r.get("ultima") or "") < (agora - timedelta(days=1)).isoformat()]:
            dados.pop(u, None)
        dados[usuario]["ultima"] = agora.isoformat()
        _gravar_bloqueios(dados)
        return est


def _limpar_falhas(usuario: str):
    with _bloqueio_lock:
        dados = _ler_bloqueios()
        if dados.pop(usuario, None) is not None:
            _gravar_bloqueios(dados)


def _minutos_restantes(ate_iso: str) -> int:
    try:
        seg = (datetime.fromisoformat(ate_iso) - _agora()).total_seconds()
    except (TypeError, ValueError):
        return BLOQUEIO_MINUTOS
    return max(1, int(seg // 60) + (1 if seg % 60 else 0))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logado"):
        return redirect(url_for("dashboard"))

    erro = None
    usuario_digitado = ""
    tentativas_restantes = MAX_TENTATIVAS_LOGIN

    if request.method == "POST":
        _validar_csrf()
        usuario = request.form.get("usuario", "").strip().lower()
        senha   = request.form.get("senha",   "").strip()
        usuario_digitado = usuario
        usuarios_db = _carregar_usuarios()
        estado = _estado_login(usuario)

        if estado["bloqueio_ate"]:
            # Bloqueado: nem confere a senha (senão o bloqueio não impediria adivinhar).
            erro = (f"Muitas tentativas. Aguarde {_minutos_restantes(estado['bloqueio_ate'])} "
                    f"minuto(s) e tente novamente.")
            tentativas_restantes = 0
        elif usuario in usuarios_db and _verificar_hash(senha, usuarios_db[usuario]["hash"]):
            # ✅ Login OK — migrar SHA-256 → bcrypt se possível
            if _bcrypt_disponivel():
                stored = usuarios_db[usuario]["hash"]
                if not (stored.startswith("$2b$") or stored.startswith("$2a$")):
                    dados = usuarios_db
                    dados[usuario]["hash"] = _hash_bcrypt(senha)
                    _salvar_usuarios(dados)
            _limpar_falhas(usuario)
            session.clear()
            session["logado"]  = True
            session["usuario"] = usuario
            _gerar_csrf()   # novo token após login
            # Só aceita caminho interno ("/vendas"); "https://..." ou "//site"
            # mandaria o usuário para fora do sistema após o login (open redirect).
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//") or "\\" in next_url:
                next_url = url_for("dashboard")
            return redirect(next_url)
        else:
            estado = _registrar_falha(usuario)
            tentativas_restantes = max(0, MAX_TENTATIVAS_LOGIN - estado["falhas"])
            if estado["bloqueio_ate"]:
                erro = f"Acesso bloqueado por {BLOQUEIO_MINUTOS} minutos após muitas tentativas."
            elif usuario and usuario not in usuarios_db:
                erro = f"Usuário '{usuario}' não encontrado."
            else:
                erro = "Usuário ou senha incorretos."

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


@app.route("/sw.js")
def service_worker():
    """Service Worker para PWA — servido da raiz para ter escopo correto."""
    from flask import send_from_directory, Response
    # Raiz do projeto primeiro (é o arquivo versionado no Git); static/ guardava uma
    # cópia feita pelo atualizar.sh que ficava velha quando só se dava "git pull".
    for pasta in [BASE_DIR, BUNDLE_DIR, os.path.join(BUNDLE_DIR, "static")]:
        caminho = os.path.join(pasta, "sw.js")
        if os.path.exists(caminho):
            resp = send_from_directory(pasta, "sw.js")
            resp.headers["Content-Type"] = "application/javascript"
            resp.headers["Service-Worker-Allowed"] = "/"
            resp.headers["Cache-Control"] = "no-cache"
            return resp
    return "", 204


@app.route("/manifest.json")
def manifest():
    """Web App Manifest para PWA."""
    from flask import send_from_directory
    for pasta in [BASE_DIR, BUNDLE_DIR, os.path.join(BUNDLE_DIR, "static")]:
        caminho = os.path.join(pasta, "manifest.json")
        if os.path.exists(caminho):
            resp = send_from_directory(pasta, "manifest.json")
            resp.headers["Content-Type"] = "application/manifest+json"
            resp.headers["Cache-Control"] = "no-cache"
            return resp
    return "", 204

