#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_sqlalchemy.py — Camada de acesso via SQLAlchemy ORM para substituir pd.read_excel gradualmente
"""

import json
import pandas as pd
from models import RegistroGenerico, Fazenda

def carregar_aba_sql(aba: str, fazenda_slug: str = "santo-antonio") -> pd.DataFrame:
    """Carrega uma aba do banco SQLite via SQLAlchemy ORM como DataFrame do pandas."""
    fazenda = Fazenda.query.filter_by(slug=fazenda_slug).first()
    if not fazenda:
        return pd.DataFrame()
        
    registros = RegistroGenerico.query.filter_by(fazenda_id=fazenda.id, aba=aba).all()
    if not registros:
        return pd.DataFrame()
        
    dados = [json.loads(r.dados_json) for r in registros]
    return pd.DataFrame(dados)

def salvar_registro_sql(aba: str, dados_dict: dict, fazenda_slug: str = "santo-antonio"):
    """Salva um novo registro no SQLite via ORM."""
    fazenda = Fazenda.query.filter_by(slug=fazenda_slug).first()
    if not fazenda:
        fazenda = Fazenda(nome="Sítio Santo Antonio", slug=fazenda_slug)
        from extensions import db
        db.session.add(fazenda)
        db.session.commit()
        
    from extensions import db
    item = RegistroGenerico(
        fazenda_id=fazenda.id,
        aba=aba,
        dados_json=json.dumps(dados_dict, ensure_ascii=False)
    )
    db.session.add(item)
    db.session.commit()
