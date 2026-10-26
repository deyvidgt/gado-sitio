# -*- coding: utf-8 -*-
"""
Fase 2 dos vários sítios — pasta por sítio, acesso por login e seletor.
Sem sitios.json: um sítio só (o de hoje) e todo mundo entra.
"""
import json
import os
import shutil

import pytest

import config
import db
import sitios


@pytest.fixture
def dois_sitios(dados_restaurados):
    """Raiz = Santo Antonio (dados de teste) + sítio do João (2 donos, pasta nova)."""
    raiz = db.RAIZ
    cfg = {"sitios": {"santo-antonio": {"nome": "Sítio Santo Antonio", "pasta": ""},
                      "joao": {"nome": "Sítio do João", "pasta": "sitios/joao"}},
           "acesso": {"deyvid": ["santo-antonio", "joao"], "joao": ["joao"],
                      "nilson": ["santo-antonio"]}}
    with open(os.path.join(raiz, "sitios.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    pasta_joao = os.path.join(raiz, "sitios", "joao")
    os.makedirs(pasta_joao, exist_ok=True)
    with open(os.path.join(pasta_joao, "sitio_config.json"), "w", encoding="utf-8") as f:
        json.dump({"nome": "Sítio do João", "membros": [
            {"chave": "Joao", "nome": "João", "emoji": "👨", "cor": "Verde", "logins": ["joao"]},
            {"chave": "Ana", "nome": "Ana", "emoji": "👩", "cor": "Rosa", "logins": ["ana"]}]}, f)
    yield pasta_joao
    os.remove(os.path.join(raiz, "sitios.json"))
    shutil.rmtree(os.path.join(raiz, "sitios"), ignore_errors=True)
    sitios.ativar(sitios.PADRAO)


# ── Task 1 ────────────────────────────────────────────────────────────────────

def test_sem_sitios_json_um_sitio_so():
    assert not os.path.exists(os.path.join(db.RAIZ, "sitios.json"))
    assert sitios.sitios_do_usuario("qualquer") == [sitios.PADRAO]
    assert os.path.abspath(sitios.pasta(sitios.PADRAO)) == os.path.abspath(db.RAIZ)


def test_slug_invalido(dois_sitios):
    for slug in ("../fora", "Joao", "", "x" * 41, "nao-existe"):
        with pytest.raises(ValueError):
            sitios.pasta(slug)


def test_acesso_por_login(dois_sitios):
    assert sitios.sitios_do_usuario("Deyvid") == ["santo-antonio", "joao"]
    assert sitios.sitios_do_usuario("joao") == ["joao"]
    assert sitios.sitios_do_usuario("fulano") == []
    assert sitios.tem_acesso("nilson", "santo-antonio") and not sitios.tem_acesso("nilson", "joao")
    assert sitios.nome("joao") == "Sítio do João"


def test_ativar_troca_pasta_e_donos(dois_sitios):
    sitios.ativar("joao")
    assert os.path.abspath(db.DATA_DIR) == os.path.abspath(dois_sitios)
    assert config.MEMBROS == ["Joao", "Ana"]
    assert os.path.exists(db.ARQUIVO_PATH)          # sítio novo nasce com o arquivo
    assert sitios.atual() == "joao"
    sitios.ativar("santo-antonio")
    assert config.MEMBROS == ["Mae", "Deyvid", "Nilson"]
    assert os.path.abspath(db.DATA_DIR) == os.path.abspath(db.RAIZ)


# ── Task 2: pedido dentro do sítio + seletor ──────────────────────────────────

def _logar(cliente, login, sitio=None):
    with cliente.session_transaction() as s:
        s.clear()
        s["logado"] = True
        s["usuario"] = login
        s["csrf_token"] = "tok"
        if sitio:
            s["sitio"] = sitio


def test_trocar_sitio_mostra_outros_dados(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    antes = len(db.carregar_aba("Compras"))
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Geane" in pagina and "Sítio do João" in pagina   # seletor com os 2 sítios
    r = cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "joao"})
    assert r.status_code == 302
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Ana" in pagina and "Geane" not in pagina
    cliente.post("/compras/nova", data={"csrf_token": "tok", "data": "2025-01-10", "cabecas": "2",
                                        "valor": "4000", "qtd_joao": "1", "qtd_ana": "1", "membro": "Joao"})
    assert "Sítio do João" in cliente.get("/").get_data(as_text=True)
    cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "santo-antonio"})
    cliente.get("/")
    assert len(db.carregar_aba("Compras")) == antes          # Santo Antonio intacto
    sitios.ativar("joao")
    assert len(db.carregar_aba("Compras")) == 1


def test_sem_acesso_nao_troca(cliente, dois_sitios):
    _logar(cliente, "nilson")
    cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "joao"})
    assert "Geane" in cliente.get("/compras/nova").get_data(as_text=True)


def test_sessao_forjada_nao_abre_sitio_alheio(cliente, dois_sitios):
    _logar(cliente, "joao", sitio="santo-antonio")
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Ana" in pagina and "Geane" not in pagina


def test_usuario_sem_sitio_403(cliente, dois_sitios):
    _logar(cliente, "fulano")
    assert cliente.get("/").status_code == 403
    assert cliente.get("/login").status_code != 403   # login/logout continuam abrindo


def test_erro_no_pedido_solta_a_trava(cliente, dois_sitios, monkeypatch):
    import extensions
    _logar(cliente, "deyvid")
    monkeypatch.setattr("routes_dashboard._gerar_alertas", lambda *a, **k: 1 / 0)
    cliente.application.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        assert cliente.get("/").status_code == 500
    finally:
        cliente.application.config["PROPAGATE_EXCEPTIONS"] = None
    assert not extensions._trava_sitio.locked()
    assert cliente.get("/compras").status_code == 200
