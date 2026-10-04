# -*- coding: utf-8 -*-
"""
saude.py — calendário sanitário (vacinas, vermifugação) — Triângulo Mineiro
===========================================================================
Fonte única das regras de saúde usadas pelo painel, pelo calendário e pelo
WhatsApp. Referências (pesquisadas em 10/2026):

  • Raiva — OBRIGATÓRIA em todo o estado de MG (IMA / PNCRH). A partir de
    3 meses; 1ª vez = 2 doses com 30 dias; depois 1 dose ANUAL. Declarar ao IMA.
  • Brucelose — OBRIGATÓRIA: fêmeas de 3 a 8 meses, dose única (B19 ou RB51),
    por veterinário cadastrado no IMA. Duas etapas por ano:
      1ª etapa: vacinar até 30/06 e declarar até 10/07;
      2ª etapa: vacinar até 31/12 e declarar até 10/01.
  • Febre aftosa — MG é zona livre SEM vacinação (MAPA 2024, OMSA 2025): não vacinar.
  • Clostridioses (+ botulismo, em geral na mesma vacina polivalente) —
    a partir de 4 meses, reforço em 30 dias, depois ANUAL.
  • Vermifugação estratégica 5-7-9 (Embrapa Gado de Corte, Brasil Central):
    maio, julho e setembro, da desmama até ~24 meses.

Os intervalos em dias continuam ajustáveis em ⚙️ Configurações (db.get_alertas_saude).
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

# Registros antigos do tipo genérico "Vacinação" não dizem qual vacina foi dada;
# para não disparar alarmes falsos, contam para as vacinas anuais.
ALIASES = {
    "Vacina Raiva":         ("Vacinação",),
    "Vacina Clostridioses": ("Vacinação",),
}

VERMIFUGACAO_MESES = {
    5: "maio — benzimidazol (largo espectro)",
    7: "julho — levamisol/imidazotiazol (mais econômico)",
    9: "setembro — endectocida (ivermectina etc.; pega também parasitas externos)",
}

BRUCELOSE_TIPO = "Vacina Brucelose"

# Exemplos de produtos do mercado brasileiro (pesquisa out/2026) — só sugestões
# para o campo "remédio/produto"; não é recomendação de marca.
SUGESTOES_PRODUTO = {
    "Vacina Raiva":         ["Raivacel Multi", "Rai-Vac K", "Rai-Vet"],
    "Vacina Clostridioses": ["Bovilis Poli-Star T", "Sintoxan Polivalente", "Sintoxan 9TH", "Covexin 9"],
    "Vacina Brucelose":     ["B19", "RB51"],
    "Vacinação":            ["Poliguard (IBR/BVD/Lepto)", "CattleMaster 4+L5 (IBR/BVD/Lepto)"],
    "Vermifugação":         ["Valbazen (albendazol)", "Ricobendazol injetável", "Levamisol",
                             "Ivomec Gold 3,15%", "Dectomax (doramectina)",
                             "Solution 3,5% (ivermectina + abamectina)", "Evol"],
}


def _do_tipo(df_man: pd.DataFrame, tipos) -> pd.DataFrame:
    if df_man is None or df_man.empty or "Tipo" not in df_man.columns or "Data" not in df_man.columns:
        return pd.DataFrame(columns=["Data", "Tipo"])
    return df_man[df_man["Tipo"].isin(tipos) & df_man["Data"].notna()]


def ultima_data(df_man: pd.DataFrame, tipo: str) -> pd.Timestamp | None:
    """Data do último registro do tipo (considerando os aliases antigos)."""
    df = _do_tipo(df_man, (tipo,) + ALIASES.get(tipo, ()))
    if df.empty:
        return None
    ult = df["Data"].max()
    return None if pd.isna(ult) else ult


def _semestre(d: datetime) -> tuple[int, int]:
    return d.year, (1 if d.month <= 6 else 2)


def brucelose_status(df_man: pd.DataFrame, hoje: datetime) -> dict:
    """
    Situação da campanha de brucelose no semestre atual:
      vacinou         — há registro de Vacina Brucelose neste semestre
      prazo_vacina    — 30/06 ou 31/12 do semestre atual
      prazo_declarar  — 10/07 ou 10/01 seguinte
    """
    ano, sem = _semestre(hoje)
    prazo_vac = datetime(ano, 6, 30) if sem == 1 else datetime(ano, 12, 31)
    prazo_dec = datetime(ano, 7, 10) if sem == 1 else datetime(ano + 1, 1, 10)
    df = _do_tipo(df_man, (BRUCELOSE_TIPO,))
    vacinou = bool(not df.empty and any(_semestre(d) == (ano, sem) for d in df["Data"]))
    ult = df["Data"].max() if not df.empty else None
    return {"vacinou": vacinou, "prazo_vacina": prazo_vac, "prazo_declarar": prazo_dec,
            "ultima": None if ult is None or pd.isna(ult) else ult}


def lembretes_sazonais(df_man: pd.DataFrame, hoje: datetime | None = None) -> list[dict]:
    """
    Lembretes de calendário (não de intervalo): campanha de brucelose e
    vermifugação 5-7-9. Retorna [{"nivel": warning|info, "msg": str}].
    """
    hoje = hoje or datetime.now()
    out = []

    # ── Brucelose: avisa nos 2 últimos meses de cada etapa e na janela de declaração
    if hoje.month in (5, 6, 11, 12):
        b = brucelose_status(df_man, hoje)
        etapa = "1ª" if hoje.month <= 6 else "2ª"
        if not b["vacinou"]:
            out.append({"nivel": "warning", "msg":
                f"Brucelose ({etapa} etapa): se houver bezerras de 3 a 8 meses, vacinar até "
                f"{b['prazo_vacina']:%d/%m} (veterinário cadastrado no IMA) e declarar até "
                f"{b['prazo_declarar']:%d/%m}."})
        else:
            out.append({"nivel": "info", "msg":
                f"Brucelose ({etapa} etapa) vacinada — lembre de declarar ao IMA até "
                f"{b['prazo_declarar']:%d/%m}."})
    elif hoje.month in (1, 7) and hoje.day <= 10:
        # janela de declaração da etapa que acabou de fechar
        anterior = hoje.replace(day=1) - pd.Timedelta(days=1)
        b = brucelose_status(df_man, anterior)
        if b["vacinou"]:
            out.append({"nivel": "warning", "msg":
                f"Brucelose: declare a vacinação ao IMA até {b['prazo_declarar']:%d/%m}."})

    # ── Vermifugação estratégica 5-7-9
    if hoje.month in VERMIFUGACAO_MESES:
        df = _do_tipo(df_man, ("Vermifugação",))
        feita = any((d.year, d.month) == (hoje.year, hoje.month) for d in df["Data"])
        if not feita:
            out.append({"nivel": "warning", "msg":
                f"Vermifugação estratégica 5-7-9 de {VERMIFUGACAO_MESES[hoje.month]} "
                f"— animais da desmama até ~24 meses."})
    return out


def brucelose_proxima(df_man: pd.DataFrame, hoje: datetime) -> dict:
    """Item da campanha de brucelose no formato da lista 'próximas' do calendário."""
    # Só a data: com a hora atual, o próprio dia do prazo contava como −1.
    hoje = datetime(hoje.year, hoje.month, hoje.day)
    b = brucelose_status(df_man, hoje)
    if b["vacinou"]:
        # já vacinou neste semestre: o próximo prazo é o da etapa seguinte
        ano, sem = _semestre(hoje)
        prazo = datetime(ano, 12, 31) if sem == 1 else datetime(ano + 1, 6, 30)
        status = "ok"
    else:
        prazo = b["prazo_vacina"]
        dias = (prazo - hoje).days
        status = "urgente" if dias <= 15 else "proximo" if dias <= 60 else "ok"
    return {
        "tipo":           BRUCELOSE_TIPO,
        "intervalo_dias": None,
        "ultima_data":    b["ultima"].strftime("%d/%m/%Y") if b["ultima"] is not None else "—",
        "data_prevista":  prazo.strftime("%Y-%m-%d"),
        "dias_restantes": (prazo - hoje).days,
        "status":         status,
    }
