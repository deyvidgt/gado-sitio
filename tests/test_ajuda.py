# -*- coding: utf-8 -*-
"""Aba Ajuda: página com passo a passo; prints guardados no Google Drive."""
import os
import shutil

import pytest

import drive
import routes_fotos
from test_fotos import DriveFalso

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50


class DriveComAjuda(DriveFalso):
    """DriveFalso + um print da ajuda já guardado."""

    def __init__(self):
        super().__init__()
        self.enviar("pastaAjuda", "p-login.png", PNG, "image/png", {"ajuda": "p-login.png"})


@pytest.fixture
def com_drive():
    shutil.rmtree(routes_fotos.cache_dir(), ignore_errors=True)
    falso = DriveComAjuda()
    drive.definir_cliente(falso)
    yield falso
    drive.definir_cliente(None)
    shutil.rmtree(routes_fotos.cache_dir(), ignore_errors=True)


@pytest.fixture
def sem_drive(monkeypatch, tmp_path):
    drive.definir_cliente(None)
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "nada.json"))


def test_menu_tem_ajuda_acima_de_configuracoes(cliente):
    html = cliente.get("/", follow_redirects=True).get_data(as_text=True)
    assert "❓ Ajuda" in html or "Ajuda</a>" in html
    assert html.index('href="/ajuda"') < html.index('href="/configuracoes"')


def test_pagina_ajuda_abre_com_drive(cliente, com_drive):
    r = cliente.get("/ajuda")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "/ajuda/img/p-login.png" in html
    for assunto in ("Visita ao Sítio", "Fotos do animal", "Comando de Voz", "Backups",
                    "BCS de 1 a 9", "Conferir PDF antes de enviar", "Bulas e embalagens"):
        assert assunto in html


def test_pagina_ajuda_sem_drive_mostra_texto(cliente, sem_drive):
    r = cliente.get("/ajuda")
    assert r.status_code == 200
    assert "imagem indisponível" in r.get_data(as_text=True)


def test_ajuda_exige_login(flask_app):
    assert flask_app.test_client().get("/ajuda").status_code == 302


def test_print_vem_do_drive_e_depois_do_cache(cliente, com_drive):
    r1 = cliente.get("/ajuda/img/p-login.png")
    r2 = cliente.get("/ajuda/img/p-login.png")
    assert r1.status_code == 200 and r1.data == PNG == r2.data
    assert r1.mimetype == "image/png"
    assert com_drive.baixados == 1


def test_print_inexistente_ou_nome_invalido_404(cliente, com_drive):
    for url in ("/ajuda/img/nao-existe.png", "/ajuda/img/..%2Fx.png", "/ajuda/img/A.PNG"):
        assert cliente.get(url).status_code == 404, url


def test_drive_acha_por_propriedade(monkeypatch, tmp_path):
    import json
    tok = tmp_path / "t.json"
    tok.write_text(json.dumps({"client_id": "c", "client_secret": "s", "refresh_token": "r",
                               "pasta_raiz": "RAIZ"}), encoding="utf-8")
    monkeypatch.setattr(drive, "token_path", lambda: str(tok))
    pedidos = []

    class R:
        status_code = 200
        text = ""

        def __init__(self, d):
            self.d = d

        def json(self):
            return self.d

    monkeypatch.setattr(drive.requests, "post",
                        lambda url, **kw: R({"access_token": "T", "expires_in": 3600}))

    def get(url, **kw):
        pedidos.append(kw["params"]["q"])
        return R({"files": [{"id": "ARQ9", "name": "p-login.png"}]})

    monkeypatch.setattr(drive.requests, "get", get)
    assert drive.Drive().achar_por_prop("ajuda", "p-login.png") == "ARQ9"
    assert "key='ajuda' and value='p-login.png'" in pedidos[0]


def test_subir_prints_envia_e_substitui(tmp_path):
    import subir_prints_ajuda as S
    falso = DriveFalso()
    (tmp_path / "c-visita-1.png").write_bytes(PNG)
    (tmp_path / "Nome Invalido.png").write_bytes(PNG)
    (tmp_path / "leia.txt").write_text("x")
    assert S.subir(str(tmp_path), falso) == ["c-visita-1.png"]
    antigo = falso.achar_por_prop("ajuda", "c-visita-1.png")
    (tmp_path / "c-visita-1.png").write_bytes(PNG + b"novo")
    S.subir(str(tmp_path), falso)
    novo = falso.achar_por_prop("ajuda", "c-visita-1.png")
    assert novo != antigo and falso.arquivos[antigo]["lixeira"] is True
    assert falso.arquivos[novo]["conteudo"].endswith(b"novo")
