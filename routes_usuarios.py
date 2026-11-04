#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Usuários e Configurações — Sítio Santo Antonio
"""
import os
import json
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, session, send_file
import db
from config import USUARIOS, MEMBROS, NOMES_MEMBROS, CORES_BRINCO
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
)


# ── Helpers locais (lêem/gravam em DATA_DIR, fora do repo Git) ────────────────

def _usuarios_path():
    return os.path.join(db.RAIZ, "usuarios.json")   # da família, não de um sítio


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
    "logo":   "🐄",        # emoji ou URL de imagem carregada
    "logo_tipo": "emoji",  # "emoji" | "imagem"
    "peso_medio": 0,       # kg peso vivo médio por cabeça (0 = não configurado)
    "rendimento": 52,      # % de rendimento de carcaça (padrão boi gordo Nelore)
}


def _sitio_config_path():
    return os.path.join(db.DATA_DIR, "sitio_config.json")


def _carregar_sitio_config() -> dict:
    caminho = _sitio_config_path()
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                cfg = json.load(f)
                # Garantir que todos os campos existem
                for k, v in SITIO_CONFIG_DEFAULTS.items():
                    cfg.setdefault(k, v)
                cfg.setdefault("donos", " · ".join(NOMES_MEMBROS[m] for m in MEMBROS))
                return cfg
        except Exception:
            pass
    return {**SITIO_CONFIG_DEFAULTS, "donos": " · ".join(NOMES_MEMBROS[m] for m in MEMBROS)}


def _salvar_sitio_config(cfg: dict):
    with open(_sitio_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Rotas ─────────────────────────────────────────────────────────────────────

def _arroba_ultima_venda():
    """(valor, data) da @ da venda mais recente que informou a arroba — dica no formulário."""
    try:
        import pandas as pd
        from extensions import _get_dados_cache, fmt_data
        v = _get_dados_cache()["Vendas"]
        if v.empty or "Valor Arroba (R$)" not in v.columns:
            return None
        v = v[pd.to_numeric(v["Valor Arroba (R$)"], errors="coerce").fillna(0) > 0]
        if v.empty:
            return None
        ult = v.sort_values("Data", na_position="first").iloc[-1]
        return float(ult["Valor Arroba (R$)"]), fmt_data(ult["Data"])
    except Exception:
        return None


def _so_admin():
    """Gestão de usuários/sítios é do administrador (com vários sítios, um parente
    não pode redefinir a senha de quem é de outro sítio)."""
    import sitios
    from flask import abort
    if not sitios.e_admin(session.get("usuario")):
        abort(403)


def _usuarios_visiveis(todos: dict) -> dict:
    """Admin vê todos; os outros, só quem tem acesso ao sítio atual."""
    import sitios
    if sitios.e_admin(session.get("usuario")):
        return todos
    deixar = set(sitios.logins_do_sitio(sitios.atual(), todos))
    return {u: i for u, i in todos.items() if u in deixar}


@app.route("/configuracoes")
@login_required
def configuracoes():
    from db import get_alertas_saude
    import sitios
    usuarios     = _usuarios_visiveis(_carregar_usuarios_local())
    sitio_config = _carregar_sitio_config()
    alertas_saude = get_alertas_saude()
    import drive
    from calculos import PRECO_ARROBA_REF
    return render_template("configuracoes.html", usuarios=usuarios,
                           sitio_config=sitio_config, alertas_saude=alertas_saude,
                           preco_arroba_padrao=PRECO_ARROBA_REF,
                           arroba_ultima_venda=_arroba_ultima_venda(),
                           drive_configurado=drive.configurado() or drive.cliente() is not None,
                           e_admin=sitios.e_admin(session.get("usuario")),
                           sitios_lista=[(s, sitios.nome(s)) for s in sitios.carregar()["sitios"]],
                           acesso_de={u: sitios.sitios_do_usuario(u) for u in usuarios},
                           CORES_BRINCO=CORES_BRINCO)


@app.route("/configuracoes/modulos", methods=["GET", "POST"])
@login_required
def configuracoes_modulos():
    import modulos
    if request.method == "POST":
        _validar_csrf()
        campos = set(request.form) - {"csrf_token"}
        if not campos.issubset(modulos.MODULOS) or any(
            request.form.getlist(chave) != ["1"] for chave in campos
        ):
            flash("As opções de módulos enviadas são inválidas.", "error")
            return redirect(url_for("configuracoes_modulos"))
        valores = {
            chave: request.form.getlist(chave) == ["1"]
            for chave in modulos.MODULOS
        }
        try:
            modulos.salvar_preferencias(_sitio_config_path(), valores)
        except ValueError as erro:
            flash(str(erro), "error")
            return redirect(url_for("configuracoes_modulos"))
        _invalidar_cache_sitio()
        flash("Preferências dos módulos salvas para este sítio.", "success")
        return redirect(url_for("configuracoes_modulos"))

    return render_template(
        "configuracoes_modulos.html",
        catalogo_modulos=modulos.MODULOS,
        preferencias_modulos=modulos.preferencias(_carregar_sitio_config()),
    )


@app.route("/configuracoes/sitios/criar", methods=["POST"])
@login_required
def criar_sitio():
    import sitios
    _validar_csrf()
    _so_admin()
    f = request.form
    membros = []
    for i in range(8):
        nome = f.get(f"dono_nome_{i}", "").strip()
        if not nome:
            continue
        login = f.get(f"dono_login_{i}", "").strip().lower()
        membros.append({"chave": sitios.chave_do_nome(nome), "nome": nome, "emoji": "👤",
                        "cor": f.get(f"dono_cor_{i}", ""), "logins": [login] if login else []})
    try:
        slug = sitios.criar(f.get("nome", ""), f.get("slug", "").strip(), membros,
                            f.getlist("acesso"), list(_carregar_usuarios_local()))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("configuracoes") + "#sitios")
    flash(f"🏡 {sitios.nome(slug)} criado! Crie os logins dos donos (se ainda não existem) "
          "e libere o acesso abaixo.", "success")
    return redirect(url_for("configuracoes") + "#sitios")


@app.route("/configuracoes/sitios/acesso", methods=["POST"])
@login_required
def salvar_acesso_sitios():
    """Caixinhas login|sítio marcadas = quem entra em cada sítio."""
    import sitios
    _validar_csrf()
    _so_admin()
    todos = list(_carregar_usuarios_local())
    acesso = {u: [] for u in todos}
    for par in request.form.getlist("acesso"):
        login, _, slug = par.partition("|")
        if login in acesso:
            acesso[login].append(slug)
    try:
        sitios.salvar_acesso(acesso, session.get("usuario"), todos)
    except ValueError as e:
        flash(str(e), "error")
    else:
        flash("Acessos salvos.", "success")
    return redirect(url_for("configuracoes") + "#sitios")


@app.route("/configuracoes/testar-drive", methods=["POST"])
@login_required
def testar_drive():
    """Fala com o Drive só quando pedido (abrir Configurações não espera o Google)."""
    import drive
    _validar_csrf()
    cli = drive.cliente()
    if cli is None:
        flash("📷 Fotos: Drive não configurado (falta o drive_token.json — veja docs/FOTOS_DRIVE.md).", "error")
    else:
        ok, msg = cli.testar()
        flash(f"📷 {msg}", "success" if ok else "error")
    return redirect(url_for("configuracoes") + "#fotos")


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
    _so_admin()
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
    _so_admin()
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
    _so_admin()
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

    def _coordenada(campo, minimo, maximo):
        bruto = request.form.get(campo, "").strip().replace(",", ".")
        if not bruto:
            return None
        try:
            valor = float(bruto)
        except ValueError:
            raise ValueError(f"{campo.capitalize()} inválida.")
        if not minimo <= valor <= maximo:
            raise ValueError(f"{campo.capitalize()} fora do intervalo válido.")
        return round(valor, 6)

    try:
        latitude = _coordenada("latitude", -90, 90)
        longitude = _coordenada("longitude", -180, 180)
    except ValueError as erro:
        flash(str(erro), "error")
        return redirect(url_for("configuracoes"))

    if not nome:
        flash("O nome do sítio não pode ser vazio.", "error")
        return redirect(url_for("configuracoes"))

    # Sanitizar: remover tags HTML
    nome  = re.sub(r"<[^>]+>", "", nome)[:80]
    donos = re.sub(r"<[^>]+>", "", donos)[:120]

    cfg = _carregar_sitio_config()
    cfg["nome"]  = nome
    cfg["donos"] = donos
    if latitude is not None:
        cfg["latitude"] = latitude
    else:
        cfg.pop("latitude", None)
    if longitude is not None:
        cfg["longitude"] = longitude
    else:
        cfg.pop("longitude", None)

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
    """Salva peso médio, rendimento, preço da arroba e capacidade de lotação."""
    _validar_csrf()

    def _num(v, default):
        try:
            return float(str(v).strip().replace(",", "."))
        except Exception:
            return default

    peso = max(0.0, min(_num(request.form.get("peso_medio"), 0.0), 2000.0))
    rend = max(1.0, min(_num(request.form.get("rendimento"), 52.0), 100.0))
    # Vazio/0 = volta ao padrão do sistema (calculos.PRECO_ARROBA_REF).
    arroba = max(0.0, min(_num(request.form.get("preco_arroba"), 0.0), 5000.0))
    # Vazio/0 = sem semáforo de lotação (pastos.nivel devolve None).
    capacidade = max(0.0, min(_num(request.form.get("capacidade_ua_ha"), 0.0), 20.0))

    cfg = _carregar_sitio_config()
    cfg["peso_medio"] = round(peso, 1)
    cfg["rendimento"] = round(rend, 1)
    cfg["preco_arroba"] = round(arroba, 2)
    cfg["capacidade_ua_ha"] = round(capacidade, 2)
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
