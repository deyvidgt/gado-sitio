# -*- coding: utf-8 -*-
"""Página de bulas e fluxo administrativo para baixar PDFs oficiais e enviar ao Drive."""
import os
import re
import time
import uuid

from flask import (Response, abort, flash, redirect, render_template, request, session,
                   url_for)
from werkzeug.utils import secure_filename

import bulas
import db
import drive
import sitios
from extensions import _validar_csrf, app, login_required

_MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png",
         ".webp": "image/webp"}
_TOKEN_PENDENTE = re.compile(r"[a-f0-9]{32}\Z")
_VALIDADE_PENDENTE = 30 * 60


def _so_admin():
    if not sitios.e_admin(session.get("usuario")):
        abort(403)


def _bulas_pendentes():
    return os.path.join(db.DATA_DIR, "cache_bulas_pendentes")


def _caminho_pendente(token):
    if not isinstance(token, str) or not _TOKEN_PENDENTE.fullmatch(token):
        abort(404)
    return os.path.join(_bulas_pendentes(), token + ".pdf")


def _remover_pendente():
    pendente = session.pop("bula_pendente", None)
    if isinstance(pendente, dict):
        token = pendente.get("token")
        if isinstance(token, str) and _TOKEN_PENDENTE.fullmatch(token):
            try:
                os.remove(_caminho_pendente(token))
            except FileNotFoundError:
                pass


def _ler_pendente(token=None):
    pendente = session.get("bula_pendente")
    if not isinstance(pendente, dict) or (token and pendente.get("token") != token):
        return None
    if pendente.get("site") != sitios.atual():
        return None
    try:
        expirado = time.time() - float(pendente.get("criado", 0)) > _VALIDADE_PENDENTE
        _caminho_pendente(pendente.get("token"))
    except (TypeError, ValueError):
        expirado = True
    if expirado:
        _remover_pendente()
        return None
    return pendente


def _bulas_faltantes():
    return sorted(
        ({"slug": bulas.slug(item["nome"]), "nome": item["nome"]}
         for item in bulas.catalogo() if not item["bula"]),
        key=lambda item: item["nome"].casefold(),
    )


@app.route("/bulas")
@login_required
def listar_bulas():
    return render_template("bulas.html", catalogo=bulas.catalogo(),
                           drive_ok=drive.cliente() is not None,
                           pode_atualizar=sitios.e_admin(session.get("usuario")))


@app.route("/bulas/<nome>")
@login_required
def bula_arquivo(nome):
    dados = bulas.arquivo(nome)
    if dados is None:
        abort(404)
    r = Response(dados, mimetype=_MIME[os.path.splitext(nome)[1]])
    r.headers["Cache-Control"] = "private, max-age=604800"
    # inline: PDF abre no visualizador do celular em vez de baixar sem querer
    r.headers["Content-Disposition"] = f'inline; filename="{nome}"'
    return r


@app.route("/bulas/atualizar")
@login_required
def atualizar_bulas():
    _so_admin()
    # Sem Drive ainda dá para conferir e cadastrar localmente (fallback de rede).
    return render_template("bulas_atualizar.html", catalogo=bulas.catalogo(),
                           drive_ok=drive.cliente() is not None)


