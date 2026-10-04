# -*- coding: utf-8 -*-
"""
Testes do motor financeiro (calculos.py) — média móvel perpétua v4.0.

As 3 invariantes do CLAUDE.md são verificadas em cenários montados à mão
e também na cópia dos dados reais. Se alguma falhar, há bug no cálculo.
"""
import pandas as pd
import pytest

import calculos as c
import db
from config import MEMBROS
from conftest import TEM_DADOS_REAIS

TOL = 0.01  # tolerância de 1 centavo


def _d(s):
    return pd.Timestamp(s)


def compras(*linhas):
    """linhas: (data, qtd, valor_total, qtd_mae, qtd_deyvid, qtd_nilson)"""
    return pd.DataFrame([{
        "Data": _d(d), "Qtd Cabeças": q, "Valor Total (R$)": v,
        "Valor/Cabeça (R$)": v / q, "Qtd Mae": m, "Qtd Deyvid": dy, "Qtd Nilson": n,
    } for d, q, v, m, dy, n in linhas])


def gastos(*linhas):
    """linhas: (data, valor_total)"""
    return pd.DataFrame([{"Data": _d(d), "Valor Total (R$)": v} for d, v in linhas])


def vendas(*linhas):
    """linhas: (data, {membro: (qtd, valor)})"""
    regs = []
    for d, por_membro in linhas:
        reg = {"Data": _d(d)}
        qtd_tot = val_tot = 0
        for m in MEMBROS:
            q, v = por_membro.get(m, (0, 0.0))
            reg[f"Qtd {m}"] = q
            reg[f"Valor {m} (R$)"] = v
            qtd_tot += q
            val_tot += v
        reg["Qtd Cabeças"] = qtd_tot
        reg["Valor Total (R$)"] = val_tot
        regs.append(reg)
    return pd.DataFrame(regs)


def manejo(*linhas):
    """linhas: (data, tipo, qtd, perda_de)"""
    return pd.DataFrame([{"Data": _d(d), "Tipo": t, "Qtd Cabeças": q, "Perda De": p}
                         for d, t, q, p in linhas])


VAZIO_MAN = pd.DataFrame(columns=["Data", "Tipo", "Qtd Cabeças", "Perda De"])


def checar_invariantes(df_comp, df_gast, df_vend, df_man):
    """As 3 invariantes contábeis do projeto."""
    resumo = c.calcular_resumo_financeiro(df_comp, df_gast, df_vend, df_man)
    sim = c._simular_media_movel(df_comp, df_gast, df_vend, df_man)
    membros = c.calcular_todos_membros(df_vend, df_comp, df_gast, df_man)

    # 1) Nada aparece do nada: vendido + perdas + capital (pools da simulação) == total
    #    (usa o capital da simulação, não o resíduo do resumo, para o teste ter dentes)
    soma = sim["custo_vendidos"] + sim["perdas"] + sim["capital"]
    assert soma == pytest.approx(resumo["total_custo"], abs=TOL)
    assert resumo["capital_imobilizado"] == pytest.approx(sim["capital"], abs=TOL)

    # 2) Soma dos custos dos membros == custo das vendas global
    soma_membros = sum(r["custo_total"] for r in membros.values())
    assert soma_membros == pytest.approx(resumo["custo_vendidos"], abs=TOL)

    # 3) Soma das perdas dos membros == perdas global
    soma_perdas = sum(r["perdas"] for r in membros.values())
    assert soma_perdas == pytest.approx(resumo["perdas"], abs=TOL)

    return resumo, membros


# ── Cenário do exemplo da docstring de _simular_media_movel ─────────────────

def test_exemplo_da_documentacao():
    """10 a R$1.000 + R$2.000 de vacina → média R$1.200; vende 7 a R$1.500."""
    df_comp = compras(("2025-01-01", 10, 10_000.0, 4, 3, 3))
    df_gast = gastos(("2025-01-10", 2_000.0))
    df_vend = vendas(("2025-02-01", {"Mae": (3, 4_500.0), "Deyvid": (2, 3_000.0),
                                     "Nilson": (2, 3_000.0)}))
    resumo, membros = checar_invariantes(df_comp, df_gast, df_vend, VAZIO_MAN)

    assert resumo["custo_vendidos"] == pytest.approx(8_400.0)
    assert resumo["resultado_realizado"] == pytest.approx(2_100.0)
    assert resumo["capital_imobilizado"] == pytest.approx(3_600.0)  # 3 × 1.200
    assert resumo["ctcab"] == pytest.approx(1_200.0)
    assert membros["Mae"]["custo_total"] == pytest.approx(3 * 1_200.0)


