import os
import pandas as pd
from app_sql import create_app
from models import db, Animal, Compra, Gasto, Venda, Manejo

def migrar(excel_path="gado_familia.xlsx", db_path="gado_familia_sql_v2.db"):
    if os.path.exists(db_path) and db_path != ":memory:":
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Não foi possível remover o arquivo existente: {e}")
            return

    app = create_app(db_path) if 'create_app' in globals() else None

    # Se estamos usando o app principal
    from extensions import app as main_app

    with main_app.app_context():
        db.create_all()
        if not os.path.exists(excel_path):
            print(f"Arquivo Excel não encontrado: {excel_path}")
            return

        # 1. Animais
        try:
            df = pd.read_excel(excel_path, sheet_name="Animais")
            ids_inseridos = set()
            count = 0
            for _, row in df.iterrows():
                aid = row.get("ID")
                if pd.isna(aid): continue
                aid_str = str(aid).strip()
                if not aid_str or aid_str.lower() == 'nan' or aid_str in ids_inseridos:
                    continue

                db.session.add(Animal(
                    id=aid_str,
                    brinco_cor=str(row.get("Brinco Cor", "") if pd.notna(row.get("Brinco Cor")) else ""),
                    brinco_num=int(row.get("Brinco Nº")) if pd.notna(row.get("Brinco Nº")) else 0,
                    dono=str(row.get("Dono", "") if pd.notna(row.get("Dono")) else ""),
                    categoria=str(row.get("Categoria", "") if pd.notna(row.get("Categoria")) else ""),
                    sexo=str(row.get("Sexo", "") if pd.notna(row.get("Sexo")) else ""),
                    raca=str(row.get("Raça", "") if pd.notna(row.get("Raça")) else ""),
                    status=str(row.get("Status", "Vivo")),
                    observacoes=str(row.get("Observações", "") if pd.notna(row.get("Observações")) else "")
                ))
                ids_inseridos.add(aid_str)
                count += 1
            db.session.commit()
            print(f"Animais migrados com sucesso ({count} registros).")
        except Exception as e: print(f"Erro Animais: {e}"); db.session.rollback()

        # 2. Compras
        try:
            df = pd.read_excel(excel_path, sheet_name="Compras")
            count = 0
            for _, row in df.iterrows():
                if pd.isna(row.get("Data")): continue
                db.session.add(Compra(
                    data=pd.to_datetime(row.get("Data"), errors='coerce', dayfirst=True),
                    qtd_cabecas=int(row.get("Qtd Cabeças")) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    valor_total=float(row.get("Valor Total (R$)")) if pd.notna(row.get("Valor Total (R$)")) else 0.0,
                    descricao=str(row.get("Descrição", "")) if pd.notna(row.get("Descrição")) else "",
                    registrado_por=str(row.get("Registrado Por", "")) if pd.notna(row.get("Registrado Por")) else ""
                ))
                count += 1
            db.session.commit()
            print(f"Compras migradas com sucesso ({count} registros).")
        except Exception as e: print(f"Erro Compras: {e}"); db.session.rollback()

        # 3. Gastos
        try:
            df = pd.read_excel(excel_path, sheet_name="Gastos")
            count = 0
            for _, row in df.iterrows():
                if pd.isna(row.get("Data")): continue
                db.session.add(Gasto(
                    data=pd.to_datetime(row.get("Data"), errors='coerce', dayfirst=True),
                    tipo=str(row.get("Tipo", "")) if pd.notna(row.get("Tipo")) else "",
                    valor_total=float(row.get("Valor Total (R$)")) if pd.notna(row.get("Valor Total (R$)")) else 0.0,
                    categoria=str(row.get("Categoria", "")) if pd.notna(row.get("Categoria")) else "",
                    registrado_por=str(row.get("Registrado Por", "")) if pd.notna(row.get("Registrado Por")) else ""
                ))
                count += 1
            db.session.commit()
            print(f"Gastos migrados com sucesso ({count} registros).")
        except Exception as e: print(f"Erro Gastos: {e}"); db.session.rollback()

        # 4. Vendas
        try:
            df = pd.read_excel(excel_path, sheet_name="Vendas")
            count = 0
            for _, row in df.iterrows():
                if pd.isna(row.get("Data")): continue
                db.session.add(Venda(
                    data=pd.to_datetime(row.get("Data"), errors='coerce', dayfirst=True),
                    qtd_cabecas=int(row.get("Qtd Cabeças")) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    valor_total=float(row.get("Valor Total (R$)")) if pd.notna(row.get("Valor Total (R$)")) else 0.0
                ))
                count += 1
            db.session.commit()
            print(f"Vendas migradas com sucesso ({count} registros).")
        except Exception as e: print(f"Erro Vendas: {e}"); db.session.rollback()

        # 5. Manejo
        try:
            df = pd.read_excel(excel_path, sheet_name="Manejo")
            count = 0
            for _, row in df.iterrows():
                if pd.isna(row.get("Data")): continue
                db.session.add(Manejo(
                    data=pd.to_datetime(row.get("Data"), errors='coerce', dayfirst=True),
                    tipo=str(row.get("Tipo", "")) if pd.notna(row.get("Tipo")) else "",
                    qtd_cabecas=int(row.get("Qtd Cabeças")) if pd.notna(row.get("Qtd Cabeças")) else 0,
                    descricao=str(row.get("Descrição", "")) if pd.notna(row.get("Descrição")) else ""
                ))
                count += 1
            db.session.commit()
            print(f"Manejo migrado com sucesso ({count} registros).")
        except Exception as e: print(f"Erro Manejo: {e}"); db.session.rollback()

if __name__ == "__main__":
    migrar()
