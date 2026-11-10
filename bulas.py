# -*- coding: utf-8 -*-
"""
bulas.py — bula (PDF) e foto da embalagem de cada remédio/vacina (v5.16).

Os arquivos ficam no Google Drive (pasta "Bulas e embalagens"), um por produto,
nomeados `<slug>__bula.pdf` e `<slug>__embalagem.jpg`. O site lista a pasta uma
vez e mostra o catálogo; quem quiser o arquivo baixa pelo próprio site (o Drive
é privado). Sem Drive, a página continua com o catálogo e diz o que falta.

Administradores também podem baixar um PDF de URL oficial permitida, conferir a
prévia e enviá-lo pela página. `python subir_bulas.py <pasta local>` continua
disponível para envio manual.
"""
from __future__ import annotations

import logging
import os
import re
from urllib.parse import urljoin, urlparse

import drive
import requests
from doencas_carencia import PERIODOS_CARENCIA_PADRAO
from routes_fotos import cache_dir, limpar_cache
from saude import SUGESTOES_PRODUTO
from sitios import slug_do_nome

NOME_PASTA = "Bulas e embalagens"
SUFIXOS = {"bula": ".pdf", "embalagem": ".jpg"}
_RE_ARQUIVO = re.compile(r"[a-z0-9][a-z0-9-]*__(bula\.pdf|embalagem\.(jpg|png|webp))")
_DOMINIOS_OFICIAIS = (
    "zoetis.com", "zoetis.com.br", "zoetis.pt",
    "msd-saude-animal.com.br", "msd-animal-health.com", "msd-animal-health.pt", "msd.com",
    "boehringer-ingelheim.com", "boehringer-ingelheim.com.br", "boehringer-ingelheim.pt",
    "elanco.com", "elanco.com.br", "elanco.pt",
    "ourofinosaudeanimal.com", "ourofinosaudeanimal.com.br",
    "ceva.com", "ceva.com.br", "ceva.pt",
    "virbac.com", "virbac.com.br", "virbac.pt",
    "dechra.com", "dechra.com.br", "vetnil.com.br", "hertape.com.br",
    "biogenesisbago.com", "biogenesisbago.com.br", "vetoquinol.com", "vetoquinol.com.br",
    "agener.com.br", "vallee.com.br", "bimeda.com", "bimeda.com.br", "labovet.com.br",
    "merial.com", "ivomec.com", "ivomec.com.br",
)
_ORGAOS_OFICIAIS = ("woah.org", "europa.eu")
LIMITE_BULA_BYTES = 25 * 1024 * 1024
MAX_REDIRECTS = 5


class BulaFonteErro(ValueError):
    """URL não oficial, PDF inválido ou falha ao baixar a bula."""


def validar_url_oficial(url: str) -> tuple[str, str | None]:
    """Valida a URL. Se não for de domínio estrito conhecido, permite com aviso."""
    try:
        partes = urlparse(str(url or "").strip())
        host = (partes.hostname or "").rstrip(".").lower()
        porta_ok = partes.port in (None, 443)
    except ValueError as e:
        raise BulaFonteErro("URL da bula inválida.") from e

    if partes.scheme != "https" or not host or not porta_ok or partes.username or partes.password:
        raise BulaFonteErro("URL inválida: use HTTPS e um domínio válido.")

    oficial = (
        host == "gov" or host.endswith((".gov", ".gov.br", ".gov.pt", ".org", ".com.br", ".pt"))
        or any(host == dominio or host.endswith("." + dominio)
               for dominio in (*_DOMINIOS_OFICIAIS, *_ORGAOS_OFICIAIS))
    )
    aviso = None
    if not oficial:
        aviso = f"Aviso: O domínio '{host}' não é oficial, mas foi aceite."
    return partes.geturl(), aviso


