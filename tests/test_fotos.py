# -*- coding: utf-8 -*-
"""
v4.4 — Fotos dos animais no Google Drive.

Nenhum teste fala com o Google: um DriveFalso (em memória) é injetado com
drive.definir_cliente(). Tudo roda na cópia temporária dos dados (conftest).
"""
import json

import pandas as pd
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

    def achar_por_prop(self, chave, valor):
        self._checar()
        for fid, a in self.arquivos.items():
            if a["props"].get(chave) == valor and not a["lixeira"]:
                return fid
        return None

    def listar(self, pasta_id):
        self._checar()
        return [{"id": fid, "name": a["nome"]} for fid, a in self.arquivos.items()
                if a["pasta"] == pasta_id and not a["lixeira"]]

    def pasta(self, nome, props):
        self._checar()
        chave = "pasta:" + repr(sorted(props.items()))
        if chave not in self.pastas:
            self.pastas[chave] = self._novo_id("pasta")
        return self.pastas[chave]

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


# ── Task 2: regras das fotos ─────────────────────────────────────────────────

import animais as A  # noqa: E402
import fotos  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100


@pytest.fixture(autouse=True)
def _sem_sobra_de_backup():
    """Excluir faz backup de verdade; apaga os criados aqui (o teste de limpeza
    de backups conta os arquivos da pasta)."""
    pasta = os.path.join(db.DATA_DIR, "backups")
    antes = set(os.listdir(pasta)) if os.path.isdir(pasta) else set()
    yield
    if os.path.isdir(pasta):
        for n in set(os.listdir(pasta)) - antes:
            os.remove(os.path.join(pasta, n))


@pytest.fixture
def amb(dados_restaurados):
    """Um animal novo (Amarelo 91) e o Drive falso no lugar do Google."""
    db.inicializar()
    if os.path.exists(fotos._ultimo_id_path()):
        os.remove(fotos._ultimo_id_path())
    A._gravar(A.carregar().iloc[0:0])
    id_ = A.cadastrar([{"Dono": "Deyvid", "Brinco Nº": 91, "Categoria": "Bezerra"}])[0]["ID"]
    falso = DriveFalso()
    drive.definir_cliente(falso)
    yield falso, id_
    drive.definir_cliente(None)
    if os.path.exists(fotos._ultimo_id_path()):
        os.remove(fotos._ultimo_id_path())


def _env(id_, envio, data="10/10/2026", tipo="Evolução", conteudo=JPG):
    return fotos.enviar(id_, conteudo, data, tipo, "legenda", "Deyvid", envio)


def test_envio_grava_linha_na_ordem(amb):
    falso, id_ = amb
    r = _env(id_, "e1")
    assert r == {"duplicada": False, "id_foto": "F00001"}
    ws = load_workbook(db.ARQUIVO_PATH)["Fotos"]
    linha = dict(zip([c.value for c in ws[1]], [c.value for c in ws[2]]))
    assert linha["ID Foto"] == "F00001" and linha["Animal"] == id_
    assert linha["Tipo"] == "Evolução" and linha["ID Envio"] == "e1"
    arq = falso.arquivos[linha["Drive ID"]]
    assert arq["nome"] == "2026-10-10_F00001.jpg"
    assert arq["props"]["id_envio"] == "e1"
    assert falso.pastas[id_] == arq["pasta"]


def test_primeira_foto_vira_principal(amb):
    _, id_ = amb
    _env(id_, "e1")
    assert fotos.principais() == {id_: "F00001"}


def test_segunda_nao_tira_a_principal(amb):
    _, id_ = amb
    _env(id_, "e1")
    _env(id_, "e2", tipo="Perfil")
    assert [f["principal"] for f in fotos.listar(id_)].count(True) == 1
    assert fotos.principais() == {id_: "F00001"}


def test_reenvio_nao_duplica(amb):
    falso, id_ = amb
    _env(id_, "e1")
    assert _env(id_, "e1") == {"duplicada": True, "id_foto": "F00001"}
    assert len(fotos.carregar()) == 1 and len(falso.arquivos) == 1


