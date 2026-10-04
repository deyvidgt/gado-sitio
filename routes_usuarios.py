#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Usuários e Configurações — Sítio Santo Antonio
"""
import os
import json
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, session, send_file
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


# ── Config do sítio (nome, donos, logo) ──────────────────────────────────────

SITIO_CONFIG_DEFAULTS = {
    "nome":   "Sítio Santo Antonio",
    "donos":  "Geane · Deyvid · Nilson",
    "logo":   "🐄",        # emoji ou URL de imagem carregada
    "logo_tipo": "emoji",  # "emoji" | "imagem"
    "peso_medio": 0,       # kg peso vivo médio por cabeça (0 = não configurado)
    "rendimento": 52,      # % de rendimento de carcaça (padrão boi gordo Nelore)
}


def _sitio_config_path():
    return os.path.join(DATA_DIR, "sitio_config.json")


def _carregar_sitio_config() -> dict:
    caminho = _sitio_config_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                cfg = json.load(f)
                # Garantir que todos os campos existem
                for k, v in SITIO_CONFIG_DEFAULTS.items():
                    cfg.setdefault(k, v)
                return cfg
        except Exception:
            pass
    return dict(SITIO_CONFIG_DEFAULTS)


def _salvar_sitio_config(cfg: dict):
    with open(_sitio_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/configuracoes")
@login_required
def configuracoes():
    from db import get_alertas_saude
    usuarios     = _carregar_usuarios_local()
    sitio_config = _carregar_sitio_config()
    alertas_saude = get_alertas_saude()
    return render_template("configuracoes.html", usuarios=usuarios,
                           sitio_config=sitio_config, alertas_saude=alertas_saude)


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
    # Senha nova = desbloqueia na hora (senão o usuário esperava os 15 min mesmo assim).
    from routes_auth import _limpar_falhas
    _limpar_falhas(alvo)
    flash(f"✅ Senha de '{alvo.capitalize()}' redefinida!", "success")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/sitio", methods=["POST"])
@login_required
def salvar_sitio_config():
    import re
    from flask import send_from_directory
    _validar_csrf()

    nome  = request.form.get("sitio_nome",  "").strip()
    donos = request.form.get("sitio_donos", "").strip()

    if not nome:
        flash("O nome do sítio não pode ser vazio.", "error")
        return redirect(url_for("configuracoes"))

    # Sanitizar: remover tags HTML
    nome  = re.sub(r"<[^>]+>", "", nome)[:80]
    donos = re.sub(r"<[^>]+>", "", donos)[:120]

    cfg = _carregar_sitio_config()
    cfg["nome"]  = nome
    cfg["donos"] = donos

    # Logo: emoji digitado ou imagem enviada
    logo_emoji = request.form.get("sitio_logo_emoji", "").strip()
    arquivo    = request.files.get("sitio_logo_imagem")

    if arquivo and arquivo.filename:
        # Salvar imagem em static/
        import werkzeug.utils
        ext = os.path.splitext(arquivo.filename)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            flash("Formato inválido. Use PNG, JPG ou JPEG.", "error")
            return redirect(url_for("configuracoes"))
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        os.makedirs(static_dir, exist_ok=True)
        nome_arquivo = "sitio_logo" + ext
        arquivo.save(os.path.join(static_dir, nome_arquivo))
        # ?v= muda a cada upload: o app no celular guarda /static/ em cache para
        # sempre, então com a mesma URL o logo novo nunca aparecia.
        cfg["logo"]      = f"/static/{nome_arquivo}?v={int(_agora().timestamp())}"
        cfg["logo_tipo"] = "imagem"
    elif logo_emoji:
        cfg["logo"]      = logo_emoji
        cfg["logo_tipo"] = "emoji"

    _salvar_sitio_config(cfg)
    _invalidar_cache_sitio()
    flash("✅ Configurações do sítio salvas!", "success")
    return redirect(url_for("configuracoes"))


def _invalidar_cache_sitio():
    """Limpa o cache de sitio_config para as mudanças aparecerem na hora."""
    try:
        from extensions import _cache_invalidar_chave
        _cache_invalidar_chave("sitio_config")
    except Exception:
        pass


@app.route("/configuracoes/rebanho", methods=["POST"])
@login_required
def salvar_rebanho_config():
    """Salva peso médio e rendimento usados na estimativa de valor do rebanho."""
    _validar_csrf()

    def _num(v, default):
        try:
            return float(str(v).strip().replace(",", "."))
        except Exception:
            return default

    peso = max(0.0, min(_num(request.form.get("peso_medio"), 0.0), 2000.0))
    rend = max(1.0, min(_num(request.form.get("rendimento"), 52.0), 100.0))

    cfg = _carregar_sitio_config()
    cfg["peso_medio"] = round(peso, 1)
    cfg["rendimento"] = round(rend, 1)
    _salvar_sitio_config(cfg)
    _invalidar_cache_sitio()
    flash("✅ Dados do rebanho salvos! A estimativa aparece no painel.", "success")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/alertas-saude", methods=["POST"])
@login_required
def salvar_alertas_saude():
    """Salva os intervalos (dias) dos alertas de saúde — ajustáveis por região."""
    _validar_csrf()
    from config import ALERTAS_SAUDE
    novos = {}
    for tipo, padrao in ALERTAS_SAUDE.items():
        raw = request.form.get(tipo, "")
        try:
            v = int(float(str(raw).strip().replace(",", ".")))
        except Exception:
            v = padrao
        novos[tipo] = max(1, min(v, 3650))   # 1 dia a 10 anos

    cfg = _carregar_sitio_config()
    cfg["alertas_saude"] = novos
    _salvar_sitio_config(cfg)
    _invalidar_cache_sitio()
    flash("✅ Intervalos de saúde atualizados!", "success")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/baixar-dados")
@login_required
def baixar_dados():
    """Baixa uma cópia do arquivo de dados atual (gado_familia.xlsx)."""
    from db import ARQUIVO_PATH
    if not os.path.exists(ARQUIVO_PATH):
        flash("Arquivo de dados não encontrado.", "error")
        return redirect(url_for("configuracoes"))
    nome = f"gado_familia_{_agora().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(ARQUIVO_PATH, as_attachment=True, download_name=nome)
