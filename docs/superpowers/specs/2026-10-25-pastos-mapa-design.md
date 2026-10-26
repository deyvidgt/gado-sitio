# Pastos com mapa — design

**Status:** em implementação · **Data:** 2026-10-25 · **Versão alvo:** 5.2

## Objetivo

Separar o sítio em pastos desenhados no mapa de satélite (como o AgriWebb dos exemplos):
área em hectares, onde o gado está, há quantos dias, e a lotação (UA/ha) de cada pasto.

## Como funciona

- **Página 🗺️ Pastos:** mapa de satélite (Leaflet 1.9.4 + imagem Esri World Imagery,
  grátis, precisa de internet) com cada pasto colorido e o rótulo: nome, área, cabeças,
  UA/ha e dias. Botão **📍 Onde estou** centraliza no GPS do celular.
- **Novo pasto:** desenhar o contorno tocando nos cantos da cerca (Leaflet.draw 1.0.4) e
  dar o nome. A **área é calculada no servidor** a partir do contorno (fórmula de área
  esférica), não confiando no número do navegador.
- **Mover gado:** escolher o pasto de destino, a data e os brincos — ou "o rebanho todo".
  Grava uma linha `Movimentação de Pasto` no Manejo com o pasto na coluna nova `Pasto`.

## Onde cada cabeça está

- Animal com brinco: o pasto da última movimentação que cita o brinco **ou** da última
  movimentação do "rebanho todo", a que for mais recente.
- Cabeças sem brinco (estoque − animais com brinco vivos): o pasto da última movimentação
  do rebanho todo (sem ela, "sem pasto").
- Dias no pasto: desde a movimentação que pôs ali o grupo maior.
- **UA** (unidade animal = 450 kg): último peso de balança do animal; sem peso, o peso
  médio (pesados → Configurações → 450 kg) — marcado como estimado.

## Dados

- Aba nova `Pastos`: `ID` (P01…), `Nome`, `Área (ha)`, `Contorno` (GeoJSON do polígono),
  `Cor`, `Ativo`, `Observações`, `Criado Por`.
- `COLUNAS_MANEJO` ganha `Pasto` no fim (ID do pasto). Movimentação antiga sem pasto
  (ou da voz) continua valendo como registro, só não move ninguém no mapa.
- Excluir pasto = `Ativo = "Não"` (o histórico das movimentações continua legível).
- Não mexe nas finanças.

## Fora (por ora)

Caminhar pela cerca gravando o GPS, oferta de forragem, cocho por pasto, lotes com
nome próprio. Mapa sem internet.
