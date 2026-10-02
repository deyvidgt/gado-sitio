#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations  # compatibilidade Python 3.9+
"""
Camada de acesso a dados — leitura, escrita e backup do Excel

IMPORTANTE — onde ficam os dados:
  Os dados (gado_familia.xlsx, usuarios.json, backups/) ficam em ~/gado-dados/,
  FORA do repositório Git. Assim o git pull nunca mais apaga seus dados.

  Hierarquia de busca do DATA_DIR:
    1. ~/gado-dados/          → pasta permanente fora do Git (produção)
    2. Pasta do executável    → modo .exe (Windows)
    3. Pasta do script        → desenvolvimento local
"""

import os, sys
import shutil
import pandas as pd
from datetime import datetime
from openpyxl import Workbook, load_workbook


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


# DATA_DIR é onde ficam gado_familia.xlsx, usuarios.json e backups/
# É DIFERENTE da pasta do código — isso protege os dados do git pull
DATA_DIR = _resolver_data_dir()

from config import (
    ARQUIVO_DADOS,
    COLUNAS_COMPRAS, COLUNAS_GASTOS,
    COLUNAS_VENDAS, COLUNAS_MANEJO, COLUNAS_VISITAS,
)

# Mapa aba → colunas esperadas, usado para migrar colunas novas sem perder dados.
_SCHEMA_ABAS = {
    "Compras": COLUNAS_COMPRAS,
    "Gastos":  COLUNAS_GASTOS,
    "Vendas":  COLUNAS_VENDAS,
    "Manejo":  COLUNAS_MANEJO,
    "Visitas": COLUNAS_VISITAS,
}

# Caminho completo do arquivo de dados
ARQUIVO_PATH = os.path.join(DATA_DIR, ARQUIVO_DADOS)

# Garantir que a pasta de dados existe (cria ~/gado-dados/ se necessário)
os.makedirs(DATA_DIR, exist_ok=True)

# Log no boot para confirmar onde estão os dados
print(f"📂 Dados em: {DATA_DIR}", flush=True)
print(f"📊 Arquivo:  {ARQUIVO_PATH}", flush=True)


# ── Backup ────────────────────────────────────────────────────────────────────

def fazer_backup() -> str | None:
    if not os.path.exists(ARQUIVO_PATH):
        return None
    backup_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    nome = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    shutil.copy(ARQUIVO_PATH, nome)
    return nome


# ── Inicialização ─────────────────────────────────────────────────────────────

def inicializar():
    """
    Cria o arquivo de dados em DATA_DIR se não existir.
    Se já existe mas falta a aba Visitas, adiciona sem perder dados.
    """
    if not os.path.exists(ARQUIVO_PATH):
        wb = Workbook()

        ws_comp = wb.active
        ws_comp.title = "Compras"
        ws_comp.append(COLUNAS_COMPRAS)

        ws_gast = wb.create_sheet("Gastos")
        ws_gast.append(COLUNAS_GASTOS)

        ws_vend = wb.create_sheet("Vendas")
        ws_vend.append(COLUNAS_VENDAS)

        ws_man = wb.create_sheet("Manejo")
        ws_man.append(COLUNAS_MANEJO)

        ws_vis = wb.create_sheet("Visitas")
        ws_vis.append(COLUNAS_VISITAS)

        wb.create_sheet("Resumo")
        wb.save(ARQUIVO_PATH)
        print(f"✅ Arquivo de dados criado: {ARQUIVO_PATH}")
        return

    # Arquivo já existe — migrar abas/colunas que faltam SEM apagar dados.
    # Colunas novas são sempre acrescentadas no FINAL (nunca reordenadas); as
    # linhas antigas ficam só com os campos novos vazios. Nenhum dado é alterado.
    #
    # IMPORTANTE (correção): se uma versão anterior gravou um valor numa coluna
    # SEM cabeçalho (ex.: "Perda De" salvo antes de a coluna existir), a linha de
    # cabeçalho fica com uma célula vazia naquela posição. Por isso nomeamos o
    # cabeçalho POR POSIÇÃO conforme o esquema — assim o valor órfão (ex.: "Mae"
    # na coluna 6) passa a ser lido corretamente como "Perda De", em vez de
    # colocarmos o nome numa coluna à frente e deixar o dado órfão.
    try:
        wb = load_workbook(ARQUIVO_PATH)
        alterado = False
        for aba, colunas in _SCHEMA_ABAS.items():
            if aba not in wb.sheetnames:
                ws = wb.create_sheet(aba)
                ws.append(colunas)
                alterado = True
                print(f"✅ Aba '{aba}' criada no arquivo existente.")
                continue

            ws = wb[aba]
            header = [cell.value for cell in ws[1]]
            novas = []

            # 1) Preenche POSICIONALMENTE os nomes do esquema onde o cabeçalho
            #    está vazio (inclui células órfãs criadas por gravações antigas).
            for i, nome in enumerate(colunas):
                atual = header[i] if i < len(header) else None
                if atual is None or str(atual).strip() == "":
                    ws.cell(row=1, column=i + 1, value=nome)
                    novas.append(nome)
                    alterado = True

            # 2) Defensivo: garante que todo nome do esquema exista no cabeçalho
            #    (acrescenta no fim os que ainda faltarem).
            header2 = [cell.value for cell in ws[1]]
            for nome in colunas:
                if nome not in header2:
                    ws.cell(row=1, column=len(header2) + 1, value=nome)
                    header2.append(nome)
                    novas.append(nome)
                    alterado = True

            if novas:
                print(f"✅ Colunas garantidas em '{aba}': {novas}")

        if alterado:
            wb.save(ARQUIVO_PATH)
    except Exception as e:
        print(f"⚠️  Não foi possível migrar as abas: {e}")


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_aba(aba: str) -> pd.DataFrame:
    """Carrega uma aba do Excel como DataFrame."""
    try:
        df = pd.read_excel(ARQUIVO_PATH, sheet_name=aba)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(
                df["Data"], dayfirst=True, format="mixed", errors="coerce"
            )
        df = df.dropna(how="all").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


def carregar_todas() -> dict[str, pd.DataFrame]:
    """Carrega todas as abas de uma vez."""
    return {
        aba: carregar_aba(aba)
        for aba in ["Compras", "Gastos", "Vendas", "Manejo", "Visitas"]
    }


# ── Escrita ───────────────────────────────────────────────────────────────────

def _preparar_valor(v):
    """Converte tipos Python/Pandas para valores compatíveis com Excel."""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")

    if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and v[7:8] == "-":
        try:
            return datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass

    if isinstance(v, float) and (pd.isna(v) or v != v):
        return None

    return v


def salvar_linha(aba: str, linha: list):
    """Adiciona uma linha ao final de uma aba."""
    wb = load_workbook(ARQUIVO_PATH)
    ws = wb[aba]
    ws.append([_preparar_valor(v) for v in linha])
    wb.save(ARQUIVO_PATH)


def reescrever_aba(aba: str, df: pd.DataFrame):
    """Reescreve completamente uma aba a partir de um DataFrame."""
    wb = load_workbook(ARQUIVO_PATH)
    ws = wb[aba]

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.value = None

    for _, row in df.iterrows():
        ws.append([_preparar_valor(v) for v in row])

    wb.save(ARQUIVO_PATH)


# ── Utilitários ───────────────────────────────────────────────────────────────

def safe_val(df: pd.DataFrame, row: int, col: int):
    """Lê uma célula de forma segura, retorna None em caso de erro."""
    try:
        v = df.iloc[row, col]
        return v if pd.notna(v) else None
    except Exception:
        return None
