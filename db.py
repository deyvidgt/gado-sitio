#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camada de acesso a dados — leitura, escrita e backup do Excel
"""

import os, sys
import shutil
import pandas as pd
from datetime import datetime
from openpyxl import Workbook, load_workbook

# Pasta de dados fica sempre ao lado do .exe / script, nunca no bundle temporário
if getattr(sys, "frozen", False):
    DATA_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

from config import (
    ARQUIVO_DADOS,
    COLUNAS_COMPRAS, COLUNAS_GASTOS,
    COLUNAS_VENDAS, COLUNAS_MANEJO, COLUNAS_VISITAS,
)

# Caminho completo do arquivo de dados (usado em todas as funções)
ARQUIVO_PATH = os.path.join(DATA_DIR, ARQUIVO_DADOS)


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
    """Cria o arquivo de dados com todas as abas se não existir.
       Se o arquivo já existe mas não tem a aba Visitas, adiciona sem perder dados.
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
        print(f"✅ Arquivo de dados criado: {ARQUIVO_DADOS}")
        return

    # Arquivo já existe — verificar se a aba Visitas precisa ser criada
    try:
        wb = load_workbook(ARQUIVO_PATH)
        if "Visitas" not in wb.sheetnames:
            ws_vis = wb.create_sheet("Visitas")
            ws_vis.append(COLUNAS_VISITAS)
            wb.save(ARQUIVO_PATH)
            print("✅ Aba 'Visitas' criada no arquivo existente.")
    except Exception as e:
        print(f"⚠️  Não foi possível verificar aba Visitas: {e}")


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_aba(aba: str) -> pd.DataFrame:
    """Carrega uma aba do Excel como DataFrame."""
    try:
        df = pd.read_excel(ARQUIVO_PATH, sheet_name=aba)
        if "Data" in df.columns:
            # format="mixed" aceita DD/MM/YYYY e YYYY-MM-DD sem inversão de mês/dia
            df["Data"] = pd.to_datetime(
                df["Data"], dayfirst=True, format="mixed", errors="coerce"
            )
        # Remover linhas totalmente vazias
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
    """Converte tipos Python/Pandas para valores compatíveis com Excel.

    Trata o caso especial de datas ISO (YYYY-MM-DD) vindas de
    inputs HTML <input type='date'> — sem conversão elas seriam
    salvas como string e lidas de volta com mês/dia invertidos
    quando dayfirst=True está ativo.
    """
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")

    # String no formato ISO YYYY-MM-DD (formulário HTML) → converter para DD/MM/YYYY
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

    # Limpar linhas de dados (mantém cabeçalho na linha 1)
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