@app.route("/bulas/atualizar/previsualizar", methods=["POST"])
@login_required
def previsualizar_bula():
    _so_admin()
    _validar_csrf()

    # Pode vir 'produto' (slug) ou 'produto_nome' (texto vindo da datalist/input livre)
    nome_produto = request.form.get("produto_nome", "").strip() or request.form.get("produto", "").strip()
    if not nome_produto:
        flash("Informe o nome do produto.", "error")
        return redirect(url_for("atualizar_bulas"))

    chave = bulas.slug(nome_produto)

    # Suporte a upload direto de ficheiro PDF (bypass de proxy/403 do PythonAnywhere)
    arquivo_up = request.files.get("bula_pdf")
    if arquivo_up and arquivo_up.filename:
        if not arquivo_up.filename.lower().endswith(".pdf"):
            flash("O arquivo enviado deve ser um PDF válido.", "error")
            return redirect(url_for("atualizar_bulas"))
        try:
            conteudo = arquivo_up.read()
            if not conteudo.startswith(b"%PDF-"):
                flash("O arquivo enviado não é um PDF válido.", "error")
                return redirect(url_for("atualizar_bulas"))
            fonte = f"Upload direto: {arquivo_up.filename}"
        except Exception as e:
            flash(f"Erro ao ler arquivo PDF enviado: {e}", "error")
            return redirect(url_for("atualizar_bulas"))
    else:
        url_pdf = request.form.get("url", "").strip()
        if not url_pdf:
            flash("Envie um arquivo PDF ou informe uma URL oficial.", "error")
            return redirect(url_for("atualizar_bulas"))
        try:
            url_valida, aviso_url = bulas.validar_url_oficial(url_pdf)
            conteudo, fonte = bulas.baixar_bula(url_pdf)
            if aviso_url:
                flash(aviso_url, "warning")
        except bulas.BulaFonteErro as e:
            flash(str(e), "error")
            return redirect(url_for("atualizar_bulas"))

    _remover_pendente()
    token = uuid.uuid4().hex
    os.makedirs(_bulas_pendentes(), exist_ok=True)
    with open(_caminho_pendente(token), "wb") as arquivo_pdf:
        arquivo_pdf.write(conteudo)
    pendente = {"token": token, "produto": chave, "nome": nome_produto,
                "fonte": fonte, "site": sitios.atual(), "criado": time.time()}
    session["bula_pendente"] = pendente
    return render_template("bulas_confirmar.html", pendente=pendente)


@app.route("/bulas/pendente/<token>")
@login_required
def visualizar_bula_pendente(token):
    _so_admin()
    if _ler_pendente(token) is None:
        abort(404)
    caminho = _caminho_pendente(token)
    try:
        with open(caminho, "rb") as arquivo_pdf:
            conteudo = arquivo_pdf.read()
    except FileNotFoundError:
        abort(404)
    resposta = Response(conteudo, mimetype="application/pdf")
    resposta.headers["Cache-Control"] = "private, no-store"
    resposta.headers["Content-Disposition"] = 'inline; filename="previa-bula.pdf"'
    return resposta


@app.route("/bulas/atualizar/confirmar", methods=["POST"])
@login_required
def confirmar_bula():
    _so_admin()
    _validar_csrf()
    pendente = _ler_pendente(request.form.get("token"))
    if pendente is None:
        flash("A prévia expirou. Confira o PDF novamente.", "warning")
        return redirect(url_for("atualizar_bulas"))

    # Formulário de pré-conferência manda o produto em campos hidden para
    # garantir a associação correta mesmo se a sessão for parcial.
    produto_form = (request.form.get("produto") or "").strip()
    nome_form = (request.form.get("produto_nome") or request.form.get("nome") or "").strip()
    if produto_form:
        pendente["produto"] = bulas.slug(produto_form)
    if nome_form:
        pendente["nome"] = nome_form
    if not pendente.get("produto"):
        flash("Produto da bula não informado.", "error")
        return redirect(url_for("atualizar_bulas"))
    pendente.setdefault("nome", pendente["produto"])

    nome_arquivo = f"{pendente['produto']}__bula.pdf"
    try:
        with open(_caminho_pendente(pendente["token"]), "rb") as arquivo_pdf:
            conteudo = arquivo_pdf.read()
        # Cache local primeiro: o produto entra em Disponíveis mesmo se o Drive falhar.
        bulas.guardar_local(nome_arquivo, conteudo)
    except (OSError, bulas.BulaFonteErro) as e:
        print(e)
        flash(f"Não foi possível guardar a bula localmente: {e}", "error")
        return redirect(url_for("atualizar_bulas"))

    drive_ok = False
    cli = drive.cliente()
    if cli is None:
        flash("Google Drive não configurado — bula cadastrada só neste sítio.", "warning")
    else:
        try:
            pasta = cli.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
            antigo = cli.achar_por_prop("bulas", nome_arquivo)
            novo = cli.enviar(
                pasta, nome_arquivo, conteudo, "application/pdf",
                {"bulas": nome_arquivo},
                descricao=f"Fonte oficial conferida: {pendente['fonte']}",
            )
            if antigo and antigo != novo:
                cli.lixeira(antigo)
            drive_ok = True
        except Exception as e:
            print(e)
            flash(
                f"Falha ao enviar ao Google Drive ({e}). "
                f"A bula de {pendente['nome']} ficou cadastrada localmente.",
                "warning",
            )

    _remover_pendente()
    if drive_ok:
        flash(f"Bula de {pendente['nome']} enviada ao Drive.", "success")
    else:
        flash(f"Bula de {pendente['nome']} cadastrada e disponível na lista.", "success")
    return redirect(url_for("listar_bulas"))


