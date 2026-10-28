#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mastite_predicao.py — Predição de mastite por análise de CCS/CPP (v5.10 Onda 1)

Detecta tendências de CCS/CPP e previne mastite até 30 dias antes dos sintomas.
Integrado com módulo leiteiro existente.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import db
import animais


LIMITE_CCS_AVISO = 200_000      # > 200k = aviso
LIMITE_CCS_URGENTE = 400_000    # > 400k = urgente
LIMITE_CBT_AVISO = 50_000       # > 50k = aviso
LIMITE_CBT_URGENTE = 100_000    # > 100k = urgente
LIMITE_CPP_AVISO = 75_000       # > 75k = aviso (Contagem de Patógenos)
LIMITE_CPP_URGENTE = 150_000    # > 150k = urgente

# MAPA IN 76: Limite regulatório = 500.000 células/mL
LIMITE_REGULATORIO = 500_000


def carregar_historico_ccs(dias: int = 60) -> pd.DataFrame:
    """Carrega histórico de CCS/CPP dos últimos N dias da aba 'Leite Produção'."""
    try:
        df_leite = db.carregar_aba("Leite Produção")
        if df_leite.empty:
            return pd.DataFrame()

        # Converte Data para datetime
        df_leite['Data'] = pd.to_datetime(df_leite.get('Data', []),
                                          format='%d/%m/%Y', errors='coerce')

        # Filtra últimos N dias
        data_limite = datetime.now() - timedelta(days=dias)
        df_recente = df_leite[df_leite['Data'] >= data_limite].copy()

        return df_recente.sort_values('Data', ascending=False)
    except Exception as e:
        print(f"Erro ao carregar histórico CCS: {e}")
        return pd.DataFrame()


def calcular_tendencia_ccs(vaca_id: str, dias: int = 30) -> Dict:
    """
    Calcula tendência de CCS para uma vaca nos últimos N dias.
    Retorna: tendência (subindo/descendo/estável), valores, dias_alerta
    """
    try:
        df_leite = carregar_historico_ccs(dias=dias)

        # Filtra registros da vaca (por ID ou por Brinco)
        df_vaca = df_leite[
            (df_leite.get('ID Animal', '').astype(str) == str(vaca_id)) |
            (df_leite.get('Brinco', '').astype(str) == str(vaca_id))
        ].sort_values('Data')

        if len(df_vaca) < 2:
            return {
                "vaca_id": vaca_id,
                "tendencia": "sem_dados",
                "ccs_valores": [],
                "dias_alerta": 0,
                "ultimas_medicoes": []
            }

        # Extrai valores de CCS (pode estar em várias colunas)
        ccs_valores = []
        datas = []
        for _, row in df_vaca.iterrows():
            ccs = row.get('CCS', 0) or row.get('CCS (células/mL)', 0)
            if pd.notna(ccs):
                try:
                    ccs_val = float(str(ccs).replace('.', '').replace(',', '.'))
                    ccs_valores.append(ccs_val)
                    datas.append(row['Data'])
                except (ValueError, TypeError):
                    pass

        if len(ccs_valores) < 2:
            return {
                "vaca_id": vaca_id,
                "tendencia": "insuficiente_dados",
                "ccs_valores": ccs_valores,
                "dias_alerta": 0,
                "ultimas_medicoes": list(zip(datas, ccs_valores))
            }

        # Calcula tendência: média últimos 3 vs média anteriores
        n = len(ccs_valores)
        media_recente = sum(ccs_valores[-3:]) / min(3, len(ccs_valores))
        media_antiga = sum(ccs_valores[:-3]) / max(1, n - 3)

        if media_recente > media_antiga * 1.2:  # Subiu 20%+
            tendencia = "subindo"
        elif media_recente < media_antiga * 0.8:  # Caiu 20%+
            tendencia = "descendo"
        else:
            tendencia = "estavel"

        # Calcula quantos dias até atingir limite de urgência (extrapolação linear)
        if len(ccs_valores) >= 3:
            delta = ccs_valores[-1] - ccs_valores[-3]  # Mudança em 3 dias
            dias_ate_urgente = 999
            if delta > 0:  # Está subindo
                dias_ate_urgente = max(0, int((LIMITE_CCS_URGENTE - ccs_valores[-1]) / (delta / 3)))
            dias_alerta = min(30, dias_ate_urgente)
        else:
            dias_alerta = 0

        return {
            "vaca_id": vaca_id,
            "tendencia": tendencia,
            "ccs_valores": ccs_valores,
            "dias_alerta": dias_alerta,
            "ultimas_medicoes": list(zip(datas, ccs_valores)),
            "media_recente": media_recente,
            "media_antiga": media_antiga
        }

    except Exception as e:
        print(f"Erro ao calcular tendência CCS: {e}")
        return {"vaca_id": vaca_id, "tendencia": "erro", "ccs_valores": [], "dias_alerta": 0}


