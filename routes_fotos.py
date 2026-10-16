# -*- coding: utf-8 -*-
"""
routes_fotos.py — envio e exibição das fotos dos animais (v4.4).

As fotos ficam privadas no Drive: o site busca e repassa (só para quem está
logado), guardando uma cópia em <DATA_DIR>/cache_fotos/ para a lista de animais
não ir ao Google a cada visita.
"""
import io
import logging
import os
import re

from flask import (Response, abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)

import db
import drive
import fotos
from extensions import _validar_csrf, app, login_required
from routes_animais import _membro_logado

_RE_ID = re.compile(r"^F\d{5}$")
LIMITE_CACHE = 50 * 1024 * 1024   # o disco do PythonAnywhere gratuito é de 512 MB no total
LIMITE_PEDIDO = 9 * 1024 * 1024   # foto de 8 MB + campos do formulário
LADO_MINI = 400


def cache_dir() -> str:
    return os.path.join(db.DATA_DIR, "cache_fotos")


def limpar_cache(limite_bytes: int = LIMITE_CACHE) -> None:
    """Apaga os arquivos acessados há mais tempo até caber no limite."""
    pasta = cache_dir()
    if not os.path.isdir(pasta):
        return
    arqs = [os.path.join(pasta, n) for n in os.listdir(pasta)]
    arqs.sort(key=os.path.getatime)
    total = sum(os.path.getsize(a) for a in arqs)
    while arqs and total > limite_bytes:
        a = arqs.pop(0)
        total -= os.path.getsize(a)
        try:
            os.remove(a)
        except OSError:
            pass


def _apagar_do_cache(id_foto: str) -> None:
    for nome in (f"{id_foto}.jpg", f"{id_foto}_mini.jpg"):
        try:
            os.remove(os.path.join(cache_dir(), nome))
        except OSError:
            pass


def _miniatura(conteudo: bytes) -> bytes:
    """~400 px em JPEG; sem Pillow (ou imagem que ele não abre), devolve a original."""
    try:
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(conteudo))).convert("RGB")
        img.thumbnail((LADO_MINI, LADO_MINI))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        return buf.getvalue()
    except Exception:
        return conteudo


def _imagem(id_foto: str, mini: bool) -> bytes:
    if not _RE_ID.match(id_foto):
        abort(404)
    nome = f"{id_foto}_mini.jpg" if mini else f"{id_foto}.jpg"
    caminho = os.path.join(cache_dir(), nome)
    if os.path.isfile(caminho):
        os.utime(caminho, None)   # marca como usado agora (limpeza pelos mais antigos)
        with open(caminho, "rb") as f:
            return f.read()

    foto = fotos.por_id(id_foto)
    cli = drive.cliente()
    if foto is None or cli is None or not foto["drive_id"]:
        abort(404)
    if mini:
        dados = _miniatura(_imagem(id_foto, mini=False))
    else:
        try:
            dados = cli.baixar(foto["drive_id"])
        except drive.DriveErro as e:
            logging.warning(f"Foto {id_foto}: {e}")
            abort(502)
    os.makedirs(cache_dir(), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(dados)
    limpar_cache()
    return dados


def _servir(dados: bytes) -> Response:
    mime = fotos.e_imagem(dados) or "application/octet-stream"
    r = Response(dados, mimetype=mime)
    r.headers["Cache-Control"] = "private, max-age=604800"
    return r


@app.route("/fotos/<id_foto>")
@login_required
def foto_inteira(id_foto):
    return _servir(_imagem(id_foto, mini=False))


@app.route("/fotos/<id_foto>/mini")
@login_required
def foto_mini(id_foto):
    return _servir(_imagem(id_foto, mini=True))


@app.route("/api/fotos", methods=["POST"])
def api_enviar_foto():
    """Recebe a foto do celular (na hora ou da fila offline). Sempre JSON: o
    celular precisa saber se tira a foto da fila ou tenta de novo depois."""
    if not session.get("logado"):
        return jsonify({"ok": False, "erro": "login"}), 401
    if (request.content_length or 0) > LIMITE_PEDIDO:
        return jsonify({"ok": False, "erro": "invalida", "msg": "Foto grande demais (máximo 8 MB)."}), 400
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        return jsonify({"ok": False, "erro": "csrf"}), 403
    if drive.cliente() is None:
        return jsonify({"ok": False, "erro": "drive", "msg": "Fotos não configuradas"}), 503
    arq = request.files.get("foto")
    if arq is None:
        return jsonify({"ok": False, "erro": "invalida", "msg": "Nenhuma foto recebida."}), 400
    f = request.form
    try:
        r = fotos.enviar(f.get("id_animal", ""), arq.read(), f.get("data"), f.get("tipo", "Evolução"),
                         f.get("legenda", ""), _membro_logado() or session.get("usuario", ""),
                         f.get("id_envio", ""))
    except fotos.FotoInvalida as e:
        return jsonify({"ok": False, "erro": "invalida", "msg": str(e)}), 400
    except drive.DriveErro as e:
        logging.warning(f"Envio de foto: {e}")
        return jsonify({"ok": False, "erro": "drive", "msg": str(e)}), 502
    return jsonify({"ok": True, **r})


def _acao(id_foto, fazer, msg_ok):
    _validar_csrf()
    if not _RE_ID.match(id_foto):
        abort(404)
    foto = fotos.por_id(id_foto)
    if foto is None:
        abort(404)
    try:
        fazer()
        flash(msg_ok, "success")
    except fotos.FotoInvalida as e:
        flash(str(e), "error")
    return redirect(url_for("ficha_animal", id_=foto["animal"]) + "#fotos")


@app.route("/fotos/<id_foto>/principal", methods=["POST"])
@login_required
def foto_principal(id_foto):
    return _acao(id_foto, lambda: fotos.definir_principal(id_foto), "⭐ Foto principal definida.")


@app.route("/fotos/<id_foto>/editar", methods=["POST"])
@login_required
def foto_editar(id_foto):
    f = request.form
    return _acao(id_foto, lambda: fotos.editar(id_foto, f.get("tipo", ""), f.get("legenda", ""),
                                                f.get("data", "")), "✏️ Foto atualizada.")


@app.route("/fotos/<id_foto>/excluir", methods=["POST"])
@login_required
def foto_excluir(id_foto):
    def fazer():
        fotos.excluir(id_foto)
        _apagar_do_cache(id_foto)
    return _acao(id_foto, fazer, "🗑️ Foto excluída (fica 30 dias na lixeira do Drive).")


@app.route("/privacidade")
def privacidade():
    """Pública (sem login): o Google exige o link para publicar o app OAuth do Drive."""
    return render_template("privacidade.html")
