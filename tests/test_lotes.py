# -*- coding: utf-8 -*-
"""
Painel por lote (v5.3): FIFO sobre os dados que já existem, sem coluna nova.
"""
import pandas as pd

import lotes as L

HOJE = pd.Timestamp("2026-11-10")


def _df(linhas, colunas):
    df = pd.DataFrame(linhas, columns=colunas)
    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
    return df


def _compras(*linhas):
    return _df(list(linhas), ["Data", "Qtd Cabeças", "Valor Total (R$)", "Descrição"])


def _gastos(*linhas):
    return _df(list(linhas), ["Data", "Valor Total (R$)"])


def _vendas(*linhas):
    return _df(list(linhas), ["Data", "Qtd Cabeças", "Valor Total (R$)"])


def _manejo(*linhas):
    return _df(list(linhas), ["Data", "Tipo", "Qtd Cabeças", "Descrição"])


VAZIO_V = _vendas()
VAZIO_G = _gastos()


def test_cada_compra_e_um_lote():
    r = L.calcular(_compras(("01/02/2026", 10, 50000, "Bezerros"),
                            ("01/06/2026", 5, 30000, "")), VAZIO_G, VAZIO_V, hoje=HOJE)
    assert r["totais"]["lotes"] == 2
    novo, velho = r["lotes"]                     # do mais novo para o mais velho
    assert velho["cab"] == 10 and velho["custo_cab"] == 5000
    assert novo["cab"] == 5 and novo["custo_cab"] == 6000
    assert velho["dias"] == 282 and not velho["fechado"]


def test_gasto_so_cai_em_quem_ja_estava_no_sitio():
    r = L.calcular(_compras(("01/02/2026", 10, 50000, ""), ("01/06/2026", 10, 60000, "")),
                   _gastos(("01/03/2026", 1000), ("01/07/2026", 2000)),
                   VAZIO_V, hoje=HOJE)
    novo, velho = r["lotes"]
    assert velho["gastos"] == 1000 + 1000        # sozinho em março, metade em julho
    assert novo["gastos"] == 1000                # não paga o gasto de março
    assert r["totais"]["gastos"] == 3000


def test_venda_sai_do_lote_mais_velho_primeiro():
    r = L.calcular(_compras(("01/02/2026", 10, 50000, ""), ("01/06/2026", 10, 60000, "")),
                   VAZIO_G, _vendas(("01/08/2026", 12, 96000)), hoje=HOJE)
    novo, velho = r["lotes"]
    assert velho["vendidas"] == 10 and velho["vivas"] == 0 and velho["fechado"]
    assert novo["vendidas"] == 2 and novo["vivas"] == 8
    assert velho["receita"] == 80000 and novo["receita"] == 16000
    assert velho["resultado"] == 30000           # 80.000 − 10 × 5.000
    assert velho["ganho_cab"] == 3000
    assert velho["dias"] == 181                  # fechou na venda, não conta até hoje


def test_morte_consome_cabeca_sem_receita():
    r = L.calcular(_compras(("01/02/2026", 10, 50000, "")), VAZIO_G, VAZIO_V,
                   _manejo(("01/05/2026", "Morte/Perda", 1, "")), hoje=HOJE)
    l = r["lotes"][0]
    assert l["mortas"] == 1 and l["vivas"] == 9 and l["receita"] == 0
    assert l["resultado"] == -5000               # a cabeça morta é prejuízo do lote


def test_nascimento_e_lote_de_custo_zero():
    r = L.calcular(_compras(("01/02/2026", 10, 50000, "")), VAZIO_G, VAZIO_V,
                   _manejo(("01/05/2026", "Nascimento", 1, "Bezerra")), hoje=HOJE)
    nasc = r["lotes"][0]
    assert nasc["origem"] == "Nascimento" and nasc["custo_cab"] == 0
    assert r["totais"]["cab"] == 11


def test_nada_desaparece():
    """Compras + gastos e a receita das vendas aparecem inteiros nos lotes."""
    comp = _compras(("01/02/2026", 10, 50000, ""), ("01/06/2026", 6, 36000, ""))
    gast = _gastos(("01/03/2026", 1200), ("01/07/2026", 800))
    vend = _vendas(("01/08/2026", 11, 88000))
    man = _manejo(("01/04/2026", "Morte/Perda", 1, ""), ("01/05/2026", "Nascimento", 2, ""))
    t = L.calcular(comp, gast, vend, man, hoje=HOJE)["totais"]
    assert t["custo_compra"] == 86000 and t["gastos"] == 2000
    assert t["receita"] == 88000
    assert t["cab"] == 18 and t["vendidas"] + t["mortas"] + t["vivas"] == 18
    # Nada aparece do nada: o realizado + o que ainda está no pasto fecham com a receita.
    assert round(t["resultado"] + t["investido"] - t["parado"], 6) == t["receita"]


def test_venda_sem_lote_aberto_nao_perde_o_dinheiro():
    r = L.calcular(_compras(("01/06/2026", 2, 12000, "")), VAZIO_G,
                   _vendas(("01/02/2026", 3, 21000)), hoje=HOJE)
    assert r["sem_lote"]["cabecas"] == 3 and r["sem_lote"]["receita"] == 21000


def test_sem_dado_nenhum_nao_quebra():
    r = L.calcular(_compras(), VAZIO_G, VAZIO_V, hoje=HOJE)
    assert r["lotes"] == [] and r["totais"]["resultado"] == 0


def test_pagina_lotes_abre(cliente):
    html = cliente.get("/lotes").get_data(as_text=True)
    assert "Lotes" in html and "FIFO" in html
