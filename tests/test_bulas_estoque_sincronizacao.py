#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bulas_estoque_sincronizacao.py — Testes da unificação e sincronização entre Bulas e Estoque de Medicamentos
"""
import pytest
import pandas as pd


def test_modelo_medicamento_bula_relacionamento():
    from extensions import app, db as db_sqla
    from models import Medicamento, Bula

    with app.app_context():
        # Criar medicamento e bula fictícios na sessão de teste do banco
        med = Medicamento.query.filter_by(nome="Ivermectina Teste").first()
        if not med:
            med = Medicamento(nome="Ivermectina Teste", principio_ativo="Ivermectina", lote="L123")
            db_sqla.session.add(med)
            db_sqla.session.commit()

        bula = Bula.query.filter_by(medicamento_id=med.id).first()
        if not bula:
            bula = Bula(medicamento_id=med.id, arquivo="uploads/bulas/ivermectina.pdf")
            db_sqla.session.add(bula)
            db_sqla.session.commit()

        assert med.bula is not None
        assert med.bula.arquivo == "uploads/bulas/ivermectina.pdf"
