# Changelog — Sistema de Gestão de Gado (Sítio Santo Antonio)

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).

## [4.0] — 2026-10-02

### Cálculos — Média Móvel Perpétua (mudança principal)
- O custo das cabeças vendidas e o resultado por membro passaram a usar **média móvel
  perpétua** (`calculos.py: _simular_media_movel`): cada venda sai pela média de custo
  (compra + gastos) vigente no momento; gastos são diluídos **só** no rebanho vivo
  naquele instante — gado comprado depois **nunca** é cobrado por despesas anteriores.
  - Antes (modelo GPCab acumulado desde a origem) o resultado realizado dos dados reais
    era **−R$ 90.418**; com a média móvel passou a **−R$ 31.164** (mais fiel).
  - Dois pools separados (compra e gasto) preservam a divisão compra/gastos por venda.
  - **Conservação garantida:** `custo_vendidos + capital_imobilizado == total_custo`
    e a soma dos custos dos membros fecha exatamente com o custo global das vendas.
  - O **snapshot gravado na aba Vendas** (Custo/Resultado por membro, CMP no momento)
    ao registrar/editar uma venda passou a usar a média móvel (`custo_medio_movel_venda`),
    ficando idêntico ao que o dashboard recomputa — antes usava o modelo acumulado e divergia.

### Mortes/Perdas como perda separada
- O custo de uma cabeça morta/perdida passou a ser uma **perda registrada** (pela média
  do momento) em vez de ser absorvido pelos sobreviventes. Com o campo *Perda De*, a perda
  é atribuída ao dono; sem indicação, é rateada em terços.
- Nova invariante: `custo_vendidos + perdas + capital_imobilizado == total_custo`.
- Exibido no **dashboard** (card "Perdas (mortes)" e, por membro, "Resultado líquido"),
  no **relatório PDF** e na **exportação Excel**. `resultado_total` já desconta as perdas.

### Corrigido
- **Custo fantasma** (`calculos.py`): o capital imobilizado usava `estoque × CTCab_atual`
  enquanto o custo das vendas usava o valor na data de cada venda; as bases não
  reconciliavam e surgiam **+R$ 99.019,96** de custo inexistente nos dados reais.
  Resolvido pela média móvel + identidade contábil do capital como resíduo.
- **Crash de emoji no console Windows** (`config.py`): `print` de boot com emojis
  (📂 📊 ✅ 🐄) quebravam com `UnicodeEncodeError` em terminais cp1252. Saída forçada a UTF-8.

### Adicionado
- **Visitas — reservatórios de água**: campos *Caixa d'Água* e *Conteiner*, cada um
  com status (Cheia/Meia/Baixa/Vazia) e litros restantes. (Por preferência da família,
  o sistema **não** sugere reabastecimento para cisterna, caixa d'água e conteiner.)
- **Manejo — "De quem foi a perda?"**: em *Morte/Perda* pode-se indicar o dono afetado;
  a baixa no estoque por membro é debitada só desse dono (sem indicar, divide em terços).
- **Gastos e Manejo**: filtro por pessoa (*Registrado Por* / *Responsável*) e
  **ordenação por clique no cabeçalho** (Tipo, Responsável, Registrado Por, Perda De,
  valores e datas), além dos filtros de ano e tipo.

### Alterado
- **Versão unificada em `config.VERSAO` (4.0)**, injetada em todos os templates
  (login e demais telas) via context processor — fim das versões hardcoded.
- **Migração de banco generalizada** (`db.py`): ao iniciar, cria colunas novas em
  **todas** as abas (antes só *Visitas*), sempre no final e sem alterar dados existentes.

---

## [3.5] e anteriores (histórico)
Histórico não versionado neste arquivo. Principais marcos registrados nos commits
(`atualizacao 3.xx`): motor de cálculos (CMP/GPCab/CTCab), resultado por membro,
fluxo de caixa, relatórios/PDF, importação/exportação Excel, visitas ao sítio,
notificações WhatsApp e PWA.
