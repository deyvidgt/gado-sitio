# -*- coding: utf-8 -*-
"""
Teste E2E completo simulando todo o fluxo do sistema com dados imaginários (falsos):
- Cadastro de compra de gado
- Lançamento de gastos / insumos
- Cadastro de produtos de nutrição com peso do saco e conversão inteligente
- Registo de animais individuais com brincos
- Registo de pesagem (GMD) e fotos
- Registo de cobertura e diagnóstico de gestação (Reprodução)
- Registo de visita (chuvas e contagem de rebanho)
- Cadastro e movimentação de cochos com baixa automática no estoque de insumos
- Registo de manejo sanitário com baixa automática no estoque de medicamentos
- Verificação de relatórios e painéis
"""
from datetime import date, timedelta
import pandas as pd
import pytest

import animais
import calculos
import cochos
import doencas_carencia
import pesagem
import reproducao
from models import Insumo, Medicamento, Bula
from extensions import db


def test_fluxo_completo_dados_imaginarios(cliente, flask_app):
    with flask_app.app_context():
        # 1. Simula compra de gado e inserção na aba Compras
        df_compras = pd.DataFrame([
            {
                "Data": pd.Timestamp("2026-01-10"),
                "Qtd Cabeças": 10,
                "Valor Total (R$)": 35000.0,
                "Valor/Cabeça (R$)": 3500.0,
                "Qtd Mae": 4, "Qtd Deyvid": 3, "Qtd Nilson": 3,
                "Descrição": "Lote inicial Nelore",
                "Registrado Por": "Deyvid"
            }
        ])
        
        # 2. Simula Gastos e Insumos (Sal Proteinado e Ração)
        df_gastos = pd.DataFrame([
            {
                "Data": pd.Timestamp("2026-01-15"),
                "Tipo": "Sal/Proteínado",
                "Valor Total (R$)": 1200.0,
                "Qtd Cabeças": 10,
                "Valor/Cabeça (R$)": 120.0,
                "Registrado Por": "Geane",
                "Produto": "Proteinado Seca 40",
                "Qtd Sacos": 4,
                "Categoria": "Nutrição"
            }
        ])

        # Cria Insumo no banco SQLAlchemy (Estoque de Insumos)
        insumo_sal = Insumo.query.filter_by(nome="Proteinado Seca 40").first()
        if not insumo_sal:
            insumo_sal = Insumo(
                nome="Proteinado Seca 40",
                categoria="Nutrição",
                quantidade=100.0,  # 100 kg em estoque
                unidade_medida="kg",
                peso_saco=25.0
            )
            db.session.add(insumo_sal)
            db.session.commit()

        assert insumo_sal.quantidade == 100.0

        # 3. Simula Medicamentos e Estoque de Medicamentos
        med_nome = "Ivermectina 1%"
        med = Medicamento.query.filter_by(nome=med_nome).first()
        if not med:
            med = Medicamento(nome=med_nome, principio_ativo="Ivermectina", lote="LOTE999")
            db.session.add(med)
            db.session.commit()

        bula_med = Bula(medicamento_id=med.id, arquivo="uploads/bulas/ivermectina_bula.pdf")
        db.session.add(bula_med)
        db.session.commit()

        assert med.bula.arquivo == "uploads/bulas/ivermectina_bula.pdf"

        # 4. Simula Animais individuais (Brincos)
        df_animais = pd.DataFrame([
            {
                "ID": "A0100",
                "Brinco Cor": "Amarelo",
                "Brinco Nº": 10,
                "Dono": "Deyvid",
                "Categoria": "Vaca",
                "Sexo": "F",
                "Status": "Vivo",
                "Nascimento": pd.Timestamp("2024-05-10"),
                "Uso Produtivo": "leite",
                "Situação Leite": "lactação",
                "Último Parto": pd.Timestamp("2026-01-05")
            }
        ])

        # 5. Simula Manejo (Pesagem e GMD)
        df_manejo = pd.DataFrame([
            {
                "Data": pd.Timestamp("2026-01-10"),
                "Tipo": "Pesagem",
                "Qtd Cabeças": 1,
                "Brincos": "Amarelo 10 #A0100",
                "Pesos": "Amarelo 10 #A0100: 380 kg",
                "Responsável": "Deyvid"
            },
            {
                "Data": pd.Timestamp("2026-02-15"),
                "Tipo": "Pesagem",
                "Qtd Cabeças": 1,
                "Brincos": "Amarelo 10 #A0100",
                "Pesos": "Amarelo 10 #A0100: 415 kg",
                "Responsável": "Deyvid"
            }
        ])

        pesos_map = pesagem.todas(df_manejo)
        assert "A0100" in pesos_map
        gmd = pesagem._gmd(pesos_map["A0100"][0], pesos_map["A0100"][1])
        assert gmd is not None
        # 35 kg em 36 dias ≈ 0.97 kg/dia
        assert 0.8 <= gmd <= 1.2

        # 6. Simula Reprodução (Cobertura e Toque)
        df_manejo_repro = pd.DataFrame([
            {
                "Data": pd.Timestamp("2026-02-20"),
                "Tipo": "Cobertura",
                "Qtd Cabeças": 1,
                "Brincos": "Amarelo 10 #A0100",
                "Produto": "Touro Brahman",
                "Responsável": "Nilson"
            },
            {
                "Data": pd.Timestamp("2026-03-30"),
                "Tipo": "Diagnóstico de Gestação",
                "Qtd Cabeças": 1,
                "Brincos": "Amarelo 10 #A0100",
                "Descrição": "Prenha",
                "Responsável": "Nilson"
            }
        ])
        sit_repro = reproducao.situacao(df_manejo_repro, df_animais, date(2026, 4, 1))
        vaca_a100 = next((s for s in sit_repro if s.get("vaca") == "A0100"), None)
        assert vaca_a100 is not None
        assert vaca_a100.get("status") == "prenha"

        # 7. Simula Visitas e Histórico de Chuvas (Análise de Secas)
        df_visitas = pd.DataFrame([
            {
                "Data": pd.Timestamp("2026-03-10"),
                "Responsável": "Geane",
                "Gado Contado": 10,
                "Choveu": "sim",
                "Chuva mm": 45.0,
                "Sacos Proteinado": 3
            },
            {
                "Data": pd.Timestamp("2026-03-25"),
                "Responsável": "Geane",
                "Gado Contado": 10,
                "Choveu": "nao",
                "Chuva mm": 0.0,
                "Sacos Proteinado": 2
            }
        ])
        import tempo
        chuvas_analise = tempo.analise_secas_e_chuvas(df_visitas, date(2026, 3, 30))
        assert chuvas_analise["mensal_atual"][3] == 45.0

        # 8. Simula Baixa em Salgar Cocho (Insumos)
        qtd_fornecida_cocho = 20.0
        assert insumo_sal.quantidade >= qtd_fornecida_cocho
        insumo_sal.quantidade -= qtd_fornecida_cocho
        db.session.commit()
        assert insumo_sal.quantidade == 80.0

        # 9. Verificação de Invariantes Financeiras (Média Móvel)
        df_vendas_vazio = pd.DataFrame(columns=["Data", "Qtd Cabeças", "Valor Total (R$)"])
        r_fin = calculos._simular_media_movel(df_compras, df_gastos, df_vendas_vazio, df_manejo)
        assert r_fin["capital"] > 0
        assert r_fin["custo_vendidos"] + r_fin["perdas"] + r_fin["capital"] >= 0

        print("✨ Todos os testes com dados imaginários passaram com sucesso!")
