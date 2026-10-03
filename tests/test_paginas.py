# -*- coding: utf-8 -*-
"""
Smoke test das páginas: abre todas as rotas GET (logado) e garante que
nenhuma devolve erro 500. Roda numa cópia temporária dos dados.
"""
import pytest

import db

# Rotas que dependem de internet (cotações/chuva) — ficam de fora do teste.
ROTAS_EXTERNAS = {"/api/chuvas", "/api/cotacao-imea", "/api/cotacao-scot"}


def _rotas_get_sem_parametro():
    import app
    rotas = []
    for r in app.app.url_map.iter_rules():
        if "GET" not in r.methods or r.arguments or r.endpoint == "static":
            continue
        if r.rule in ROTAS_EXTERNAS:
            continue
        rotas.append(r.rule)
    return sorted(rotas)


@pytest.mark.parametrize("rota", _rotas_get_sem_parametro())
def test_pagina_abre_sem_erro(cliente, rota):
    resp = cliente.get(rota)
    assert resp.status_code < 500, f"{rota} deu {resp.status_code}"


@pytest.mark.parametrize("aba,rota", [
    ("Compras", "/compras/editar/0"),
    ("Gastos", "/gastos/editar/0"),
    ("Vendas", "/vendas/editar/0"),
    ("Manejo", "/manejo/editar/0"),
])
def test_tela_de_edicao_abre(cliente, aba, rota):
    if db.carregar_aba(aba).empty:
        pytest.skip(f"aba {aba} vazia")
    assert cliente.get(rota).status_code == 200


def test_sem_login_redireciona(flask_app):
    resp = flask_app.test_client().get("/")
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers["Location"]


def test_post_sem_csrf_e_recusado(cliente):
    resp = cliente.post("/compras/nova", data={"cabecas": "1", "valor": "100"})
    assert resp.status_code in (400, 403)


def test_nova_compra_grava_na_ordem_certa(cliente, dados_restaurados):
    """Grava uma compra pelo formulário e confere coluna por coluna."""
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    antes = len(db.carregar_aba("Compras"))
    resp = cliente.post("/compras/nova", data={
        "csrf_token": "tok", "data": "15/01/2026", "cabecas": "3",
        "valor": "4.500,00", "qtd_mae": "1", "qtd_deyvid": "1", "qtd_nilson": "1",
        "descricao": "TESTE AUTOMATICO",
    })
    assert resp.status_code in (302, 303)

    df = db.carregar_aba("Compras")
    assert len(df) == antes + 1
    nova = df.iloc[-1]
    assert int(nova["Qtd Cabeças"]) == 3
    assert float(nova["Valor Total (R$)"]) == pytest.approx(4500.0)
    assert float(nova["Valor/Cabeça (R$)"]) == pytest.approx(1500.0)
    assert int(nova["Qtd Mae"]) == int(nova["Qtd Deyvid"]) == int(nova["Qtd Nilson"]) == 1
    assert nova["Descrição"] == "TESTE AUTOMATICO"


def test_api_rebanho(cliente):
    d = cliente.get("/api/rebanho").get_json()
    assert set(d) == {"labels", "entradas", "saidas", "cabecas", "custo_cab"}
    assert len({len(v) for v in d.values()}) == 1  # todas as séries do mesmo tamanho


def test_painel_tem_grafico_do_rebanho(cliente):
    assert 'id="chartRebanho"' in cliente.get("/").get_data(as_text=True)


def _post_manejo(cliente, **campos):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    dados = {"csrf_token": "tok", "data": "2026-05-10", "cabecas": "10",
             "responsavel": "Deyvid", "descricao": ""}
    dados.update(campos)
    return cliente.post("/manejo/novo", data=dados)


def test_vacina_exige_produto(cliente, dados_restaurados):
    antes = len(db.carregar_aba("Manejo"))
    resp = _post_manejo(cliente, tipo="Vacina Raiva", produto="")
    assert resp.status_code in (302, 303) and "/manejo/novo" in resp.headers["Location"]
    assert len(db.carregar_aba("Manejo")) == antes  # nada gravado


def test_vacina_grava_produto_na_ultima_coluna(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Vermifugação", produto="Ivermectina 1%")
    df = db.carregar_aba("Manejo")
    from config import COLUNAS_MANEJO
    assert list(df.columns) == COLUNAS_MANEJO  # colunas novas só no fim, na ordem
    assert df.iloc[-1]["Tipo"] == "Vermifugação"
    assert df.iloc[-1]["Produto"] == "Ivermectina 1%"
    assert int(df.iloc[-1]["Qtd Cabeças"]) == 10
    # o produto aparece como sugestão no próximo registro
    assert "Ivermectina 1%" in cliente.get("/manejo/novo").get_data(as_text=True)


def test_produto_ignorado_em_outros_tipos(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Pesagem", produto="não deveria salvar")
    p = db.carregar_aba("Manejo").iloc[-1].get("Produto")
    assert p is None or str(p) in ("", "nan")


def test_nascimento_grava_de_quem_e(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Nascimento", cabecas="2", nascimento_de="Nilson",
                 perda_de="Mae")  # perda_de deve ser ignorado
    ult = db.carregar_aba("Manejo").iloc[-1]
    assert ult["Tipo"] == "Nascimento" and ult["Nascimento De"] == "Nilson"
    assert str(ult.get("Perda De")) in ("", "nan", "None")


def test_exportacao_excel_manejo_tem_titulo_em_todas_as_colunas(cliente):
    import io
    from openpyxl import load_workbook
    resp = cliente.get("/exportar")
    assert resp.status_code == 200
    wb = load_workbook(io.BytesIO(resp.data), read_only=True)
    aba = next(n for n in wb.sheetnames if "Manejo" in n)
    linhas = list(wb[aba].iter_rows(values_only=True))
    cab = linhas[0]
    largura = max(len([v for v in l if v is not None]) and len(l) for l in linhas)
    assert all(cab[i] for i in range(largura)), cab


def test_form_manejo_sugere_produtos_do_mercado(cliente):
    html = cliente.get("/manejo/novo").get_data(as_text=True)
    for nome in ("Raivacel Multi", "Bovilis Poli-Star T", "Dectomax (doramectina)"):
        assert nome in html


def test_lista_de_visitas_nao_mostra_nan(cliente):
    html = cliente.get("/visitas").get_data(as_text=True)
    assert "📝 nan" not in html
