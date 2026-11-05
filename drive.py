# -*- coding: utf-8 -*-
"""
drive.py — cliente mínimo do Google Drive (v4.4), só com `requests`.

Por que não a biblioteca oficial do Google: ela é pesada e o site só precisa de
meia dúzia de chamadas REST (achar/criar pasta, subir, baixar, mandar p/ lixeira).

Credencial: <DATA_DIR>/drive_token.json, gerado uma vez por configurar_drive.py
  {"client_id", "client_secret", "refresh_token", "pasta_raiz"}
Sem esse arquivo o recurso de fotos fica desligado e o resto do site segue normal.

O escopo OAuth é o Drive inteiro (drive.file não enxerga a pasta que já existia),
então TODA operação aqui fica presa dentro da pasta raiz configurada.
"""
from __future__ import annotations

import json
import os
import time
import uuid

import requests

import db
from config import DRIVE_PASTA_PADRAO

URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_API = "https://www.googleapis.com/drive/v3/files"
URL_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
TIPO_PASTA = "application/vnd.google-apps.folder"
TIMEOUT = 30
_CHAVES = ("client_id", "client_secret", "refresh_token")


class DriveErro(Exception):
    """Qualquer falha ao falar com o Drive (rede, token revogado, HTTP ≥ 400)."""


def token_path() -> str:
    return os.path.join(db.DATA_DIR, "drive_token.json")


