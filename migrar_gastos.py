#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRAÇÃO: Corrige gastos importados com Qtd Cabeças = 0 e Valor/Cabeça = 0

Execute UMA VEZ para corrigir permanentemente o arquivo gado_familia.xlsx.
O sistema já funciona sem isso (o motor de cálculo compensa), mas corrigir
os dados em disco torna o arquivo mais transparente e legível.

Uso:
    python migrar_gastos.py
"""

import os, sys

# Encontrar o diretório do arquivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import pandas as pd
import shutil
from datetime import datetime

ARQUIVO = os.path.join(BASE_DIR, "gado_familia.xlsx")

if not os.path.exists(ARQUIVO):
    print(f"❌ Arquivo não encontrado: {ARQUIVO}")
    sys.exit(1)

# Backup antes de qualquer alteração
backup = os.path.join(BASE_DIR, "backups",
                      f"pre_migracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
os.makedirs(os.path.dirname(backup), exist_ok=True)
shutil.copy(ARQUIVO, backup)
print(f"✅ Backup salvo em: {backup}")

# Importar cálculos
from calculos import calcular_estoque_ate_data, calcular_estoque

def carregar(aba):
    df = pd.read_excel(ARQUIVO, sheet_name=aba)
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    return df.dropna(how="all").reset_index(drop=True)

comp = carregar("Compras")
vend = carregar("Vendas")
man  = carregar("Manejo")
gast = carregar("Gastos")

total_cab_comp = max(1, int(comp["Qtd Cabeças"].sum())) if not comp.empty else 1

print(f"\n📋 Gastos encontrados: {len(gast)} linhas")
problemas = gast[(gast["Qtd Cabeças"].fillna(0) == 0) &
                 (gast["Valor/Cabeça (R$)"].fillna(0) == 0)]
print(f"   Com Qtd Cabeças = 0: {len(problemas)} linhas  (serão corrigidas)\n")

if len(problemas) == 0:
    print("✅ Nenhuma correção necessária.")
    sys.exit(0)

confirmacao = input("Confirmar correção? (s/n): ").strip().lower()
if confirmacao != "s":
    print("Cancelado.")
    sys.exit(0)

# Corrigir cada linha
gast_corr = gast.copy()
gast_corr["Qtd Cabeças"]       = gast_corr["Qtd Cabeças"].astype(float)
gast_corr["Valor/Cabeça (R$)"] = gast_corr["Valor/Cabeça (R$)"].astype(float)

corrigidos = 0
for idx, row in gast_corr.iterrows():
    vcab = float(row.get("Valor/Cabeça (R$)", 0) or 0)
    qtd  = float(row.get("Qtd Cabeças",      0) or 0)
    if vcab == 0 and qtd == 0:
        val = float(row.get("Valor Total (R$)", 0) or 0)
        if val > 0:
            data = row.get("Data")
            if pd.notna(data):
                est = calcular_estoque_ate_data(comp, vend, man, data)
            else:
                est = calcular_estoque(comp, vend, man)
            if est <= 0:
                est = total_cab_comp
            gast_corr.at[idx, "Qtd Cabeças"]       = float(est)
            gast_corr.at[idx, "Valor/Cabeça (R$)"] = round(val / est, 4)
            corrigidos += 1
            print(f"  ✓ [{idx}] {str(row.get('Data',''))[:10]} | {row.get('Descrição',''):<20} "
                  f"R${val:,.2f} / {est} cab = R${val/est:.4f}/cab")

# Salvar de volta no Excel preservando as outras abas
from openpyxl import load_workbook
wb = load_workbook(ARQUIVO)
ws = wb["Gastos"]

# Limpar dados (manter cabeçalho)
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
        cell.value = None

# Reescrever
for _, row in gast_corr.iterrows():
    linha = []
    for v in row:
        if isinstance(v, pd.Timestamp):
            linha.append(v.strftime("%d/%m/%Y"))
        elif isinstance(v, float) and pd.isna(v):
            linha.append(None)
        else:
            linha.append(v)
    ws.append(linha)

wb.save(ARQUIVO)
print(f"\n✅ Migração concluída! {corrigidos} gastos corrigidos em {ARQUIVO}")