def baixar_bula(url: str) -> tuple[bytes, str]:
    """Baixa um PDF de qualquer URL HTTPS válida, inclusive redirecionamentos verificados."""
    url_valida, aviso = validar_url_oficial(url)
    destino = url_valida
    for tentativa in range(MAX_REDIRECTS + 1):
        try:
            resposta = requests.get(
                destino, timeout=(5, 25), stream=True, allow_redirects=False,
                headers={"User-Agent": "GadoSitio/1.0 (download de bula veterinaria)"},
            )
        except requests.RequestException as e:
            if isinstance(e, requests.exceptions.ProxyError) or "proxy" in str(e).lower() or "403" in str(e):
                raise BulaFonteErro(
                    "O download direto foi bloqueado por restrições de rede ou proxy (403/Proxy). "
                    "Por favor, descarregue o PDF da bula no seu computador e adicione-o "
                    "diretamente na pasta 'Bulas e embalagens' do Google Drive ou faça o upload manual."
                ) from e
            raise BulaFonteErro(f"Não foi possível baixar a bula: {e}") from e
        try:
            if resposta.is_redirect or resposta.is_permanent_redirect:
                local = resposta.headers.get("Location")
                if not local or tentativa == MAX_REDIRECTS:
                    raise BulaFonteErro("A fonte redirecionou demais ou sem destino.")
                url_valida, _ = validar_url_oficial(urljoin(destino, local))
                destino = url_valida
                continue
            if resposta.status_code == 403:
                raise BulaFonteErro(
                    "A fonte negou o acesso (HTTP 403 / bloqueio de proxy ou origem). "
                    "Por favor, descarregue o PDF da bula no seu computador e adicione-o "
                    "diretamente na pasta 'Bulas e embalagens' do Google Drive ou faça o upload manual."
                )
            if resposta.status_code != 200:
                raise BulaFonteErro(f"A fonte respondeu HTTP {resposta.status_code}.")
            blocos = []
            total = 0
            for bloco in resposta.iter_content(64 * 1024):
                if not bloco:
                    continue
                total += len(bloco)
                if total > LIMITE_BULA_BYTES:
                    raise BulaFonteErro("O PDF excede o limite de 25 MB.")
                blocos.append(bloco)
            conteudo = b"".join(blocos)
            if not conteudo.startswith(b"%PDF-"):
                raise BulaFonteErro("O arquivo recebido não é um PDF válido.")
            return conteudo, (aviso or destino)
        finally:
            resposta.close()
    raise BulaFonteErro("Não foi possível obter o PDF da fonte oficial.")


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


def _arquivos_locais() -> set[str]:
    """Nomes lógicos (ex.: ivermectina__bula.pdf) já guardados no cache do sítio."""
    pasta = cache_dir()
    if not os.path.isdir(pasta):
        return set()
    out = set()
    for nome in os.listdir(pasta):
        if nome.startswith("bula_") and _RE_ARQUIVO.fullmatch(nome[5:]):
            out.add(nome[5:])
    return out


def _slug_do_arquivo(nome: str) -> str | None:
    m = _RE_ARQUIVO.fullmatch(nome or "")
    return m.group(0).split("__", 1)[0] if m else None


def catalogo() -> list[dict]:
    """Produtos com o que já existe no Drive ou no cache local:
    {'nome', 'bula', 'embalagem'} (nome do arquivo, ou None quando falta)."""
    arquivos: set[str] = set()
    cli = drive.cliente()
    if cli is not None:
        try:
            arquivos = {a["name"] for a in cli.listar(cli.pasta(NOME_PASTA, {"bulas": "pasta"}))}
        except drive.DriveErro as e:
            logging.warning(f"Catálogo de bulas: {e}")
    arquivos |= _arquivos_locais()

    base = dict(_catalogo_base())
    for arq in arquivos:
        chave = _slug_do_arquivo(arq)
        if chave and chave not in base:
            base[chave] = chave.replace("-", " ").title()

    out = []
    for chave, nome in sorted(base.items(), key=lambda kv: kv[1].lower()):
        bula = next((a for a in arquivos if a.startswith(chave + "__bula.")), None)
        foto = next((a for a in arquivos if a.startswith(chave + "__embalagem.")), None)
        out.append({"nome": nome, "bula": bula, "embalagem": foto})
    return out


def _cache_path(nome: str) -> str:
    return os.path.join(cache_dir(), f"bula_{nome}")


def guardar_local(nome: str, conteudo: bytes) -> str:
    """Grava a bula no cache do sítio para aparecer em Disponíveis mesmo sem Drive."""
    if not _RE_ARQUIVO.fullmatch(nome):
        raise BulaFonteErro("Nome de arquivo de bula inválido.")
    caminho = _cache_path(nome)
    os.makedirs(cache_dir(), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "wb") as f:
        f.write(conteudo)
    os.replace(tmp, caminho)
    limpar_cache()
    return caminho


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
    guardar_local(nome, dados)
    return dados
