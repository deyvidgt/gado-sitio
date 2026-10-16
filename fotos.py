# -*- coding: utf-8 -*-
"""
fotos.py — linha do tempo de fotos dos animais (v4.4).

O arquivo vai para o Google Drive (drive.py); aqui ficam as regras e a aba
"Fotos" do gado_familia.xlsx. Fotos NÃO entram em nenhuma conta (calculos.py).

Ordem do envio: Drive primeiro, Excel depois. Se o Excel falhar depois do
upload, o arquivo fica "órfão" no Drive com o id_envio gravado nas
appProperties — o reenvio do celular o encontra e só grava a linha.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime

import pandas as pd

import animais as A
import db
import drive
from config import COLUNAS_FOTOS, TIPOS_FOTO
from extensions import _agora, _limpar_backups_antigos

ABA = "Fotos"
MAX_BYTES = 8 * 1024 * 1024
# Um envio por vez: o upload ao Drive leva segundos no 3G, e dois envios juntos
# (2 celulares, ou o reenvio da fila) leriam a mesma aba e gravariam o mesmo ID.
_trava = threading.Lock()
_TEXTO = ("ID Foto", "Animal", "Tipo", "Legenda", "Principal", "Drive ID",
          "Enviado Por", "Enviado Em", "ID Envio")


class FotoInvalida(ValueError):
    """Pedido recusado (mensagem pronta para a tela)."""


def e_imagem(conteudo: bytes) -> str | None:
    """Mime pela assinatura do arquivo (não confia na extensão nem no navegador)."""
    if conteudo[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if conteudo[:4] == b"\x89PNG":
        return "image/png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    if conteudo[4:8] == b"ftyp" and conteudo[8:12] in (b"heic", b"heix", b"mif1", b"heif"):
        return "image/heic"
    return None


_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic"}


def carregar() -> pd.DataFrame:
    df = db.carregar_aba(ABA)
    for c in COLUNAS_FOTOS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUNAS_FOTOS].copy()
    for c in _TEXTO:
        df[c] = df[c].apply(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip())
    return df


def _gravar(df: pd.DataFrame):
    db.reescrever_aba(ABA, df[COLUNAS_FOTOS])


def _data(v) -> pd.Timestamp:
    """'dd/mm/aaaa' (formulário/voz) ou 'aaaa-mm-dd' (input date). Vazio → hoje."""
    txt = str(v or "").strip()
    if not txt:
        return pd.Timestamp(_agora().date())
    try:
        if len(txt) >= 10 and txt[4] == "-":
            return pd.Timestamp(datetime.strptime(txt[:10], "%Y-%m-%d"))
        return pd.Timestamp(datetime.strptime(txt[:10], "%d/%m/%Y"))
    except ValueError:
        raise FotoInvalida(f"Data inválida: {txt}")


def _ultimo_id_path() -> str:
    return os.path.join(db.DATA_DIR, "fotos_ultimo_id.txt")


def _proximo_id(df: pd.DataFrame) -> str:
    """Nunca reaproveita: o navegador guarda /fotos/<id> por 7 dias, e um ID reusado
    mostraria a foto excluída no lugar da nova. O maior já usado fica num arquivo."""
    nums = [int(x[1:]) for x in df["ID Foto"] if x[1:].isdigit()]
    try:
        with open(_ultimo_id_path(), encoding="utf-8") as f:
            nums.append(int(f.read().strip() or 0))
    except (OSError, ValueError):
        pass
    n = max(nums, default=0) + 1
    try:
        with open(_ultimo_id_path(), "w", encoding="utf-8") as f:
            f.write(str(n))
    except OSError as e:
        logging.warning(f"Não foi possível guardar o último ID de foto: {e}")
    return f"F{n:05d}"


def _linha(r) -> dict:
    data = r["Data"] if pd.notna(r["Data"]) else None   # célula apagada à mão no Excel
    return {"id_foto": r["ID Foto"], "animal": r["Animal"], "data": data,
            "dia": data.strftime("%Y-%m-%d") if data is not None else "",
            "tipo": r["Tipo"], "legenda": r["Legenda"], "principal": r["Principal"] == "Sim",
            "drive_id": r["Drive ID"], "enviado_por": r["Enviado Por"],
            "enviado_em": r["Enviado Em"]}


def enviar(id_animal: str, conteudo: bytes, data: str | None, tipo: str, legenda: str,
           enviado_por: str, id_envio: str) -> dict:
    with _trava:
        return _enviar(id_animal, conteudo, data, tipo, legenda, enviado_por, id_envio)


def _enviar(id_animal, conteudo, data, tipo, legenda, enviado_por, id_envio) -> dict:
    df = carregar()
    if id_envio:
        ja = df[df["ID Envio"] == id_envio]
        if not ja.empty:
            return {"duplicada": True, "id_foto": ja.iloc[0]["ID Foto"]}

    animal = A.por_id(A.carregar(), id_animal)
    if animal is None:
        raise FotoInvalida("Animal não encontrado.")
    if tipo not in TIPOS_FOTO:
        raise FotoInvalida(f"Tipo inválido: {tipo}")
    if len(conteudo) > MAX_BYTES:
        raise FotoInvalida("Foto grande demais (máximo 8 MB).")
    mime = e_imagem(conteudo)
    if not mime:
        raise FotoInvalida("O arquivo enviado não é uma foto.")
    quando = _data(data)

    cli = drive.cliente()
    if cli is None:
        raise drive.DriveErro("Fotos não configuradas.")
    id_foto = _proximo_id(df)
    drive_id = cli.achar_por_envio(id_envio) if id_envio else None
    if not drive_id:
        nome_pasta = f"{id_animal} - {A.fmt_brinco(animal['Brinco Cor'], animal['Brinco Nº'])}"
        pasta = cli.pasta_animal(id_animal, nome_pasta)
        nome = f"{quando.strftime('%Y-%m-%d')}_{id_foto}.{_EXT[mime]}"
        drive_id = cli.enviar(pasta, nome, conteudo, mime,
                              {"id_envio": id_envio, "animal": id_animal, "id_foto": id_foto})

    tem_principal = ((df["Animal"] == id_animal) & (df["Principal"] == "Sim")).any()
    db.salvar_linha(ABA, [
        id_foto, id_animal, quando, tipo, (legenda or "").strip(),
        "" if tem_principal else "Sim", drive_id, enviado_por,
        _agora().strftime("%d/%m/%Y %H:%M"), id_envio,
    ])
    return {"duplicada": False, "id_foto": id_foto}


def _ordenar(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(_em=pd.to_datetime(df["Enviado Em"], format="%d/%m/%Y %H:%M", errors="coerce")) \
             .sort_values(["Data", "_em", "ID Foto"], ascending=False).drop(columns="_em")


def listar(id_animal: str) -> list[dict]:
    df = carregar()
    return [_linha(r) for _, r in _ordenar(df[df["Animal"] == id_animal]).iterrows()]


def principais() -> dict[str, str]:
    df = carregar()
    p = df[df["Principal"] == "Sim"]
    return dict(zip(p["Animal"], p["ID Foto"]))


def por_id(id_foto: str) -> dict | None:
    df = carregar()
    m = df[df["ID Foto"] == id_foto]
    return None if m.empty else _linha(m.iloc[0])


def _indice(df: pd.DataFrame, id_foto: str):
    m = df.index[df["ID Foto"] == id_foto]
    if len(m) == 0:
        raise FotoInvalida("Foto não encontrada.")
    return m[0]


def definir_principal(id_foto: str) -> None:
    df = carregar()
    i = _indice(df, id_foto)
    animal = df.at[i, "Animal"]
    df.loc[df["Animal"] == animal, "Principal"] = ""
    df.at[i, "Principal"] = "Sim"
    _gravar(df)


def editar(id_foto: str, tipo: str, legenda: str, data: str) -> None:
    if tipo not in TIPOS_FOTO:
        raise FotoInvalida(f"Tipo inválido: {tipo}")
    df = carregar()
    i = _indice(df, id_foto)
    df.at[i, "Tipo"] = tipo
    df.at[i, "Legenda"] = (legenda or "").strip()
    df.at[i, "Data"] = _data(data)
    _gravar(df)


def excluir(id_foto: str) -> None:
    df = carregar()
    i = _indice(df, id_foto)
    animal, era_principal, drive_id = df.at[i, "Animal"], df.at[i, "Principal"] == "Sim", df.at[i, "Drive ID"]
    db.fazer_backup()
    _limpar_backups_antigos()
    cli = drive.cliente()
    try:
        if cli and drive_id:
            cli.lixeira(drive_id)
    except drive.DriveErro as e:
        # A linha sai mesmo assim: o arquivo fica no Drive, sem perder nada.
        logging.warning(f"Foto {id_foto}: não foi para a lixeira do Drive ({e}).")
    df = df.drop(index=i)
    if era_principal:
        resto = _ordenar(df[df["Animal"] == animal])
        if not resto.empty:
            df.loc[resto.index[0], "Principal"] = "Sim"
    _gravar(df)
