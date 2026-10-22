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
