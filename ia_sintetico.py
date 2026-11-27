from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ia_sintetico.py — Generate 5k synthetic animal records for ML training.

Reproduces realistic distributions of births, deaths, treatments, and genetic
markers without leaking real farm data. Output compatible with ia_features.py.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import MEMBROS


def gerar_sintetico(n_animais=5000, anos=3, seed=42):
    """
    Generate n_animais synthetic animal records over anos years.

    Returns DataFrame with columns:
      animal_id, data_nascimento, sexo, dono, pai_id, mae_id, evento_tipo,
      evento_data, idade_dias_evento, status_vivo, peso_estimado_kg,
      num_tratamentos_90d, dias_desde_parto, iep_dias, ciclo_cio_dias,
      inbreeding_avk_pct, peso_ratio_esperado, num_parentes_mortos
    """
    np.random.seed(seed)

    hoje = agora()
    dias_historico = anos * 365

    # Generate base animals
    animais = []
    for i in range(n_animais):
        animal_id = f"A{i:04d}"

        # Birth date: uniform over history
        dias_desde_nascimento = np.random.randint(30, dias_historico + 365)
        data_nascimento = hoje - timedelta(days=dias_desde_nascimento)

        # Sex: 55% F, 45% M
        sexo = np.random.choice(['F', 'M'], p=[0.55, 0.45])

        # Owner: random member
        dono = np.random.choice(MEMBROS)

        # Pedigree: 80% known parents
        if np.random.random() < 0.80:
            pai_id = f"A{np.random.randint(0, n_animais):04d}"
            mae_id = f"A{np.random.randint(0, n_animais):04d}"
        else:
            pai_id = None
            mae_id = None

        # Event date: within history
        evento_data = hoje - timedelta(days=np.random.randint(0, dias_historico))

        # Age at event
        idade_dias_evento = (evento_data - data_nascimento).days
        if idade_dias_evento < 0:
            idade_dias_evento = 0

        # Weight estimate: 200-450kg (Gaussian centered at 350)
        peso_estimado_kg = np.random.normal(350, 50)
        peso_estimado_kg = max(150, min(550, peso_estimado_kg))

        # Treatments in last 90d
        num_tratamentos_90d = np.random.poisson(0.5)

        # Inbreeding (AVK simple heuristic): 0-30% in synthetic
        inbreeding_avk_pct = np.random.uniform(0, 0.25)

        # Event type: weighted (6% morte ≈ 2%/year over 3 years)
        # A morte DEPENDE dos fatores de risco — se for sorteada solta, o modelo
        # não tem sinal nenhum para aprender (era o que acontecia: acurácia 24%).
        # Idade HOJE (não na data do evento): é o que ia_features.extrair_features
        # calcula a partir de Nascimento. Usar a idade do evento aqui e a de hoje
        # lá deixava o sinal fraco (AUC ~0.60 mesmo com risco bem separado).
        idade_norm = min(max(0, dias_desde_nascimento) / (dias_historico + 365), 1.0)
        inb_norm = min(inbreeding_avk_pct / 0.25, 1.0)
        trat_norm = min(num_tratamentos_90d / 3.0, 1.0)
        peso_norm = max(0.0, 1.0 - peso_estimado_kg / 350.0)
        risco = (0.35 * idade_norm + 0.25 * inb_norm
                 + 0.20 * trat_norm + 0.20 * peso_norm)

        # Base alta + curva: sem isso quase ninguém morre, o modelo só acerta a
        # classe majoritária e o AUC fica em ~0.55 (chute).
        morreu = np.random.random() < (0.02 + 0.45 * risco ** 2)
        if morreu:
            evento_tipo = 'MORTE'
        else:
            evento_tipo = np.random.choice(
                ['VIVO', 'PARTO', 'TRATAMENTO'], p=[0.68, 0.16, 0.16])

        # Status
        status_vivo = 'Vivo' if evento_tipo != 'MORTE' else 'Morto'

        # Days since last birth (fêmeas only)
        if sexo == 'F':
            dias_desde_parto = np.random.randint(0, 400)
        else:
            dias_desde_parto = None

        # Interval between births (IEP): fêmeas 21-85 days avg
        if sexo == 'F' and evento_tipo == 'PARTO':
            iep_dias = int(np.random.normal(50, 12))
            iep_dias = max(21, min(120, iep_dias))
        else:
            iep_dias = None

        # Estrus cycle: ~21 days for cattle. Varia com inbreeding e idade —
        # sorteado solto daria R²=0 (nenhum modelo aprende ruído puro).
        ciclo_cio_dias = int(round(21 + 6 * inb_norm - 3 * idade_norm
                                   + np.random.normal(0, 1.5)))
        ciclo_cio_dias = max(17, min(25, ciclo_cio_dias))

        # Dias até o PRÓXIMO cio: alvo do modelo, distinto do ciclo observado
        # (se o alvo fosse o próprio ciclo, a feature homônima seria vazamento).
        # Depende de fatores que o extrator também enxerga — senão não há o que aprender.
        dias_ate_cio = int(round(10 + 8 * inb_norm - 3 * idade_norm
                                 + np.random.normal(0, 2.0)))
        dias_ate_cio = max(1, min(25, dias_ate_cio))

        # Weight ratio to expected
        peso_ratio_esperado = peso_estimado_kg / 350.0

        # Dead relatives (Poisson)
        num_parentes_mortos = np.random.poisson(0.3)

        animais.append({
            'animal_id': animal_id,
            'data_nascimento': data_nascimento.strftime('%d/%m/%Y'),
            'sexo': sexo,
            'dono': dono,
            'pai_id': pai_id,
            'mae_id': mae_id,
            'evento_tipo': evento_tipo,
            'evento_data': evento_data.strftime('%d/%m/%Y'),
            'idade_dias_evento': idade_dias_evento,
            'status_vivo': status_vivo,
            'peso_estimado_kg': peso_estimado_kg,
            'num_tratamentos_90d': num_tratamentos_90d,
            'dias_desde_parto': dias_desde_parto,
            'iep_dias': iep_dias,
            'ciclo_cio_dias': ciclo_cio_dias,
            'dias_ate_cio': dias_ate_cio,
            'inbreeding_avk_pct': inbreeding_avk_pct,
            'peso_ratio_esperado': peso_ratio_esperado,
            'num_parentes_mortos': num_parentes_mortos,
        })

    df = pd.DataFrame(animais)

    # Log distribution stats
    mortes = (df['evento_tipo'] == 'MORTE').sum()
    taxa_anual = mortes / n_animais / anos if anos > 0 else 0
    print(f"✅ Synthetic: {n_animais} animals, {anos} years")
    print(f"   Deaths: {mortes} ({taxa_anual*100:.1f}%/year)")
    print(f"   Partos: {(df['evento_tipo'] == 'PARTO').sum()}")
    print(f"   Avg inbreeding: {df['inbreeding_avk_pct'].mean():.2%}")

    return df
