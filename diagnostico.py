#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico do arquivo de dados — mostra o estado real da aba Manejo
e por que uma Morte/Perda pode estar caindo no membro errado.

Rode no console Bash do PythonAnywhere:
    cd ~/gado          (ou a pasta do projeto)
    python diagnostico.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openpyxl import load_workbook
import db, calculos as c

print("Arquivo:", db.ARQUIVO_PATH)
wb = load_workbook(db.ARQUIVO_PATH)
ws = wb["Manejo"]

print("\n── Cabeçalho da aba Manejo (coluna: valor) ──")
for col in range(1, ws.max_column + 1):
    print(f"  col{col}: {ws.cell(row=1, column=col).value!r}")

print("\n── Últimas 3 linhas (todas as células) ──")
primeira = max(2, ws.max_row - 2)
for r in range(primeira, ws.max_row + 1):
    vals = [ws.cell(row=r, column=col).value for col in range(1, ws.max_column + 1)]
    print(f"  linha {r}: {vals}")

print("\n── Como o sistema LÊ a aba Manejo ──")
man = db.carregar_aba("Manejo")
print("  colunas:", list(man.columns))
if not man.empty:
    ult = man.iloc[-1]
    print("  última linha -> Tipo:", repr(ult.get("Tipo")),
          "| Qtd:", repr(ult.get("Qtd Cabeças")),
          "| Perda De:", repr(ult.get("Perda De")))
    print("  _normalizar_membro(Perda De) =", repr(c._normalizar_membro(ult.get("Perda De"))))

print("\n── Estoque por membro (resultado atual) ──")
print(" ", c.calcular_estoque_por_membro(
    db.carregar_aba("Compras"), db.carregar_aba("Vendas"), man))
