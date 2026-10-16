# -*- coding: utf-8 -*-
"""
v4.4 — Fotos dos animais no Google Drive.

Nenhum teste fala com o Google: um DriveFalso (em memória) é injetado com
drive.definir_cliente(). Tudo roda na cópia temporária dos dados (conftest).
"""
import json
import os

import pytest
from openpyxl import load_workbook

import db
import drive
from config import COLUNAS_FOTOS


class DriveFalso:
    """Mesma interface de drive.Drive, guardando tudo num dict."""

    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.pastas = {}      # id_animal -> pasta_id
        self.arquivos = {}    # file_id -> {"nome", "conteudo", "mime", "props", "pasta", "lixeira"}
        self.baixados = 0
        self._n = 0

    def _checar(self):
        if self.falhar:
            raise drive.DriveErro("Não foi possível falar com o Google Drive: teste")

    def _novo_id(self, prefixo):
        self._n += 1
        return f"{prefixo}{self._n}"

    def pasta_animal(self, id_animal, nome):
        self._checar()
        if id_animal not in self.pastas:
            self.pastas[id_animal] = self._novo_id("pasta")
        return self.pastas[id_animal]

    def enviar(self, pasta_id, nome, conteudo, mime, props):
        self._checar()
        fid = self._novo_id("arq")
        self.arquivos[fid] = {"nome": nome, "conteudo": conteudo, "mime": mime,
                              "props": dict(props), "pasta": pasta_id, "lixeira": False}
        return fid

    def achar_por_envio(self, id_envio):
        self._checar()
        for fid, a in self.arquivos.items():
            if a["props"].get("id_envio") == id_envio and not a["lixeira"]:
                return fid
        return None

    def baixar(self, file_id):
        self._checar()
        self.baixados += 1
        return self.arquivos[file_id]["conteudo"]

    def lixeira(self, file_id):
        self._checar()
        self.arquivos[file_id]["lixeira"] = True

    def testar(self):
        if self.falhar:
            return False, "Não foi possível falar com o Google Drive: teste"
        return True, "Drive conectado — pasta Fotos Teste"


# ── Task 1: aba Fotos e cliente do Drive ─────────────────────────────────────

def test_aba_fotos_criada_com_colunas():
    db.inicializar()
    ws = load_workbook(db.ARQUIVO_PATH)["Fotos"]
    assert [c.value for c in ws[1]][:len(COLUNAS_FOTOS)] == COLUNAS_FOTOS


def test_drive_nao_configurado_sem_token(monkeypatch, tmp_path):
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "drive_token.json"))
    drive.definir_cliente(None)
    assert drive.configurado() is False
    assert drive.cliente() is None


class _Resp:
    def __init__(self, status, dados):
        self.status_code = status
        self._dados = dados
        self.text = json.dumps(dados)
        self.content = self.text.encode()

    def json(self):
        return self._dados


def test_drive_renova_token_e_envia(monkeypatch, tmp_path):
    tok = tmp_path / "drive_token.json"
    tok.write_text(json.dumps({"client_id": "c", "client_secret": "s",
                               "refresh_token": "r", "pasta_raiz": "RAIZ"}), encoding="utf-8")
    monkeypatch.setattr(drive, "token_path", lambda: str(tok))
    chamadas = []

    def falso_post(url, **kw):
        chamadas.append((url, kw))
        if url == "https://oauth2.googleapis.com/token":
            return _Resp(200, {"access_token": "TOK", "expires_in": 3600})
        return _Resp(200, {"id": "ARQ1"})

    monkeypatch.setattr(drive.requests, "post", falso_post)
    d = drive.Drive()
    assert d.enviar("PASTA", "a.jpg", b"\xff\xd8\xff", "image/jpeg", {"id_envio": "x"}) == "ARQ1"
    assert d.enviar("PASTA", "b.jpg", b"\xff\xd8\xff", "image/jpeg", {"id_envio": "y"}) == "ARQ1"

    tokens = [c for c in chamadas if c[0] == "https://oauth2.googleapis.com/token"]
    uploads = [c for c in chamadas
               if c[0] == "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"]
    assert len(tokens) == 1
    assert len(uploads) == 2
    assert uploads[0][1]["headers"]["Authorization"] == "Bearer TOK"

    monkeypatch.setattr(drive.requests, "post",
                        lambda url, **kw: _Resp(200, {"access_token": "TOK", "expires_in": 3600})
                        if "oauth2" in url else _Resp(500, {"error": "x"}))
    with pytest.raises(drive.DriveErro):
        d.enviar("PASTA", "c.jpg", b"\xff\xd8\xff", "image/jpeg", {})
