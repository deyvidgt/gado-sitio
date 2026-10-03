# -*- coding: utf-8 -*-
"""Testes do resumo mensal do WhatsApp — nada é enviado de verdade."""
from datetime import datetime

import pytest

import db
import resumo_mensal as rm
from conftest import TEM_DADOS_REAIS
from test_calculos import compras, gastos, vendas, manejo, VAZIO_MAN


def test_mes_anterior_vira_o_ano():
    assert rm.mes_anterior(datetime(2026, 1, 1)) == (2025, 12)
    assert rm.mes_anterior(datetime(2026, 10, 1)) == (2026, 9)


def test_resumo_com_movimento():
    g = gastos(("2025-03-05", 500.0), ("2025-03-20", 1_500.0))
    g["Tipo"] = ["Sal/Proteínado", "Remédio/Vacina"]
    dados = {
        "Compras": compras(("2025-01-10", 10, 20_000.0, 4, 3, 3)),
        "Gastos": g,
        "Vendas": vendas(("2025-03-25", {"Mae": (2, 6_000.0)})),
        "Manejo": manejo(("2025-03-02", "Nascimento", 1, None)),
    }
    msg = rm.montar_resumo_mensal(dados, 2025, 3)
    assert "Resumo de Março/2025" in msg
    assert "Vendas: 2 cab — R$ 6.000,00" in msg
    assert "Gastos: R$ 2.000,00 (maior: Remédio/Vacina, R$ 1.500,00)" in msg
    assert "Nascimentos: 1" in msg
    assert "Compras" not in msg            # compra foi em janeiro, não em março
    assert "🐄 9 cabeças" in msg           # 10 + 1 nascimento − 2 vendidas
    assert "Geane" in msg


def test_resumo_mes_sem_movimento():
    dados = {"Compras": compras(("2025-01-10", 3, 3_000.0, 1, 1, 1)),
             "Gastos": gastos(), "Vendas": vendas(), "Manejo": VAZIO_MAN}
    msg = rm.montar_resumo_mensal(dados, 2025, 6)
    assert "Nenhuma movimentação registrada no mês." in msg
    assert "🐄 3 cabeças" in msg


def test_fora_do_dia_1_nao_faz_nada(monkeypatch):
    class Dia15(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 15)
    monkeypatch.setattr(rm, "datetime", Dia15)
    chamado = []
    monkeypatch.setattr("alertas_whatsapp.enviar_para_familia", lambda msg: chamado.append(msg) or 3)
    assert rm.main([]) == 0
    assert chamado == []


def test_dia_1_envia_para_familia(monkeypatch):
    class Dia1(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1)
    monkeypatch.setattr(rm, "datetime", Dia1)
    enviados = []
    monkeypatch.setattr("alertas_whatsapp.enviar_para_familia", lambda msg: enviados.append(msg) or 2)
    assert rm.main([]) == 0
    assert len(enviados) == 1 and "Resumo de Setembro/2026" in enviados[0]


@pytest.mark.skipif(not TEM_DADOS_REAIS, reason="sem gado_familia.xlsx para copiar")
def test_resumo_com_dados_reais_bate_com_o_painel():
    d = db.carregar_todas()
    agora = datetime.now()
    msg = rm.montar_resumo_mensal(d, agora.year, agora.month)
    import calculos as c
    estoque = c.calcular_estoque(d["Compras"], d["Vendas"], d["Manejo"])
    assert f"🐄 {estoque} cabeças" in msg
