#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onde ficam os dados (gado_familia.xlsx, sitio_config.json, backups/).
Separado do db.py porque o config.py precisa saber disso ao importar (os donos
do sítio vêm do sitio_config.json) e o db.py importa o config."""
import os
import sys


def _resolver_data_dir() -> str:
    """
    Resolve onde ficam os dados, independente de como o programa foi iniciado.

    Prioridade:
      1. Variável de ambiente GADO_DATA_DIR   (configuração manual)
      2. ~/gado-dados/                         (padrão PythonAnywhere — fora do Git)
      3. Pasta do executável (.exe)             (Windows compilado)
      4. Pasta do script atual                  (desenvolvimento)
    """
    # 1) Variável de ambiente explícita (útil para testes e outras hospedagens)
    if os.environ.get("GADO_DATA_DIR"):
        pasta = os.path.expanduser(os.environ["GADO_DATA_DIR"])
        os.makedirs(pasta, exist_ok=True)
        return pasta

    # 2) ~/gado-dados/ — pasta permanente fora do repositório Git
    #    Funciona no PythonAnywhere e em qualquer servidor Linux/Mac
    pasta_permanente = os.path.expanduser("~/gado-dados")
    if os.path.isdir(pasta_permanente):
        return pasta_permanente

    # 3) Modo .exe (PyInstaller/Windows)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    # 4) Fallback: pasta do próprio script (desenvolvimento local)
    return os.path.dirname(os.path.abspath(__file__))
