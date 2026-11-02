# -*- coding: utf-8 -*-
"""
routes_bulas.py — página 📖 Bulas (v5.16): bula em PDF e foto da embalagem de
cada remédio/vacina, guardadas no Drive (bulas.py) e servidas só para quem
está logado.
"""
import os

from flask import Response, abort, render_template

import bulas
import drive
from extensions import app, login_required

_MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png",
         ".webp": "image/webp"}


@app.route("/bulas")
@login_required
def listar_bulas():
    return render_template("bulas.html", catalogo=bulas.catalogo(),
                           drive_ok=drive.cliente() is not None)


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
