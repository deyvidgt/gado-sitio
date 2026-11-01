#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do ponto de corte e dos relatórios avançados (v5.14).
"""
import pandas as pd
import pytest

import ponto_corte as PC
import relatorios_avancados as R


def _manejo():
    return pd.DataFrame([
        {"Data": "01/01/2026", "Tipo": "Pesagem",
         "Pesos": "Amarelo 21 #A0003: 380 kg", "Brincos": "Amarelo 21 #A0003"},
        {"Data": "01/03/2026", "Tipo": "Pesagem",
         "Pesos": "Amarelo 21 #A0003: 440 kg", "Brincos": "Amarelo 21 #A0003"},
    ])


def test_ponto_corte_simula_e_escolhe_melhor_dia():
    r = PC.simular_ponto_corte("A0003", _manejo(), pd.DataFrame(), 340.0, 0.52,
                               custo_diario=3.5)
    assert "erro" not in r
    assert r["peso_atual"] == 440.0
    assert len(r["simulacao"]) == 4
    # Com GMD positivo e custo baixo, esperar rende mais que vender hoje.
    assert r["melhor_dia"] == 30
    assert r["melhor_resultado"] > r["simulacao"][0]["resultado"]
    # Arrobas = peso vivo × rendimento / 15
    dia0 = r["simulacao"][0]
    assert dia0["arrobas"] == pytest.approx(440 * 0.52 / 15, abs=0.01)


def test_ponto_corte_sem_pesagem_devolve_erro():
    r = PC.simular_ponto_corte("X999", _manejo(), pd.DataFrame(), 340.0)
    assert "sem pesagem" in r["erro"]


def test_ponto_corte_recomendacao_texto():
    r = PC.simular_ponto_corte("A0003", _manejo(), pd.DataFrame(), 340.0, 0.52,
                               custo_diario=3.5)
    txt = PC.recomendacao_venda(r)
    assert "A0003" in txt
    assert "esperar 30" in txt


def test_relatorio_leite_le_coluna_litros():
    """A coluna real é "Litros" — o código antigo lia "Produção (litros)" e dava 0."""
    df = pd.DataFrame({
        "Data": ["01/11/2026", "02/11/2026"],
        "Litros": [20.0, 30.0],
        "CCS (células/mL)": [150000, 250000],
        "CPP (UFC/mL)": [50000, 60000],
    })
    r = R.gerar_relatorio_leite(df)
    assert r["sucesso"]
    assert r["resumo"]["producao_total"] == 50.0
    assert r["resumo"]["media_diaria"] == 25.0
    assert r["resumo"]["ccs_media"] == 200000


def test_relatorio_financeiro_nao_desconta_compras():
    """Comprar gado é troca de caixa por estoque, não despesa: o resultado
    não pode subtrair as compras (contaria o custo duas vezes)."""
    vendas = pd.DataFrame({"Valor Total (R$)": [1000.0]})
    gastos = pd.DataFrame({"Valor Total (R$)": [200.0]})
    compras = pd.DataFrame({"Valor Total (R$)": [500.0]})
    r = R.gerar_relatorio_financeiro(vendas, gastos, compras)
    assert r["sucesso"]
    assert r["resumo"]["resultado"] == 800.0


def test_pdf_relatorio_gera_bytes(cliente):
    """O PDF de verdade (não o placeholder de texto que existia)."""
    dados = {"sucesso": True, "resumo": {"total_vendas": 100.0, "total_gastos": 40.0,
                                         "total_compras": 10.0, "resultado": 60.0,
                                         "margem": 60.0}}
    buf = R.exportar_pdf_relatorio("financeiro", dados)
    assert buf is not None
    assert buf.getvalue()[:4] == b"%PDF"


def test_rotas_novas_respondem(cliente):
    assert cliente.get("/ponto-corte").status_code == 200
    assert cliente.get("/relatorios/avancados").status_code == 200
    for tipo in ("anual", "vendas", "sanitario", "reprodutivo", "leite", "financeiro"):
        r = cliente.get(f"/relatorios/avancados/{tipo}")
        assert r.status_code == 200, tipo
        assert r.mimetype == "application/pdf", tipo
