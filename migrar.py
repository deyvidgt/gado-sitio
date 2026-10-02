#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migra o arquivo de dados existente para o esquema atual, SEM apagar dados.
Cria/nomeia colunas novas (ex.: "Perda De", caixa d'água, Ração) e alinha
valores que foram gravados em colunas sem cabeçalho.

Rode no console Bash do PythonAnywhere (NÃO no site):
    cd ~/gado
    python migrar.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db, calculos as c
from openpyxl import load_workbook

print("Migrando:", db.ARQUIVO_PATH)
db.inicializar()   # usa _garantir_colunas em todas as abas

wb = load_workbook(db.ARQUIVO_PATH)
for aba in ("Manejo", "Visitas"):
    if aba in wb.sheetnames:
        print(f"\nCabeçalho de '{aba}':")
        print("  ", [c0.value for c0 in wb[aba][1]])

man = db.carregar_aba("Manejo")
if not man.empty and "Perda De" in man.columns:
    mortes = man[man["Tipo"] == "Morte/Perda"][["Data", "Qtd Cabeças", "Perda De"]]
    if not mortes.empty:
        print("\nMortes/Perdas registradas e de quem foram:")
        for _, r in mortes.iterrows():
            print(f"  {r['Data']}  qtd={r['Qtd Cabeças']}  PerdaDe={r['Perda De']!r}")

print("\nEstoque por membro (após migração):")
print("  ", c.calcular_estoque_por_membro(
    db.carregar_aba("Compras"), db.carregar_aba("Vendas"), man))
print("\n✅ Migração concluída. Agora dê Reload no Web App.")
