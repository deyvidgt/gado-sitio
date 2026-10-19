# -*- coding: utf-8 -*-
"""
Testes da revisão de 10/2026: cache por versão do arquivo, gravação atômica,
cotas que não somam o total, venda maior que o rebanho, evolução do rebanho em
uma passada, comparativo anual pela média móvel e gado esperado na visita.
"""
import os
import time

import pandas as pd
import pytest
from openpyxl import load_workbook

import calculos as c
import db
from config import MEMBROS
from conftest import TEM_DADOS_REAIS
from test_calculos import compras, gastos, vendas, manejo, VAZIO_MAN, checar_invariantes, TOL


# ── Evolução do rebanho: uma passada == simular até cada corte ────────────────

def _evolucao_antiga(df_comp, df_gast, df_vend, df_man, hoje):
    """A implementação anterior (uma simulação por mês), como referência."""
    todas = [d for df in (df_comp, df_gast, df_vend, df_man) if not df.empty
             for d in df["Data"].dropna()]
    meses = pd.period_range(min(todas).to_period("M"),
                            max(max(todas), hoje).to_period("M"), freq="M")
    out = []
    for mes in meses:
        corte = mes.to_timestamp(how="end")
        sim = c._simular_media_movel(c._ate(df_comp, corte), c._ate(df_gast, corte),
                                     c._ate(df_vend, corte), c._ate(df_man, corte))
        out.append((int(round(sim["units_final"])),
                    round(sim["avg_compra_final"] + sim["avg_gasto_final"], 2)))
    return out


def _cenario_completo():
    df_c = compras(("2025-01-10", 10, 10000, 4, 3, 3), ("2025-03-05", 6, 9000, 2, 2, 2))
    df_g = gastos(("2025-01-20", 1500), ("2025-02-28", 700), ("2025-03-05", 300))
    df_v = vendas(("2025-02-15", {"Mae": (2, 3000)}), ("2025-04-01", {"Deyvid": (3, 5000)}))
    df_m = manejo(("2025-02-01", "Morte/Perda", 1, "Nilson"),
                  ("2025-03-20", "Nascimento", 2, None))
    return df_c, df_g, df_v, df_m


def test_evolucao_em_uma_passada_igual_a_antiga():
    df_c, df_g, df_v, df_m = _cenario_completo()
    hoje = pd.Timestamp("2025-06-15")
    nova = c.calcular_evolucao_rebanho(df_c, df_g, df_v, df_m, hoje=hoje)
    assert [(m["cabecas"], m["custo_cab"]) for m in nova] == \
        _evolucao_antiga(df_c, df_g, df_v, df_m, hoje)
    # entradas/saídas por mês continuam certas
    fev = next(m for m in nova if m["label"] == "02/2025")
    assert fev["saidas"] == 3   # 2 vendidas + 1 morta
    mar = next(m for m in nova if m["label"] == "03/2025")
    assert mar["entradas"] == 8  # 6 compradas + 2 nascidas


