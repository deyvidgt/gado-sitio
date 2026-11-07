#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_manager.py — Gerenciador unificado de persistência via SQLite/SQLAlchemy ORM
Substitui o antigo db.py baseado em Excel (.xlsx) por consultas em tabelas SQLite.
"""

from __future__ import annotations
import os
import json
import pandas as pd
from datetime import datetime
from extensions import db
from models import Fazenda, RegistroGenerico
from config import _SCHEMA_ABAS

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("GADO_DATA_DIR", "/home/deyvidgt16/gado-dados" if os.path.exists("/home/deyvidgt16") else RAIZ)
ARQUIVO_PATH = os.path.join(DATA_DIR, "gado_familia.xlsx") # Mantido por compatibilidade de rotas legadas

def usar_pasta(pasta: str) -> None:
    global DATA_DIR, ARQUIVO_PATH
    os.makedirs(pasta, exist_ok=True)
    DATA_DIR = pasta
    ARQUIVO_PATH = os.path.join(pasta, "gado_familia.xlsx")

def _obter_fazenda_id(slug: str = "santo-antonio") -> int:
    fazenda = Fazenda.query.filter_by(slug=slug).first()
    if not fazenda:
        fazenda = Fazenda(nome="Sítio Santo Antonio", slug=slug)
        db.session.add(fazenda)
        db.session.commit()
    return fazenda.id

def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, format="mixed", errors="coerce")
    return df.dropna(how="all").reset_index(drop=True)

def carregar_aba_sql(aba: str, fazenda_slug: str = "santo-antonio") -> pd.DataFrame:
    fazenda_id = _obter_fazenda_id(fazenda_slug)
    registros = RegistroGenerico.query.filter_by(fazenda_id=fazenda_id, aba=aba).all()
    if not registros:
        # Tenta popular do Excel legado se existir
        df_legado = _carregar_legado_se_necessario(aba)
        if not df_legado.empty:
            reescrever_aba_sql(aba, df_legado, fazenda_slug)
            return df_legado
        return pd.DataFrame(columns=_SCHEMA_ABAS.get(aba, []))
    
    dados = [json.loads(r.dados_json) for r in registros]
    df = pd.DataFrame(dados)
    return _preparar_df(df)

def _carregar_legado_se_necessario(aba: str) -> pd.DataFrame:
    if os.path.exists(ARQUIVO_PATH):
        try:
            return pd.read_excel(ARQUIVO_PATH, sheet_name=aba)
        except Exception:
            pass
    return pd.DataFrame()

def salvar_linha_sql(aba: str, linha: list, fazenda_slug: str = "santo-antonio"):
    fazenda_id = _obter_fazenda_id(fazenda_slug)
    colunas = _SCHEMA_ABAS.get(aba, [])
    
    # Mapeia lista posicional para dicionário baseado nas colunas do schema
    dados_dict = {}
    for i, val in enumerate(linha):
        col_nome = colunas[i] if i < len(colunas) else f"col_{i}"
        if hasattr(val, "strftime"):
            val = val.strftime("%d/%m/%Y")
        dados_dict[col_nome] = val
        
    item = RegistroGenerico(
        fazenda_id=fazenda_id,
        aba=aba,
        dados_json=json.dumps(dados_dict, ensure_ascii=False)
    )
    db.session.add(item)
    db.session.commit()

def reescrever_aba_sql(aba: str, df: pd.DataFrame, fazenda_slug: str = "santo-antonio"):
    fazenda_id = _obter_fazenda_id(fazenda_slug)
    RegistroGenerico.query.filter_by(fazenda_id=fazenda_id, aba=aba).delete()
    
    # Normaliza datas para string antes de serializar
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].dt.strftime("%d/%m/%Y")
            
    registros = df_copy.astype(object).where(pd.notnull(df_copy), None).to_dict(orient="records")
    for reg in registros:
        item = RegistroGenerico(
            fazenda_id=fazenda_id,
            aba=aba,
            dados_json=json.dumps(reg, ensure_ascii=False)
        )
        db.session.add(item)
    db.session.commit()

def carregar_todas(fazenda_slug: str = "santo-antonio") -> dict[str, pd.DataFrame]:
    abas_principais = ["Compras", "Gastos", "Vendas", "Manejo", "Visitas"]
    return {aba: carregar_aba_sql(aba, fazenda_slug) for aba in abas_principais}

def carregar_todas_abas(fazenda_slug: str = "santo-antonio") -> dict[str, pd.DataFrame]:
    return {aba: carregar_aba_sql(aba, fazenda_slug) for aba in _SCHEMA_ABAS.keys()}

def versao_arquivo():
    return int(datetime.now().timestamp())

def fazer_backup():
    return None

def inicializar():
    db.create_all()
    _obter_fazenda_id("santo-antonio")
