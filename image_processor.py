#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_processor.py — Processamento de imagens para detecção de perímetro animal.
"""
import cv2
import numpy as np
import logging

def processar_foto_animal(caminho_imagem):
    """
    Tenta detectar o perímetro de um animal na foto e retorna estimativas.
    Nota: Acurácia limitada em condições de campo.
    """
    try:
        img = cv2.imread(caminho_imagem)
        if img is None:
            logging.error(f"Não foi possível ler a imagem: {caminho_imagem}")
            return None

        # Processamento básico
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        # Encontrar contornos
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Pega o maior contorno (assumindo ser o animal)
        c = max(contours, key=cv2.contourArea)

        # Obtém a caixa delimitadora
        x, y, w, h = cv2.boundingRect(c)

        # Medidas estimadas (proporções simplificadas)
        # Em um cenário real, precisaríamos de uma referência de escala (ex: um objeto conhecido)
        return {
            'comprimento': float(w),
            'profundidade': float(h)
        }
    except Exception as e:
        logging.error(f"Erro no processamento de imagem: {e}")
        return None