def _ler_token() -> dict | None:
    try:
        with open(token_path(), encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return None
    if not all(dados.get(k) for k in _CHAVES):
        return None
    dados.setdefault("pasta_raiz", DRIVE_PASTA_PADRAO)
    return dados


def configurado() -> bool:
    return _ler_token() is not None


def _q(valor: str) -> str:
    """Escapa um valor para a linguagem de busca do Drive."""
    return valor.replace("\\", "\\\\").replace("'", "\\'")


class Drive:
    def __init__(self, credencial: dict | None = None):
        cred = credencial or _ler_token()
        if not cred:
            raise DriveErro("Fotos não configuradas (falta o drive_token.json).")
        self.cred = cred
        self.raiz = cred.get("pasta_raiz") or DRIVE_PASTA_PADRAO
        self._token = None
        self._expira = 0.0

    # ── HTTP ────────────────────────────────────────────────────────────────
    def _access_token(self) -> str:
        if self._token and time.time() < self._expira:
            return self._token
        r = self._http(requests.post, URL_TOKEN, autenticar=False, data={
            "client_id": self.cred["client_id"],
            "client_secret": self.cred["client_secret"],
            "refresh_token": self.cred["refresh_token"],
            "grant_type": "refresh_token",
        })
        dados = r.json()
        self._token = dados["access_token"]
        # Renova um minuto antes de vencer, para não falhar no meio de um upload.
        self._expira = time.time() + int(dados.get("expires_in", 3600)) - 60
        return self._token

    def _http(self, metodo, url, autenticar=True, headers=None, **kw):
        headers = dict(headers or {})
        if autenticar:
            headers["Authorization"] = f"Bearer {self._access_token()}"
        try:
            r = metodo(url, headers=headers, timeout=TIMEOUT, **kw)
        except requests.RequestException as e:
            raise DriveErro(f"Não foi possível falar com o Google Drive: {e}") from e
        if r.status_code >= 400:
            raise DriveErro(f"Não foi possível falar com o Google Drive: "
                            f"HTTP {r.status_code} {r.text[:200]}")
        return r

    def _buscar(self, q: str) -> list[dict]:
        r = self._http(requests.get, URL_API, params={
            "q": q, "fields": "files(id,name)", "pageSize": 10, "spaces": "drive"})
        return r.json().get("files", [])

    # ── Operações ───────────────────────────────────────────────────────────
    def pasta_animal(self, id_animal: str, nome: str) -> str:
        """Acha a subpasta do animal pelo ID (sobrevive a troca de brinco) ou cria."""
        achadas = self._buscar(
            f"'{_q(self.raiz)}' in parents and mimeType='{TIPO_PASTA}' and trashed=false "
            f"and appProperties has {{ key='animal' and value='{_q(id_animal)}' }}")
        if achadas:
            return achadas[0]["id"]
        r = self._http(requests.post, URL_API, params={"fields": "id"}, json={
            "name": nome, "mimeType": TIPO_PASTA, "parents": [self.raiz],
            "appProperties": {"animal": id_animal}})
        return r.json()["id"]

    def enviar(self, pasta_id: str, nome: str, conteudo: bytes, mime: str, props: dict,
               descricao: str = "") -> str:
        meta = {"name": nome, "parents": [pasta_id],
                "appProperties": {k: str(v) for k, v in props.items()}}
        if descricao:
            meta["description"] = descricao
        fronteira = uuid.uuid4().hex
        corpo = (
            f"--{fronteira}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(meta)}\r\n--{fronteira}\r\nContent-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + conteudo + f"\r\n--{fronteira}--".encode()
        r = self._http(requests.post, URL_UPLOAD, data=corpo,
                       headers={"Content-Type": f"multipart/related; boundary={fronteira}"})
        return r.json()["id"]

    def pasta(self, nome: str, props: dict) -> str:
        """Subpasta da raiz achada pelas appProperties (ex.: {"ajuda": "pasta"}) ou criada."""
        filtro = " and ".join(f"appProperties has {{ key='{_q(k)}' and value='{_q(str(v))}' }}"
                              for k, v in props.items())
        achadas = self._buscar(f"'{_q(self.raiz)}' in parents and mimeType='{TIPO_PASTA}' "
                               f"and trashed=false and {filtro}")
        if achadas:
            return achadas[0]["id"]
        r = self._http(requests.post, URL_API, params={"fields": "id"}, json={
            "name": nome, "mimeType": TIPO_PASTA, "parents": [self.raiz],
            "appProperties": {k: str(v) for k, v in props.items()}})
        return r.json()["id"]

    def listar(self, pasta_id: str) -> list[dict]:
        """Arquivos de uma pasta (id e nome) numa chamada só — a tela de bulas
        mostra o catálogo inteiro sem uma consulta por remédio."""
        r = self._http(requests.get, URL_API, params={
            "q": f"'{_q(pasta_id)}' in parents and trashed=false",
            "fields": "files(id,name)", "pageSize": 200, "spaces": "drive"})
        return r.json().get("files", [])

    def achar_por_prop(self, chave: str, valor: str) -> str | None:
        """Arquivo marcado com appProperties chave=valor (ex.: print da Ajuda)."""
        achados = self._buscar(
            f"appProperties has {{ key='{_q(chave)}' and value='{_q(valor)}' }} and trashed=false")
        return achados[0]["id"] if achados else None

    def achar_por_envio(self, id_envio: str) -> str | None:
        """Arquivo que já subiu com esse id_envio (o Excel pode não ter gravado)."""
        achados = self._buscar(
            f"appProperties has {{ key='id_envio' and value='{_q(id_envio)}' }} and trashed=false")
        return achados[0]["id"] if achados else None

    def baixar(self, file_id: str) -> bytes:
        return self._http(requests.get, f"{URL_API}/{file_id}", params={"alt": "media"}).content

    def lixeira(self, file_id: str) -> None:
        # Lixeira e não exclusão definitiva: o Drive guarda por 30 dias.
        self._http(requests.patch, f"{URL_API}/{file_id}", json={"trashed": True})

    def testar(self) -> tuple[bool, str]:
        try:
            r = self._http(requests.get, f"{URL_API}/{self.raiz}", params={"fields": "name"})
            return True, f"Drive conectado — pasta {r.json().get('name', '?')}"
        except DriveErro as e:
            return False, str(e)


# ── Instância compartilhada (e troca nos testes) ─────────────────────────────
_cliente = None
_injetado = False


def cliente():
    """Drive pronto para uso, ou None se as fotos não estão configuradas."""
    global _cliente
    if _injetado:
        return _cliente
    if _cliente is None and configurado():
        _cliente = Drive()
    return _cliente


def definir_cliente(c) -> None:
    """Testes: injeta um Drive falso (ou None = 'não configurado')."""
    global _cliente, _injetado
    _cliente, _injetado = c, c is not None
