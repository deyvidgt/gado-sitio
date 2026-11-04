#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preferências por sítio para módulos opcionais da aplicação."""
from __future__ import annotations

import json
import os
import tempfile


MODULOS = {
    "leite": {
        "nome": "Leite",
        "descricao": "Produção, animais leiteiros, ordenha e relatórios.",
    },
    "conforto": {
        "nome": "Conforto e Colchão",
        "descricao": "Conforto térmico e acompanhamento de colchões.",
        "depende_de": "leite",
    },
    "reproducao": {
        "nome": "Reprodução",
        "descricao": "Painel reprodutivo, IATF, observação de cio e previsão de partos.",
    },
    "genetica_confinamento": {
        "nome": "Genética e Confinamento",
        "descricao": "Consanguinidade, compatibilidade e lotes de confinamento.",
    },
}

_ROTAS_FIXAS = (
    ("/leite/alimentacao", None),
    ("/leite/necessidades", None),
    ("/leite/calculador", None),
    ("/leite/nutricao", None),
    ("/leite/consumo", None),
)


def preferencias(config: dict | None) -> dict[str, bool]:
    """Preferências persistidas; configurações antigas mantêm tudo ativo."""
    salvas = config.get("modulos") if isinstance(config, dict) else None
    salvas = salvas if isinstance(salvas, dict) else {}
    return {chave: salvas.get(chave) if isinstance(salvas.get(chave), bool) else True
            for chave in MODULOS}


def estado_efetivo(config: dict | None) -> dict[str, bool]:
    estado = preferencias(config)
    estado["conforto"] = estado["leite"] and estado["conforto"]
    return estado


def esta_ativo(chave: str, estado: dict[str, bool]) -> bool:
    if chave not in MODULOS:
        return True
    if chave == "conforto":
        return bool(estado.get("leite", True) and estado.get("conforto", True))
    return bool(estado.get(chave, True))


def estado_sitio() -> dict[str, bool]:
    """Estado efetivo da configuração já isolada pelo cache do sítio atual."""
    from extensions import _cache_get, _cache_set, _ler_sitio_config_disco

    config = _cache_get("sitio_config")
    if config is None:
        config = _ler_sitio_config_disco()
        _cache_set("sitio_config", config)
    return estado_efetivo(config)


def modulo_da_rota(caminho: str) -> str | None:
    """Resolve páginas/APIs controladas; deixa grupos fora do catálogo intactos."""
    caminho = str(caminho or "").rstrip("/") or "/"

    def corresponde(prefixo: str) -> bool:
        return caminho == prefixo or caminho.startswith(prefixo + "/")

    if corresponde("/api/leite"):
        return "leite"
    for prefixo, modulo in _ROTAS_FIXAS:
        if corresponde(prefixo):
            return modulo

    if corresponde("/leite"):
        if corresponde("/leite/conforto") or corresponde("/leite/colchao"):
            return "conforto"
        if any(corresponde(prefixo) for prefixo in (
            "/leite/alimentacao", "/leite/necessidades", "/leite/calculador",
            "/leite/nutricao", "/leite/consumo",
        )):
            return None
        return "leite"

    if any(corresponde(prefixo) for prefixo in ("/reproducao", "/partos", "/api/partos")):
        return "reproducao"
    if any(corresponde(prefixo) for prefixo in ("/genetica", "/api/genetica", "/confinamento")):
        return "genetica_confinamento"
    return None


def salvar_preferencias(caminho: str, valores: dict[str, bool]) -> None:
    """Atualiza somente as preferências, substituindo o JSON de forma atômica."""
    if not isinstance(valores, dict) or set(valores) != set(MODULOS) \
            or any(type(valor) is not bool for valor in valores.values()):
        raise ValueError("As opções de módulos são inválidas.")

    config = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as arquivo:
                config = json.load(arquivo)
        except (OSError, ValueError) as erro:
            raise ValueError("Não foi possível ler a configuração atual do sítio.") from erro
        if not isinstance(config, dict):
            raise ValueError("A configuração atual do sítio está inválida.")
    config["modulos"] = valores

    pasta = os.path.dirname(caminho) or "."
    temporario = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=pasta, delete=False) as arquivo:
            temporario = arquivo.name
            json.dump(config, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        os.replace(temporario, caminho)
    except OSError as erro:
        if temporario and os.path.exists(temporario):
            os.unlink(temporario)
        raise ValueError("Não foi possível salvar as preferências dos módulos.") from erro
