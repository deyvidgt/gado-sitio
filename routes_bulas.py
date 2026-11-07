# -*- coding: utf-8 -*-
"""Página de bulas e fluxo administrativo para baixar PDFs oficiais e enviar ao Drive."""
import os
import re
import time
import uuid

from flask import (Response, abort, flash, redirect, render_template, request, session,
                   url_for)

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
    if drive.cliente() is None:
        flash("Configure o Google Drive antes de enviar bulas.", "warning")
        return redirect(url_for("listar_bulas"))
    return render_template("bulas_atualizar.html", catalogo=bulas.catalogo())


@app.route("/bulas/atualizar/previsualizar", methods=["POST"])
@login_required
def previsualizar_bula():
    _so_admin()
    _validar_csrf()
    chave = request.form.get("produto", "")
    produto = next((p for p in _bulas_faltantes() if p["slug"] == chave), None)
    if produto is None:
        flash("Selecione um produto válido que ainda não tenha bula.", "error")
        return redirect(url_for("atualizar_bulas"))

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
        try:
            conteudo, fonte = bulas.baixar_bula(request.form.get("url", ""))
        except bulas.BulaFonteErro as e:
            flash(str(e), "error")
            return redirect(url_for("atualizar_bulas"))

    _remover_pendente()
    token = uuid.uuid4().hex
    os.makedirs(_bulas_pendentes(), exist_ok=True)
    with open(_caminho_pendente(token), "wb") as arquivo_pdf:
        arquivo_pdf.write(conteudo)
    pendente = {"token": token, "produto": chave, "nome": produto["nome"],
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
    if not any(p["slug"] == pendente["produto"] for p in _bulas_faltantes()):
        flash("Este produto já tem uma bula no Drive; a prévia não foi enviada.", "warning")
        return redirect(url_for("listar_bulas"))
    cli = drive.cliente()
    if cli is None:
        flash("Configure o Google Drive antes de enviar bulas.", "warning")
        return redirect(url_for("listar_bulas"))

    try:
        with open(_caminho_pendente(pendente["token"]), "rb") as arquivo_pdf:
            conteudo = arquivo_pdf.read()
        nome_arquivo = f"{pendente['produto']}__bula.pdf"
        pasta = cli.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
        antigo = cli.achar_por_prop("bulas", nome_arquivo)
        novo = cli.enviar(
            pasta, nome_arquivo, conteudo, "application/pdf",
            {"bulas": nome_arquivo},
            descricao=f"Fonte oficial conferida: {pendente['fonte']}",
        )
        if antigo and antigo != novo:
            cli.lixeira(antigo)
    except (OSError, drive.DriveErro) as e:
        flash(f"Não foi possível enviar a bula ao Google Drive: {e}", "error")
        return redirect(url_for("atualizar_bulas"))

    _remover_pendente()
    flash(f"Bula de {pendente['nome']} enviada ao Drive.", "success")
    return redirect(url_for("listar_bulas"))
