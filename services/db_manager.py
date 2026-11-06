import os
import pandas as pd
from models import db, Animal, Compra, Gasto, Venda, Manejo
from datetime import datetime

def carregar_aba_sql(aba: str) -> pd.DataFrame:
    """Carrega os dados da tabela correspondente no SQLite e retorna como DataFrame do Pandas
    mantendo compatibilidade exata com os nomes de colunas do Excel."""
    try:
        if aba == "Animais":
            records = Animal.query.all()
            if not records: return pd.DataFrame()
            data = [{
                "ID": r.id,
                "Brinco Cor": r.brinco_cor,
                "Brinco Nº": r.brinco_num,
                "Dono": r.dono,
                "Categoria": r.categoria,
                "Sexo": r.sexo,
                "Raça": r.raca,
                "Status": r.status,
                "Observações": r.observacoes
            } for r in records]
            return pd.DataFrame(data)

        elif aba == "Compras":
            records = Compra.query.all()
            if not records: return pd.DataFrame()
            data = [{
                "Data": r.data,
                "Qtd Cabeças": r.qtd_cabecas,
                "Valor Total (R$)": r.valor_total,
                "Descrição": r.descricao,
                "Registrado Por": r.registrado_por
            } for r in records]
            return pd.DataFrame(data)

        elif aba == "Gastos":
            records = Gasto.query.all()
            if not records: return pd.DataFrame()
            data = [{
                "Data": r.data,
                "Tipo": r.tipo,
                "Valor Total (R$)": r.valor_total,
                "Categoria": r.categoria,
                "Registrado Por": r.registrado_por
            } for r in records]
            return pd.DataFrame(data)

        elif aba == "Vendas":
            records = Venda.query.all()
            if not records: return pd.DataFrame()
            data = [{
                "Data": r.data,
                "Qtd Cabeças": r.qtd_cabecas,
                "Valor Total (R$)": r.valor_total
            } for r in records]
            return pd.DataFrame(data)

        elif aba == "Manejo":
            records = Manejo.query.all()
            if not records: return pd.DataFrame()
            data = [{
                "Data": r.data,
                "Tipo": r.tipo,
                "Qtd Cabeças": r.qtd_cabecas,
                "Descrição": r.descricao
            } for r in records]
            return pd.DataFrame(data)

    except Exception as e:
        print(f"Erro ao carregar {aba} via SQL: {e}")
        return pd.DataFrame()

    return pd.DataFrame()

def salvar_linha_sql(aba: str, linha: list):
    """Grava uma linha no banco SQL mapeando do formato Excel."""
    try:
        if aba == "Compras":
            c = Compra(
                data=pd.to_datetime(linha[0], dayfirst=True),
                qtd_cabecas=int(linha[1]),
                valor_total=float(linha[2]),
                descricao=str(linha[6]) if len(linha) > 6 else "",
                registrado_por=str(linha[7]) if len(linha) > 7 else ""
            )
            db.session.add(c)
        elif aba == "Gastos":
            g = Gasto(
                data=pd.to_datetime(linha[0], dayfirst=True),
                tipo=str(linha[1]),
                valor_total=float(linha[3]),
                categoria=str(linha[11]) if len(linha) > 11 else "",
                registrado_por=str(linha[6]) if len(linha) > 6 else ""
            )
            db.session.add(g)
        elif aba == "Vendas":
            v = Venda(
                data=pd.to_datetime(linha[0], dayfirst=True),
                qtd_cabecas=int(linha[1]),
                valor_total=float(linha[2])
            )
            db.session.add(v)
        elif aba == "Manejo":
            m = Manejo(
                data=pd.to_datetime(linha[0], dayfirst=True),
                tipo=str(linha[1]),
                qtd_cabecas=int(linha[2]),
                descricao=str(linha[3]) if len(linha) > 3 else ""
            )
            db.session.add(m)
        else:
            raise ValueError(f"Aba {aba} não suportada para escrita SQL")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def reescrever_aba_sql(aba: str, df: pd.DataFrame):
    """Apaga os dados da tabela correspondente no SQLite e insere os novos dados do DataFrame."""
    try:
        model_map = {
            "Compras": Compra,
            "Gastos": Gasto,
            "Vendas": Venda,
            "Manejo": Manejo
        }
        model = model_map.get(aba)
        if not model:
            raise ValueError(f"Aba {aba} não suportada para escrita SQL")

        db.session.query(model).delete()

        for _, row in df.iterrows():
            if aba == "Compras":
                c = Compra(
                    data=pd.to_datetime(row.get("Data"), dayfirst=True, errors='coerce'),
                    qtd_cabecas=int(row.get("Qtd Cabeças", 0)) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    valor_total=float(row.get("Valor Total (R$)", 0.0)) if pd.notna(row.get("Valor Total (R$)")) else 0.0,
                    descricao=str(row.get("Descrição", "")) if pd.notna(row.get("Descrição")) else "",
                    registrado_por=str(row.get("Registrado Por", "")) if pd.notna(row.get("Registrado Por")) else ""
                )
                db.session.add(c)
            elif aba == "Gastos":
                g = Gasto(
                    data=pd.to_datetime(row.get("Data"), dayfirst=True, errors='coerce'),
                    tipo=str(row.get("Tipo", "")) if pd.notna(row.get("Tipo")) else "",
                    valor_total=float(row.get("Valor Total (R$)", 0.0)) if pd.notna(row.get("Valor Total (R$)")) else 0.0,
                    categoria=str(row.get("Categoria", "")) if pd.notna(row.get("Categoria")) else "",
                    registrado_por=str(row.get("Registrado Por", "")) if pd.notna(row.get("Registrado Por")) else ""
                )
                db.session.add(g)
            elif aba == "Vendas":
                v = Venda(
                    data=pd.to_datetime(row.get("Data"), dayfirst=True, errors='coerce'),
                    qtd_cabecas=int(row.get("Qtd Cabeças", 0)) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    valor_total=float(row.get("Valor Total (R$)", 0.0)) if pd.notna(row.get("Valor Total (R$)")) else 0.0
                )
                db.session.add(v)
            elif aba == "Manejo":
                m = Manejo(
                    data=pd.to_datetime(row.get("Data"), dayfirst=True, errors='coerce'),
                    tipo=str(row.get("Tipo", "")) if pd.notna(row.get("Tipo")) else "",
                    qtd_cabecas=int(row.get("Qtd Cabeças", 0)) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    descricao=str(row.get("Descrição", "")) if pd.notna(row.get("Descrição")) else ""
                )
                db.session.add(m)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
