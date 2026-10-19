# -*- coding: utf-8 -*-
"""
Brincos voltam a Vivo ao excluir/editar a venda; preço da arroba configurável;
cotação do IMEA com cache e sem instalar o Chromium durante a requisição.
"""
import pandas as pd
import pytest

import animais as A
import db
from test_animais import _voz, sem_animais, _sem_sobra_de_backup  # noqa: F401 (fixtures)


def _form(cliente, url, **campos):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    dados = {"csrf_token": "tok", "data": "2026-05-10", "descricao": ""}
    dados.update(campos)
    return cliente.post(url, data=dados)


def _status(num, cor):
    df = A.carregar()
    return df[(df["Brinco Nº"] == num) & (df["Brinco Cor"] == cor)]["Status"].tolist()


def _vender_dois(cliente):
    _voz(cliente, "registrar boi brinco amarelo 81 deyvid")
    _voz(cliente, "registrar boi brinco amarelo 82 deyvid")
    r = _form(cliente, "/vendas/nova", cabecas="2", valor="9000", qtd_deyvid="2",
              brincos="amarelo 81, amarelo 82")
    assert r.status_code == 302
    assert _status(81, "Amarelo") == ["Vendido"] and _status(82, "Amarelo") == ["Vendido"]
    return len(db.carregar_aba("Vendas")) - 1


# ── Brincos ───────────────────────────────────────────────────────────────────

def test_excluir_venda_devolve_animais(cliente, sem_animais):
    idx = _vender_dois(cliente)
    _form(cliente, f"/excluir/Vendas/{idx}")
    assert _status(81, "Amarelo") == ["Vivo"] and _status(82, "Amarelo") == ["Vivo"]
    df = A.carregar()
    assert df[df["Brinco Nº"] == 81]["Data Saída"].isna().all()


def test_editar_venda_sem_mudar_brincos_nao_da_erro(cliente, sem_animais):
    idx = _vender_dois(cliente)
    # o formulário de edição mostra "Amarelo 81, Amarelo 82" (sem #ID) — antes
    # isso dava "Nenhum animal vivo com brinco" e a venda não podia ser editada
    r = _form(cliente, f"/vendas/editar/{idx}", cabecas="2", valor="9500", qtd_deyvid="2",
              brincos="Amarelo 81, Amarelo 82")
    assert r.status_code == 302 and r.headers["Location"].endswith("/vendas")
    v = db.carregar_aba("Vendas").iloc[idx]
    assert float(v["Valor Total (R$)"]) == 9500 and "Amarelo 81 #A" in v["Brincos"]


def test_editar_venda_tirando_brinco_devolve_o_animal(cliente, sem_animais):
    idx = _vender_dois(cliente)
    _form(cliente, f"/vendas/editar/{idx}", cabecas="1", valor="4500", qtd_deyvid="1",
          brincos="Amarelo 81")
    assert _status(81, "Amarelo") == ["Vendido"]
    assert _status(82, "Amarelo") == ["Vivo"]


def test_brinco_reaproveitado_nao_volta(cliente, sem_animais):
    idx = _vender_dois(cliente)
    _voz(cliente, "registrar boi brinco amarelo 82 deyvid")   # outro animal com o 82
    _form(cliente, f"/excluir/Vendas/{idx}")
    st = _status(82, "Amarelo")
    assert sorted(st) == ["Vendido", "Vivo"]   # o antigo continua vendido
    assert _status(81, "Amarelo") == ["Vivo"]


# ── Preço da arroba ───────────────────────────────────────────────────────────

def test_preco_arroba_config():
    from calculos import preco_arroba_config, PRECO_ARROBA_REF
    assert preco_arroba_config({}) == PRECO_ARROBA_REF
    assert preco_arroba_config({"preco_arroba": 0}) == PRECO_ARROBA_REF
    assert preco_arroba_config({"preco_arroba": "abc"}) == PRECO_ARROBA_REF
    assert preco_arroba_config({"preco_arroba": 312.5}) == 312.5


def test_preco_arroba_salvo_vale_no_painel(cliente, monkeypatch, tmp_path):
    import routes_usuarios
    from extensions import _cache_invalidar_chave
    cfg_path = tmp_path / "sitio_config.json"
    monkeypatch.setattr(routes_usuarios, "_sitio_config_path", lambda: str(cfg_path))
    import extensions
    monkeypatch.setattr(extensions, "_ler_sitio_config_disco",
                        lambda: __import__("json").loads(cfg_path.read_text(encoding="utf-8")))
    import routes_dashboard
    monkeypatch.setattr(routes_dashboard, "_ler_sitio_config_disco",
                        extensions._ler_sitio_config_disco)

    r = _form(cliente, "/configuracoes/rebanho", peso_medio="480", rendimento="52",
              preco_arroba="299,90")
    assert r.status_code == 302
    import json
    assert json.loads(cfg_path.read_text(encoding="utf-8"))["preco_arroba"] == 299.9
    _cache_invalidar_chave("sitio_config")
    html = cliente.get("/").get_data(as_text=True)
    assert "R$ 299,90/@" in html
    assert "Preço da arroba" in cliente.get("/configuracoes").get_data(as_text=True)


# ── IMEA ──────────────────────────────────────────────────────────────────────

HTML_IMEA = """<html><body><table>
<tr><th>Região</th><th>R$/cab</th><th>Var %</th></tr>
<tr><td>Sudeste</td><td>2.890,00</td><td>1,2%</td></tr>
</table><p>NOVILHA NELORE 18M 255 kg 8,5@</p></body></html>"""


@pytest.fixture
def imea(monkeypatch):
    import routes_api
    routes_api._imea_cache.clear()
    chamadas = []
    monkeypatch.setattr(routes_api, "_fetch_imea_inline",
                        lambda: chamadas.append(1) or (HTML_IMEA, "fake"))
    yield routes_api, chamadas
    routes_api._imea_cache.clear()


def test_imea_busca_uma_vez_e_usa_cache(imea):
    routes_api, chamadas = imea
    r1 = routes_api._precos_imea()
    r2 = routes_api._precos_imea()
    assert len(chamadas) == 1
    assert r1["erro"] is None and r1["precos"][0]["preco"] == 2890.0
    assert r2["precos"] == r1["precos"]


def test_imea_sem_chromium_nao_instala(monkeypatch):
    import subprocess
    import routes_api
    routes_api._imea_cache.clear()

    def _sem_chromium():
        raise RuntimeError("Chromium não instalado no servidor.")
    monkeypatch.setattr(routes_api, "_fetch_imea_inline", _sem_chromium)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("não pode instalar"))
    r = routes_api._precos_imea()
    assert "Chromium não instalado" in r["erro"] and r["ttl"] == routes_api._IMEA_TTL_ERRO
    routes_api._imea_cache.clear()


def test_api_imea_compara_com_break_even(cliente, imea):
    pytest.importorskip("playwright")
    d = cliente.get("/api/cotacao-imea").get_json()
    assert d["ok"] and d["cotacoes"][0]["preco_cab"] == 2890.0
    assert d["cotacoes"][0]["vs_breakeven"] == pytest.approx(2890.0 - d["break_even"], abs=0.01)