def gerar_alertas_mastite() -> List[Dict]:
    """
    Gera alertas de mastite (aviso/urgente) para todas as vacas.
    Integra: CCS em tendência alta, CPP elevado, histórico de problemas.
    """
    alertas = []

    try:
        # Carrega últimas medicoes por vaca
        df_leite = carregar_historico_ccs(dias=30)
        if df_leite.empty:
            return alertas

        # Agrupa por vaca (última medição por animal)
        vacas_ids = df_leite.get('ID Animal', []).dropna().unique()

        for vaca_id in vacas_ids:
            df_vaca_recente = df_leite[
                df_leite.get('ID Animal', '').astype(str) == str(vaca_id)
            ].iloc[0]

            ccs_atual = df_vaca_recente.get('CCS', 0)
            cpp_atual = df_vaca_recente.get('CPP', 0) or df_vaca_recente.get('CPP (UFC/mL)', 0)
            cbt_atual = df_vaca_recente.get('CBT', 0)
            data_medicao = df_vaca_recente.get('Data')

            # Converte para valores numéricos
            try:
                ccs_val = float(str(ccs_atual).replace('.', '').replace(',', '.')) if ccs_atual else 0
                cpp_val = float(str(cpp_atual).replace('.', '').replace(',', '.')) if cpp_atual else 0
                cbt_val = float(str(cbt_atual).replace('.', '').replace(',', '.')) if cbt_atual else 0
            except (ValueError, TypeError):
                continue

            # Calcula tendência
            tend = calcular_tendencia_ccs(str(vaca_id), dias=30)
            dias_alerta = tend.get("dias_alerta", 0)
            tendencia = tend.get("tendencia", "")

            # Gera alertas
            tipo_alerta = None
            motivo = []

            # CCS
            if ccs_val >= LIMITE_CCS_URGENTE:
                tipo_alerta = "urgente"
                motivo.append(f"CCS {int(ccs_val):,}/mL (urgente ≥ 400k)")
            elif ccs_val >= LIMITE_CCS_AVISO:
                tipo_alerta = "aviso"
                motivo.append(f"CCS {int(ccs_val):,}/mL (aviso ≥ 200k)")

            # Tendência subindo
            if tendencia == "subindo" and dias_alerta <= 14:
                if tipo_alerta is None:
                    tipo_alerta = "aviso"
                motivo.append(f"CCS subindo — risco em ~{dias_alerta} dias")

            # CBT (higiene/armazenamento)
            if cbt_val >= LIMITE_CBT_URGENTE:
                if tipo_alerta != "urgente":
                    tipo_alerta = "urgente"
                motivo.append(f"CBT {int(cbt_val):,}/mL (higiene crítica)")
            elif cbt_val >= LIMITE_CBT_AVISO:
                if tipo_alerta is None:
                    tipo_alerta = "aviso"
                motivo.append(f"CBT {int(cbt_val):,}/mL (revisar higiene)")

            # CPP (patógenos)
            if cpp_val >= LIMITE_CPP_URGENTE:
                if tipo_alerta != "urgente":
                    tipo_alerta = "urgente"
                motivo.append(f"CPP {int(cpp_val):,}/mL (infecção ativa)")
            elif cpp_val >= LIMITE_CPP_AVISO:
                if tipo_alerta is None:
                    tipo_alerta = "aviso"
                motivo.append(f"CPP {int(cpp_val):,}/mL (monitorar)")

            # Cria alerta
            if tipo_alerta:
                try:
                    df_animais = animais.carregar()
                    animal = df_animais[df_animais['ID'].astype(str) == str(vaca_id)].iloc[0] if not df_animais.empty else {}
                    brinco_desc = f"{animal.get('Brinco Cor', '')} {int(animal.get('Brinco Nº', 0)) or '??'}"
                except Exception:
                    brinco_desc = f"ID {vaca_id}"

                alertas.append({
                    "tipo": tipo_alerta,
                    "animal_id": vaca_id,
                    "animal_desc": brinco_desc,
                    "motivo": " | ".join(motivo),
                    "data_medicao": data_medicao,
                    "ccs": ccs_val,
                    "cpp": cpp_val,
                    "cbt": cbt_val,
                    "acao": _gerar_acao_recomendada(tipo_alerta, ccs_val, cpp_val, cbt_val, tendencia)
                })

    except Exception as e:
        print(f"Erro ao gerar alertas de mastite: {e}")

    # Ordena: urgentes primeiro
    alertas.sort(key=lambda a: (a['tipo'] != 'urgente', a['animal_desc']))
    return alertas


