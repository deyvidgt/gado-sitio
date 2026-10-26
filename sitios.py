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


# ── Criar sítio e mudar acessos (tela de Configurações, só admin) ────────────

def _gravar_json(caminho: str, dados) -> None:
    """Grava inteiro ou nada (tmp + os.replace): um sitios.json pela metade
    trancaria todo mundo fora."""
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)


def _arquivo_atual(todos_logins) -> dict:
    """sitios.json como está — ou o equivalente ao de hoje (um sítio, todos com acesso)."""
    caminho = os.path.join(db.RAIZ, "sitios.json")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return {"sitios": {PADRAO: {"nome": nome(PADRAO), "pasta": ""}},
            "acesso": {str(l).lower(): [PADRAO] for l in todos_logins}}


def chave_do_nome(texto: str) -> str:
    """'Maria Clara' → 'MariaClara' (só letras: vira coluna "Qtd MariaClara")."""
    import unicodedata
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return "".join(p.capitalize() for p in re.findall(r"[A-Za-z]+", sem_acento))


def slug_do_nome(texto: str) -> str:
    import unicodedata
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento).strip("-")[:40]


def criar(nome_sitio: str, slug: str, membros: list, acesso_logins, todos_logins) -> str:
    """Cria a pasta sitios/<slug> com os donos e libera o acesso. ValueError com a
    mensagem para a tela; nada é gravado se algo estiver errado."""
    nome_sitio = str(nome_sitio or "").strip()
    if not nome_sitio or len(nome_sitio) > 60:
        raise ValueError("Dê um nome ao sítio (até 60 letras).")
    slug = slug or slug_do_nome(nome_sitio)
    if not _RE_SLUG.fullmatch(slug or ""):
        raise ValueError("Endereço do sítio inválido (use letras minúsculas, números e -).")
    cfg = _arquivo_atual(todos_logins)
    if slug in cfg["sitios"]:
        raise ValueError(f"Já existe um sítio '{slug}'.")
    if config.ler_membros({"membros": membros}) is config.MEMBROS_PADRAO:
        raise ValueError(f"Donos inválidos: de {config.MEMBROS_MIN} a {config.MEMBROS_MAX}, "
                         "cada um com nome e uma cor de brinco diferente.")
    todos = {str(l).lower() for l in todos_logins}
    pasta_rel = f"sitios/{slug}"
    p = os.path.join(db.RAIZ, pasta_rel)
    if os.path.exists(os.path.join(p, "sitio_config.json")):
        raise ValueError(f"A pasta {pasta_rel} já tem um sítio.")
    os.makedirs(p, exist_ok=True)
    _gravar_json(os.path.join(p, "sitio_config.json"), {"nome": nome_sitio, "membros": membros})
    cfg["sitios"][slug] = {"nome": nome_sitio, "pasta": pasta_rel}
    for login in acesso_logins:
        login = str(login).lower()
        if login in todos:
            cfg.setdefault("acesso", {}).setdefault(login, [])
            if slug not in cfg["acesso"][login]:
                cfg["acesso"][login].append(slug)
    _gravar_json(os.path.join(db.RAIZ, "sitios.json"), cfg)
    return slug


def salvar_acesso(acesso: dict, quem: str, todos_logins) -> None:
    """acesso = {login: [slugs]}. Recusa se `quem` (o admin que está mudando)
    deixaria de ser admin — sempre sobra alguém para administrar."""
    cfg = _arquivo_atual(todos_logins)
    validos = set(cfg["sitios"])
    todos = {str(l).lower() for l in todos_logins}
    novo = {l: [s for s in cfg["sitios"] if s in set(slugs) & validos]
            for l, slugs in acesso.items() if l in todos}
    antes = cfg.get("acesso")
    cfg["acesso"] = novo
    caminho = os.path.join(db.RAIZ, "sitios.json")
    _gravar_json(caminho, cfg)
    if not e_admin(quem):
        cfg["acesso"] = antes
        _gravar_json(caminho, cfg)
        raise ValueError("Você deixaria de ser administrador — mantenha o seu acesso ao "
                         f"{nome(next(iter(cfg['sitios'])))}.")


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
