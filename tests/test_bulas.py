# -*- coding: utf-8 -*-
"""📖 Bulas (v5.16): catálogo lido do Drive e download só para quem está logado."""
import pytest

import bulas
import drive
from subir_bulas import nome_destino, subir
from test_fotos import DriveFalso

PDF = b"%PDF-1.4\n" + b"0" * 50
JPG = b"\xff\xd8\xff" + b"0" * 50


@pytest.fixture
def com_drive():
    falso = DriveFalso()
    drive.definir_cliente(falso)
    yield falso
    drive.definir_cliente(None)


def test_nome_destino_pela_extensao():
    assert nome_destino("Ivermectina.pdf") == "ivermectina__bula.pdf"
    assert nome_destino("ivermectina.jpg") == "ivermectina__embalagem.jpg"
    assert nome_destino("ivermectina__bula.pdf") == "ivermectina__bula.pdf"
    assert nome_destino("leia.txt") is None


def test_subir_envia_e_substitui(tmp_path, com_drive):
    (tmp_path / "ivermectina.pdf").write_bytes(PDF)
    (tmp_path / "ivermectina.jpg").write_bytes(JPG)
    (tmp_path / "leia.txt").write_text("x")
    assert sorted(subir(str(tmp_path), com_drive)) == [
        "ivermectina__bula.pdf", "ivermectina__embalagem.jpg"]
    antigo = com_drive.achar_por_prop("bulas", "ivermectina__bula.pdf")
    (tmp_path / "ivermectina.pdf").write_bytes(PDF + b"novo")
    subir(str(tmp_path), com_drive)
    novo = com_drive.achar_por_prop("bulas", "ivermectina__bula.pdf")
    assert novo != antigo and com_drive.arquivos[antigo]["lixeira"] is True


def test_catalogo_mostra_o_que_existe_no_drive(com_drive):
    subir_dummy = com_drive.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
    com_drive.enviar(subir_dummy, "ivermectina__bula.pdf", PDF, "application/pdf",
                     {"bulas": "ivermectina__bula.pdf"})
    itens = {i["nome"]: i for i in bulas.catalogo()}
    assert itens["Ivermectina"]["bula"] == "ivermectina__bula.pdf"
    assert itens["Ivermectina"]["embalagem"] is None
    assert itens["Penicilina"]["bula"] is None


def test_catalogo_sem_drive_lista_produtos_sem_arquivo(monkeypatch, tmp_path):
    drive.definir_cliente(None)
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "nada.json"))
    itens = bulas.catalogo()
    assert itens and all(i["bula"] is None and i["embalagem"] is None for i in itens)
    assert any(i["nome"] == "Ivermectina" for i in itens)


def test_pagina_lista_e_abre_a_bula(cliente, com_drive):
    pasta = com_drive.pasta(bulas.NOME_PASTA, {"bulas": "pasta"})
    com_drive.enviar(pasta, "ivermectina__bula.pdf", PDF, "application/pdf",
                     {"bulas": "ivermectina__bula.pdf"})

    html = cliente.get("/bulas").get_data(as_text=True)
    assert "/bulas/ivermectina__bula.pdf" in html

    r = cliente.get("/bulas/ivermectina__bula.pdf")
    assert r.status_code == 200 and r.data == PDF
    assert r.mimetype == "application/pdf"


def test_arquivo_inexistente_ou_nome_invalido_404(cliente, com_drive):
    for url in ("/bulas/nao-existe__bula.pdf", "/bulas/..%2Fdrive_token.json",
                "/bulas/IVermectina__bula.pdf"):
        assert cliente.get(url).status_code == 404, url


def test_bulas_exige_login(flask_app):
    assert flask_app.test_client().get("/bulas").status_code == 302
