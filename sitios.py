#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sitios.py — vários sítios no mesmo site (v5.0 fase 2)

<raiz>/sitios.json:
    {"sitios": {"santo-antonio": {"nome": "Sítio Santo Antonio", "pasta": ""},
                "joao": {"nome": "Sítio do João", "pasta": "sitios/joao"}},
     "acesso": {"deyvid": ["santo-antonio", "joao"], "joao": ["joao"]}}

Sem o arquivo: um sítio só (a própria raiz) e todo login entra — como sempre foi.
Com o arquivo, login fora de "acesso" não entra em nenhum.

ativar(slug) aponta db.DATA_DIR/ARQUIVO_PATH para a pasta do sítio e aplica os
donos dela. Quem chama no site é o before_request (extensions), um pedido por
vez por processo — os globais não se misturam entre sítios.
"""
from __future__ import annotations

import json
import os
import re

import config
import db

PADRAO = "santo-antonio"
_RE_SLUG = re.compile(r"[a-z0-9-]{1,40}")
_atual = PADRAO
_inicializadas: set = set()


def carregar() -> dict:
    try:
        with open(os.path.join(db.RAIZ, "sitios.json"), encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except (OSError, ValueError):
        cfg = {}
    sit = cfg.get("sitios") if isinstance(cfg.get("sitios"), dict) else {}
    if not sit:
        return {"sitios": {PADRAO: {"nome": config.NOME_SITIO, "pasta": ""}}, "acesso": None}
    return {"sitios": sit, "acesso": cfg.get("acesso") if isinstance(cfg.get("acesso"), dict) else {},
            "admins": cfg.get("admins") if isinstance(cfg.get("admins"), list) else None}


def pasta(slug: str) -> str:
    """Pasta absoluta do sítio — sempre dentro da raiz."""
    sit = carregar()["sitios"]
    if not isinstance(slug, str) or not _RE_SLUG.fullmatch(slug) or slug not in sit:
        raise ValueError(f"Sítio inválido: {slug!r}")
    raiz = os.path.abspath(db.RAIZ)
    p = os.path.abspath(os.path.join(raiz, str(sit[slug].get("pasta") or "")))
    if os.path.commonpath([raiz, p]) != raiz:
        raise ValueError(f"Pasta do sítio fora da raiz: {slug!r}")
    return p


def sitios_do_usuario(login: str) -> list[str]:
    cfg = carregar()
    if cfg["acesso"] is None:
        return list(cfg["sitios"])
    acesso = {str(k).strip().lower(): v for k, v in cfg["acesso"].items()}
    pedidos = acesso.get(str(login or "").strip().lower()) or []
    return [s for s in cfg["sitios"] if s in pedidos]


def tem_acesso(login: str, slug: str) -> bool:
    return slug in sitios_do_usuario(login)


def e_admin(login: str) -> bool:
    """Quem gerencia usuários e sítios. Sem sitios.json: todos (como sempre foi).
    Sem "admins": quem tem acesso ao 1º sítio — ninguém de fora vira admin por esquecimento."""
    cfg = carregar()
    if cfg["acesso"] is None:
        return True
    login = str(login or "").strip().lower()
    if cfg["admins"] is not None:
        return login in {str(a).strip().lower() for a in cfg["admins"]}
    return tem_acesso(login, next(iter(cfg["sitios"])))


def logins_do_sitio(slug: str, logins) -> list:
    """Dos `logins`, os que têm acesso ao sítio (o que um não-admin pode ver)."""
    return [l for l in logins if tem_acesso(l, slug)]


def nome(slug: str) -> str:
    return str(carregar()["sitios"].get(slug, {}).get("nome") or slug)


def ativar(slug: str) -> None:
    """Entra no sítio: pasta de dados e donos dele (arquivo criado na 1ª vez)."""
    global _atual
    p = pasta(slug)
    db.usar_pasta(p)
    try:
        with open(os.path.join(p, "sitio_config.json"), encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except (OSError, ValueError):
        cfg = {}
    config.aplicar_membros(config.ler_membros(cfg))
    _atual = slug
    if p not in _inicializadas or not os.path.exists(db.ARQUIVO_PATH):
        db.inicializar()
        _inicializadas.add(p)


def atual() -> str:
    return _atual


def cada_sitio():
    """Para as Tasks (processos próprios, sem a trava do site): entra em cada
    sítio, um por vez, e no fim volta ao primeiro."""
    lista = list(carregar()["sitios"])
    try:
        for slug in lista:
            ativar(slug)
            yield slug
    finally:
        ativar(lista[0])
