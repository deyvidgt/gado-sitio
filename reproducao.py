#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproducao.py — controle de cobertura e parto sem sensor nenhum (v5.3)

Só caderno: a família anota a cobertura (monta ou inseminação) e, mais tarde,
o resultado do toque do veterinário. O resto é conta de calendário.

Onde ficam os dados (nada de aba nova):
  • Manejo tipo "Cobertura"               — Brincos = a vaca, Produto = touro/sêmen
  • Manejo tipo "Diagnóstico de Gestação" — Brincos = a vaca, Descrição = Prenha/Vazia
  • o parto é o bezerro cadastrado em Animais com "Mãe" = a vaca (já existia)

Prazos usados (gado de corte, Nelore/cruzado):
  gestação 285 dias · toque a partir de 35 dias · secagem 60 dias antes do parto.
Não mexe nas finanças — quem põe a cabeça no estoque continua sendo o Nascimento.
"""
from __future__ import annotations

import re

import pandas as pd

import animais as A

GESTACAO_DIAS = 285
DIAGNOSTICO_DIAS = 35      # a partir daqui o veterinário já sente no toque
SECAGEM_DIAS = 60          # antes do parto previsto
ATRASO_DIAS = 30           # passou tanto do parto previsto sem notícia → "perdida?"
PARTO_PROXIMO_DIAS = 30

TIPO_COBERTURA = "Cobertura"
TIPO_DIAGNOSTICO = "Diagnóstico de Gestação"
RESULTADOS = ["Prenha", "Vazia"]


def _eventos(df_man, tipo) -> list[tuple[pd.Timestamp, str, str, str]]:
    """[(data, id do animal, descrição, produto)] de um tipo, em ordem de data."""
    if df_man is None or df_man.empty or "Tipo" not in df_man.columns:
        return []
    df = df_man[(df_man["Tipo"] == tipo) & df_man["Data"].notna()]
    out = []
    for _, r in df.iterrows():
        d = pd.Timestamp(r["Data"]).normalize()
        for i in A.ids_de(r.get("Brincos")):
            out.append((d, i, A._txt(r.get("Descrição")), A._txt(r.get("Produto"))))
    out.sort(key=lambda e: e[0])
    return out


def _resultado(desc: str) -> str:
    """'Prenha'/'Vazia' escritos de qualquer jeito na descrição."""
    t = (desc or "").lower()
    if "vazia" in t or "negativ" in t:
        return "Vazia"
    if "prenh" in t or "positiv" in t or "cheia" in t:
        return "Prenha"
    return ""


def _partos(df_animais) -> dict[str, list[pd.Timestamp]]:
    """{ID da mãe: [datas de nascimento das crias]} — a cria já é cadastrada com Mãe."""
    out: dict[str, list[pd.Timestamp]] = {}
    if df_animais is None or df_animais.empty or "Mãe" not in df_animais.columns:
        return out
    for _, r in df_animais.iterrows():
        mae = A.ids_de(r.get("Mãe"))
        d = A._data(r.get("Nascimento"))
        if mae and pd.notna(d):
            out.setdefault(mae[0], []).append(pd.Timestamp(d).normalize())
    for v in out.values():
        v.sort()
    return out


def situacao(df_man, df_animais, hoje=None) -> list[dict]:
    """Uma linha por vaca com cobertura anotada, da mais perto de parir em diante.

    Só vale a ÚLTIMA cobertura de cada vaca: anotar de novo é o jeito de corrigir
    ou de registrar que ela repetiu o cio."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    ultima = {i: (d, prod) for d, i, _, prod in _eventos(df_man, TIPO_COBERTURA)}
    diagnosticos = _eventos(df_man, TIPO_DIAGNOSTICO)
    partos = _partos(df_animais)
    nomes = {}
    if df_animais is not None and not df_animais.empty:
        nomes = {r["ID"]: A.ref(r) for _, r in df_animais.iterrows()}

    out = []
    for vaca, (coberta_em, touro) in ultima.items():
        parto_prev = coberta_em + pd.Timedelta(days=GESTACAO_DIAS)
        # Diagnóstico e parto só contam se vieram DEPOIS desta cobertura.
        res = ""
        for d, i, desc, _ in diagnosticos:
            if i == vaca and d >= coberta_em:
                res = _resultado(desc) or res
        pariu = next((d for d in partos.get(vaca, []) if d > coberta_em), None)

        if pariu is not None:
            status = "pariu"
        elif res == "Vazia":
            status = "vazia"
        elif hoje > parto_prev + pd.Timedelta(days=ATRASO_DIAS):
            status = "atrasada"      # nem parto nem toque: alguém esqueceu de anotar
        elif res == "Prenha":
            status = "prenha"
        else:
            status = "coberta"       # esperando o toque

        out.append({
            "vaca": vaca, "nome": nomes.get(vaca, vaca), "touro": touro,
            "coberta_em": coberta_em, "resultado": res, "status": status,
            "parto_previsto": parto_prev, "pariu_em": pariu,
            "diagnostico_a_partir": coberta_em + pd.Timedelta(days=DIAGNOSTICO_DIAS),
            "secagem_em": parto_prev - pd.Timedelta(days=SECAGEM_DIAS),
            "dias_para_parto": (parto_prev - hoje).days,
            "dias_de_gestacao": (hoje - coberta_em).days,
        })
    # Quem está para parir primeiro aparece em cima; já resolvidas vão para o fim.
    out.sort(key=lambda v: (v["status"] in ("pariu", "vazia"), v["dias_para_parto"]))
    return out


