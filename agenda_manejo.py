# -*- coding: utf-8 -*-
"""Sugestões revisáveis de manejo por animal e pasto/lote."""
from datetime import date, datetime, timedelta

import pandas as pd

import animais as A
import db
import pastos as PA


def sugestoes(df_manejo, df_animais, hoje=None, janela_dias=30) -> list[dict]:
    """Calcula vencimentos a partir do último manejo aplicável a cada animal."""
    hoje = hoje.date() if isinstance(hoje, datetime) else (hoje or date.today())
    limite = hoje + timedelta(days=janela_dias)
    if df_manejo is None or df_manejo.empty or df_animais is None or df_animais.empty:
        return []

    intervalos = db.get_alertas_saude()
    aliases = {
        "Vacina Raiva": ("Vacinação",),
        "Vacina Clostridioses": ("Vacinação",),
    }
    nomes_pastos = {}
    df_pastos = PA.ativos(PA.carregar())
    if not df_pastos.empty:
        nomes_pastos = dict(zip(df_pastos["ID"].astype(str), df_pastos["Nome"].astype(str)))

    grupos = {}
    vivos = A.vivos(df_animais)
    for _, animal in vivos.iterrows():
        animal_id = A._txt(animal.get("ID"))
        if not animal_id:
            continue
        ref = A.ref(animal)
        pasto_id, _ = PA.pasto_do_animal(animal_id, df_manejo)
        pasto_id = A._txt(pasto_id)
        pasto_nome = nomes_pastos.get(pasto_id, "Sem pasto definido")
        for tipo, intervalo in intervalos.items():
            tipos_validos = (tipo,) + aliases.get(tipo, ())
            aplicaveis = []
            for _, registro in df_manejo.iterrows():
                if registro.get("Tipo") not in tipos_validos:
                    continue
                data = A._data(registro.get("Data"))
                if pd.isna(data):
                    continue
                ids = A.ids_de(registro.get("Brincos"))
                if ids and animal_id not in ids:
                    continue
                pasto_registro = A._txt(registro.get("Pasto"))
                if pasto_registro and pasto_registro != pasto_id:
                    continue
                aplicaveis.append(data.date())
            if not aplicaveis:
                continue
            ultima = max(aplicaveis)
            prevista = ultima + timedelta(days=int(intervalo))
            if prevista > limite:
                continue
            chave = (tipo, pasto_id, prevista, ultima)
            item = grupos.setdefault(chave, {
                "tipo": tipo,
                "pasto_id": pasto_id,
                "pasto": pasto_nome,
                "prevista": prevista,
                "ultima": ultima,
                "intervalo": int(intervalo),
                "animais": [],
                "ids": [],
            })
            item["animais"].append(ref)
            item["ids"].append(animal_id)

    saida = list(grupos.values())
    for item in saida:
        dias = (item["prevista"] - hoje).days
        item["dias"] = dias
        item["status"] = "vencido" if dias < 0 else ("hoje" if dias == 0 else "proximo")
        item["titulo"] = (
            f"{item['tipo']} — {item['pasto']} ({len(item['animais'])} animal(is))"
        )[:80]
    return sorted(saida, key=lambda x: (x["prevista"], x["tipo"], x["pasto"]))
