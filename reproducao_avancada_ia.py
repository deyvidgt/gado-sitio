from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproducao_avancada.py — Add alertas_ia_preditiva() function for Onda 19
"""

import pandas as pd
import pickle
import logging
from pathlib import Path
from datetime import datetime
from ia_features import extrair_features
from ia_modelos import calcular_inbreeding_avk

logger = logging.getLogger(__name__)

# Modelos ficam ao lado do código, não no cwd (o app roda de qualquer pasta).
MODELOS_DIR = Path(__file__).parent / "data" / "ia_models"


def _ref_animal(animal):
    """Nome curto do animal: 'Amarelo 21 #A0003' (colunas reais da aba Animais)."""
    cor = str(animal.get('Brinco Cor') or '').strip()
    num = str(animal.get('Brinco Nº') or '').strip()
    aid = str(animal.get('ID') or animal.get('animal_id') or '').strip()
    base = f"{cor} {num}".strip()
    return f"{base} #{aid}".strip() if aid else (base or "animal")


def alertas_ia_preditiva(df_animais, df_manejo, df_compras, df_vendas, hoje=None):
    """
    Orquestra 3 modelos preditivos → alertas consolidados.

    Returns:
        {urgentes: [...], avisos: [...], total: int, timestamp: str}
    """
    hoje = pd.Timestamp(hoje or agora()).normalize()

    # Carrega modelos (com fallback automático para retreino se houver incompatibilidade de versão do scikit-learn)
    try:
        with open(MODELOS_DIR / 'modelo_morte.pkl', 'rb') as f:
            modelo_morte = pickle.load(f)
        with open(MODELOS_DIR / 'modelo_cio.pkl', 'rb') as f:
            modelo_cio = pickle.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao carregar modelos IA ({e}). Retreinando automaticamente...")
        try:
            import subprocess
            import sys
            script_path = Path(__file__).parent / "scripts" / "train_ia_modelos.py"
            python_exe = sys.executable
            if "uwsgi" in python_exe.lower() or not Path(python_exe).exists():
                virtual_env = os.environ.get("VIRTUAL_ENV")
                if virtual_env:
                    python_exe = str(Path(virtual_env) / "bin" / "python")
                else:
                    python_exe = "python3"
            elif os.name != "nt":
                virtual_env = os.environ.get("VIRTUAL_ENV")
                if virtual_env and Path(virtual_env, "bin", "python").exists():
                    python_exe = str(Path(virtual_env, "bin", "python"))
            subprocess.run([python_exe, str(script_path), "--n-animais", "200"], check=True, capture_output=True)
            with open(MODELOS_DIR / 'modelo_morte.pkl', 'rb') as f:
                modelo_morte = pickle.load(f)
            with open(MODELOS_DIR / 'modelo_cio.pkl', 'rb') as f:
                modelo_cio = pickle.load(f)
        except Exception as e2:
            logger.error(f"❌ Falha no retreino automático dos modelos IA: {e2}")
            return {"urgentes": [], "avisos": [], "total": 0, "timestamp": hoje.isoformat()}

    alertas_urgentes = []
    alertas_avisos = []

    # Itera animais vivos (Status vazio/NaN = vivo, como no resto do app)
    # Sem coluna de ID não há como ligar features/histórico: não inventa alerta.
    id_col = next((c for c in ('animal_id', 'ID') if c in df_animais.columns), None)
    if id_col is None:
        return {"urgentes": [], "avisos": [], "total": 0, "timestamp": hoje.isoformat()}
    status = df_animais.get('Status')
    if status is None:
        animais_vivos = df_animais
    else:
        vivo = status.isna() | status.astype(str).str.strip().str.lower().isin(['', 'vivo', 'nan', 'none'])
        animais_vivos = df_animais[vivo]

    for _, animal in animais_vivos.iterrows():
        animal_id = animal[id_col]
        ref_animal = _ref_animal(animal)

        # Features uma vez por animal (usadas por morte e cio)
        features = None
        try:
            features = extrair_features(animal_id, df_animais, df_manejo, df_vendas, hoje)
        except Exception as e:
            logger.debug(f"Erro ao extrair features de {animal_id}: {e}")

        # MORTE (todos os animais)
        if features:
            try:
                pred_morte = modelo_morte.prever(features)

                if pred_morte['urgencia'] == 'URGENTE':
                    alertas_urgentes.append({
                        "tipo": "🚨 MORTE PREVISTA",
                        "animal": ref_animal,
                        "prob": pred_morte['prob_morte'],
                        "motivos": pred_morte['motivos'],
                        "acao": pred_morte['acao'],
                        "prioridade": 1,
                    })
                elif pred_morte['urgencia'] == 'AVISO':
                    alertas_avisos.append({
                        "tipo": "⚠️ RISCO MORTE",
                        "animal": ref_animal,
                        "prob": pred_morte['prob_morte'],
                        "prioridade": 3,
                    })
            except Exception as e:
                logger.debug(f"Erro ao prever morte {animal_id}: {e}")

        # CIO (fêmeas)
        if features and str(animal.get('Sexo', 'M')).upper().startswith('F'):
            try:
                pred_cio = modelo_cio.prever(features)

                if pred_cio['alertar']:
                    alertas_urgentes.append({
                        "tipo": "🔥 CIO EM",
                        "animal": ref_animal,
                        "dias": pred_cio['dias_ate_cio'],
                        "data": pred_cio['data_prevista'],
                        "confianca": pred_cio['confianca'],
                        "acao": f"INSEMINAR EM {pred_cio['dias_ate_cio'] - 1} DIAS",
                        "prioridade": 2,
                    })
            except Exception as e:
                logger.debug(f"Erro ao prever cio {animal_id}: {e}")

        # INBREEDING (todos)
        try:
            avk = calcular_inbreeding_avk(animal_id, df_animais)

            if avk > 0.15:
                alertas_avisos.append({
                    "tipo": "⚠️ INBREEDING CRÍTICO",
                    "animal": ref_animal,
                    "avk": round(avk * 100, 1),
                    "acao": "🚫 NÃO CRUZAR COM PARENTES PRÓXIMOS",
                    "prioridade": 3,
                })
            elif avk > 0.10:
                alertas_avisos.append({
                    "tipo": "⚠️ INBREEDING ALTO",
                    "animal": ref_animal,
                    "avk": round(avk * 100, 1),
                    "acao": "Considerar cruzamento com genética externa",
                    "prioridade": 4,
                })
        except Exception as e:
            logger.debug(f"Erro ao calcular inbreeding {animal_id}: {e}")

    # Ordena por prioridade
    alertas_urgentes.sort(key=lambda x: x.get('prioridade', 99))
    alertas_avisos.sort(key=lambda x: x.get('prioridade', 99))

    return {
        "urgentes": alertas_urgentes,
        "avisos": alertas_avisos,
        "total": len(alertas_urgentes) + len(alertas_avisos),
        "timestamp": hoje.isoformat(),
    }