def indicadores(situacoes: list[dict], df_animais=None) -> dict:
    """Números do rebanho de cria: prenhas, taxa de prenhez e intervalo entre partos."""
    prenhas = [v for v in situacoes if v["status"] == "prenha"]
    diagnosticadas = [v for v in situacoes if v["resultado"]]
    taxa = (100.0 * sum(1 for v in diagnosticadas if v["resultado"] == "Prenha")
            / len(diagnosticadas)) if diagnosticadas else None
    intervalos = []
    for datas in _partos(df_animais).values():
        intervalos += [(b - a).days for a, b in zip(datas, datas[1:])]
    return {"prenhas": len(prenhas), "coberturas": len(situacoes),
            "aguardando_toque": sum(1 for v in situacoes if v["status"] == "coberta"),
            "taxa_prenhez": taxa,
            "iep_dias": round(sum(intervalos) / len(intervalos)) if intervalos else None}


def alertas(situacoes: list[dict], hoje=None) -> list[dict]:
    """{texto, urgente} para o painel e o WhatsApp. Só o que exige ação."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    out = []
    for v in situacoes:
        if v["status"] in ("pariu", "vazia"):
            continue
        if v["status"] == "atrasada":
            out.append({"texto": f"❓ {v['nome']}: parto era para {v['parto_previsto']:%d/%m} "
                                 f"e não foi anotado — confira se nasceu ou se ela perdeu.",
                        "urgente": False, "chave": f"repro:{v['vaca']}:atrasada"})
        elif v["dias_para_parto"] <= PARTO_PROXIMO_DIAS:
            urg = v["dias_para_parto"] <= 7
            quando = ("HOJE" if v["dias_para_parto"] == 0 else
                      f"em {v['dias_para_parto']} dia(s)" if v["dias_para_parto"] > 0
                      else f"há {-v['dias_para_parto']} dia(s)")
            out.append({"texto": f"🐮 {v['nome']}: parto previsto {quando} "
                                 f"({v['parto_previsto']:%d/%m}) — olho nela.",
                        "urgente": urg, "chave": f"repro:{v['vaca']}:parto"})
        elif v["status"] == "coberta" and hoje >= v["diagnostico_a_partir"]:
            out.append({"texto": f"🩺 {v['nome']}: coberta em {v['coberta_em']:%d/%m}, "
                                 f"já dá para fazer o toque (sem resultado anotado).",
                        "urgente": False, "chave": f"repro:{v['vaca']}:toque"})
    return out


def registrar(tipo: str, vaca_ref: str, data, touro: str = "", resultado: str = "",
              responsavel: str = ""):
    """Grava a Cobertura ou o Diagnóstico no Manejo (uma vaca por vez)."""
    import db
    if tipo not in (TIPO_COBERTURA, TIPO_DIAGNOSTICO):
        raise ValueError("Tipo de registro de reprodução inválido.")
    refs, erros = A.resolver_texto(vaca_ref or "")
    if erros or not refs:
        raise ValueError("; ".join(erros) or "Diga qual é a vaca (cor e número do brinco).")
    if len(refs) > 1:
        raise ValueError("Anote uma vaca por vez.")
    d = A._data(data) if data else pd.NaT
    if pd.isna(d):
        d = pd.Timestamp.now().normalize()
    if tipo == TIPO_DIAGNOSTICO:
        if resultado not in RESULTADOS:
            raise ValueError("O toque deu Prenha ou Vazia?")
        desc, produto = resultado, ""
    else:
        desc = f"Cobertura — {touro}".strip(" —") if touro else "Cobertura"
        produto = re.sub(r"\s+", " ", str(touro or "")).strip()[:60]
    db.salvar_linha("Manejo", A._linha_manejo(d, tipo, 1, desc, responsavel,
                                              produto=produto, brincos="; ".join(refs)))


def planejamento_ia(df_anim: pd.DataFrame, df_man: pd.DataFrame, hoje: pd.Timestamp | None = None) -> list[dict]:
    """Retorna vacas candidatas a IA planejada nos próximos 30 dias.

    Critérios: vaca viva, vazia (ultimo diagnóstico foi "Vazia"), sem cobertura
    nos últimos 60 dias, e com BCS adequado (se disponível).

    Útil para comunicar ao veterinário ou inseminador quem vai trabalhar.
    """
    if df_man is None or df_man.empty or df_anim is None or df_anim.empty:
        return []

    if hoje is None:
        hoje = pd.Timestamp.now().normalize()

    candidatas = []

    for id_, animal in df_anim.iterrows():
        if animal.get("Status") != "Vivo":
            continue
        if animal.get("Uso Produtivo") not in ("leite", "ambos"):
            continue

        # Procura último diagnóstico
        diagnosticos = _eventos(df_man, TIPO_DIAGNOSTICO)
        ultimo_diag = None
        for data, anim_id, resultado, _ in reversed(diagnosticos):
            if anim_id == animal.get("ID"):
                ultimo_diag = (data, resultado)
                break

        # Só candidata se foi vazia no diagnóstico
        if not ultimo_diag or ultimo_diag[1] != "Vazia":
            continue

        # Procura última cobertura
        coberturas = _eventos(df_man, TIPO_COBERTURA)
        ultima_cob = None
        for data, anim_id, _, touro in reversed(coberturas):
            if anim_id == animal.get("ID"):
                ultima_cob = (data, touro)
                break

        # Só candidata se faz >= 60 dias da última cobertura
        if ultima_cob and (hoje - ultima_cob[0]).days < 60:
            continue

        dias_proxima_ia = 21 if not ultima_cob else ((ultima_cob[0] + pd.Timedelta(days=21)) - hoje).days

        candidatas.append({
            "id": animal.get("ID"),
            "nome": animal.get("Nome", ""),
            "cor": animal.get("Cor", ""),
            "ultimo_diag": ultimo_diag[0] if ultimo_diag else None,
            "dias_proxima_ia": max(0, dias_proxima_ia),
            "prioridade": "alta" if dias_proxima_ia <= 7 else "normal"
        })

    return sorted(candidatas, key=lambda x: (x["prioridade"] == "normal", x["dias_proxima_ia"]))
