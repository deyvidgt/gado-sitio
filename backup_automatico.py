#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backup_automatico.py — Sítio Santo Antonio
==========================================
Faz backup diário do gado_familia.xlsx e usuarios.json
para a pasta backups/ DA PASTA DE DADOS (~/gado-dados/backups/), com timestamp.

Os backups da planilha usam o mesmo nome dos backups do site
(backup_AAAAMMDD_HHMMSS.xlsx), então aparecem na página "Backups" e podem
ser baixados por lá — é o jeito fácil de guardar uma cópia fora do servidor.

Configure no PythonAnywhere em:
  Dashboard → Tasks → Add a new scheduled task
  Comando: python3 /home/deyvidgt16/gado/backup_automatico.py
  Horário: Daily às 03:00

Mantém os últimos 30 backups e apaga os mais antigos.
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

import sys

# ── Configuração ──────────────────────────────────────────────────────────────
# Os dados NÃO ficam na pasta do código: usa a mesma resolução do site
# (GADO_DATA_DIR → ~/gado-dados/ → ...). Antes usava a pasta do script e, em
# produção, copiava um arquivo velho (ou nenhum) em vez do ~/gado-dados/.
sys.path.insert(0, str(Path(__file__).parent))
from db import _resolver_data_dir  # noqa: E402

DATA_DIR    = Path(_resolver_data_dir())
BACKUP_DIR  = DATA_DIR / "backups"
MAX_BACKUPS = 30   # quantos backups manter

XLSX         = DATA_DIR / "gado_familia.xlsx"
USUARIOS     = DATA_DIR / "usuarios.json"
# arquivo → prefixo do backup ("backup_" é o mesmo padrão da página Backups)
ARQUIVOS_BACKUP = [
    (XLSX,     "backup_"),
    (USUARIOS, "usuarios_"),
]

LOG_FILE = BACKUP_DIR / "backup.log"

# ── Logging ───────────────────────────────────────────────────────────────────
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)

def fazer_backup():
    agora     = datetime.now().strftime("%Y%m%d_%H%M%S")
    copiados  = []
    erros     = []

    for arquivo, prefixo in ARQUIVOS_BACKUP:
        if not arquivo.exists():
            logging.warning(f"Arquivo não encontrado: {arquivo}")
            continue
        nome_backup = BACKUP_DIR / f"{prefixo}{agora}{arquivo.suffix}"
        try:
            shutil.copy2(arquivo, nome_backup)
            tam = nome_backup.stat().st_size / 1024
            logging.info(f"Backup OK: {nome_backup.name}  ({tam:.1f} KB)")
            copiados.append(nome_backup.name)
        except Exception as e:
            logging.error(f"Erro ao copiar {arquivo.name}: {e}")
            erros.append(str(e))

    return copiados, erros

def limpar_backups_antigos():
    """Mantém apenas os MAX_BACKUPS arquivos mais recentes de cada tipo."""
    removidos = 0
    for padrao in ["backup_*.xlsx", "usuarios_*.json"]:
        arquivos = sorted(
            BACKUP_DIR.glob(padrao),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for antigo in arquivos[MAX_BACKUPS:]:
            try:
                antigo.unlink()
                logging.info(f"Backup antigo removido: {antigo.name}")
                removidos += 1
            except Exception as e:
                logging.error(f"Erro ao remover {antigo.name}: {e}")
    return removidos

def verificar_integridade():
    """Verifica se o gado_familia.xlsx está íntegro (não vazio e abrível)."""
    xlsx = XLSX
    if not xlsx.exists():
        logging.error("CRÍTICO: gado_familia.xlsx não encontrado!")
        return False
    tam = xlsx.stat().st_size
    if tam < 5000:  # arquivo menor que 5KB provavelmente está corrompido/vazio
        logging.warning(f"ATENÇÃO: gado_familia.xlsx parece muito pequeno ({tam} bytes)!")
        return False
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        abas = wb.sheetnames
        wb.close()
        logging.info(f"Integridade OK: {tam/1024:.1f} KB, abas: {abas}")
        return True
    except Exception as e:
        logging.error(f"CRÍTICO: gado_familia.xlsx corrompido! {e}")
        return False

if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info(f"Iniciando backup automático — dados em {DATA_DIR}")

    ok = verificar_integridade()
    erros = []
    if not ok:
        logging.error("Backup abortado — arquivo com problema.")
    else:
        copiados, erros = fazer_backup()
        removidos = limpar_backups_antigos()
        logging.info(
            f"Concluído: {len(copiados)} arquivo(s) copiado(s), "
            f"{removidos} backup(s) antigo(s) removido(s), "
            f"{len(erros)} erro(s)."
        )

    logging.info("=" * 60)
    # Código de saída ≠ 0 faz a falha aparecer no log da Task do PythonAnywhere
    sys.exit(0 if ok and not erros else 1)
