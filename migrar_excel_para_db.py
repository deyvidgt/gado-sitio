#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrar_excel_para_db.py — Script de migração idempotente de Excel para SQLite
"""

import os
import pandas as pd
from app import app
from extensions import db
from models import Fazenda, RegistroGenerico
from db import carregar_aba, _SCHEMA_ABAS

def migrar():
    with app.app_context():
        db.create_all()
        
        # Garante fazenda padrão
        fazenda = Fazenda.query.filter_by(slug='santo-antonio').first()
        if not fazenda:
            fazenda = Fazenda(nome='Sítio Santo Antonio', slug='santo-antonio')
            db.session.add(fazenda)
            db.session.commit()
            
        abas = list(_SCHEMA_ABAS.keys())
        print(f"📦 Encontradas {len(abas)} abas para migrar.")
        
        for aba in abas:
            try:
                df = carregar_aba(aba)
                if df is None or df.empty:
                    print(f"  [AVISO] Aba '{aba}' vazia ou indisponível.")
                    continue
                
                # Limpa dados anteriores desta aba para esta fazenda
                RegistroGenerico.query.filter_by(fazenda_id=fazenda.id, aba=aba).delete()
                
                registros = df.astype(object).where(pd.notnull(df), None).to_dict(orient='records')
                import json
                for reg in registros:
                    # Converte datas/timestamps para string para serialização JSON segura
                    for k, v in reg.items():
                        if hasattr(v, 'isoformat'):
                            reg[k] = v.isoformat()
                    item = RegistroGenerico(
                        fazenda_id=fazenda.id,
                        aba=aba,
                        dados_json=json.dumps(reg, ensure_ascii=False)
                    )
                    db.session.add(item)
                db.session.commit()
                print(f"  [OK] Aba '{aba}': {len(registros)} registros migrados com sucesso.")
            except Exception as e:
                db.session.rollback()
                print(f"  [ERRO] Falha ao migrar aba '{aba}': {e}")

if __name__ == '__main__':
    migrar()
