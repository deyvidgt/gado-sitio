#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pastos_ocupacao.py — Lotação dinâmica e períodos de ocupação/descanso (v5.10 Onda 6)

Aprimora cálculos de UA/ha com:
- Períodos de ocupação e descanso por pasto
- Alertas de sobrelotação
- Recomendações de rotação
- Capacidade de carga por tipo de pasto
"""
import pandas as pd
from datetime import date, datetime, timedelta


def _hoje_br():
    """Hoje no fuso de Brasília (o servidor pode estar em UTC)."""
    try:
        from extensions import _agora
        return _agora().date()
    except Exception:
        return date.today()
from typing import Dict, List, Optional

import pastos


def _data(valor):
    """Normaliza datas."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip()[:10]
    formato = "%Y-%m-%d" if texto[4:5] == "-" else "%d/%m/%Y"
    try:
        return datetime.strptime(texto, formato).date()
    except ValueError:
        return None


def _numero(valor):
    """Normaliza números."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


# Capacidades padrão de lotação por tipo de pasto (UA/ha)
CAPACIDADE_PADRAO = {
    "brachiaria": 3.0,      # Capim Braquiária
    "paspalum": 2.5,        # Capim Paspalum
    "coastcross": 3.5,      # Coastcross (intensivo)
    "tifton": 3.2,          # Tifton 85
    "mombaça": 3.5,         # Capim Mombaça
    "tanzânia": 3.0,        # Capim Tanzânia
    "grama_nativa": 1.5,    # Gramíneas nativas
    "default": 2.5          # Padrão conservador
}

# Períodos recomendados (dias)
DIAS_OCUPACAO_RECOMENDADO = 25  # Dias de ocupação ideal
DIAS_DESCANSO_RECOMENDADO = 35   # Dias de descanso ideal


def estimar_dias_ocupacao(pasto_id: str) -> Dict:
    """
    Estima dias de ocupação recomendados baseado na lotação atual.
    
    Fórmula: se a lotação atual é X% da capacidade, dias de ocupação = 25 * (capacidade/lotacao_atual)
    Assim, em lotação baixa dura mais; em lotação alta, menos dias.
    """
    try:
        situacao = pastos.situacao(pasto_id)
        
        if not situacao:
            return {
                "pasto_id": pasto_id,
                "dias_ocupacao_recomendado": DIAS_OCUPACAO_RECOMENDADO,
                "dias_descanso_recomendado": DIAS_DESCANSO_RECOMENDADO,
                "motivo": "Sem dados de lotação"
            }
        
        ua_ha_atual = situacao.get('ua_ha_atual', 0)
        capacidade_ua_ha = situacao.get('capacidade_ua_ha', CAPACIDADE_PADRAO['default'])
        
        if ua_ha_atual <= 0 or capacidade_ua_ha <= 0:
            return {
                "pasto_id": pasto_id,
                "dias_ocupacao_recomendado": DIAS_OCUPACAO_RECOMENDADO,
                "dias_descanso_recomendado": DIAS_DESCANSO_RECOMENDADO,
                "motivo": "Dados insuficientes de lotação"
            }
        
        # Calcula dias baseado na carga
        razao = capacidade_ua_ha / ua_ha_atual
        dias_ocupacao = max(10, min(35, DIAS_OCUPACAO_RECOMENDADO * razao))
        
        # Dias de descanso inversamente proporcional à lotação
        if ua_ha_atual >= capacidade_ua_ha:
            dias_descanso = 14  # Descanso curto se sobrelotado
        else:
            dias_descanso = min(45, DIAS_DESCANSO_RECOMENDADO * (1 / razao) if razao > 0 else 35)
        
        return {
            "pasto_id": pasto_id,
            "dias_ocupacao_recomendado": round(dias_ocupacao),
            "dias_descanso_recomendado": round(dias_descanso),
            "ua_ha_atual": round(ua_ha_atual, 2),
            "capacidade_ua_ha": capacidade_ua_ha,
            "taxa_ocupacao_percent": round((ua_ha_atual / capacidade_ua_ha) * 100, 1) if capacidade_ua_ha > 0 else 0
        }
    except Exception as e:
        print(f"Erro ao estimar dias de ocupação: {e}")
        return {
            "pasto_id": pasto_id,
            "dias_ocupacao_recomendado": DIAS_OCUPACAO_RECOMENDADO,
            "dias_descanso_recomendado": DIAS_DESCANSO_RECOMENDADO,
            "motivo": f"Erro: {str(e)[:50]}"
        }


def gerar_alertas_lotacao() -> List[Dict]:
    """Gera alertas de sobrelotação para todos os pastos."""
    alertas = []
    
    try:
        # Carrega dados de pastos
        from db import carregar_aba
        df_pastos = carregar_aba('Pastos')
        
        if df_pastos is None or df_pastos.empty:
            return alertas
        
        for _, pasto in df_pastos.iterrows():
            pasto_id = str(pasto.get('ID', '')).strip()
            if not pasto_id:
                continue
            
            situacao = pastos.situacao(pasto_id)
            
            if not situacao:
                continue
            
            ua_ha_atual = situacao.get('ua_ha_atual', 0)
            capacidade_ua_ha = situacao.get('capacidade_ua_ha', CAPACIDADE_PADRAO['default'])
            
            if ua_ha_atual <= 0 or capacidade_ua_ha <= 0:
                continue
            
            taxa_ocupacao = (ua_ha_atual / capacidade_ua_ha) * 100
            
            tipo_alerta = None
            motivo = ""
            recomendacao = ""
            
            if taxa_ocupacao > 120:
                tipo_alerta = "critico"
                motivo = f"Sobrelotado: {taxa_ocupacao:.1f}% da capacidade"
                recomendacao = "RETIRAR ANIMAIS COM URGENCIA - risco de degradação do pasto"
            elif taxa_ocupacao > 100:
                tipo_alerta = "aviso"
                motivo = f"Lotação acima da capacidade: {taxa_ocupacao:.1f}%"
                recomendacao = "Planejar movimentação de animais nos próximos dias"
            elif taxa_ocupacao > 85:
                tipo_alerta = "alerta"
                motivo = f"Lotação elevada: {taxa_ocupacao:.1f}% (quase na capacidade)"
                recomendacao = "Monitorar consumo de forragem; retirar se necessário"
            elif taxa_ocupacao < 30:
                tipo_alerta = "subutilizacao"
                motivo = f"Pasto subutilizado: {taxa_ocupacao:.1f}% da capacidade"
                recomendacao = "Oportunidade: aumentar rebanho ou consertar cobertura"
            
            if tipo_alerta:
                nome_pasto = pasto.get('Nome', f'Pasto {pasto_id}')
                alertas.append({
                    "pasto_id": pasto_id,
                    "nome_pasto": nome_pasto,
                    "ua_ha_atual": round(ua_ha_atual, 2),
                    "capacidade_ua_ha": capacidade_ua_ha,
                    "taxa_ocupacao_percent": round(taxa_ocupacao, 1),
                    "tipo": tipo_alerta,
                    "motivo": motivo,
                    "recomendacao": recomendacao,
                    "cabeças": situacao.get('cabeças', 0),
                    "dias": situacao.get('dias', 0),
                    "area_ha": situacao.get('area_ha', 0)
                })
    except Exception as e:
        print(f"Erro ao gerar alertas de lotação: {e}")
    
    # Ordena por severidade
    ordem_severidade = {'critico': 0, 'aviso': 1, 'alerta': 2, 'subutilizacao': 3}
    alertas.sort(key=lambda a: ordem_severidade.get(a['tipo'], 99))
    
    return alertas


def recomendar_rotacao(pasto_id: str) -> Dict:
    """
    Recomenda plano de rotação para um pasto baseado em lotação e capacidade.
    """
    try:
        estimativa = estimar_dias_ocupacao(pasto_id)
        situacao = pastos.situacao(pasto_id)
        
        if not situacao:
            return {
                "pasto_id": pasto_id,
                "recomendacao": "Dados insuficientes",
                "plano": []
            }
        
        dias_ocupacao = estimativa.get('dias_ocupacao_recomendado', DIAS_OCUPACAO_RECOMENDADO)
        dias_descanso = estimativa.get('dias_descanso_recomendado', DIAS_DESCANSO_RECOMENDADO)
        taxa_ocupacao = estimativa.get('taxa_ocupacao_percent', 0)
        
        plano = []
        data_inicio = _hoje_br()
        
        # Simula 3 ciclos de rotação
        for ciclo in range(3):
            if taxa_ocupacao > 100:
                status_ocupacao = "RETIRAR"
                dias = 1
            elif taxa_ocupacao > 85:
                status_ocupacao = "OCUPADO (reduzir dias)"
                dias = max(10, dias_ocupacao - 10)
            else:
                status_ocupacao = "OCUPADO"
                dias = dias_ocupacao
            
            data_fim = data_inicio + timedelta(days=dias)
            
            plano.append({
                "ciclo": ciclo + 1,
                "fase": "Ocupacao" if ciclo % 2 == 0 else "Descanso",
                "data_inicio": data_inicio.strftime("%d/%m/%Y"),
                "data_fim": data_fim.strftime("%d/%m/%Y"),
                "dias": dias,
                "status": status_ocupacao,
                "acao": _sugerir_acao(taxa_ocupacao, status_ocupacao)
            })
            
            data_inicio = data_fim
        
        return {
            "pasto_id": pasto_id,
            "taxa_ocupacao_atual_percent": round(taxa_ocupacao, 1),
            "dias_ciclo_total": dias_ocupacao + dias_descanso,
            "recomendacao": _recomendacao_rotacao(taxa_ocupacao),
            "plano": plano
        }
    except Exception as e:
        print(f"Erro ao recomendar rotação: {e}")
        return {
            "pasto_id": pasto_id,
            "recomendacao": f"Erro ao processar: {str(e)[:50]}",
            "plano": []
        }


def _sugerir_acao(taxa_ocupacao: float, status: str) -> str:
    """Sugere ação baseada na taxa de ocupação."""
    if taxa_ocupacao > 100:
        return "Retirar animais IMEDIATAMENTE"
    elif taxa_ocupacao > 85:
        return "Preparar para retirada; monitorar diariamente"
    elif taxa_ocupacao < 30:
        return "Aumentar rebanho neste pasto ou consertar cobertura"
    else:
        return "Manutenção normal; acompanhar consumo"


def _recomendacao_rotacao(taxa_ocupacao: float) -> str:
    """Gera recomendação de rotação baseada em taxa de ocupação."""
    if taxa_ocupacao > 120:
        return "EMERGENCIA: Sobrelotacao critica. Retirar 20%+ do rebanho HOJE"
    elif taxa_ocupacao > 100:
        return "Reduzir ciclo de ocupacao para 10-15 dias; aumentar descanso para 45+ dias"
    elif taxa_ocupacao > 85:
        return "Otimizado para producao. Manter ciclo atual; retirar se chover pouco"
    elif taxa_ocupacao > 70:
        return "Boa utilizacao. Considerar aumentar rebanho ou adicionar pasto"
    else:
        return "Pasto subutilizado. Aumentar rebanho ou usar para recuperacao"


def resumo_ocupacao_pastos() -> Dict:
    """Resumo consolidado de ocupação de todos os pastos."""
    try:
        alertas = gerar_alertas_lotacao()
        
        if not alertas:
            return {
                "total_pastos": 0,
                "pastos_ok": 0,
                "pastos_aviso": 0,
                "pastos_criticos": 0,
                "pastos_subutilizados": 0,
                "media_taxa_ocupacao": 0,
                "taxa_area_disponivel": 0
            }
        
        criticos = len([a for a in alertas if a['tipo'] == 'critico'])
        avisos = len([a for a in alertas if a['tipo'] == 'aviso'])
        alerta = len([a for a in alertas if a['tipo'] == 'alerta'])
        subutilizado = len([a for a in alertas if a['tipo'] == 'subutilizacao'])
        
        media_taxa = sum([a['taxa_ocupacao_percent'] for a in alertas]) / len(alertas) if alertas else 0
        area_total = sum([a.get('area_ha', 0) for a in alertas])
        
        return {
            "total_pastos": len(alertas),
            "pastos_ok": alerta,
            "pastos_aviso": avisos,
            "pastos_criticos": criticos,
            "pastos_subutilizados": subutilizado,
            "media_taxa_ocupacao_percent": round(media_taxa, 1),
            "area_total_ha": round(area_total, 1),
            "saude_rebanho": "CRITICA" if criticos > 0 else ("AVISO" if avisos > 0 else "OK")
        }
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return {
            "total_pastos": 0,
            "saude_rebanho": "DESCONHECIDO"
        }


if __name__ == '__main__':
    print("\n=== Ocupacao de Pastos ===")
    resumo = resumo_ocupacao_pastos()
    print(f"Total de pastos: {resumo.get('total_pastos')}")
    print(f"Saude do rebanho: {resumo.get('saude_rebanho')}")
    print(f"Taxa media de ocupacao: {resumo.get('media_taxa_ocupacao_percent')}%")
