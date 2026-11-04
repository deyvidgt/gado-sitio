#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/train_ia_modelos.py — Standalone ML training pipeline.

Generates 5k synthetic animals, extracts 25 features, trains 3 models,
serializes to pkl files for production use.

Usage:
    python scripts/train_ia_modelos.py [--n-animais 5000] [--anos 3] [--output data/ia_models]
"""

import sys
import os
import pickle
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Add parent directory to path so we can import ia_sintetico, etc.
sys.path.insert(0, str(Path(__file__).parent.parent))

from ia_sintetico import gerar_sintetico
from ia_features import extrair_features
from ia_modelos import ModeloMorte, ModeloCio


def main():
    parser = argparse.ArgumentParser(description="Train ML models on synthetic cattle data")
    parser.add_argument("--n-animais", type=int, default=5000, help="Number of synthetic animals")
    parser.add_argument("--anos", type=int, default=3, help="Years of history to generate")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "ia_models",
        help="Output directory for pkl files",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"🤖 Treinamento IA Preditiva — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*70}\n")

    # ========== STEP 1: Generate synthetic data ==========
    print(f"📊 Step 1: Gerando {args.n_animais} animais sintéticos ({args.anos} anos)...")
    df_sintetico = gerar_sintetico(n_animais=args.n_animais, anos=args.anos, seed=args.seed)
    print(f"   ✅ Gerado: {len(df_sintetico)} registros\n")

    # ========== STEP 2: Extract features ==========
    print(f"🔧 Step 2: Extraindo 25 features por animal...")
    features_list = []
    labels_morte = []
    labels_cio = []

    for idx, row in df_sintetico.iterrows():
        animal_id = row['animal_id']

        # Extract features
        features = extrair_features(animal_id, df_sintetico, pd.DataFrame(), pd.DataFrame())
        if features is None:
            continue

        features_list.append(features)

        # Label for morte model: 1 if evento_tipo == 'MORTE', else 0
        labels_morte.append(1 if row['evento_tipo'] == 'MORTE' else 0)

        # Label for cio model: dias até o PRÓXIMO cio (alvo próprio, não o ciclo —
        # usar o ciclo daria vazamento, pois a feature ciclo_cio_dias_norm é o mesmo número)
        ciclo_dias = row.get('dias_ate_cio', 21)
        ciclo_dias = max(1, min(25, ciclo_dias))
        labels_cio.append(ciclo_dias)

        if (idx + 1) % 500 == 0:
            print(f"   ✓ {idx + 1}/{len(df_sintetico)} features extraídas")

    print(f"   ✅ Features extraídas: {len(features_list)}\n")

    # ========== STEP 3: Preprocess batch ==========
    print(f"⚙️  Step 3: Preparando batch ({len(features_list)} amostras)...")
    # Passa as features CRUAS para treinar(): ele ajusta o próprio scaler. Antes
    # passava dado já normalizado, então o modelo aprendia z-scores enquanto
    # prever() mandava valores crus — todas as previsões caíam numa faixa estreita.
    X_raw = pd.DataFrame(features_list)
    print(f"   ✅ {X_raw.shape[1]} features x {X_raw.shape[0]} amostras\n")

    # Holdout 80/20: medir no próprio treino sempre dá ~99% e não prova nada.
    # O modelo só presta se acertar em animal que ele nunca viu.
    from sklearn.model_selection import train_test_split
    idx_treino, idx_teste = train_test_split(
        np.arange(len(features_list)), test_size=0.2, random_state=42,
        stratify=np.array(labels_morte))

    # ========== STEP 4: Train ModeloMorte ==========
    print(f"🎯 Step 4: Treinando ModeloMorte (RandomForest)...")
    modelo_morte = ModeloMorte()
    y_morte = np.array(labels_morte)
    modelo_morte.treinar(X_raw.values[idx_treino], y_morte[idx_treino])
    # Limiares pelos percentis do HOLDOUT: no treino as probabilidades saem
    # otimistas (o modelo já viu aquele animal) e o corte ficava acima do que
    # um animal novo alcança — URGENTE nunca disparava em produção.
    X_teste_raw = X_raw.values[idx_teste]
    lim_urg, lim_avi = modelo_morte.calibrar_limiares(X_teste_raw)

    # Evaluate on holdout
    from sklearn.metrics import roc_auc_score
    X_teste = modelo_morte.scaler.transform(X_teste_raw)
    prob_teste = modelo_morte.modelo.predict_proba(X_teste)[:, 1]
    acc_morte = modelo_morte.modelo.score(X_teste, y_morte[idx_teste])
    auc_morte = roc_auc_score(y_morte[idx_teste], prob_teste)
    print(f"   ✅ Acurácia (holdout): {acc_morte:.1%} | AUC: {auc_morte:.3f} (0.5 = chute)")
    print(f"   Limiares calibrados: urgente>{lim_urg:.2f} | aviso>{lim_avi:.2f}")
    print(f"   Feature importances (top 3):")
    top_features = np.argsort(modelo_morte.modelo.feature_importances_)[-3:][::-1]
    for i, feat_idx in enumerate(top_features):
        print(f"      {i+1}. {list(features_list[0].keys())[feat_idx]}: {modelo_morte.modelo.feature_importances_[feat_idx]:.3f}")
    print()

    # ========== STEP 5: Train ModeloCio ==========
    print(f"🎯 Step 5: Treinando ModeloCio (GradientBoosting)...")
    modelo_cio = ModeloCio()
    y_cio = np.array(labels_cio)
    modelo_cio.treinar(X_raw.values[idx_treino], y_cio[idx_treino])

    # Evaluate on holdout
    X_teste_cio = modelo_cio.scaler.transform(X_teste_raw)
    r2_cio = modelo_cio.modelo.score(X_teste_cio, y_cio[idx_teste])
    print(f"   ✅ R² score (holdout): {r2_cio:.3f}")
    print(f"   Feature importances (top 3):")
    top_features = np.argsort(modelo_cio.modelo.feature_importances_)[-3:][::-1]
    for i, feat_idx in enumerate(top_features):
        print(f"      {i+1}. {list(features_list[0].keys())[feat_idx]}: {modelo_cio.modelo.feature_importances_[feat_idx]:.3f}")
    print()

    # ========== STEP 6: Save models ==========
    print(f"💾 Step 6: Salvando modelos em {output_dir}...")

    with open(output_dir / "modelo_morte.pkl", "wb") as f:
        pickle.dump(modelo_morte, f)
    print(f"   ✅ modelo_morte.pkl ({(output_dir / 'modelo_morte.pkl').stat().st_size / 1024:.1f} KB)")

    with open(output_dir / "modelo_cio.pkl", "wb") as f:
        pickle.dump(modelo_cio, f)
    print(f"   ✅ modelo_cio.pkl ({(output_dir / 'modelo_cio.pkl').stat().st_size / 1024:.1f} KB)")

    # Ninguém lê este arquivo (cada modelo carrega o próprio scaler); fica só
    # porque o pipeline já o gerava e pode haver script externo esperando.
    with open(output_dir / "scaler.pkl", "wb") as f:
        pickle.dump(modelo_morte.scaler, f)
    print(f"   ✅ scaler.pkl ({(output_dir / 'scaler.pkl').stat().st_size / 1024:.1f} KB)")

    # ========== STEP 7: Summary ==========
    print(f"\n{'='*70}")
    print(f"✅ TREINAMENTO COMPLETO")
    print(f"{'='*70}")
    print(f"  Animais sintéticos: {len(df_sintetico)}")
    print(f"  Features extraídas: {len(features_list)}")
    print(f"  ModeloMorte acurácia: {acc_morte:.1%} (holdout) | AUC: {auc_morte:.3f}")
    print(f"  ModeloCio R² score: {r2_cio:.3f} (holdout)")
    print(f"  Output: {output_dir.resolve()}")
    print(f"  Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")


if __name__ == "__main__":
    main()
