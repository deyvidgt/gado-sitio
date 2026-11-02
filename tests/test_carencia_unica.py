# -*- coding: utf-8 -*-
"""B4/B5 — carência de uma fonte só (3 abas) e tabela em dias reais."""
from datetime import date

import pandas as pd

import doencas_carencia as DC


def _abas(monkeypatch, **abas):
    monkeypatch.setattr(DC, "carregar_aba",
                        lambda aba: abas.get(aba, pd.DataFrame()))


def test_tabela_esta_em_dias_e_conhece_ceftiofur():
    # Penicilina era "48" (horas gravadas na coluna de dias → 48 dias de descarte).
    assert DC._obter_carencia("Penicilina", "leite") == 2
    assert DC._obter_carencia("Ceftiofur", "leite") == 3
    assert DC._obter_carencia("Ceftiofur", "carne") == 4


def test_remedio_fora_da_tabela_nao_finge_que_sabe():
    assert DC._obter_carencia("Remedio Inventado", "leite") is None
    assert DC.PERIODOS_CARENCIA_PADRAO  # tabela não ficou vazia


def test_carencia_de_leite_tratamentos_aparece_na_quarentena(monkeypatch):
    """Era o bug: medicações só lia a aba `Medicações` e não via este tratamento."""
    _abas(monkeypatch, **{"Leite Tratamentos": pd.DataFrame([{
        "Data": "30/10/2026", "Vaca ID": "A0001", "Brinco": "Amarelo 21",
        "Descrição": "Mastite", "Período de Carência": "2",
    }])})

    import medicacoes
    alerta = medicacoes.alertas_quarentena(hoje="31/10/2026")

    assert alerta["total"] == 1
    assert alerta["por_liberar"][0]["brinco"] == "Amarelo 21"
    assert alerta["por_liberar"][0]["motivo"] == "Mastite"
    assert alerta["por_liberar"][0]["dias_falta"] == 1
    # No dia da liberação ele aparece em "vencem hoje", não some da tela.
    assert medicacoes.alertas_quarentena(hoje="01/11/2026")["por_vencer_hoje"][0]["brinco"] == "Amarelo 21"


def test_mesmo_animal_le_mesma_carencia_em_todas_as_telas(monkeypatch):
    """Tratamentos, Medicações e Leite Tratamentos para o MESMO animal: o status
    tem que ser um só (o prazo mais longo), não um por tela."""
    _abas(monkeypatch, **{
        "Tratamentos": pd.DataFrame([{
            "ID Animal": "A0001", "Data": "28/10/2026", "Medicamento": "Ivermectina",
        }]),
        "Medicações": pd.DataFrame([{
            "Data": "29/10/2026", "Brincos": "Amarelo 21 #A0001",
            "Princípio Ativo": "Ceftiofur", "Motivo": "Mastite",
            "Quarentena Leite (dias)": "3",
        }]),
        "Leite Tratamentos": pd.DataFrame([{
            "Data": "30/10/2026", "Vaca ID": "A0001", "Descrição": "Mastite",
            "Período de Carência": "1",
        }]),
    })
    ref = date(2026, 10, 30)

    status = DC.obter_status_carencia("A0001", "leite", ref)
    ativos = DC.carencias_ativas("leite", ref)

    # O prazo que vale é o mais longo (Ceftiofur: 29/10 + 3 = 01/11).
    assert status["em_carencia"] and status["data_liberacao"] == date(2026, 11, 1)
    assert [c["animal_id"] for c in ativos] == ["A0001"]
    assert DC.validar_venda("A0001", "leite", status)[0] is False
    # Carne: a Ivermectina é a que manda (35 dias), não o Ceftiofur (4).
    assert DC.obter_status_carencia("A0001", "carne", ref)["carencia_dias"] == 35


def test_tela_doencas_usa_a_fonte_unica(cliente, monkeypatch):
    _abas(monkeypatch, **{"Leite Tratamentos": pd.DataFrame([{
        "Data": "30/10/2026", "Vaca ID": "A0001", "Brinco": "Amarelo 21",
        "Descrição": "Mastite", "Período de Carência": "2",
    }])})
    monkeypatch.setattr(DC, "_hoje", lambda: date(2026, 11, 1))

    html = cliente.get("/doencas").get_data(as_text=True)
    assert "EM CARÊNCIA" in html
