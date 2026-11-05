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


def test_url_da_fonte_deve_ser_https_e_oficial():
    assert bulas.validar_url_oficial("https://zoetis.com.br/bulas/produto.pdf")
<<<<<<< HEAD
    assert bulas.validar_url_oficial("https://docs.gov/bula.pdf")
    assert bulas.validar_url_oficial("https://docs.gov.br/bula.pdf")
    assert bulas.validar_url_oficial("https://documentos.gov.pt/bula.pdf")
    assert bulas.validar_url_oficial("https://www.boehringer-ingelheim.pt/bulas/produto.pdf")
    assert bulas.validar_url_oficial("https://www.merial.com/bulas/produto.pdf")
    assert bulas.validar_url_oficial("https://www.woah.org/bulas/produto.pdf")
=======
    assert bulas.validar_url_oficial("https://docs.gov.br/bula.pdf")
>>>>>>> f98ba577cb0a04c0a1e525a4d8fb26a1bf3d8dbc
    for url in (
        "http://zoetis.com.br/bula.pdf",
        "https://zoetis.com.br.example.org/bula.pdf",
        "https://site-desconhecido.example/bula.pdf",
<<<<<<< HEAD
        "https://fabricante-falso.com.br/bula.pdf",
        "https://qualquer-site.org/bula.pdf",
=======
>>>>>>> f98ba577cb0a04c0a1e525a4d8fb26a1bf3d8dbc
        "https://usuario@zoetis.com.br/bula.pdf",
        "https://zoetis.com.br:8443/bula.pdf",
    ):
        with pytest.raises(bulas.BulaFonteErro):
            bulas.validar_url_oficial(url)


<<<<<<< HEAD
def test_mensagem_de_url_nao_oficial_informa_fontes_aceitas():
    with pytest.raises(bulas.BulaFonteErro, match="URL não reconhecida como fonte oficial"):
        bulas.validar_url_oficial("https://fabricante-desconhecido.pt/bula.pdf")


=======
>>>>>>> f98ba577cb0a04c0a1e525a4d8fb26a1bf3d8dbc
def test_baixar_bula_valida_pdf_e_restringe_redirecionamento(monkeypatch):
    class Resposta:
        status_code = 200
        is_redirect = False
        is_permanent_redirect = False
        headers = {}

        def iter_content(self, tamanho):
            return iter([PDF])

        def close(self):
            pass

    chamadas = []

    def get(url, **kwargs):
        chamadas.append(url)
        return Resposta()

    monkeypatch.setattr(bulas.requests, "get", get)
    dados, fonte = bulas.baixar_bula("https://zoetis.com.br/bula.pdf")
    assert dados == PDF and fonte == "https://zoetis.com.br/bula.pdf"
    assert chamadas == [fonte]


def test_baixar_bula_rejeita_conteudo_que_nao_e_pdf(monkeypatch):
    class Resposta:
        status_code = 200
        is_redirect = False
        is_permanent_redirect = False
        headers = {}

        def iter_content(self, tamanho):
            return iter([b"<html>not a PDF</html>"])

        def close(self):
            pass

    monkeypatch.setattr(bulas.requests, "get", lambda *a, **k: Resposta())
    with pytest.raises(bulas.BulaFonteErro, match="não é um PDF"):
        bulas.baixar_bula("https://zoetis.com.br/bula.pdf")


def test_admin_confere_e_confirma_envio_da_bula(cliente, com_drive, monkeypatch):
    import routes_bulas

    monkeypatch.setattr(routes_bulas.sitios, "e_admin", lambda usuario: True)
    monkeypatch.setattr(bulas, "baixar_bula", lambda url: (PDF, url))
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "csrf-bulas"
    resposta = cliente.post("/bulas/atualizar/previsualizar", data={
        "csrf_token": "csrf-bulas",
        "produto": "ivermectina",
        "url": "https://zoetis.com.br/bulas/ivermectina.pdf",
    })
    assert resposta.status_code == 200
    assert "Conferir bula" in resposta.get_data(as_text=True)
    with cliente.session_transaction() as sess:
        token = sess["bula_pendente"]["token"]
    previa = cliente.get(f"/bulas/pendente/{token}")
    assert previa.status_code == 200 and previa.data == PDF

    resposta = cliente.post("/bulas/atualizar/confirmar", data={
        "csrf_token": "csrf-bulas", "token": token,
    })
    assert resposta.status_code == 302 and resposta.headers["Location"].endswith("/bulas")
    arquivo = com_drive.achar_por_prop("bulas", "ivermectina__bula.pdf")
    assert arquivo
    assert com_drive.arquivos[arquivo]["conteudo"] == PDF
    assert com_drive.arquivos[arquivo]["descricao"].endswith("https://zoetis.com.br/bulas/ivermectina.pdf")
    with cliente.session_transaction() as sess:
        assert "bula_pendente" not in sess


def test_atualizar_bulas_exige_admin(cliente, monkeypatch):
    import routes_bulas

    monkeypatch.setattr(routes_bulas.sitios, "e_admin", lambda usuario: False)
    assert cliente.get("/bulas/atualizar").status_code == 403


def test_bulas_exige_login(flask_app):
    assert flask_app.test_client().get("/bulas").status_code == 302