@app.route("/bulas/upload-embalagem", methods=["POST"])
@login_required
def upload_embalagem_bula():
    _validar_csrf()
    nome_produto = (request.form.get("produto") or "").strip()
    if not nome_produto:
        flash("Informe o nome do produto.", "error")
        return redirect(url_for("listar_bulas"))

    arquivo_up = request.files.get("foto_embalagem")
    if not arquivo_up or not arquivo_up.filename:
        flash("Selecione ou tire uma foto da embalagem.", "error")
        return redirect(url_for("listar_bulas"))

    ext = os.path.splitext(arquivo_up.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        flash("Formato de imagem inválido. Use JPG, PNG ou WEBPA.", "error")
        return redirect(url_for("listar_bulas"))

    chave = bulas.slug(nome_produto)
    safe_ext = ".jpg" if ext in (".jpg", ".jpeg") else (ext if ext in (".png", ".webp") else ".jpg")
    nombre_seguro = secure_filename(f"{chave}__embalagem{safe_ext}")
    nome_arquivo = nombre_seguro or f"{chave}__embalagem{safe_ext}"

    try:
        conteudo = arquivo_up.read()
        if len(conteudo) > 15 * 1024 * 1024:
            flash("Imagem muito grande (máximo 15 MB).", "error")
            return redirect(url_for("listar_bulas"))
        bulas.guardar_local(nome_arquivo, conteudo)
    except Exception as e:
        flash(f"Erro ao guardar foto localmente: {e}", "error")
        return redirect(url_for("listar_bulas"))

    drive_ok = False
    cli = drive.cliente()
    if cli is None:
        flash(f"📸 Foto da embalagem de {nome_produto} salva localmente (Google Drive não configurado).", "warning")
    else:
        try:
            pasta = cli.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
            antigo = cli.achar_por_prop("bulas", nome_arquivo)
            mime = "image/jpeg" if safe_ext == ".jpg" else ("image/png" if safe_ext == ".png" else "image/webp")
            novo = cli.enviar(
                pasta, nome_arquivo, conteudo, mime,
                {"bulas": nome_arquivo},
                descricao=f"Foto da embalagem de {nome_produto}",
            )
            if antigo and antigo != novo:
                cli.lixeira(antigo)
            drive_ok = True
        except Exception as e:
            flash(f"Foto salva localmente, mas falhou ao enviar ao Google Drive: {e}", "warning")

    if drive_ok:
        flash(f"📸 Foto da embalagem de {nome_produto} enviada com sucesso ao Google Drive!", "success")
    else:
        flash(f"📸 Foto da embalagem de {nome_produto} salva com sucesso!", "success")
    return redirect(url_for("listar_bulas"))

