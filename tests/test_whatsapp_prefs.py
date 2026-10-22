"""Preferências de WhatsApp por pessoa: filtro no envio e na fila de avisos."""
import json

import pytest

import alertas_whatsapp as aw

TIPOS = ("urgentes", "semanal", "visita", "eventos", "mensal", "valores")


def _usuarios(**receber_por_login):
    base = {
        "geane": {"whatsapp": {"telefone": "111", "apikey": "k1"}},
        "deyvid": {"whatsapp": {"telefone": "222", "apikey": "k2"}},
        "nilson": {"whatsapp": {"telefone": "333", "apikey": "k3"}},
    }
    for login, receber in receber_por_login.items():
        base[login]["whatsapp"]["receber"] = receber
    return base


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(aw, "enviar_whatsapp", lambda tel, key, msg: lista.append((tel, msg)) or True)
    return lista


def _simular(monkeypatch, usuarios):
    monkeypatch.setattr(aw, "carregar_usuarios", lambda: usuarios)


def test_sem_receber_recebe_tudo():
    cfg = {"telefone": "1", "apikey": "k"}
    assert all(aw.quer_receber(cfg, t) for t in TIPOS)
    assert aw.TIPOS_RECEBER == TIPOS


def test_alertas_ativos_false_vence():
    cfg = {"alertas_ativos": False, "receber": {"semanal": True}}
    assert aw.quer_receber(cfg, "semanal") is False
    assert aw.quer_receber(cfg, None) is False


def test_filtra_por_tipo(monkeypatch, enviados):
    _simular(monkeypatch, _usuarios(nilson={"semanal": False}))
    assert aw.enviar_para_familia("X", tipo="semanal") == 2
    assert "333" not in [t for t, _ in enviados]


def test_msg_sem_valores(monkeypatch, enviados):
    _simular(monkeypatch, _usuarios(geane={"valores": False}))
    aw.enviar_para_familia("COM R$", tipo="semanal", msg_sem_valores="SEM")
    por_tel = dict(enviados)
    assert por_tel["111"] == "SEM"
    assert por_tel["222"] == "COM R$" and por_tel["333"] == "COM R$"


def test_tipo_none_comportamento_antigo(monkeypatch, enviados):
    _simular(monkeypatch, _usuarios(nilson={"semanal": False}))
    assert aw.enviar_para_familia("X") == 3


def test_excluir_por_membro_ou_login(monkeypatch, enviados):
    _simular(monkeypatch, _usuarios())
    aw.enviar_para_familia("X", "Mae")
    assert "111" not in [t for t, _ in enviados]
    enviados.clear()
    aw.enviar_para_familia("X", excluir_usuario="deyvid")
    assert "222" not in [t for t, _ in enviados]


def test_fila_antiga_sem_tipo(monkeypatch, dados_restaurados):
    aw._pendentes_path().write_text(
        json.dumps([{"msg": "velha", "criado": "2026-10-01T10:00:00"}]), encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(aw, "enviar_para_familia", lambda msg, **kw: chamadas.append((msg, kw)) or 1)
    assert aw.enviar_avisos_pendentes() == 1
    assert chamadas[0][1]["tipo"] == "visita"


def test_fila_guarda_tipo_e_excluir(monkeypatch, dados_restaurados):
    aw.guardar_aviso_pendente("m", tipo="eventos", excluir="Deyvid", msg_sem_valores="s")
    chamadas = []
    monkeypatch.setattr(aw, "enviar_para_familia", lambda msg, **kw: chamadas.append((msg, kw)) or 1)
    aw.enviar_avisos_pendentes()
    assert chamadas[0][1] == {"tipo": "eventos", "excluir_usuario": "Deyvid", "msg_sem_valores": "s"}


# ── API de preferências ──────────────────────────────────────────────────────
@pytest.fixture
def usuarios_restaurados():
    """Guarda o usuarios.json da pasta de teste e o restaura no fim."""
    import os
    import shutil
    from extensions import _usuarios_path
    arq = _usuarios_path()
    existia = os.path.exists(arq)
    copia = arq + ".antes_do_teste"
    if existia:
        shutil.copy2(arq, copia)
    yield
    if existia:
        shutil.move(copia, arq)
    elif os.path.exists(arq):
        os.remove(arq)


def test_api_grava_e_devolve_receber(cliente, usuarios_restaurados):
    r = cliente.post("/api/config-whatsapp", json={
        "telefone": "5534999", "apikey": "k", "bot_number": "+34644663262",
        "receber": {"semanal": False, "xyz": True}})
    assert r.get_json()["ok"] is True
    d = cliente.get("/api/config-whatsapp").get_json()
    assert d["receber"]["semanal"] is False
    assert d["receber"]["visita"] is True
    assert "xyz" not in d["receber"]
    assert set(d["receber"]) == set(TIPOS)
    todos = cliente.get("/api/config-whatsapp-todos").get_json()["usuarios"]
    meu = next(u for u in todos if u["usuario"] == "deyvid")
    assert meu["receber"]["semanal"] is False


def test_api_post_sem_receber_mantem(cliente, usuarios_restaurados):
    base = {"telefone": "5534999", "apikey": "k", "bot_number": "+34644663262"}
    cliente.post("/api/config-whatsapp", json={**base, "receber": {"semanal": False}})
    cliente.post("/api/config-whatsapp", json=base)
    d = cliente.get("/api/config-whatsapp").get_json()
    assert d["receber"]["semanal"] is False


def test_pagina_tem_as_seis_caixinhas(cliente):
    html = cliente.get("/configuracoes").get_data(as_text=True)
    for t in TIPOS:
        assert f'id="cfg-wpp-rec-{t}"' in html
