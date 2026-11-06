#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cochos.py — Gerenciamento de cochos (comedouros) e rastreamento de alimentação (v5.10)

Integra visitas com alimentação para rastrear:
- Consumo diário por cocho (proteinado, sal, ração, silo, feno)
- Dias estimados até acabar
- Estado do cocho (Vazio, Normal, Cheio)
- Próxima salga/reposição
"""

from datetime import datetime, date, timedelta


def _hoje_br():
    """Hoje no fuso de Brasília (o servidor pode estar em UTC)."""
    try:
        from extensions import _agora
        return _agora().date()
    except Exception:
        return date.today()
from typing import Dict, List, Optional, Tuple
import pandas as pd

from db import carregar_aba


def normalizar_cochos(df):
    """Remove IDs repetidos, preservando o registro mais recente."""
    if df is None:
        return pd.DataFrame()
    if df.empty or "ID" not in df.columns:
        return df.copy()

    resultado = df.copy()
    ids = resultado["ID"].fillna("").astype(str).str.strip()
    manter = ids.eq("") | ~ids.duplicated(keep="last")
    resultado["ID"] = ids
    return resultado.loc[manter].reset_index(drop=True)


def carregar():
    """Carrega aba 'Cochos' do Excel."""
    try:
        df = carregar_aba("Cochos")
        return normalizar_cochos(df)
    except Exception:
        return pd.DataFrame()


def carregar_movimentos():
    """Carrega o histórico de reposições e leituras manuais dos cochos."""
    df = carregar_aba("Movimentos Cocho")
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "ID", "Data", "Cocho ID", "Tipo", "Quantidade (kg)", "Cabeças",
            "Observações", "Responsável",
        ])
    return df


def _normalizar_data(valor):
    """Normaliza data em vários formatos (com suporte robusto a dd/mm/aaaa e pandas)."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "nat", "none"}:
        return None
    try:
        dt = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")
        if not pd.isna(dt):
            return dt.date()
    except Exception:
        pass
    try:
        dt = pd.to_datetime(texto, errors="coerce")
        if not pd.isna(dt):
            return dt.date()
    except Exception:
        pass
    try:
        texto_10 = texto[:10]
        if "-" in texto_10:
            return datetime.strptime(texto_10, "%Y-%m-%d").date()
        return datetime.strptime(texto_10, "%d/%m/%Y").date()
    except ValueError:
        return None


