#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subir_bulas.py — envia bulas (PDF) e fotos de embalagem para o Google Drive (v5.16).

    python subir_bulas.py <pasta com os arquivos>

Cada arquivo vira `<produto>__bula.pdf` ou `<produto>__embalagem.jpg` dentro de
"sitio santo antonio / Bulas e embalagens" (é por esse nome que o site acha).
Um arquivo com o mesmo nome substitui o anterior (o antigo vai para a lixeira).

Aceita os nomes já prontos (`ivermectina__bula.pdf`) ou um nome só com a extensão
(`ivermectina.pdf`, `ivermectina.jpg` → vira bula ou embalagem pela extensão).
Usa o drive_token.json da pasta de dados (GADO_DATA_DIR ou ~/gado-dados).
"""
import os
import sys

import drive
import bulas

_MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".png": "image/png", ".webp": "image/webp"}
# Extensão gravada: .jpeg vira .jpg (mesmos bytes, nome que o site reconhece).
_EXT = {".pdf": ".pdf", ".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}


def nome_destino(arquivo: str) -> str | None:
    """'Ivermectina.pdf' → 'ivermectina__bula.pdf'; None se não é bula/embalagem."""
    base, ext = os.path.splitext(arquivo.lower())
    if ext not in _MIME:
        return None
    tipo = "bula" if ext == ".pdf" else "embalagem"
    base = bulas.slug(base.replace("__bula", "").replace("__embalagem", ""))
    return f"{base}__{tipo}{_EXT[ext]}"


def subir(pasta_local: str, cli) -> list[str]:
    """Envia os arquivos válidos; devolve os nomes enviados."""
    destino = cli.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
    enviados = []
    for arquivo in sorted(os.listdir(pasta_local)):
        nome = nome_destino(arquivo)
        if nome is None:
            continue
        with open(os.path.join(pasta_local, arquivo), "rb") as f:
            conteudo = f.read()
        if not bulas._RE_ARQUIVO.fullmatch(nome):
            print(f"⚠️  ignorado (nome fora do padrão): {arquivo}")
            continue
        antigo = cli.achar_por_prop("bulas", nome)
        cli.enviar(destino, nome, conteudo, _MIME[os.path.splitext(nome)[1]], {"bulas": nome})
        if antigo:
            cli.lixeira(antigo)
        enviados.append(nome)
        print(f"✅ {nome}{' (substituído)' if antigo else ''}")
    return enviados


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("Uso: python subir_bulas.py <pasta com os PDFs e fotos>")
    cli = drive.cliente()
    if cli is None:
        sys.exit("❌ Drive não configurado (falta o drive_token.json). Veja docs/FOTOS_DRIVE.md.")
    n = len(subir(sys.argv[1], cli))
    print(f"📤 {n} arquivo(s) enviados para '{bulas.NOME_PASTA}'.")


if __name__ == "__main__":
    main()
