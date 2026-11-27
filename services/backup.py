from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/backup.py — Módulo de backup automático em Excel a partir do SQLite
"""

import os
import json
import pandas as pd
from datetime import datetime
from models import RegistroGenerico, Fazenda
from db import RAIZ

def gerar_backup_excel(fazenda_id=None) -> str:
    """Gera um arquivo .xlsx consolidado com todas as abas a partir do SQLite."""
    backup_dir = "/home/deyvidgt16/gado-dados/backups" if os.path.exists("/home/deyvidgt16/gado-dados") else os.path.join(RAIZ, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = agora().strftime("%Y%m%d_%H%M%S")
    caminho_arquivo = os.path.join(backup_dir, f"backup_sitio_{timestamp}.xlsx")
    
    query = RegistroGenerico.query
    if fazenda_id is not None:
        query = query.filter_by(fazenda_id=fazenda_id)
        
    registros = query.all()
    
    # Agrupa por aba
    abas_dict = {}
    for r in registros:
        aba = r.aba
        dados = json.loads(r.dados_json)
        abas_dict.setdefault(aba, []).append(dados)
        
    with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
        if not abas_dict:
            # Cria aba vazia se não houver dados
            pd.DataFrame(columns=["ID", "Data", "Descrição"]).to_excel(writer, sheet_name="Geral", index=False)
        for aba, lista in abas_dict.items():
            df = pd.DataFrame(lista)
            nome_aba = aba[:31]
            df.to_excel(writer, sheet_name=nome_aba, index=False)
            
    return caminho_arquivo
