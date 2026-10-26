# Peso estimado por foto — design

**Status:** em implementação · **Data:** 2026-10-25 · **Versão alvo:** 5.1

## Objetivo

Estimar o peso de um animal sem balança, por uma foto de lado tirada no celular — como
o app Peso Rural das imagens de exemplo, mas sem modelo de IA treinado (não temos os
dados para treinar): medidas tiradas da foto + fórmula zootécnica + calibração com as
pesagens de balança do próprio rebanho.

## Como funciona

1. Na ficha do animal: **📷 Estimar peso por foto**. Foto **de lado**, de uns 4 m, com o
   celular na altura do meio do boi e uma **referência de tamanho conhecido no mesmo
   plano** (vara de 1 m encostada no animal, ou a tábua da cerca medida).
2. Três toques duplos na foto: as 2 pontas da referência; ponta do ombro → ponta da
   nádega (comprimento); lombo logo atrás da paleta → embaixo do peito (profundidade).
3. Contas (em cm, a partir da escala da referência):
   - perímetro do peito ≈ `2,6 × profundidade` (proporção típica de zebuíno);
   - peso bruto (kg) = `perímetro² × comprimento / 10838` (Schaeffer, métrico);
   - peso mostrado = `bruto × fator do sítio`.
4. **Fator do sítio (calibração):** pares (estimativa bruta, balança) do mesmo animal com
   até 15 dias de diferença; com 3+ pares, fator = mediana de `balança / bruto`, limitado
   a 0,7–1,3. Sem calibração, a tela diz que o erro pode passar de 15%.

## Dados

- Linha no Manejo com `Tipo = "Peso Estimado"`, `Qtd Cabeças = 1`, `Brincos` = ref do
  animal, `Pesos` = peso **bruto** (`"Amarelo 21 #A0003: 452 kg"`), `Descrição` =
  medidas (`"Foto: comprimento 158 cm, peito 71 cm, ref. 100 cm"`). Bruto para a
  calibração poder melhorar e recalcular o que se mostra.
- `pesagem.todas()` ignora "Peso Estimado" (GMD e média do rebanho só com balança);
  `pesagem.todas(..., estimados=True)` lê só as estimativas.
- Não mexe nas finanças nem no alerta de "Pesagem" do calendário sanitário.

## Limites (ditos na tela)

- Erro típico de 8–15% sem calibração; melhora com a calibração. Serve para acompanhar a
  evolução e decidir a venda — **não para negociar**.
- A referência fora do plano do animal, foto de frente/torta ou animal encolhido erram
  muito. A foto não é guardada (só as medidas).