def test_gado_comprado_depois_nao_paga_gasto_anterior():
    df_comp = compras(("2025-01-01", 3, 3_000.0, 1, 1, 1),
                      ("2025-03-01", 9, 11_700.0, 3, 3, 3))
    df_gast = gastos(("2025-02-01", 600.0))  # só as 3 primeiras pagam
    resumo, _ = checar_invariantes(df_comp, df_gast, vendas(), VAZIO_MAN)
    # gasto/cab final = 600 / 12 cabeças (diluído depois), mas o pool é o mesmo
    assert resumo["capital_imobilizado"] == pytest.approx(3_000 + 11_700 + 600)


def test_morte_com_dono_vai_para_o_dono():
    df_comp = compras(("2025-01-01", 10, 10_000.0, 4, 3, 3))
    df_man = manejo(("2025-01-15", "Morte/Perda", 1, "Deyvid"))
    resumo, membros = checar_invariantes(df_comp, gastos(), vendas(), df_man)
    assert resumo["perdas"] == pytest.approx(1_000.0)
    assert membros["Deyvid"]["perdas"] == pytest.approx(1_000.0)
    assert membros["Mae"]["perdas"] == pytest.approx(0.0)
    # perda não infla os sobreviventes
    assert resumo["ctcab"] == pytest.approx(1_000.0)


def test_morte_sem_dono_rateia_em_tercos():
    df_comp = compras(("2025-01-01", 10, 9_000.0, 4, 3, 3))
    df_man = manejo(("2025-01-15", "Morte/Perda", 1, None))
    _, membros = checar_invariantes(df_comp, gastos(), vendas(), df_man)
    for m in MEMBROS:
        assert membros[m]["perdas"] == pytest.approx(300.0, abs=TOL)


def test_cenario_misto_com_nascimento_morte_e_varias_vendas():
    df_comp = compras(("2025-01-01", 12, 24_000.0, 4, 4, 4),
                      ("2025-04-01", 6, 15_000.0, 2, 2, 2))
    df_gast = gastos(("2025-01-20", 1_800.0), ("2025-05-01", 2_500.0),
                     ("2025-07-01", 900.0))
    df_man = manejo(("2025-02-01", "Nascimento", 2, None),
                    ("2025-03-01", "Morte/Perda", 1, "Nilson"),
                    ("2025-06-01", "Morte/Perda", 1, None))
    df_vend = vendas(("2025-03-15", {"Mae": (2, 6_000.0), "Nilson": (1, 2_900.0)}),
                     ("2025-08-01", {"Deyvid": (4, 13_000.0), "Mae": (1, 3_100.0)}))
    checar_invariantes(df_comp, df_gast, df_vend, df_man)


def test_tudo_vazio_nao_quebra():
    resumo, membros = checar_invariantes(compras(), gastos(), vendas(), VAZIO_MAN)
    assert resumo["estoque"] == 0
    assert all(r["custo_total"] == 0 for r in membros.values())


# ── Dados reais (na cópia temporária) ────────────────────────────────────────

@pytest.mark.skipif(not TEM_DADOS_REAIS, reason="sem gado_familia.xlsx para copiar")
def test_invariantes_com_dados_reais():
    d = db.carregar_todas()
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


# ── Evolução do rebanho (gráfico do painel) ──────────────────────────────────

def test_evolucao_rebanho_mes_a_mes():
    df_comp = compras(("2025-01-05", 10, 10_000.0, 4, 3, 3))
    df_gast = gastos(("2025-01-20", 2_000.0))
    df_man = manejo(("2025-02-10", "Nascimento", 2, None),
                    ("2025-02-20", "Morte/Perda", 1, "Mae"))
    df_vend = vendas(("2025-03-15", {"Deyvid": (5, 7_500.0)}))
    ev = c.calcular_evolucao_rebanho(df_comp, df_gast, df_vend, df_man,
                                     hoje=pd.Timestamp("2025-04-10"))

    assert [m["label"] for m in ev] == ["01/2025", "02/2025", "03/2025", "04/2025"]
    assert [m["entradas"] for m in ev] == [10, 2, 0, 0]
    assert [m["saidas"] for m in ev] == [0, 1, 5, 0]
    assert [m["cabecas"] for m in ev] == [10, 11, 6, 6]
    assert ev[0]["custo_cab"] == pytest.approx(1_200.0)       # 12.000 / 10
    assert ev[1]["custo_cab"] == pytest.approx(12_000 / 12)   # nasc. baixa a média; morte não muda


def test_evolucao_rebanho_vazio():
    assert c.calcular_evolucao_rebanho(compras(), gastos(), vendas(), VAZIO_MAN) == []


