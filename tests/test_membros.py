# -*- coding: utf-8 -*-
"""
Fase 1 dos vários sítios — donos (sócios) vindos do sitio_config.json.
Sem configuração, tudo igual a hoje (Geane/Deyvid/Nilson).
"""
import os

import pytest
from openpyxl import Workbook

import config
import db

def test_padrao_igual_ao_de_hoje():
    assert config.MEMBROS == ["Mae", "Deyvid", "Nilson"]
    assert config.NOMES_MEMBROS == {"Mae": "Geane", "Deyvid": "Deyvid", "Nilson": "Nilson"}
    assert config.CORES_BRINCO_PADRAO == {"Deyvid": "Amarelo", "Nilson": "Azul", "Mae": "Vermelho"}
    assert config.COLUNAS_COMPRAS == [
        "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
        "Qtd Mae", "Qtd Deyvid", "Qtd Nilson", "Descrição", "Registrado Por"]
    assert config.COLUNAS_VENDAS == [
        "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
        "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
        "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
        "Custo Mae (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
        "Resultado Mae (R$)", "Resultado Deyvid (R$)", "Resultado Nilson (R$)",
        "CMP no momento (R$)", "Descrição", "Brincos"]
    assert config.LOGIN_MEMBRO == {"geane": "Mae", "mae": "Mae", "deyvid": "Deyvid", "nilson": "Nilson"}


def test_quatro_donos_gera_colunas(membros_teste):
    membros_teste(4)
    assert config.MEMBROS == ["A", "B", "C", "D"]
    c = config.COLUNAS_COMPRAS
    assert c[c.index("Qtd C") + 1] == "Qtd D" and c[c.index("Qtd D") + 1] == "Descrição"
    v = config.COLUNAS_VENDAS
    assert v.index("Resultado D (R$)") + 1 == v.index("CMP no momento (R$)")
    # quem importou por nome vê a troca (mesmo objeto)
    from calculos import MEMBROS as M_calc
    assert M_calc == ["A", "B", "C", "D"]
    assert db._SCHEMA_ABAS["Vendas"] is config.COLUNAS_VENDAS


def _m(chave, cor, nome=None):
    return {"chave": chave, "nome": nome or chave, "emoji": "🙂", "cor": cor, "logins": [chave.lower()]}


@pytest.mark.parametrize("membros", [
    [_m("Jo ao", "Azul"), _m("Ana", "Verde")],          # chave com espaço
    [_m("Joao", "Azul"), _m("Ana", "Azul")],             # cor repetida
    [_m("Joao", "Azul"), _m("Joao", "Verde")],           # chave repetida
    [_m("Joao", "Azul")],                                # um dono só
    [_m(f"D{chr(65 + i)}", c) for i, c in enumerate(config.CORES_BRINCO[:9])],  # 9 donos
    [_m("Joao", "Lilás"), _m("Ana", "Verde")],           # cor que não existe
    "não é lista",
])
def test_config_invalida_usa_padrao(membros):
    assert [m["chave"] for m in config.ler_membros({"membros": membros})] == ["Mae", "Deyvid", "Nilson"]


def test_config_sem_membros_usa_padrao():
    assert config.ler_membros(None) == config.MEMBROS_PADRAO
    assert config.ler_membros({"preco_arroba": 300}) == config.MEMBROS_PADRAO


def test_config_valida():
    lista = [_m("Joao", "Azul", "João"), _m("Ana", "Verde")]
    assert config.ler_membros({"membros": lista}) == lista


def test_arquivo_com_outros_donos_recusa(membros_teste, tmp_path, monkeypatch):
    # Arquivo de 3 donos (o de hoje) e configuração com 4: não pode gravar desalinhado.
    arq = tmp_path / "gado_familia.xlsx"
    wb = Workbook()
    wb.active.title = "Compras"
    wb.active.append(list(config.COLUNAS_COMPRAS))
    wb.save(arq)
    membros_teste(4)
    monkeypatch.setattr(db, "ARQUIVO_PATH", str(arq))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="donos"):
        db.inicializar()