def _normalizar_numero(valor):
    """Normaliza número em vários formatos."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _cocho_ativo(valor):
    """Considera ativos os registros legados sem status e os marcados como Sim."""
    return str(valor if valor is not None else "Sim").strip().casefold() not in {
        "não", "nao", "inativo", "false", "0"
    }


def extrair_consumo_visitas(df_visitas, dias: int = 60) -> Dict[str, Dict]:
    """
    Extrai consumo de alimentação das visitas dos últimos N dias.

    Retorna: {
        "proteinado": {"sacos": X, "kg": Y, "media_dia": Z},
        "sal": {...},
        "racao": {...},
        "silo": {...},
        "feno": {...}
    }
    """
    if df_visitas.empty:
        return {}

    # Filtra por data (últimos N dias)
    df_visitas = df_visitas.copy()
    df_visitas["_data"] = df_visitas.get("Data", "").apply(_normalizar_data)
    data_limite = _hoje_br() - timedelta(days=dias)
    df_filtro = df_visitas[df_visitas["_data"].notna()]
    df_filtro = df_filtro[df_filtro["_data"] >= data_limite]

    if df_filtro.empty:
        return {}

    consumo = {}

    # Proteinado
    sacos_prot = df_filtro["Sacos Proteinado"].apply(_normalizar_numero).sum() or 0
    consumo["proteinado"] = {
        "sacos": int(sacos_prot),
        "kg": round(sacos_prot * 25, 2),  # Assume 25 kg por saco
        "dias_com_dados": len(df_filtro),
        "media_dia": round((sacos_prot * 25) / dias, 2) if dias > 0 else 0
    }

    # Sal/Ração (legado)
    sacos_sal = df_filtro["Sacos Sal/Ração"].apply(_normalizar_numero).sum() or 0
    consumo["sal_racao"] = {
        "sacos": int(sacos_sal),
        "kg": round(sacos_sal * 25, 2),
        "dias_com_dados": len(df_filtro),
        "media_dia": round((sacos_sal * 25) / dias, 2) if dias > 0 else 0
    }

    # Ração (separado)
    sacos_racao = df_filtro["Sacos Ração"].apply(_normalizar_numero).sum() or 0
    consumo["racao"] = {
        "sacos": int(sacos_racao),
        "kg": round(sacos_racao * 25, 2),
        "dias_com_dados": len(df_filtro),
        "media_dia": round((sacos_racao * 25) / dias, 2) if dias > 0 else 0
    }

    return consumo


def calcular_situacao_cochos(df_cochos, df_visitas, df_movimentos=None) -> Dict[str, Dict]:
    """
    Calcula situação de cada cocho: volume, dias restantes, próxima salga.

    Retorna: {
        "cocho_id": {
            "nome": "Cocho Pasto Remanga",
            "tipo": "proteinado",
            "volume_kg": 432,
            "capacidade_kg": 500,
            "percentual": 86,
            "estado": "Cheio",
            "consumo_dia_kg": 108,
            "dias_restantes": 4,
            "ultima_salga": "2026-06-26",
            "proxima_salga_estimada": "2026-06-30"
        }
    }
    """

    if df_cochos.empty:
        return {}

    consumo_visitas = extrair_consumo_visitas(df_visitas, dias=60)
    situacao = {}

    for _, cocho in df_cochos.iterrows():
        cocho_id = str(cocho.get("ID", "")).strip()
        if not cocho_id or not _cocho_ativo(cocho.get("Ativo", "Sim")):
            continue

        nome = str(cocho.get("Nome", "Cocho")).strip()
        tipo = str(cocho.get("Tipo", "")).lower().strip()  # proteinado, sal, ração, etc.
        capacidade = _normalizar_numero(cocho.get("Capacidade (kg)")) or 500
        volume_atual = _normalizar_numero(cocho.get("Volume Atual (kg)")) or 0
        ultima_salga = _normalizar_data(cocho.get("Última Salga"))
        consumo_g_cab_dia = None
        cabecas_ultima_leitura = 0

        if df_movimentos is not None and not df_movimentos.empty:
            historico = df_movimentos[
                df_movimentos.get("Cocho ID", pd.Series(dtype=str)).astype(str).str.strip() == cocho_id
            ].copy()
            if not historico.empty:
                historico["_data"] = historico["Data"].apply(_normalizar_data)
                historico = historico.dropna(subset=["_data"])
                historico = historico[historico["_data"] <= _hoje_br()].sort_values(
                    "_data", kind="stable"
                )
                saldo = volume_atual
                leitura_anterior = None
                reposicoes = 0.0
                for _, mov in historico.iterrows():
                    quantidade = _normalizar_numero(mov.get("Quantidade (kg)")) or 0
                    tipo_mov = str(mov.get("Tipo", "")).strip()
                    if tipo_mov == "Reposição":
                        saldo += quantidade
                        reposicoes += quantidade
                        ultima_salga = mov["_data"]
                    elif tipo_mov == "Leitura":
                        if leitura_anterior:
                            dias = (mov["_data"] - leitura_anterior["data"]).days
                            cabecas = _normalizar_numero(mov.get("Cabeças")) or 0
                            consumido = leitura_anterior["saldo"] + reposicoes - quantidade
                            if dias > 0 and cabecas > 0 and consumido >= 0:
                                consumo_g_cab_dia = consumido * 1_000 / cabecas / dias
                        cabecas_ultima_leitura = _normalizar_numero(mov.get("Cabeças")) or 0
                        saldo = quantidade
                        reposicoes = 0.0
                        leitura_anterior = {
                            "data": mov["_data"], "saldo": quantidade,
                        }
                volume_atual = saldo

        # Cálculo robusto do consumo diário do cocho baseado no número real de animais e grama por cabeça/dia
        try:
            from db import carregar_aba
            import animais as A
            import pastos as PA
            df_animais = A.carregar()
            df_pastos = PA.carregar()
            # Descobre quantas cabeças estão no pasto associado a este cocho (ou rebanho total se não vinculado)
            pasto_cocho = str(cocho.get("Pasto", "")).strip()
            if not pasto_cocho or pasto_cocho.lower() in {"nan", "none", ""}:
                # Se não vinculado especificamente, usa total de animais vivos no rebanho
                n_animais = len(df_animais[df_animais.get("Status", "Ativo").astype(str).str.strip().str.lower() != "baixado"]) if not df_animais.empty else 0
            else:
                # Conta animais no pasto correspondente
                sit_pastos = PA.situacao(df_pastos, df_animais, carregar_aba("Manejo"), len(df_animais), hoje=_hoje_br())
                n_animais = sit_pastos.get(pasto_cocho, {}).get("cabecas", 0)
        except Exception:
            n_animais = 0

        # Grama por cabeça por dia (padrão 100g para proteinado/sal se não especificado)
        g_cab_dia = _normalizar_numero(cocho.get("Grama/Cab/Dia")) or 100.0
        if consumo_g_cab_dia is not None:
            g_cab_dia = consumo_g_cab_dia

        # Consumo Diário Total (kg) = (Grama por cabeça por dia * Nº de animais) / 1000
        if n_animais > 0 and g_cab_dia > 0:
            consumo_dia = (g_cab_dia * n_animais) / 1000.0
        else:
            consumo_info = consumo_visitas.get(tipo, {})
            consumo_dia = consumo_info.get("media_dia", 0)
            if consumo_g_cab_dia is not None and cabecas_ultima_leitura > 0:
                consumo_dia = consumo_g_cab_dia * cabecas_ultima_leitura / 1_000

        # Calcula dias restantes
        if volume_atual <= 0:
            dias_restantes = 0
        elif consumo_dia > 0:
            dias_restantes = round(volume_atual / consumo_dia)
        else:
            dias_restantes = 0  # Indeterminado / Sem consumo, evita o 999 alucinado

        proxima_salga = None
        if ultima_salga and consumo_dia > 0 and dias_restantes < 999:
            proxima_salga = (ultima_salga + timedelta(days=dias_restantes)).strftime("%Y-%m-%d")

        # Estado visual do cocho
        percentual = round((volume_atual / capacidade * 100)) if capacidade > 0 else 0
        if percentual <= 25:
            estado = "Vazio"
        elif percentual <= 75:
            estado = "Normal"
        else:
            estado = "Cheio"

        situacao[cocho_id] = {
            "nome": nome,
            "tipo": tipo,
            "volume_kg": round(volume_atual, 1),
            "capacidade_kg": round(capacidade, 1),
            "percentual": int(percentual),
            "estado": estado,
            "consumo_dia_kg": round(consumo_dia, 2),
            "consumo_g_cab_dia": round(g_cab_dia, 1) if g_cab_dia > 0 else None,
            "dias_restantes": dias_restantes,
            "ultima_salga": ultima_salga.strftime("%Y-%m-%d") if ultima_salga else None,
            "proxima_salga_estimada": proxima_salga
        }

    return situacao


def resumo_cochos(df_cochos, df_visitas, df_movimentos=None) -> Dict:
    """Retorna resumo geral dos cochos."""
    sit = calcular_situacao_cochos(df_cochos, df_visitas, df_movimentos)

    if not sit:
        return {
            "total_cochos": 0,
            "cochos_cheios": 0,
            "cochos_normais": 0,
            "cochos_vazios": 0,
            "proximo_para_salgar": None
        }

    estados = [c["estado"] for c in sit.values()]

    # Encontra próximo cocho para salgar (menor dias restantes)
    proximo = min(
        [c for c in sit.values() if c["dias_restantes"] > 0],
        key=lambda x: x["dias_restantes"],
        default=None
    )

    return {
        "total_cochos": len(sit),
        "cochos_cheios": estados.count("Cheio"),
        "cochos_normais": estados.count("Normal"),
        "cochos_vazios": estados.count("Vazio"),
        "proximo_para_salgar": proximo
    }


if __name__ == "__main__":
    df_cochos = carregar()
    from db import carregar_aba
    df_visitas = carregar_aba("Visitas")

    print("=== Situação dos Cochos ===")
    sit = calcular_situacao_cochos(df_cochos, df_visitas)
    for cocho_id, info in sit.items():
        print(f"\n{info['nome']} ({cocho_id})")
        print(f"  Volume: {info['volume_kg']}/{info['capacidade_kg']} kg ({info['percentual']}%)")
        print(f"  Estado: {info['estado']}")
        print(f"  Consumo: {info['consumo_dia_kg']} kg/dia")
        print(f"  Dias restantes: {info['dias_restantes']}")
        if info['proxima_salga_estimada']:
            print(f"  Próxima salga: {info['proxima_salga_estimada']}")
