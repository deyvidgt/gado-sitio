from services.db_manager import carregar_aba_sql, salvar_linha_sql, reescrever_aba_sql
import pandas as pd

def carregar_aba(aba: str) -> pd.DataFrame:
    return carregar_aba_sql(aba)

def carregar_todas() -> dict[str, pd.DataFrame]:
    return {
        "Compras": carregar_aba_sql("Compras"),
        "Gastos": carregar_aba_sql("Gastos"),
        "Vendas": carregar_aba_sql("Vendas"),
        "Manejo": carregar_aba_sql("Manejo"),
        "Visitas": pd.DataFrame()
    }

def carregar_todas_abas() -> dict[str, pd.DataFrame]:
    return carregar_todas()

def versao_arquivo():
    return 1

def salvar_linha(aba: str, linha: list):
    return salvar_linha_sql(aba, linha)

def reescrever_aba(aba: str, df: pd.DataFrame):
    return reescrever_aba_sql(aba, df)

def fazer_backup():
    return None