def test_arquivo_novo_nasce_com_os_donos(membros_teste, tmp_path, monkeypatch):
    membros_teste(2)
    arq = tmp_path / "gado_familia.xlsx"
    monkeypatch.setattr(db, "ARQUIVO_PATH", str(arq))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    db.inicializar()
    db.inicializar()   # 2ª vez (arquivo existe, donos batem): não reclama
    from openpyxl import load_workbook
    cab = [c.value for c in load_workbook(arq)["Compras"][1]]
    assert cab[4:6] == ["Qtd A", "Qtd B"]
    assert os.path.exists(arq)


# ── Task 2: contas em partes iguais para qualquer número de donos ────────────

import pandas as pd

import calculos as c


def test_partes_iguais_resto_no_ultimo(membros_teste):
    membros_teste(4)
    assert c.dividir_cotas(10) == (2, 2, 2, 4)
    assert c.dividir_cotas(10, 1, 1, 1, 1) == (3, 3, 2, 2)
    assert c.dividir_cotas(4, 1, 1, 1, 1) == (1, 1, 1, 1)
    membros_teste(2)
    assert c.dividir_cotas(5) == (2, 3)
    assert c.dividir_cotas(5, 4, 1) == (4, 1)


def test_padrao_dividir_cotas_igual_a_hoje():
    assert c.dividir_cotas(10) == (3, 3, 4)
    assert c.dividir_cotas(3, 5, 5, 0) == (2, 1, 0)


def _cenario(chaves):
    """Compra com cotas, gasto, venda com e sem cotas, morte com e sem dono,
    nascimento sem dono — com os donos `chaves`."""
    from test_calculos import _d
    n = len(chaves)
    compra = {"Data": _d("2025-01-01"), "Qtd Cabeças": 4 * n + 3, "Valor Total (R$)": 40_000.0,
              **{f"Qtd {m}": 4 for m in chaves}}
    compra[f"Qtd {chaves[-1]}"] += 3
    venda_cotas = {"Data": _d("2025-05-01"), "Qtd Cabeças": n, "Valor Total (R$)": 7_000.0,
                   **{f"Qtd {m}": 1 for m in chaves},
                   **{f"Valor {m} (R$)": 7_000.0 / n for m in chaves}}
    venda_sem = {"Data": _d("2025-06-01"), "Qtd Cabeças": 3, "Valor Total (R$)": 5_000.0}
    df_c = pd.DataFrame([compra])
    df_g = pd.DataFrame([{"Data": _d("2025-02-01"), "Valor Total (R$)": 3_000.0}])
    df_v = pd.DataFrame([venda_cotas, venda_sem])
    df_m = pd.DataFrame([
        {"Data": _d("2025-03-01"), "Tipo": "Morte/Perda", "Qtd Cabeças": 1, "Perda De": chaves[0]},
        {"Data": _d("2025-03-05"), "Tipo": "Morte/Perda", "Qtd Cabeças": 2, "Perda De": None},
        {"Data": _d("2025-04-01"), "Tipo": "Nascimento", "Qtd Cabeças": 3, "Perda De": None},
    ])
    return df_c, df_g, df_v, df_m


@pytest.mark.parametrize("n", [2, 3, 4])
def test_invariantes_com_n_donos(membros_teste, n):
    from test_calculos import checar_invariantes
    membros_teste(n)
    df_c, df_g, df_v, df_m = _cenario(list(config.MEMBROS))
    resumo, membros = checar_invariantes(df_c, df_g, df_v, df_m)
    assert set(membros) == set(config.MEMBROS)
    est = c.calcular_estoque_por_membro(df_c, df_v, df_m)
    assert set(est) == set(config.MEMBROS)
    assert sum(est.values()) == c.calcular_estoque(df_c, df_v, df_m)


# ── Task 3: gravação, telas, voz e WhatsApp ───────────────────────────────────