def test_orfao_no_drive_e_reaproveitado(amb):
    falso, id_ = amb
    pasta = falso.pasta_animal(id_, "x")
    fid = falso.enviar(pasta, "orfao.jpg", JPG, "image/jpeg", {"id_envio": "e9"})
    _env(id_, "e9")
    assert len(falso.arquivos) == 1
    assert fotos.carregar().iloc[0]["Drive ID"] == fid


def test_recusa_nao_imagem(amb):
    _, id_ = amb
    with pytest.raises(fotos.FotoInvalida):
        _env(id_, "e1", conteudo=b"%PDF-1.4 nada de foto")


def test_recusa_grande(amb):
    _, id_ = amb
    with pytest.raises(fotos.FotoInvalida):
        _env(id_, "e1", conteudo=JPG + b"0" * (8 * 1024 * 1024))


def test_recusa_animal_inexistente(amb):
    with pytest.raises(fotos.FotoInvalida):
        _env("A9999", "e1")


def test_recusa_tipo_invalido(amb):
    _, id_ = amb
    with pytest.raises(fotos.FotoInvalida):
        _env(id_, "e1", tipo="Selfie")


def test_drive_fora_nao_grava(amb):
    falso, id_ = amb
    falso.falhar = True
    with pytest.raises(drive.DriveErro):
        _env(id_, "e1")
    assert fotos.carregar().empty


def test_definir_principal_unica(amb):
    _, id_ = amb
    _env(id_, "e1")
    _env(id_, "e2")
    fotos.definir_principal("F00002")
    assert [(f["id_foto"], f["principal"]) for f in fotos.listar(id_) if f["principal"]] == [("F00002", True)]


def test_excluir_principal_promove_proxima(amb):
    falso, id_ = amb
    _env(id_, "e1", data="01/10/2026")
    _env(id_, "e2", data="05/10/2026")
    _env(id_, "e3", data="03/10/2026")
    drive_id = fotos.por_id("F00001")["drive_id"]
    fotos.excluir("F00001")
    assert fotos.por_id("F00001") is None
    assert falso.arquivos[drive_id]["lixeira"] is True
    assert fotos.principais() == {id_: "F00002"}


def test_listar_mais_recente_primeiro(amb):
    _, id_ = amb
    _env(id_, "e1", data="01/10/2026")
    _env(id_, "e2", data="05/10/2026")
    assert [f["id_foto"] for f in fotos.listar(id_)] == ["F00002", "F00001"]


def test_editar(amb):
    _, id_ = amb
    _env(id_, "e1")
    fotos.editar("F00001", "Ocorrência", "pata machucada", "12/10/2026")
    f = fotos.listar(id_)[0]
    assert (f["tipo"], f["legenda"], f["data"].strftime("%d/%m/%Y")) == \
        ("Ocorrência", "pata machucada", "12/10/2026")


# ── Task 3: rotas ────────────────────────────────────────────────────────────

import io  # noqa: E402
import time  # noqa: E402

import routes_fotos  # noqa: E402


def _jpeg_real(w=900, h=600) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 90, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _post_foto(cliente, id_, envio="e1", csrf="tok", conteudo=None):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    return cliente.post("/api/fotos", data={
        "id_animal": id_, "tipo": "Evolução", "legenda": "", "data": "10/10/2026",
        "id_envio": envio, "csrf_token": csrf,
        "foto": (io.BytesIO(conteudo or _jpeg_real()), "f.jpg"),
    }, content_type="multipart/form-data")


@pytest.fixture
def cache_limpo():
    import shutil
    shutil.rmtree(routes_fotos.cache_dir(), ignore_errors=True)
    yield
    shutil.rmtree(routes_fotos.cache_dir(), ignore_errors=True)


def test_api_sem_login_401(flask_app):
    r = flask_app.test_client().post("/api/fotos", data={})
    assert r.status_code == 401 and r.get_json()["erro"] == "login"


def test_api_sem_csrf_403(cliente, amb):
    r = _post_foto(cliente, amb[1], csrf="errado")
    assert r.status_code == 403 and r.get_json()["erro"] == "csrf"


def test_api_envia_e_duplicada(cliente, amb):
    r = _post_foto(cliente, amb[1])
    assert r.status_code == 200 and r.get_json() == {"ok": True, "duplicada": False, "id_foto": "F00001"}
    r = _post_foto(cliente, amb[1])
    assert r.get_json()["duplicada"] is True
    assert fotos.carregar().iloc[0]["Enviado Por"] == "Deyvid"


