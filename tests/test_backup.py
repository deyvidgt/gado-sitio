# -*- coding: utf-8 -*-
"""
Testes do backup: o script diário e a limpeza do site precisam usar a pasta
de DADOS (GADO_DATA_DIR / ~/gado-dados/), nunca a pasta do código.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

import db
from conftest import RAIZ, TEM_DADOS_REAIS


@pytest.mark.skipif(not TEM_DADOS_REAIS, reason="sem gado_familia.xlsx para copiar")
def test_script_diario_faz_backup_na_pasta_de_dados():
    pasta = tempfile.mkdtemp(prefix="gado_bkp_")
    try:
        shutil.copy2(db.ARQUIVO_PATH, os.path.join(pasta, "gado_familia.xlsx"))
        env = dict(os.environ, GADO_DATA_DIR=pasta, PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, os.path.join(RAIZ, "backup_automatico.py")],
                              env=env, capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr

        gerados = os.listdir(os.path.join(pasta, "backups"))
        assert any(n.startswith("backup_") and n.endswith(".xlsx") for n in gerados)
        # nada pode ter sido criado na pasta do código
        assert not os.path.exists(os.path.join(RAIZ, "backups"))
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def test_script_diario_falha_sem_planilha():
    pasta = tempfile.mkdtemp(prefix="gado_bkp_vazio_")
    try:
        env = dict(os.environ, GADO_DATA_DIR=pasta, PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, os.path.join(RAIZ, "backup_automatico.py")],
                              env=env, capture_output=True, text=True, timeout=120)
        assert proc.returncode != 0  # falha visível no log da Task
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def test_limpeza_do_site_atua_na_pasta_de_dados():
    from extensions import _limpar_backups_antigos
    pasta = os.path.join(db.DATA_DIR, "backups")
    os.makedirs(pasta, exist_ok=True)
    criados = []
    for i in range(5):
        p = os.path.join(pasta, f"backup_2020010{i + 1}_000000.xlsx")
        open(p, "wb").close()
        os.utime(p, (1_600_000_000 + i, 1_600_000_000 + i))
        criados.append(p)
    try:
        _limpar_backups_antigos(max_backups=2)
        restantes = sorted(n for n in os.listdir(pasta) if n.startswith("backup_2020"))
        assert restantes == ["backup_20200104_000000.xlsx", "backup_20200105_000000.xlsx"]
    finally:
        for p in criados:
            if os.path.exists(p):
                os.remove(p)


def test_backup_aparece_na_pagina_backups(cliente):
    pasta = os.path.join(db.DATA_DIR, "backups")
    os.makedirs(pasta, exist_ok=True)
    nome = "backup_20991231_235959.xlsx"
    caminho = os.path.join(pasta, nome)
    shutil.copy2(db.ARQUIVO_PATH, caminho)
    try:
        assert nome in cliente.get("/backups").get_data(as_text=True)
        assert cliente.get(f"/backups/download/{nome}").status_code == 200
    finally:
        os.remove(caminho)