def _gerar_acao_recomendada(tipo: str, ccs: float, cpp: float, cbt: float, tendencia: str) -> str:
    """Gera ação recomendada baseada no tipo de alerta."""
    acoes = []

    if ccs >= LIMITE_CCS_URGENTE:
        acoes.append("🚨 Examinar úbere — possível mastite clínica")
        acoes.append("Coletar amostra para teste de sensibilidade")
    elif ccs >= LIMITE_CCS_AVISO and tendencia == "subindo":
        acoes.append("⚠️ Aumentar monitoramento — ordenha 2-3x/dia")
        acoes.append("Revisar higiene da ordenha")
    elif ccs >= LIMITE_CCS_AVISO:
        acoes.append("Revisar rotina de limpeza")
        acoes.append("Monitorar próximas ordenhas")

    if cpp >= LIMITE_CPP_URGENTE:
        acoes.append("Considerar isolamento e tratamento")
        acoes.append("Excluir leite da venda")

    if cbt >= LIMITE_CBT_URGENTE:
        acoes.append("Conferir funcionamento do resfriador")
        acoes.append("Revisar higiene geral da sala de ordenha")

    return " · ".join(acoes) if acoes else "Continuar monitoramento"


def alertas_whatsapp() -> str:
    """Monta mensagem de mastite para enviar via WhatsApp."""
    alertas = gerar_alertas_mastite()
    if not alertas:
        return ""

    linhas = ["🏥 **ALERTA DE MASTITE** — Saúde do Leite\n"]

    urgentes = [a for a in alertas if a['tipo'] == 'urgente']
    avisos = [a for a in alertas if a['tipo'] == 'aviso']

    if urgentes:
        linhas.append("🚨 **URGENTE:**")
        for a in urgentes[:3]:  # Max 3 urgentes
            linhas.append(f"  {a['animal_desc']}: {a['motivo']}")
            linhas.append(f"    └ {a['acao']}")

    if avisos:
        linhas.append("\n⚠️ **AVISO:**")
        for a in avisos[:2]:  # Max 2 avisos
            linhas.append(f"  {a['animal_desc']}: {a['motivo']}")

    linhas.append(f"\n📊 Total: {len(urgentes)} urgente(s), {len(avisos)} aviso(s)")
    return "\n".join(linhas)


def resumo_saude_leite() -> Dict:
    """Retorna resumo de saúde do leite para o painel."""
    alertas = gerar_alertas_mastite()
    df_leite = carregar_historico_ccs(dias=7)

    total_vacas_monitoradas = len(df_leite.get('ID Animal', []).dropna().unique()) if not df_leite.empty else 0

    return {
        "total_vacas": total_vacas_monitoradas,
        "alertas_urgentes": len([a for a in alertas if a['tipo'] == 'urgente']),
        "alertas_aviso": len([a for a in alertas if a['tipo'] == 'aviso']),
        "ccs_medio_semana": _calcular_media_ccs(df_leite),
        "alertas_detalhados": alertas[:10]  # Top 10
    }


def _calcular_media_ccs(df: pd.DataFrame) -> float:
    """Calcula CCS médio do dataframe."""
    if df.empty:
        return 0.0
    ccs_valores = []
    for _, row in df.iterrows():
        ccs = row.get('CCS', 0) or row.get('CCS (células/mL)', 0)
        if pd.notna(ccs):
            try:
                ccs_val = float(str(ccs).replace('.', '').replace(',', '.'))
                ccs_valores.append(ccs_val)
            except (ValueError, TypeError):
                pass

    return sum(ccs_valores) / len(ccs_valores) if ccs_valores else 0.0


if __name__ == '__main__':
    # Teste
    print("=== Resumo de Saúde do Leite ===")
    resumo = resumo_saude_leite()
    print(f"Vacas monitoradas: {resumo['total_vacas']}")
    print(f"Alertas urgentes: {resumo['alertas_urgentes']}")
    print(f"Alertas aviso: {resumo['alertas_aviso']}")
    print(f"CCS médio (7 dias): {resumo['ccs_medio_semana']:,.0f}")
    print("\n=== Alertas Detalhados ===")
    for a in resumo['alertas_detalhados'][:5]:
        print(f"  [{a['tipo'].upper()}] {a['animal_desc']}: {a['motivo']}")
