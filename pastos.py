#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pastos.py — pastos desenhados no mapa (v5.2)

Aba "Pastos": um polígono (GeoJSON) por pasto; a área é calculada AQUI pelo
contorno, não vem do navegador. Mover o gado grava "Movimentação de Pasto" no
Manejo com o ID do pasto na coluna "Pasto" (Brincos vazio = o rebanho todo).
Não mexe nas finanças. Design: docs/superpowers/specs/2026-10-25-pastos-mapa-design.md
"""
from __future__ import annotations
from agora import agora

import io
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

import animais as A
import db
import pesagem as P
from config import COLUNAS_PASTOS

ABA = "Pastos"
TIPO_MOV = "Movimentação de Pasto"
UA_KG = 450                       # 1 unidade animal
RAIO_TERRA = 6378137.0
AREA_MIN, AREA_MAX = 0.01, 100000
PONTOS_MIN, PONTOS_MAX = 3, 500
CORES = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
         "#46f0f0", "#f032e6", "#bcf60c", "#fabebe"]


def area_ha(geo: dict) -> float:
    """Área esférica do anel externo (mesma fórmula do Leaflet.draw/Google), em ha."""
    anel = geo["coordinates"][0]
    soma = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(anel, anel[1:] + anel[:1]):
        soma += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1))
                                             + math.sin(math.radians(lat2)))
    return abs(soma * RAIO_TERRA ** 2 / 2) / 10000


def validar_contorno(texto: str) -> tuple[dict, float]:
    """Texto do formulário (Feature ou Polygon) → (Polygon limpo, área ha); ValueError."""
    try:
        geo = json.loads(texto)
        if geo.get("type") == "Feature":
            geo = geo["geometry"]
        if geo.get("type") != "Polygon":
            raise ValueError
        anel = [[float(lon), float(lat)] for lon, lat in geo["coordinates"][0]]
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ValueError("Contorno do pasto inválido — desenhe de novo no mapa.")
    if anel and anel[0] == anel[-1]:
        anel = anel[:-1]
    if not PONTOS_MIN <= len(anel) <= PONTOS_MAX:
        raise ValueError(f"O contorno precisa ter de {PONTOS_MIN} a {PONTOS_MAX} cantos.")
    if not all(math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90
               for lon, lat in anel):
        raise ValueError("Contorno do pasto com ponto fora do mapa.")
    limpo = {"type": "Polygon", "coordinates": [anel + [anel[0]]]}
    area = area_ha(limpo)
    if not AREA_MIN <= area <= AREA_MAX:
        raise ValueError(f"Área de {area:g} ha não parece certa — desenhe de novo.")
    return limpo, round(area, 2)


def carregar() -> pd.DataFrame:
    df = db.carregar_aba(ABA)
    for c in COLUNAS_PASTOS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUNAS_PASTOS].copy()
    for c in COLUNAS_PASTOS:
        if c != "Área (ha)":
            df[c] = df[c].apply(A._txt).astype(object)
    df["Área (ha)"] = pd.to_numeric(df["Área (ha)"], errors="coerce").fillna(0.0)
    return df.reset_index(drop=True)


def ativos(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Ativo"] != "Não"]


def _gravar(df: pd.DataFrame):
    out = df[COLUNAS_PASTOS].astype(object)
    db.reescrever_aba(ABA, out.where(pd.notna(out), None))


def _nome(nome, df, exceto=None) -> str:
    nome = re.sub(r"\s+", " ", str(nome or "")).strip()
    if not 1 <= len(nome) <= 40:
        raise ValueError("Dê um nome ao pasto (até 40 letras).")
    outros = ativos(df)
    outros = outros[outros["ID"] != exceto]
    if nome.lower() in outros["Nome"].str.lower().tolist():
        raise ValueError(f"Já existe um pasto chamado {nome}.")
    return nome


def _nome_unico(base_nome: str, nomes_existentes: set[str]) -> str:
    base = re.sub(r"\s+", " ", str(base_nome or "Pasto")).strip()[:35] or "Pasto"
    nome = base
    cont = 2
    while nome.lower() in nomes_existentes:
        nome = f"{base} ({cont})"
        cont += 1
    nomes_existentes.add(nome.lower())
    return nome


def _parse_coords_kml(texto: str) -> list[list[float]]:
    texto = re.sub(r"\s*,\s*", ",", texto.strip())
    pts = []
    for item in texto.split():
        partes = item.split(",")
        if len(partes) >= 2:
            try:
                lon, lat = float(partes[0]), float(partes[1])
                if math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90:
                    pts.append([lon, lat])
            except ValueError:
                continue
    return pts


def extrair_poligonos_kmz(conteudo: bytes, nome_arquivo: str = "") -> list[tuple[str, dict]]:
    """Lê bytes de .kmz ou .kml e devolve lista de (nome, geojson_polygon_dict)."""
    kml_bytes = None
    if zipfile.is_zipfile(io.BytesIO(conteudo)):
        with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
            kml_nomes = [n for n in zf.namelist() if n.lower().endswith(".kml") and not n.startswith("__MACOSX")]
            if not kml_nomes:
                raise ValueError("Arquivo KMZ não contém nenhum arquivo KML interno.")
            doc = next((n for n in kml_nomes if n.lower().endswith("doc.kml")), kml_nomes[0])
            kml_bytes = zf.read(doc)
    else:
        kml_bytes = conteudo

    try:
        root = ET.fromstring(kml_bytes)
    except Exception:
        try:
            root = ET.fromstring(kml_bytes.decode("utf-8", errors="replace").encode("utf-8"))
        except Exception:
            raise ValueError("Não foi possível ler o KML: arquivo corrompido ou formato inválido.")

    for el in root.iter():
        el.tag = el.tag.split("}")[-1]

    poligonos = []
    for pm in root.iter("Placemark"):
        nome = pm.findtext("name") or ""
        polys = list(pm.iter("Polygon"))
        for i, poly in enumerate(polys):
            coords_txt = poly.findtext(".//outerBoundaryIs//coordinates") or poly.findtext(".//coordinates")
            if not coords_txt:
                continue
            anel = _parse_coords_kml(coords_txt)
            if len(anel) < PONTOS_MIN:
                continue
            if anel[0] != anel[-1]:
                anel.append(anel[0])
            geo = {"type": "Polygon", "coordinates": [anel]}
            subnome = f"{nome} ({i+1})" if len(polys) > 1 and nome else (nome or "Pasto")
            poligonos.append((subnome, geo))

    if not poligonos:
        for i, poly in enumerate(root.iter("Polygon")):
            coords_txt = poly.findtext(".//outerBoundaryIs//coordinates") or poly.findtext(".//coordinates")
            if not coords_txt:
                continue
            anel = _parse_coords_kml(coords_txt)
            if len(anel) >= PONTOS_MIN:
                if anel[0] != anel[-1]:
                    anel.append(anel[0])
                poligonos.append((f"Pasto {i+1}", {"type": "Polygon", "coordinates": [anel]}))

    if not poligonos:
        raise ValueError("Nenhum polígono de pasto encontrado dentro do arquivo KMZ/KML.")

    return poligonos


def importar_kmz(conteudo: bytes, nome_arquivo: str = "", criado_por: str = "") -> list[dict]:
    """Importa pastos a partir de arquivo KMZ ou KML. Devolve lista dos pastos criados."""
    poligonos = extrair_poligonos_kmz(conteudo, nome_arquivo)
    df = carregar()
    nomes_existentes = set(ativos(df)["Nome"].str.lower().tolist())
    nums = [int(i[1:]) for i in df["ID"] if re.fullmatch(r"P\d+", i)]
    prox_num = max(nums, default=0) + 1
    total_linhas = len(df)

    linhas_novas = []
    criados = []
    for nome_bruto, geo in poligonos:
        try:
            geo_limpo, area = validar_contorno(json.dumps(geo))
        except ValueError:
            continue
        nome = _nome_unico(nome_bruto, nomes_existentes)
        id_ = f"P{prox_num:02d}"
        prox_num += 1
        cor = CORES[(total_linhas + len(linhas_novas)) % len(CORES)]
        linha = [id_, nome, area, json.dumps(geo_limpo), cor, "Sim", "", criado_por]
        linhas_novas.append(linha)
        criados.append({"id": id_, "nome": nome, "area": area})

    if not criados:
        raise ValueError("Nenhum pasto com formato e área válidos encontrado no arquivo.")

    for l in linhas_novas:
        db.salvar_linha(ABA, l)
    return criados


def criar(nome, contorno_json, criado_por: str = "") -> str:
    df = carregar()
    nome = _nome(nome, df)
    geo, area = validar_contorno(contorno_json)
    nums = [int(i[1:]) for i in df["ID"] if re.fullmatch(r"P\d+", i)]
    id_ = f"P{max(nums, default=0) + 1:02d}"
    db.salvar_linha(ABA, [id_, nome, area, json.dumps(geo), CORES[len(df) % len(CORES)],
                          "Sim", "", criado_por])
    return id_


def criar_simples(nome, area_ha, criado_por: str = "") -> str:
    df = carregar()
    nome = _nome(nome, df)
    # Cria um polígono "quadrado" dummy de 1x1 grau centrado num ponto qualquer,
    # ajustado para ter aproximadamente a área informada
    lado = math.sqrt(area_ha * 10000) / 111320
    geo = {
        "type": "Polygon",
        "coordinates": [[
            [-48.28 - lado/2, -18.92 - lado/2],
            [-48.28 + lado/2, -18.92 - lado/2],
            [-48.28 + lado/2, -18.92 + lado/2],
            [-48.28 - lado/2, -18.92 + lado/2],
            [-48.28 - lado/2, -18.92 - lado/2]
        ]]
    }
    nums = [int(i[1:]) for i in df["ID"] if re.fullmatch(r"P\d+", i)]
    id_ = f"P{max(nums, default=0) + 1:02d}"
    db.salvar_linha(ABA, [id_, nome, area_ha, json.dumps(geo), CORES[len(df) % len(CORES)],
                          "Sim", "Criado via formulário simples", criado_por])
    return id_


def _linha(df, id_):
    m = df.index[(df["ID"] == id_) & (df["Ativo"] != "Não")]
    if m.empty:
        raise ValueError("Pasto não encontrado.")
    return m[0]


def editar(id_, nome=None, contorno_json=None):
    df = carregar()
    i = _linha(df, id_)
    if nome is not None:
        df.at[i, "Nome"] = _nome(nome, df, exceto=id_)
    if contorno_json is not None:
        geo, area = validar_contorno(contorno_json)
        df.at[i, "Contorno"], df.at[i, "Área (ha)"] = json.dumps(geo), area
    _gravar(df)


def excluir(id_):
    """Só desativa: as movimentações antigas continuam apontando para um ID que existe."""
    df = carregar()
    df.at[_linha(df, id_), "Ativo"] = "Não"
    _gravar(df)


def mover(pasto_id, data, refs: list[str] | None, qtd: int, responsavel: str = ""):
    """refs None = o rebanho todo (Brincos vazio)."""
    df = carregar()
    nome = df.at[_linha(df, pasto_id), "Nome"]
    data_ts = A._data(data) if data else pd.NaT
    if pd.isna(data_ts):
        data_ts = pd.Timestamp(agora()).normalize()
    qtd = len(refs) if refs else int(qtd)
    if qtd <= 0:
        raise ValueError("Nenhuma cabeça para mover.")
    quem = "rebanho todo" if refs is None else f"{qtd} animal(is)"
    db.salvar_linha("Manejo", A._linha_manejo(
        data_ts, TIPO_MOV, qtd, f"Para o pasto {nome} ({quem})", responsavel,
        brincos="; ".join(refs or []), pasto=pasto_id))


def situacao(df_pastos, df_animais, df_man, estoque: int, peso_medio: float, hoje=None) -> dict:
    """{ID do pasto ativo: {cab, ua, ua_ha, dias, estimado}} + None = sem pasto.

    Percorre as movimentações em ordem: a do rebanho todo leva todo mundo (apaga
    as individuais anteriores); a com brincos leva só aqueles."""
    hoje = pd.Timestamp(hoje or pd.Timestamp(agora())).normalize()
    peso_padrao = peso_medio if peso_medio and peso_medio > 0 else UA_KG
    rebanho, individual = (None, None), {}
    ultimas_saidas = {}
    if df_man is not None and not df_man.empty and "Pasto" in df_man.columns:
        movs = df_man[(df_man["Tipo"] == TIPO_MOV) & df_man["Pasto"].apply(A._txt).ne("")]
        movs = movs.assign(_d=pd.to_datetime(movs["Data"], dayfirst=True, errors="coerce"))
        for _, r in movs.dropna(subset=["_d"]).sort_values("_d", kind="stable").iterrows():
            onde = (A._txt(r["Pasto"]), r["_d"].normalize())
            ids = A.ids_de(r.get("Brincos"))
            if ids:
                for i in ids:
                    p_ant = individual.get(i, rebanho)[0]
                    if p_ant and p_ant != onde[0]:
                        ultimas_saidas[p_ant] = onde[1]
                individual.update({i: onde for i in ids})
            else:
                p_ant = rebanho[0]
                if p_ant and p_ant != onde[0]:
                    ultimas_saidas[p_ant] = onde[1]
                for p_ind, _ in individual.values():
                    if p_ind and p_ind != onde[0]:
                        ultimas_saidas[p_ind] = onde[1]
                rebanho, individual = onde, {}

    pesos = P.todas(df_man)
    vivos = A.vivos(df_animais)["ID"].tolist() if not df_animais.empty else []
    sem_brinco = max(0, int(estoque) - len(vivos))
    # (pasto, data de chegada, nº de cabeças, kg, quantas sem peso de balança)
    grupos = [(*rebanho, sem_brinco, sem_brinco * peso_padrao, sem_brinco)]
    for i in vivos:
        kg = pesos[i][-1][1] if i in pesos else None
        grupos.append((*individual.get(i, rebanho), 1, kg or peso_padrao, 0 if kg else 1))

    validos = set(ativos(df_pastos)["ID"]) if not df_pastos.empty else set()
    area = dict(zip(df_pastos["ID"], df_pastos["Área (ha)"])) if not df_pastos.empty else {}
    out = {p: {"cab": 0, "kg": 0.0, "estimado": False, "_chegadas": {}} for p in [*validos, None]}
    for pasto, data, n, kg, sem_peso in grupos:
        if n == 0:
            continue
        s = out[pasto if pasto in validos else None]
        s["cab"] += n
        s["kg"] += kg
        s["estimado"] |= sem_peso > 0
        if pasto in validos:
            s["_chegadas"][data] = s["_chegadas"].get(data, 0) + n
    for p, s in out.items():
        s["ua"] = s.pop("kg") / UA_KG
        chegadas = s.pop("_chegadas")
        s["dias"] = (hoje - max(chegadas, key=chegadas.get)).days if chegadas else None
        s["descanso"] = (hoje - ultimas_saidas[p]).days if (p in ultimas_saidas and s["cab"] == 0) else None
        a = float(area.get(p) or 0)
        s["ua_ha"] = s["ua"] / a if a > 0 else None
    return out


def nivel(ua_ha: float | None, capacidade: float | None) -> str | None:
    """Semáforo da lotação (v5.9): 4 níveis com cores.

    - baixa: < 50% (laranja) — pasto subutilizado
    - ideal: 50–70% (verde) — aproveitamento ótimo
    - atencao: 70–100% (amarelo) — no limite
    - lotado: > 100% (vermelho) — sobrecarga

    None quando não há como comparar — pasto sem contorno (ua_ha None) ou
    capacidade não configurada. Sem referência não se pinta nada."""
    if ua_ha is None or not capacidade or capacidade <= 0:
        return None
    pct = ua_ha / capacidade
    if pct < 0.5:
        return "baixa"
    elif pct < 0.7:
        return "ideal"
    elif pct <= 1.0:
        return "atencao"
    else:
        return "lotado"


def total_lotacao(df_pastos, sit: dict, capacidade: float | None = None) -> dict:
    """Lotação somando os pastos desenhados: {ua, ha, ua_ha, nivel}.

    Só entra pasto ativo com área; o que está "sem pasto" fica de fora porque
    não tem área para dividir."""
    ids = set(ativos(df_pastos)["ID"]) if not df_pastos.empty else set()
    ha = sum(float(p["Área (ha)"] or 0) for _, p in ativos(df_pastos).iterrows()) if ids else 0.0
    ua = sum(s["ua"] for p, s in sit.items() if p in ids)
    ua_ha = ua / ha if ha > 0 else None
    return {"ua": ua, "ha": ha, "ua_ha": ua_ha, "nivel": nivel(ua_ha, capacidade),
            "capacidade": capacidade}


def animais_por_pasto(df_man: pd.DataFrame, df_anim: pd.DataFrame | None = None) -> dict:
    """Retorna {pasto_id: [lista de animais]} baseado na última movimentação de pasto.

    Útil para mostrar no mapa quais animais estão em cada pasto. Cada animal
    aparece no destino efetivo após aplicar movimentações individuais e do
    rebanho inteiro em ordem cronológica.

    Se df_anim fornecido, enriquece com cor/nome do animal.
    """
    resultado = {}
    local_rebanho = None
    locais_individuais = {}
    ids_encontrados = set()
    brinco_por_id = {}

    if (df_man is not None and not df_man.empty
            and {"Tipo", "Pasto", "Data"}.issubset(df_man.columns)):
        movs = df_man[
            (df_man["Tipo"] == TIPO_MOV) & df_man["Pasto"].apply(A._txt).ne("")
        ].copy()
        movs["_data_mov"] = pd.to_datetime(movs["Data"], dayfirst=True, errors="coerce")
        movs = movs.dropna(subset=["_data_mov"]).sort_values("_data_mov", kind="stable")

        for _, row in movs.iterrows():
            pasto_id = A._txt(row.get("Pasto"))
            brincos = row.get("Brincos", "")
            ids = A.ids_de(brincos)
            if ids:
                ids_encontrados.update(ids)
                for animal_id in ids:
                    locais_individuais[animal_id] = pasto_id
                    brinco_por_id[animal_id] = str(brincos)
            else:
                local_rebanho = pasto_id
                locais_individuais.clear()

    if df_anim is not None:
        animais = A.vivos(df_anim) if not df_anim.empty else df_anim
        animais_por_id = {
            A._txt(animal.get("ID")): animal
            for _, animal in animais.iterrows()
            if A._txt(animal.get("ID"))
        }
        ids_encontrados = set(animais_por_id)
    else:
        animais_por_id = {}

    cores_dono = A.cores_brinco() if animais_por_id else {}
    for animal_id in sorted(ids_encontrados):
        animal = animais_por_id.get(animal_id)
        if animal is not None:
            brinco = A.fmt_brinco(animal.get("Brinco Cor"), animal.get("Brinco Nº"))
            cor_nome = A._txt(animal.get("Brinco Cor"))
            dono = A._txt(animal.get("Dono"))
            cor_nome = cor_nome or cores_dono.get(dono, "")
            cor = A.hex_cor_brinco(cor_nome)
            cor_texto = A.cor_texto_brinco(cor_nome)
            nome = A._txt(animal.get("Nome"))
        else:
            brinco = brinco_por_id.get(animal_id, animal_id)
            cor_nome = ""
            cor = "#999999"
            cor_texto = "#ffffff"
            nome = ""

        pasto_id = locais_individuais.get(animal_id, local_rebanho)
        resultado.setdefault(pasto_id, []).append({
            "id": animal_id,
            "brinco": brinco,
            "nome": nome,
            "cor": cor,
            "cor_nome": cor_nome,
            "cor_texto": cor_texto,
        })

    return resultado


def pasto_do_animal(animal_id: str, df_man: pd.DataFrame) -> tuple[str | None, str | None]:
    """Retorna (ID do pasto, nome do pasto) onde o animal está na última movimentação.

    Percorre a aba Manejo de trás pra frente (mais recente primeiro) procurando
    a última "Movimentação de Pasto" que contenha este animal_id nos Brincos.
    Retorna (None, None) se nunca foi movido para pasto específico.
    """
    if df_man is None or df_man.empty:
        return None, None

    movs = df_man[(df_man["Tipo"] == TIPO_MOV) & df_man["Pasto"].apply(A._txt).ne("")].copy()
    if movs.empty:
        return None, None

    # Ordena por data DESC (mais recente primeiro)
    movs_ordenadas = movs.sort_values("Data", ascending=False, na_position="last")

    for _, row in movs_ordenadas.iterrows():
        brincos_str = row.get("Brincos", "")
        pasto_id = A._txt(row.get("Pasto", ""))

        # Se brincos vazio = toda a rebanho foi movida
        if pd.isna(brincos_str) or not brincos_str or not str(brincos_str).strip():
            return pasto_id, None  # Retorna só o ID, sem nome (não é animal específico)

        # Busca o animal nesta movimentação
        ids = A.ids_de(brincos_str)
        if animal_id in ids:
            return pasto_id, None  # Encontrou — retorna o pasto

    return None, None  # Nunca foi movido