def test_api_invalida_400(cliente, amb):
    r = _post_foto(cliente, amb[1], conteudo=b"%PDF nada")
    assert r.status_code == 400 and r.get_json()["erro"] == "invalida"


def test_api_drive_fora_nao_grava(cliente, amb):
    amb[0].falhar = True
    r = _post_foto(cliente, amb[1])
    assert r.status_code == 502 and r.get_json()["erro"] == "drive"
    assert fotos.carregar().empty


def test_api_nao_configurado_503(cliente, amb, monkeypatch, tmp_path):
    drive.definir_cliente(None)
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "nada.json"))
    r = _post_foto(cliente, amb[1])
    assert r.status_code == 503 and r.get_json()["erro"] == "drive"


def test_rota_imagem_usa_cache(cliente, amb, cache_limpo):
    _post_foto(cliente, amb[1])
    r1 = cliente.get("/fotos/F00001")
    r2 = cliente.get("/fotos/F00001")
    assert r1.status_code == 200 and r1.data == r2.data
    assert amb[0].baixados == 1
    assert "private" in r1.headers["Cache-Control"]
    mini = cliente.get("/fotos/F00001/mini")
    from PIL import Image
    assert max(Image.open(io.BytesIO(mini.data)).size) <= 400


def test_rota_id_invalido_404(cliente, amb, cache_limpo):
    for url in ("/fotos/..%2Fx", "/fotos/F99999", "/fotos/abc/mini"):
        assert cliente.get(url).status_code == 404, url


def test_rota_imagem_exige_login(flask_app):
    r = flask_app.test_client().get("/fotos/F00001")
    assert r.status_code == 302


def test_principal_e_excluir_pela_rota(cliente, amb, cache_limpo):
    _post_foto(cliente, amb[1], "e1")
    _post_foto(cliente, amb[1], "e2")
    cliente.get("/fotos/F00001")  # popula o cache
    r = cliente.post("/fotos/F00002/principal", data={"csrf_token": "tok"})
    assert r.status_code == 302 and fotos.principais() == {amb[1]: "F00002"}
    r = cliente.post("/fotos/F00001/excluir", data={"csrf_token": "tok"})
    assert r.status_code == 302 and fotos.por_id("F00001") is None
    assert not os.path.exists(os.path.join(routes_fotos.cache_dir(), "F00001.jpg"))
    r = cliente.post("/fotos/F00002/editar", data={"csrf_token": "tok", "tipo": "Perfil",
                                                   "legenda": "x", "data": "2026-10-11"})
    assert r.status_code == 302 and fotos.por_id("F00002")["tipo"] == "Perfil"


def test_limpar_cache_respeita_limite(cache_limpo):
    pasta = routes_fotos.cache_dir()
    os.makedirs(pasta, exist_ok=True)
    agora = time.time()
    for i, nome in enumerate(("F00001.jpg", "F00002.jpg", "F00003.jpg")):
        p = os.path.join(pasta, nome)
        with open(p, "wb") as f:
            f.write(b"0" * 1024)
        os.utime(p, (agora - 100 + i * 10, agora - 100 + i * 10))
    routes_fotos.limpar_cache(2048)
    assert sorted(os.listdir(pasta)) == ["F00002.jpg", "F00003.jpg"]


# ── Task 4: telas ────────────────────────────────────────────────────────────

def test_ficha_com_fotos_mostra_miniaturas(cliente, amb):
    _post_foto(cliente, amb[1])
    html = cliente.get(f"/animais/{amb[1]}").get_data(as_text=True)
    assert "/fotos/F00001/mini" in html
    assert "📷 Tirar foto" in html
    assert "fila_fotos.js" in html


def test_ficha_sem_drive_mostra_aviso(cliente, amb, monkeypatch, tmp_path):
    drive.definir_cliente(None)
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "nada.json"))
    r = cliente.get(f"/animais/{amb[1]}")
    assert r.status_code == 200
    assert "Fotos não configuradas" in r.get_data(as_text=True)


