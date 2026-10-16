#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subir_prints_ajuda.py — envia os prints da aba ❓ Ajuda para o Google Drive (v4.5).

    python subir_prints_ajuda.py <pasta com os .png>

Vão para "sitio santo antonio / Ajuda - passo a passo", cada um marcado com
appProperties ajuda=<nome> (é por essa marca que o site acha o print). Um print
com o mesmo nome substitui o anterior (o antigo vai para a lixeira do Drive).
Nomes: minúsculas, números e hífen — "c-" celular, "p-" computador.
Usa o drive_token.json da pasta de dados (GADO_DATA_DIR ou ~/gado-dados).
"""
import os
import sys

import drive
from routes_ajuda import _RE_NOME

NOME_PASTA = "Ajuda - passo a passo"


def subir(pasta_local: str, cli) -> list[str]:
    """Envia os .png válidos; devolve os nomes enviados."""
    destino = cli.pasta(NOME_PASTA, {"ajuda": "pasta"})
    enviados = []
    for nome in sorted(os.listdir(pasta_local)):
        if not _RE_NOME.fullmatch(nome):
            if nome.lower().endswith(".png"):
                print(f"⚠️  ignorado (nome fora do padrão): {nome}")
            continue
        with open(os.path.join(pasta_local, nome), "rb") as f:
            conteudo = f.read()
        antigo = cli.achar_por_prop("ajuda", nome)
        cli.enviar(destino, nome, conteudo, "image/png", {"ajuda": nome})
        if antigo:
            cli.lixeira(antigo)
        enviados.append(nome)
        print(f"✅ {nome}{' (substituído)' if antigo else ''}")
    return enviados


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("Uso: python subir_prints_ajuda.py <pasta com os .png>")
    cli = drive.cliente()
    if cli is None:
        sys.exit("❌ Drive não configurado (falta o drive_token.json). Veja docs/FOTOS_DRIVE.md.")
    n = len(subir(sys.argv[1], cli))
    print(f"📤 {n} print(s) enviados para '{NOME_PASTA}'. No servidor, o cache antigo some "
          "sozinho; para ver na hora apague ~/gado-dados/cache_fotos/ajuda_*.")


if __name__ == "__main__":
    main()
