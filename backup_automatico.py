from agora import agora
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
# Vários sítios (v5.0): cada um faz backup na sua pasta; os arquivos da família
# (usuarios.json, sitios.json) só na pasta principal.
sys.path.insert(0, str(Path(__file__).parent))
from pasta_dados import _resolver_data_dir  # noqa: E402

DATA_DIR    = Path(os.path.abspath(_resolver_data_dir()))
BACKUP_DIR  = DATA_DIR / "backups"
MAX_BACKUPS = 30   # quantos backups manter

LOG_FILE = BACKUP_DIR / "backup.log"

# ── Logging ───────────────────────────────────────────────────────────────────
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)


def pastas_dos_sitios() -> list[Path]:
    """Pasta principal primeiro, depois a de cada sítio do sitios.json."""
    import sitios
    pastas = []
    for slug in sitios.carregar()["sitios"]:
        p = Path(os.path.abspath(sitios.pasta(slug)))
        if p not in pastas:
            pastas.append(p)
    return pastas or [DATA_DIR]


def arquivos_backup(pasta: Path) -> list[tuple[Path, str]]:
    # arquivo → prefixo do backup ("backup_" é o mesmo padrão da página Backups)
    arquivos = [(pasta / "gado_familia.xlsx", "backup_")]
    if pasta == DATA_DIR:
        arquivos += [(pasta / "usuarios.json", "usuarios_"), (pasta / "sitios.json", "sitios_")]
    return arquivos


def fazer_backup(pasta: Path = DATA_DIR):
    agora     = agora().strftime("%Y%m%d_%H%M%S")
    copiados  = []
    erros     = []
    destino   = pasta / "backups"
    destino.mkdir(parents=True, exist_ok=True)

    for arquivo, prefixo in arquivos_backup(pasta):
        if not arquivo.exists():
            if prefixo != "sitios_":   # sem sitios.json é o normal (um sítio só)
                logging.warning(f"Arquivo não encontrado: {arquivo}")
            continue
        nome_backup = destino / f"{prefixo}{agora}{arquivo.suffix}"
        try:
            shutil.copy2(arquivo, nome_backup)
            tam = nome_backup.stat().st_size / 1024
            logging.info(f"Backup OK: {nome_backup}  ({tam:.1f} KB)")
            copiados.append(nome_backup.name)
        except Exception as e:
            logging.error(f"Erro ao copiar {arquivo}: {e}")
            erros.append(str(e))

    return copiados, erros

def limpar_backups_antigos(pasta: Path = DATA_DIR):
    """Mantém apenas os MAX_BACKUPS arquivos mais recentes de cada tipo."""
    removidos = 0
    for padrao in ["backup_*.xlsx", "usuarios_*.json", "sitios_*.json"]:
        arquivos = sorted(
            (pasta / "backups").glob(padrao),
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

def verificar_integridade(pasta: Path = DATA_DIR):
    """Verifica se o gado_familia.xlsx está íntegro (não vazio e abrível)."""
    xlsx = pasta / "gado_familia.xlsx"
    if not xlsx.exists():
        logging.error(f"CRÍTICO: {xlsx} não encontrado!")
        return False
    tam = xlsx.stat().st_size
    if tam < 5000:  # arquivo menor que 5KB provavelmente está corrompido/vazio
        logging.warning(f"ATENÇÃO: {xlsx} parece muito pequeno ({tam} bytes)!")
        return False
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        abas = wb.sheetnames
        wb.close()
        logging.info(f"Integridade OK: {tam/1024:.1f} KB, abas: {abas}")
        return True
    except Exception as e:
        logging.error(f"CRÍTICO: {xlsx} corrompido! {e}")
        return False

if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info(f"Iniciando backup automático — dados em {DATA_DIR}")

    tudo_ok = True
    for pasta in pastas_dos_sitios():
        # Um sítio com problema não impede o backup dos outros.
        if not verificar_integridade(pasta):
            logging.error(f"Backup de {pasta} abortado — arquivo com problema.")
            tudo_ok = False
            continue
        copiados, erros = fazer_backup(pasta)
        removidos = limpar_backups_antigos(pasta)
        tudo_ok = tudo_ok and not erros
        logging.info(
            f"{pasta}: {len(copiados)} arquivo(s) copiado(s), "
            f"{removidos} backup(s) antigo(s) removido(s), "
            f"{len(erros)} erro(s)."
        )

    logging.info("=" * 60)
    # Código de saída ≠ 0 faz a falha aparecer no log da Task do PythonAnywhere
    sys.exit(0 if tudo_ok else 1)
