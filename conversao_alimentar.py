#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conversao_alimentar.py — Eficiência nutritiva e conversão alimentar (v5.10 Onda 5)

Rastreia consumo real de ração vs. ganho de peso por animal/lote.
Calcula: kg ração consumida / kg ganho = conversão alimentar (ideal: 5-8 para corte, 1.2-1.5 para leite).
Detecta desperdício (>15%) e sugere otimizações.
"""
import pandas as pd
import math
from datetime import date, datetime, timedelta


def _hoje_br():
    """Hoje no fuso de Brasília (o servidor pode estar em UTC)."""
    try:
        from extensions import _agora
        return _agora().date()
    except Exception:
        return date.today()
from typing import Dict, List, Tuple, Optional

import animais
import pesagem


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


# Padrões de conversão alimentar por categoria (kg ração / kg ganho)
CONVERSAO_PADRAO = {
    "bezerro": 4.5,      # Animais até 6 meses
    "novilha": 6.0,      # Fêmeas em crescimento
    "boi": 6.5,          # Machos em engorda
    "vaca": 1.3,         # Lactação (kg MS / kg leite)
    "vaca_seca": 8.0,    # Vaca seca em repouso
    "touro": 7.0,        # Reprodutor
    "default": 6.5
}

# Limites de alerta (% acima do padrão)
LIMITE_AVISO = 10       # 10% acima
LIMITE_CRITICO = 20     # 20% acima


def obter_historico_consumo(animal_id: str, dias: int = 60) -> Dict:
    """
    Retorna histórico de consumo de ração para um animal nos últimos N dias.

    Busca registros da aba 'Manejo' com tipo 'Alimentação' e brinco do animal.
    Formato esperado: 'Descrição' contém "kg" ou valor numérico.
    """
    try:
        from db import carregar_aba
        df_manejo = carregar_aba('Manejo')

        if df_manejo is None or df_manejo.empty:
            return {"animal_id": animal_id, "registros": [], "consumo_total_kg": 0}

        # Filtra por data (últimos N dias)
        data_limite = _hoje_br() - timedelta(days=dias)
        df_manejo['_data'] = df_manejo.get('Data', '').apply(_data)
        df_filtro = df_manejo[df_manejo['_data'].notna()]
        df_filtro = df_filtro[df_filtro['_data'] >= data_limite]

        # Busca registros de alimentação para este animal
        registros = []
        consumo_total = 0

        for _, row in df_filtro.iterrows():
            brinco = str(row.get('Brincos', '')).strip()
            tipo = str(row.get('Tipo', '')).strip().lower()

            if 'alimentação' not in tipo:
                continue

            if animal_id not in brinco:
                continue

            # Extrai quantidade de ração da descrição
            desc = str(row.get('Descrição', ''))
            qtd_kg = _numero(desc)

            if qtd_kg is None or qtd_kg <= 0:
                # Tenta extrair da coluna de quantidade (se houver)
                qtd_kg = _numero(row.get('Qtd Sacos')) or _numero(row.get('Quantidade'))

            if qtd_kg and qtd_kg > 0:
                registros.append({
                    "data": row.get('_data'),
                    "quantidade_kg": qtd_kg,
                    "tipo": "Consumo",
                    "observacoes": desc[:50]
                })
                consumo_total += qtd_kg

        return {
            "animal_id": animal_id,
            "periodo_dias": dias,
            "registros": registros,
            "consumo_total_kg": round(consumo_total, 2),
            "consumo_medio_dia": round(consumo_total / dias, 3) if dias > 0 else 0
        }
    except Exception as e:
        print(f"Erro ao obter histórico de consumo: {e}")
        return {"animal_id": animal_id, "registros": [], "consumo_total_kg": 0}


def obter_ganho_peso(animal_id: str, dias: int = 60) -> Dict:
    """
    Retorna ganho de peso para um animal nos últimos N dias.

    Usa última pesagem (peso atual) menos peso há N dias atrás.
    Se não houver histórico, retorna 0.
    """
    try:
        # Obtém histórico de pesagens
        from db import carregar_aba
        df_man = carregar_aba('Manejo')

        if df_man is None or df_man.empty:
            return {
                "animal_id": animal_id,
                "periodo_dias": dias,
                "peso_inicial_kg": None,
                "peso_final_kg": None,
                "ganho_kg": 0,
                "ganho_dia_kg": 0,
                "dias_com_dados": 0
            }

        historico = pesagem.todas(df_man)

        if not historico:
            return {
                "animal_id": animal_id,
                "periodo_dias": dias,
                "peso_inicial_kg": None,
                "peso_final_kg": None,
                "ganho_kg": 0,
                "ganho_dia_kg": 0,
                "dias_com_dados": 0
            }

        # Filtra por animal
        registros_animal = []
        for item in historico:
            if item.get('animal_id') == animal_id:
                registros_animal.append(item)

        if not registros_animal:
            return {
                "animal_id": animal_id,
                "periodo_dias": dias,
                "peso_inicial_kg": None,
                "peso_final_kg": None,
                "ganho_kg": 0,
                "ganho_dia_kg": 0,
                "dias_com_dados": 0
            }

        # Ordena por data
        registros_animal.sort(key=lambda x: x.get('data', date.min))

        # Peso final (mais recente) e inicial (há N dias)
        peso_final = registros_animal[-1].get('peso_kg')
        data_limite = _hoje_br() - timedelta(days=dias)

        peso_inicial = None
        for item in registros_animal:
            if item.get('data') >= data_limite:
                peso_inicial = item.get('peso_kg')
                break

        if peso_inicial is None and registros_animal:
            peso_inicial = registros_animal[0].get('peso_kg')

        ganho = 0
        ganho_dia = 0
        dias_com_dados = 0

        if peso_inicial and peso_final:
            ganho = peso_final - peso_inicial
            if ganho > 0:
                # Calcula dias entre primeiro e último registro
                primeiro = registros_animal[0].get('data', _hoje_br())
                ultimo = registros_animal[-1].get('data', _hoje_br())
                dias_com_dados = (ultimo - primeiro).days + 1
                ganho_dia = ganho / dias_com_dados if dias_com_dados > 0 else 0

        return {
            "animal_id": animal_id,
            "periodo_dias": dias,
            "peso_inicial_kg": round(peso_inicial, 1) if peso_inicial else None,
            "peso_final_kg": round(peso_final, 1) if peso_final else None,
            "ganho_kg": round(ganho, 2),
            "ganho_dia_kg": round(ganho_dia, 3),
            "dias_com_dados": dias_com_dados,
            "registros": len(registros_animal)
        }
    except Exception as e:
        print(f"Erro ao obter ganho de peso: {e}")
        return {
            "animal_id": animal_id,
            "periodo_dias": dias,
            "peso_inicial_kg": None,
            "peso_final_kg": None,
            "ganho_kg": 0,
            "ganho_dia_kg": 0,
            "dias_com_dados": 0
        }


def calcular_conversao_alimentar(animal_id: str, dias: int = 60) -> Dict:
    """
    Calcula conversão alimentar: kg ração consumida / kg ganho de peso.

    Para vacas leiteiras: kg ração / kg leite (mais relevante).
    Para corte: kg ração / kg ganho de peso corporal.
    """
    consumo = obter_historico_consumo(animal_id, dias)
    ganho = obter_ganho_peso(animal_id, dias)

    # Determina categoria do animal
    try:
        df_animais = animais.carregar()
        animal = df_animais[df_animais['ID'].astype(str) == str(animal_id)]

        if animal.empty:
            categoria = "default"
        else:
            categoria = str(animal.iloc[0].get('Categoria', 'default')).lower()
            if 'vaca' in categoria and 'seca' in categoria:
                categoria = 'vaca_seca'
            elif 'vaca' in categoria:
                categoria = 'vaca'
            elif 'boi' in categoria or 'novilho' in categoria:
                categoria = 'boi'
            elif 'novilha' in categoria or 'fêmea' in categoria:
                categoria = 'novilha'
            elif 'bezerro' in categoria:
                categoria = 'bezerro'
            elif 'touro' in categoria:
                categoria = 'touro'
            else:
                categoria = 'default'
    except:
        categoria = 'default'

    padraoconv = CONVERSAO_PADRAO.get(categoria, CONVERSAO_PADRAO['default'])

    consumo_kg = consumo.get('consumo_total_kg', 0)
    ganho_kg = ganho.get('ganho_kg', 0)

    conversao = None
    desvio_percent = None
    tipo_alerta = None
    motivo = ""

    if ganho_kg > 0.5:  # Ganho significativo
        conversao = round(consumo_kg / ganho_kg, 2)
        desvio = ((conversao - padraoconv) / padraoconv) * 100
        desvio_percent = round(desvio, 1)

        if desvio > LIMITE_CRITICO:
            tipo_alerta = "critico"
            motivo = f"Conversão {conversao:.2f} está {desvio_percent:.1f}% ACIMA do padrão ({padraoconv})"
        elif desvio > LIMITE_AVISO:
            tipo_alerta = "aviso"
            motivo = f"Conversão {conversao:.2f} está {desvio_percent:.1f}% acima do padrão ({padraoconv})"
        else:
            tipo_alerta = "ok"
            motivo = f"Conversão {conversao:.2f} dentro do esperado (padrão: {padraoconv})"

    return {
        "animal_id": animal_id,
        "categoria": categoria,
        "periodo_dias": dias,
        "consumo_total_kg": consumo.get('consumo_total_kg', 0),
        "consumo_medio_dia_kg": consumo.get('consumo_medio_dia', 0),
        "ganho_total_kg": ganho.get('ganho_kg', 0),
        "ganho_dia_kg": ganho.get('ganho_dia_kg', 0),
        "peso_inicial_kg": ganho.get('peso_inicial_kg'),
        "peso_final_kg": ganho.get('peso_final_kg'),
        "conversao_alimentar": conversao,
        "padrao_conversao": padraoconv,
        "desvio_percent": desvio_percent,
        "tipo_alerta": tipo_alerta,
        "motivo": motivo,
        "dias_com_dados": ganho.get('dias_com_dados', 0),
        "registros_consumo": len(consumo.get('registros', []))
    }


def gerar_alertas_conversao() -> List[Dict]:
    """Gera alertas de conversão alimentar inadequada para todos os animais."""
    alertas = []

    try:
        df_animais = animais.carregar()

        if df_animais is None or df_animais.empty:
            return alertas

        for _, animal in df_animais.iterrows():
            animal_id = str(animal.get('ID', '')).strip()
            if not animal_id:
                continue

            resultado = calcular_conversao_alimentar(animal_id)

            if resultado['tipo_alerta'] in ['aviso', 'critico']:
                brinco = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}"
                alertas.append({
                    "animal_id": animal_id,
                    "brinco": brinco,
                    "categoria": resultado['categoria'],
                    "conversao": resultado['conversao_alimentar'],
                    "padrao": resultado['padrao_conversao'],
                    "desvio_percent": resultado['desvio_percent'],
                    "tipo": resultado['tipo_alerta'],
                    "motivo": resultado['motivo'],
                    "recomendacao": _recomendacao_conversao(resultado)
                })
    except Exception as e:
        print(f"Erro ao gerar alertas de conversão: {e}")

    alertas.sort(key=lambda a: -(a.get('desvio_percent', 0)))
    return alertas


def _recomendacao_conversao(resultado: Dict) -> str:
    """Sugere ações baseadas em conversão inadequada."""
    categoria = resultado.get('categoria', 'default')
    conversao = resultado.get('conversao_alimentar')

    if conversao is None:
        return "Insuficientes dados de consumo e ganho de peso"

    if categoria == 'vaca':
        return "Revisar qualidade do concentrado, higiene da ordenha e CCS. Verificar mastite."
    elif 'boi' in categoria or 'novilha' in categoria:
        return "Aumentar qualidade de forragem, verificar parasitas e calcular ração balanciada"
    elif 'bezerro' in categoria:
        return "Revisar qualidade do leite/colostro e concentrado inicial"
    else:
        return "Revisar consumo de ração e qualidade de forragem disponível"


def resumo_conversao_alimentar() -> Dict:
    """Retorna resumo consolidado de eficiência alimentar do rebanho."""
    try:
        df_animais = animais.carregar()

        if df_animais is None or df_animais.empty:
            return {
                "total_animais": 0,
                "animais_com_dados": 0,
                "conversao_media": 0.0,
                "animais_ok": 0,
                "animais_aviso": 0,
                "animais_criticos": 0,
                "consumo_total_kg": 0,
                "ganho_total_kg": 0,
                "eficiencia_rebanho_percent": 0
            }

        alertas = gerar_alertas_conversao()

        total_animais = len(df_animais)
        consumo_total = 0
        ganho_total = 0
        conversoes = []

        for _, animal in df_animais.iterrows():
            animal_id = str(animal.get('ID', '')).strip()
            if not animal_id:
                continue

            resultado = calcular_conversao_alimentar(animal_id)
            consumo_total += resultado.get('consumo_total_kg', 0)
            ganho_total += resultado.get('ganho_total_kg', 0)

            conversoes.append(resultado.get('conversao_alimentar'))

        serie_conversoes = pd.to_numeric(
            pd.Series(conversoes, dtype="object"), errors="coerce"
        )
        serie_conversoes = serie_conversoes[serie_conversoes.map(math.isfinite)]
        conversao_media = (
            round(float(serie_conversoes.mean()), 2)
            if not serie_conversoes.empty else 0.0
        )

        return {
            "total_animais": total_animais,
            "animais_com_dados": len(conversoes),
            "conversao_media": conversao_media,
            "animais_ok": len([a for a in alertas if a['tipo'] == 'ok']),
            "animais_aviso": len([a for a in alertas if a['tipo'] == 'aviso']),
            "animais_criticos": len([a for a in alertas if a['tipo'] == 'critico']),
            "consumo_total_kg": round(consumo_total, 2),
            "ganho_total_kg": round(ganho_total, 2),
            "eficiencia_rebanho_percent": round(100 - ((sum([a['desvio_percent'] for a in alertas]) / len(alertas)) if alertas else 0), 1)
        }
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return {
            "total_animais": 0,
            "animais_com_dados": 0,
            "conversao_media": 0.0,
            "animais_ok": 0,
            "animais_aviso": 0,
            "animais_criticos": 0,
            "consumo_total_kg": 0,
            "ganho_total_kg": 0,
            "eficiencia_rebanho_percent": 0
        }


if __name__ == '__main__':
    print("\n=== Conversao Alimentar ===")
    resumo = resumo_conversao_alimentar()
    print(f"Total de animais: {resumo['total_animais']}")
    print(f"Conversao media: {resumo['conversao_media']}")
    print(f"Animais em alerta: {resumo['animais_aviso'] + resumo['animais_criticos']}")
