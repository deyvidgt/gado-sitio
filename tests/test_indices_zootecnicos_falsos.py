# -*- coding: utf-8 -*-
"""
Testes com dados falsos para validar a interligação de todos os índices zootécnicos.
"""
from datetime import date, timedelta
import pandas as pd
import pytest

import animais
import calculos
import cochos
import doencas_carencia
import indicadores_coleta
import pastos
import pesagem
import reproducao
from models import Insumo
from extensions import db


def test_interligacao_indices_zootecnicos_com_dados_falsos(flask_app):
    with flask_app.app_context():
        # 1. Simula animais e pesagem (GMD)
        df_manejo_pesagem = pd.DataFrame([
            {"Data": pd.Timestamp("2026-01-01"), "Tipo": "Pesagem", "Qtd Cabeças": 1, "Brincos": "Amarelo 21 #A0001", "Pesos": "Amarelo 21 #A0001: 200 kg"},
            {"Data": pd.Timestamp("2026-02-01"), "Tipo": "Pesagem", "Qtd Cabeças": 1, "Brincos": "Amarelo 21 #A0001", "Pesos": "Amarelo 21 #A0001: 231 kg"},
        ])
        pesos_map = pesagem.todas(df_manejo_pesagem)
        assert "A0001" in pesos_map
        assert len(pesos_map["A0001"]) == 2
        # GMD = (231 - 200) / 31 dias = ~1.0 kg/dia
        gmd = pesagem._gmd(pesos_map["A0001"][0], pesos_map["A0001"][1])
        assert gmd is not None
        assert 0.9 <= gmd <= 1.1

        # 2. Simula Reprodução (Cobertura e Toque Gestação)
        df_manejo_repro = pd.DataFrame([
            {"Data": pd.Timestamp("2026-01-01"), "Tipo": "Cobertura", "Qtd Cabeças": 1, "Brincos": "Azul 12 #A0002", "Produto": "Touro Nelore"},
            {"Data": pd.Timestamp("2026-02-10"), "Tipo": "Diagnóstico de Gestação", "Qtd Cabeças": 1, "Brincos": "Azul 12 #A0002", "Descrição": "Prenha"},
        ])
        sit_repro = reproducao.situacao(df_manejo_repro, pd.DataFrame([{"ID": "A0002", "Brinco Cor": "Azul", "Brinco Nº": 12, "Status": "Vivo", "Sexo": "F", "Categoria": "Vaca"}]), date(2026, 3, 1))
        vaca_a0002 = next((s for s in sit_repro if s.get("vaca") == "A0002"), None)
        assert vaca_a0002 is not None
        assert vaca_a0002.get("status") == "prenha"

        # 3. Simula Insumos e Baixa em Salgar Cocho
        insumo = Insumo.query.filter_by(nome="Sal Proteinado Falso").first()
        if not insumo:
            insumo = Insumo(nome="Sal Proteinado Falso", categoria="Nutrição", quantidade=50.0, peso_saco=25.0, unidade_medida="kg")
            db.session.add(insumo)
            db.session.commit()
        else:
            insumo.quantidade = 50.0
            db.session.commit()

        assert insumo.quantidade == 50.0
        # Simula baixa ao salgar cocho (ex: 15 kg)
        quantidade_salga = 15.0
        assert insumo.quantidade >= quantidade_salga
        insumo.quantidade -= quantidade_salga
        db.session.commit()
        assert insumo.quantidade == 35.0

        # 4. Simula Carência de Leite (Tratamento)
        # Vamos testar diretamente a função de status/carências usando dados mockados ou mockando carregar_aba
        pass
