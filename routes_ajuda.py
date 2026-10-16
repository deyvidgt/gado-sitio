# -*- coding: utf-8 -*-
"""
routes_ajuda.py — aba ❓ Ajuda (v4.5): passo a passo de todo o sistema.

Os prints ficam no Google Drive (pasta "Ajuda - passo a passo", enviada por
subir_prints_ajuda.py), cada um marcado com appProperties ajuda=<nome>. O site
acha pelo nome, baixa uma vez e guarda no mesmo cache das fotos. Sem Drive, a
página continua com o texto e mostra "imagem indisponível" no lugar do print.
"""
import logging
import os
import re

from flask import Response, abort, render_template

import drive
from extensions import app, login_required
from routes_fotos import cache_dir, limpar_cache

_RE_NOME = re.compile(r"[a-z0-9][a-z0-9-]*\.png")


def _print(nome: str) -> bytes:
    if not _RE_NOME.fullmatch(nome):
        abort(404)
    caminho = os.path.join(cache_dir(), f"ajuda_{nome}")
    if os.path.isfile(caminho):
        os.utime(caminho, None)
        with open(caminho, "rb") as f:
            return f.read()
    cli = drive.cliente()
    if cli is None:
        abort(404)
    try:
        fid = cli.achar_por_prop("ajuda", nome)
        if not fid:
            abort(404)
        dados = cli.baixar(fid)
    except drive.DriveErro as e:
        logging.warning(f"Print da ajuda {nome}: {e}")
        abort(502)
    os.makedirs(cache_dir(), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(dados)
    limpar_cache()
    return dados


@app.route("/ajuda")
@login_required
def ajuda():
    return render_template("ajuda.html", prints_ativos=drive.cliente() is not None)


@app.route("/ajuda/img/<nome>")
@login_required
def ajuda_img(nome):
    r = Response(_print(nome), mimetype="image/png")
    r.headers["Cache-Control"] = "private, max-age=604800"
    return r