@pytest.mark.skipif(not TEM_DADOS_REAIS, reason="sem cópia dos dados reais")
def test_evolucao_nos_dados_reais_igual_a_antiga():
    d = db.carregar_todas()
    hoje = pd.Timestamp.now()
    nova = c.calcular_evolucao_rebanho(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"], hoje=hoje)
    assert [(m["cabecas"], m["custo_cab"]) for m in nova] == \
        _evolucao_antiga(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"], hoje)


# ── Cotas que não somam o total / venda maior que o rebanho ───────────────────

def test_cotas_que_nao_somam_o_total_mantem_invariantes():
    df_c = compras(("2025-01-10", 10, 10000, 2, 2, 2))      # 6 de 10 nas cotas
    df_v = vendas(("2025-02-01", {"Mae": (2, 3000), "Deyvid": (2, 3000)}))
    df_v.loc[0, "Qtd Cabeças"] = 5                         # 4 de 5 nas cotas
    df_v.loc[0, "Valor Total (R$)"] = 7500
    checar_invariantes(df_c, gastos(("2025-01-15", 1000)), df_v, VAZIO_MAN)

    est = c.calcular_estoque_por_membro(df_c, df_v, VAZIO_MAN)
    assert sum(est.values()) == c.calcular_estoque(df_c, df_v, VAZIO_MAN) == 5


def test_venda_maior_que_o_rebanho_mantem_invariantes():
    df_c = compras(("2025-01-10", 3, 3000, 1, 1, 1))
    df_v = vendas(("2025-02-01", {"Mae": (2, 4000), "Deyvid": (2, 4000)}))  # 4 > 3
    checar_invariantes(df_c, gastos(("2025-01-15", 600)), df_v, VAZIO_MAN)


# ── Comparativo anual pela média móvel ────────────────────────────────────────

def test_anual_soma_bate_com_resultado_total():
    df_c, df_g, df_v, df_m = _cenario_completo()
    df_c = pd.concat([df_c, compras(("2026-02-01", 5, 8000, 2, 2, 1))], ignore_index=True)
    df_v = pd.concat([df_v, vendas(("2026-05-01", {"Nilson": (4, 9000)}))], ignore_index=True)
    anual = c.calcular_resultado_anual(df_c, df_g, df_v, df_m)
    r = c.calcular_resumo_financeiro(df_c, df_g, df_v, df_m)
    assert sum(a["lucro"] for a in anual) == pytest.approx(r["resultado_total"], abs=TOL)
    assert sum(a["caixa"] for a in anual) == pytest.approx(r["total_vend"] - r["total_custo"], abs=TOL)
    # 2026 comprou gado e vendeu pouco: no caixa fica negativo, mas o resultado
    # só conta o custo das cabeças que saíram.
    a26 = next(a for a in anual if a["ano"] == 2026)
    assert a26["lucro"] != pytest.approx(a26["caixa"])


# ── Cache acompanha o arquivo ─────────────────────────────────────────────────

def test_cache_recarrega_quando_outro_processo_grava(dados_restaurados):
    from extensions import _get_dados_cache
    antes = len(_get_dados_cache()["Gastos"])

    # Grava "por fora" (como a Task do WhatsApp ou outro worker), sem passar pelo
    # salvar_linha deste processo — o cache não é invalidado na mão.
    wb = load_workbook(db.ARQUIVO_PATH)
    wb["Gastos"].append(["01/01/2026", "Manutenção/Outros", "teste cache", 1.0, 1, 1.0, "teste"])
    time.sleep(0.05)
    wb.save(db.ARQUIVO_PATH)
    st = os.stat(db.ARQUIVO_PATH)   # garante mtime diferente mesmo em FS de 2 s
    os.utime(db.ARQUIVO_PATH, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))

    assert len(_get_dados_cache()["Gastos"]) == antes + 1


def test_carregar_todas_igual_a_ler_aba_por_aba():
    todas = db.carregar_todas()
    for aba, df in todas.items():
        pd.testing.assert_frame_equal(df, db.carregar_aba(aba))


def test_gravacao_nao_deixa_temporario(dados_restaurados):
    db.salvar_linha("Gastos", ["01/01/2026", "Manutenção/Outros", "x", 1.0, 1, 1.0, "t"])
    assert not os.path.exists(db.ARQUIVO_PATH + ".tmp")
    assert load_workbook(db.ARQUIVO_PATH)["Gastos"].max_row >= 2


# ── Visita: gado esperado na data da visita ───────────────────────────────────

def test_visita_offline_usa_estoque_do_dia():
    from routes_visitas import _estoque_na_data
    df_c, df_g, df_v, df_m = _cenario_completo()
    dados = {"Compras": df_c, "Vendas": df_v, "Manejo": df_m}
    # 10/01 compra 10; 01/02 morre 1; 15/02 vende 2 → em 10/02 eram 9
    assert _estoque_na_data(dados, "2025-02-10") == 9
    assert _estoque_na_data(dados, "10/02/2025") == 9
    assert _estoque_na_data(dados, "") == c.calcular_estoque(df_c, df_v, df_m)


# ── Segurança ─────────────────────────────────────────────────────────────────

def test_sem_variavel_a_chave_secreta_nao_e_a_do_git(monkeypatch):
    import config
    from extensions import _chave_secreta
    monkeypatch.delenv("GADO_SECRET_KEY", raising=False)
    k1 = _chave_secreta()
    assert k1 != config.SECRET_KEY and len(k1) >= 32
    assert _chave_secreta() == k1   # persistida: sobrevive a reinício


def test_cotacao_scot_exige_login(flask_app):
    r = flask_app.test_client().get("/api/cotacao-scot")
    assert r.status_code == 302