def test_lista_animais_com_principal(cliente, amb):
    _post_foto(cliente, amb[1])
    assert "/fotos/F00001/mini" in cliente.get("/animais").get_data(as_text=True)


# ── Task 5: configuração e alerta ────────────────────────────────────────────

def test_configuracoes_mostra_cartao_fotos(cliente, monkeypatch, tmp_path):
    drive.definir_cliente(None)
    monkeypatch.setattr(drive, "token_path", lambda: str(tmp_path / "nada.json"))
    html = cliente.get("/configuracoes").get_data(as_text=True)
    assert "📷 Fotos" in html and "não configurado" in html


def test_testar_drive_com_falso_ok(cliente):
    drive.definir_cliente(DriveFalso())
    try:
        with cliente.session_transaction() as s:
            s["csrf_token"] = "tok"
        r = cliente.post("/configuracoes/testar-drive", data={"csrf_token": "tok"})
        assert r.status_code == 302
        with cliente.session_transaction() as s:
            assert any("Drive conectado" in m for _, m in s.get("_flashes", []))
    finally:
        drive.definir_cliente(None)


def test_alerta_drive_quebrado(monkeypatch):
    import alertas_whatsapp as W
    monkeypatch.setattr(drive, "configurado", lambda: True)
    drive.definir_cliente(DriveFalso(falhar=True))
    try:
        itens = W.montar_itens()
    finally:
        drive.definir_cliente(None)
    alerta = [i for i in itens if i["chave"] == "drive:erro"]
    assert alerta and alerta[0]["urgente"] and alerta[0]["repetir"] == 1


def test_alerta_drive_ok_nao_avisa(monkeypatch):
    import alertas_whatsapp as W
    monkeypatch.setattr(drive, "configurado", lambda: True)
    drive.definir_cliente(DriveFalso())
    try:
        assert not [i for i in W.montar_itens() if i["chave"] == "drive:erro"]
    finally:
        drive.definir_cliente(None)


# ── Revisão final ────────────────────────────────────────────────────────────

import threading  # noqa: E402


def test_id_nao_e_reaproveitado_apos_excluir_a_ultima(amb):
    _, id_ = amb
    _env(id_, "e1")
    _env(id_, "e2")
    fotos.excluir("F00002")
    assert _env(id_, "e3")["id_foto"] == "F00003"


class _DriveLento(DriveFalso):
    def enviar(self, *a, **kw):
        time.sleep(0.3)
        return super().enviar(*a, **kw)


def _em_paralelo(*funcs):
    ts = [threading.Thread(target=f) for f in funcs]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def test_mesmo_envio_simultaneo_nao_duplica(amb):
    _, id_ = amb
    lento = _DriveLento()
    drive.definir_cliente(lento)
    _em_paralelo(lambda: _env(id_, "x"), lambda: _env(id_, "x"))
    assert len(fotos.carregar()) == 1 and len(lento.arquivos) == 1


def test_envios_simultaneos_ids_distintos_e_uma_principal(amb):
    _, id_ = amb
    drive.definir_cliente(_DriveLento())
    _em_paralelo(lambda: _env(id_, "a"), lambda: _env(id_, "b"))
    df = fotos.carregar()
    assert sorted(df["ID Foto"]) == ["F00001", "F00002"]
    assert (df["Principal"] == "Sim").sum() == 1


def test_ficha_com_foto_sem_data_nao_quebra(cliente, amb):
    _post_foto(cliente, amb[1])
    df = fotos.carregar()
    df["Data"] = pd.NaT
    fotos._gravar(df)
    r = cliente.get(f"/animais/{amb[1]}")
    assert r.status_code == 200 and "/fotos/F00001/mini" in r.get_data(as_text=True)


# ── Política de privacidade (exigida pelo Google para publicar o app OAuth) ───

def test_privacidade_e_publica(flask_app):
    r = flask_app.test_client().get("/privacidade")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Política de Privacidade" in html
    assert "Google Drive" in html
    assert "nilsondavid45@gmail.com" in html


def test_cache_cabe_no_disco_do_pythonanywhere():
    # Plano gratuito: 512 MB no total, ~284 MB já usados (planilha, backups, código).
    assert routes_fotos.LIMITE_CACHE == 50 * 1024 * 1024