@pytest.fixture
def sitio_quatro_donos(membros_teste, tmp_path, monkeypatch):
    """Sítio novo (arquivo vazio em pasta temporária) com os donos A, B, C, D."""
    import sitios
    from extensions import _cache_invalidar
    membros_teste(4)
    # o sítio é montado à mão aqui; o pedido não pode voltar para o Santo Antonio
    monkeypatch.setattr(sitios, "ativar", lambda slug: None)
    monkeypatch.setattr(db, "ARQUIVO_PATH", str(tmp_path / "gado_familia.xlsx"))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    db.inicializar()
    _cache_invalidar()
    yield
    _cache_invalidar()


def test_venda_quatro_donos_grava_colunas(cliente, sitio_quatro_donos):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    r = cliente.post("/compras/nova", data={
        "csrf_token": "tok", "data": "2025-01-10", "cabecas": "10", "valor": "20000",
        "qtd_a": "1", "qtd_b": "2", "qtd_c": "3", "qtd_d": "4", "membro": "A"})
    assert r.status_code == 302
    comp = db.carregar_aba("Compras").iloc[-1]
    assert [int(comp[f"Qtd {m}"]) for m in "ABCD"] == [1, 2, 3, 4]
    assert comp["Descrição"] in ("", None) or pd.isna(comp["Descrição"])
    assert comp["Registrado Por"] == "A"

    r = cliente.post("/vendas/nova", data={
        "csrf_token": "tok", "data": "2025-03-01", "cabecas": "3", "valor": "10000",
        "qtd_a": "1", "qtd_b": "1", "qtd_c": "0", "qtd_d": "1", "descricao": "teste 4"})
    assert r.status_code == 302
    v = db.carregar_aba("Vendas").iloc[-1]
    assert [int(v[f"Qtd {m}"]) for m in "ABCD"] == [1, 1, 0, 1]
    assert sum(float(v[f"Valor {m} (R$)"]) for m in "ABCD") == pytest.approx(10_000.0)
    assert float(v["Valor C (R$)"]) == 0
    assert v["Descrição"] == "teste 4"
    from test_calculos import checar_invariantes
    d = db.carregar_todas()
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


@pytest.mark.parametrize("url", ["/", "/compras", "/compras/nova", "/vendas", "/vendas/nova",
                                 "/manejo/novo", "/gastos/novo", "/animais", "/animais/novo",
                                 "/relatorios", "/configuracoes", "/visitas/nova", "/voz"])
def test_paginas_com_quatro_donos(cliente, sitio_quatro_donos, url):
    r = cliente.get(url)
    assert r.status_code in (200, 302), url
    if r.status_code == 200 and url.endswith("nova"):
        assert "Dono D" in r.get_data(as_text=True)


def test_login_membro_configurado(membros_teste, cliente):
    import alertas_whatsapp
    from routes_animais import _membro_logado
    membros_teste(3)
    with cliente.application.test_request_context():
        from flask import session
        session["usuario"] = "B"
        assert _membro_logado() == "B"
        session["usuario"] = "nd"
        assert _membro_logado() == ""
    assert alertas_whatsapp._chave_pessoa("b") == "b"


def test_voz_reconhece_dono_configurado(membros_teste):
    import comando_voz as V
    from datetime import datetime
    membros_teste(4)
    config.NOMES_MEMBROS["D"] = "Joaquim"
    r = V.analisar("comprei 4 cabeças por 8 mil, 2 do joaquim", datetime(2026, 10, 15))
    assert r["acao"] == "compra"
    assert r["cotas"].get("D") == 2


def test_pdf_e_exportar_com_quatro_donos(cliente, sitio_quatro_donos):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    cliente.post("/compras/nova", data={"csrf_token": "tok", "data": "2025-01-10", "cabecas": "8",
                                        "valor": "16000", "membro": "A"})
    cliente.post("/vendas/nova", data={"csrf_token": "tok", "data": "2025-03-01", "cabecas": "4",
                                       "valor": "10000"})
    for url in ("/exportar", "/relatorio-pdf"):
        r = cliente.get(url)
        assert r.status_code == 200, url
        assert len(r.data) > 1000
