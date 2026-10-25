# -*- coding: utf-8 -*-
"""Aviso na hora de Morte/Perda e Nascimento (Task 5)."""
import json

import pytest

import alertas_whatsapp
import animais as A


def _fila(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture
def sem_animais(dados_restaurados):
    A._gravar(A.carregar().iloc[0:0])
    yield


def _csrf(cliente):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    return {"X-CSRF-Token": "tok"}


def _form_manejo(cliente, **extra):
    dados = {"csrf_token": "tok", "data": "2026-10-01", "cabecas": "1", "responsavel": "Deyvid"}
    dados.update(extra)
    _csrf(cliente)
    return cliente.post("/manejo/novo", data=dados)


def test_avisar_nascimento_vai_para_fila(dados_restaurados, fila_avisos_vazia):
    assert alertas_whatsapp.avisar_manejo("Nascimento", 1, "Amarelo 21 #A0003", "Mae",
                                          registrado_por="Deyvid") is True
    fila = _fila(fila_avisos_vazia)
    assert len(fila) == 1
    assert fila[0]["tipo"] == "eventos" and fila[0]["excluir"] == "Deyvid"
    assert "Amarelo 21" in fila[0]["msg"] and "#A0003" not in fila[0]["msg"]


def test_avisar_morte_com_e_sem_valores(dados_restaurados, fila_avisos_vazia):
    alertas_whatsapp.avisar_manejo("Morte/Perda", 2, "Azul 05 #A0010", "Nilson",
                                   registrado_por="Mae")
    item = _fila(fila_avisos_vazia)[0]
    assert "R$" in item["msg"] and "R$" not in item["msg_sem_valores"]
    assert "Azul 05" in item["msg"] and "#A0010" not in item["msg"]


def test_avisar_outro_tipo_nao_faz_nada(dados_restaurados, fila_avisos_vazia):
    assert alertas_whatsapp.avisar_manejo("Vacina Aftosa", 28) is False
    assert not fila_avisos_vazia.exists()


def test_form_manejo_avisa(cliente, dados_restaurados, monkeypatch, fila_avisos_vazia):
    chamadas = []
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia",
                        lambda msg, **kw: chamadas.append(kw) or 1)
    r = _form_manejo(cliente, tipo="Nascimento", nascimento_de="Mae")
    assert chamadas == []
    r.close()
    assert len(chamadas) == 1 and chamadas[0]["tipo"] == "eventos"


def test_form_manejo_vacina_nao_avisa(cliente, dados_restaurados, monkeypatch, fila_avisos_vazia):
    chamadas = []
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia",
                        lambda msg, **kw: chamadas.append(kw) or 1)
    r = _form_manejo(cliente, tipo="Vacina Aftosa", produto="X")
    r.close()
    assert chamadas == [] and not fila_avisos_vazia.exists()


def test_cadastro_nascimento_avisa(sem_animais, fila_avisos_vazia):
    A.cadastrar([{"Dono": "Mae", "Brinco Nº": 21, "Categoria": "Bezerra",
                  "Origem": "Nascimento"}], registrado_por="Deyvid")
    assert len(_fila(fila_avisos_vazia)) == 1


def test_cadastro_compra_nao_avisa(sem_animais, fila_avisos_vazia):
    A.cadastrar([{"Dono": "Mae", "Brinco Nº": 22, "Categoria": "Bezerra",
                  "Origem": "Compra"}], registrado_por="Deyvid")
    assert not fila_avisos_vazia.exists()


def test_baixa_morte_dois_donos_dois_avisos(sem_animais, fila_avisos_vazia):
    regs = A.cadastrar([
        {"Dono": "Mae", "Brinco Nº": 31, "Categoria": "Vaca", "Origem": "Compra"},
        {"Dono": "Nilson", "Brinco Nº": 32, "Categoria": "Vaca", "Origem": "Compra"}])
    assert not fila_avisos_vazia.exists()
    A.dar_baixa([r["ID"] for r in regs], "Morto", registrar_morte=True, responsavel="Deyvid")
    assert len(_fila(fila_avisos_vazia)) == 2


def test_editar_manejo_nao_avisa(cliente, dados_restaurados, fila_avisos_vazia):
    _form_manejo(cliente, tipo="Nascimento", nascimento_de="Mae").close()
    fila_avisos_vazia.unlink(missing_ok=True)
    import db
    idx = len(db.carregar_aba("Manejo")) - 1
    _csrf(cliente)
    r = cliente.post(f"/manejo/editar/{idx}", data={
        "csrf_token": "tok", "data": "2026-10-01", "tipo": "Nascimento", "cabecas": "1",
        "nascimento_de": "Mae", "responsavel": "Deyvid"})
    r.close()
    assert not fila_avisos_vazia.exists()


def test_voz_nascimento_sem_brinco_gera_um_aviso(cliente, dados_restaurados, monkeypatch,
                                                 fila_avisos_vazia):
    # nunca enviar de verdade: o r.close() abaixo dispararia o envio da fila
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia", lambda msg, **kw: 1)
    h = _csrf(cliente)
    r = cliente.post("/api/voz/executar", json={"texto": "nasceu um bezerro do nilson"}, headers=h)
    assert r.status_code == 200 and r.get_json()["ok"], r.get_json()
    assert len(_fila(fila_avisos_vazia)) == 1
    r.close()
