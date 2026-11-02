# -*- coding: utf-8 -*-
"""
bulas.py — bula (PDF) e foto da embalagem de cada remédio/vacina (v5.16).

Os arquivos ficam no Google Drive (pasta "Bulas e embalagens"), um por produto,
nomeados `<slug>__bula.pdf` e `<slug>__embalagem.jpg`. O site lista a pasta uma
vez e mostra o catálogo; quem quiser o arquivo baixa pelo próprio site (o Drive
é privado). Sem Drive, a página continua com o catálogo e diz o que falta.

`python subir_bulas.py <pasta local>` envia os arquivos (mesmo padrão do
subir_prints_ajuda.py).
"""
from __future__ import annotations

import logging
import os
import re

import drive
from doencas_carencia import PERIODOS_CARENCIA_PADRAO
from routes_fotos import cache_dir, limpar_cache
from saude import SUGESTOES_PRODUTO
from sitios import slug_do_nome

NOME_PASTA = "Bulas e embalagens"
SUFIXOS = {"bula": ".pdf", "embalagem": ".jpg"}
_RE_ARQUIVO = re.compile(r"[a-z0-9][a-z0-9-]*__(bula\.pdf|embalagem\.(jpg|png|webp))")


def slug(produto: str) -> str:
    """'Valbazen (albendazol)' → 'valbazen' — o parêntese é explicação, não nome."""
    return slug_do_nome(re.sub(r"\s*\([^)]*\)", "", str(produto or "")).strip())


def _catalogo_base() -> list[tuple[str, str]]:
    """(slug, nome para a tela) de tudo que o sistema conhece.
    O parêntese sai do nome do arquivo: "Poliguard (IBR/BVD)" → poliguard.pdf."""
    itens = {slug(n): n for n in PERIODOS_CARENCIA_PADRAO}
    for marcas in SUGESTOES_PRODUTO.values():
        for marca in marcas:
            itens.setdefault(slug(marca), marca)
    return sorted(itens.items(), key=lambda kv: kv[1].lower())


def catalogo() -> list[dict]:
    """Produtos com o que já existe no Drive: {'nome', 'bula', 'embalagem'}
    (o valor é o nome do arquivo, ou None quando falta)."""
    arquivos: set[str] = set()
    cli = drive.cliente()
    if cli is not None:
        try:
            arquivos = {a["name"] for a in cli.listar(cli.pasta(NOME_PASTA, {"bulas": "pasta"}))}
        except drive.DriveErro as e:
            logging.warning(f"Catálogo de bulas: {e}")
    out = []
    for chave, nome in _catalogo_base():
        bula = next((a for a in arquivos if a.startswith(chave + "__bula.")), None)
        foto = next((a for a in arquivos if a.startswith(chave + "__embalagem.")), None)
        out.append({"nome": nome, "bula": bula, "embalagem": foto})
    return out


def _cache_path(nome: str) -> str:
    return os.path.join(cache_dir(), f"bula_{nome}")


def arquivo(nome: str) -> bytes | None:
    """Conteúdo do arquivo (do cache ou do Drive); None se não existir."""
    if not _RE_ARQUIVO.fullmatch(nome):
        return None
    caminho = _cache_path(nome)
    if os.path.isfile(caminho):
        os.utime(caminho, None)   # marca como usado agora (limpeza pelos mais antigos)
        with open(caminho, "rb") as f:
            return f.read()
    cli = drive.cliente()
    if cli is None:
        return None
    try:
        fid = cli.achar_por_prop("bulas", nome)
        if not fid:
            return None
        dados = cli.baixar(fid)
    except drive.DriveErro as e:
        logging.warning(f"Bula {nome}: {e}")
        return None
    os.makedirs(cache_dir(), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(dados)
    limpar_cache()
    return dados
