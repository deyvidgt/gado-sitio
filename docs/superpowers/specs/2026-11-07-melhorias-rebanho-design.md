# Design: Melhorias do Rebanho (Ponto de Abate, IA, Insumos, PWA, Foto)

## 1. Ponto de Abate Preditivo
- **Objetivo:** Comparar venda hoje vs. futuro (7, 14, 30 dias).
- **Mecânica:** `ponto_corte.py` utiliza GMD individual + custo diário por cabeça.
- **Interface:** Tela `/ponto-corte` (já existente), ajuste de cálculos para precisão.

## 2. IA & Alertas Proativos
- **Objetivo:** Centralizar predições e alertas no painel.
- **Arquitetura:**
    - `ia_modelos.py`: Inferência.
    - `routes_ia.py`: Orquestração de alertas proativos.
- **Integração:** Exibir alertas (risco morte/cio/consanguinidade) no painel principal.

## 3. Gestão de Insumos
- **Objetivo:** Estoque inteligente.
- **Mecânica:** `insumos.py` calcula "acaba em X dias" baseado em consumo histórico das visitas vs compras.
- **Alertas:** Painel e WhatsApp.

## 4. Modo Campo (PWA)
- **Objetivo:** Confiabilidade offline.
- **Refinamento:** Melhorar `fila_visitas.js` e `fila_fotos.js` para garantir sincronização robusta mesmo com quedas de sinal.

## 5. Identificação Visual
- **Objetivo:** Linkar foto ao ID.
- **Ajuste:** `fotos.py` garante que o fluxo `peso_foto` vincule a foto ao ID do animal e atualize histórico no `db`.