@pytest.mark.skipif(not TEM_DADOS_REAIS, reason="sem gado_familia.xlsx para copiar")
def test_evolucao_rebanho_bate_com_o_painel():
    d = db.carregar_todas()
    ev = c.calcular_evolucao_rebanho(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    resumo = c.calcular_resumo_financeiro(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    assert ev, "dados reais deveriam gerar meses"
    assert ev[-1]["custo_cab"] == pytest.approx(resumo["ctcab"], abs=TOL)
    assert ev[-1]["cabecas"] == resumo["estoque"]


# ── Estoque por membro: Nascimento De (inverso de Perda De) ──────────────────

def _man_nasc(*linhas):
    """linhas: (data, tipo, qtd, perda_de, nascimento_de)"""
    return pd.DataFrame([{"Data": _d(d), "Tipo": t, "Qtd Cabeças": q,
                          "Perda De": p, "Nascimento De": n} for d, t, q, p, n in linhas])


def test_nascimento_com_dono_vai_para_o_dono():
    df_comp = compras(("2025-01-01", 9, 9_000.0, 3, 3, 3))
    df_man = _man_nasc(("2025-03-01", "Nascimento", 2, None, "Deyvid"))
    est = c.calcular_estoque_por_membro(df_comp, vendas(), df_man)
    assert est == {"Mae": 3, "Deyvid": 5, "Nilson": 3}


def test_nascimento_sem_dono_divide_em_tercos():
    df_comp = compras(("2025-01-01", 9, 9_000.0, 3, 3, 3))
    df_man = _man_nasc(("2025-03-01", "Nascimento", 3, None, None))
    assert c.calcular_estoque_por_membro(df_comp, vendas(), df_man) == \
        {"Mae": 4, "Deyvid": 4, "Nilson": 4}


def test_nascimento_aceita_nome_de_exibicao_e_planilha_antiga():
    df_comp = compras(("2025-01-01", 3, 3_000.0, 1, 1, 1))
    df_man = _man_nasc(("2025-03-01", "Nascimento", 1, None, "Geane"))
    assert c.calcular_estoque_por_membro(df_comp, vendas(), df_man)["Mae"] == 2
    # planilha sem a coluna nova continua funcionando (terços)
    antigo = manejo(("2025-03-01", "Nascimento", 3, None))
    assert c.calcular_estoque_por_membro(df_comp, vendas(), antigo) == \
        {"Mae": 2, "Deyvid": 2, "Nilson": 2}


def test_nascimento_com_dono_nao_mexe_nas_invariantes():
    df_comp = compras(("2025-01-01", 9, 9_000.0, 3, 3, 3))
    df_man = _man_nasc(("2025-02-01", "Nascimento", 3, None, "Nilson"),
                       ("2025-03-01", "Morte/Perda", 1, "Mae", None))
    df_vend = vendas(("2025-04-01", {"Nilson": (4, 6_000.0)}))
    checar_invariantes(df_comp, gastos(), df_vend, df_man)


# ── Regressões (revisão de bugs out/2026) ──────────────────────────────────────

@pytest.mark.parametrize("cab,cotas,esperado", [
    (3, (5, 5, 0), (2, 1, 0)),   # antes: (2, 2, -1) — cota negativa
    (7, (0, 0, 0), (2, 2, 3)),   # sem cotas: terços, resto p/ Nilson
    (5, (2, 2, 1), (2, 2, 1)),   # já bate: mantém
    (10, (1, 1, 1), (4, 3, 3)),
])
def test_dividir_cotas_nunca_negativa_e_fecha(cab, cotas, esperado):
    r = c.dividir_cotas(cab, *cotas)
    assert r == esperado
    assert sum(r) == cab and min(r) >= 0


def test_venda_sem_cotas_rateia_custo_em_tercos():
    """Venda importada sem Qtd por membro: o custo tem que ir para os membros
    (invariante 2), senão some da soma deles."""
    df_c = compras(("2025-01-01", 9, 9000.0, 3, 3, 3))
    df_g = gastos(("2025-02-01", 900.0))
    df_v = vendas(("2025-03-01", {}))
    df_v.loc[0, ["Qtd Cabeças", "Valor Total (R$)"]] = [3, 6000.0]
    checar_invariantes(df_c, df_g, df_v, VAZIO_MAN)
    membros = c.calcular_todos_membros(df_v, df_c, df_g, VAZIO_MAN)
    assert sum(m["receita"] for m in membros.values()) == pytest.approx(6000.0)


def test_celula_vazia_nan_nao_derruba_calculos():
    nan = float("nan")
    df_c = compras(("2025-01-01", 9, 9000.0, 3, 3, 3))
    df_c.loc[0, "Qtd Mae"] = nan
    df_g = gastos(("2025-02-01", 900.0), ("2025-02-02", nan))
    df_v = vendas(("2025-03-01", {"Mae": (1, 2000.0)}))
    c.calcular_estoque_por_membro(df_c, df_v, VAZIO_MAN)
    r = c.calcular_resumo_financeiro(df_c, df_g, df_v, VAZIO_MAN)
    assert r["capital_imobilizado"] == pytest.approx(9900.0 * 8 / 9, abs=TOL)
    checar_invariantes(df_c, df_g, df_v, VAZIO_MAN)
