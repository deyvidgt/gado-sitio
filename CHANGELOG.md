# Changelog — Sistema de Gestão de Gado (Sítio Santo Antonio)

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).

## [4.2.0] — 2026-10-04

### Novo
- **Visita sem internet**: o formulário de visita abre e salva sem sinal. A visita fica
  guardada no celular (`static/fila_visitas.js`, IndexedDB) e é enviada sozinha quando a
  internet volta (ao abrir o app, ao reconectar ou a cada 30 s). Faixa no topo mostra
  quantas aguardam envio. Cada visita tem um código único (`ID Envio`): reenvio nunca
  grava em dobro. Novo endpoint `/api/visitas` (JSON) e `/api/csrf`.
- **Estoque de insumos** (`insumos.py`, card no painel): na visita, "Sacos em estoque"
  de Sal, Proteinado e Ração; no gasto do tipo Sal/Proteínado, produto e quantidade de
  sacos comprados. Calcula consumo, estoque estimado e "acaba por volta de / compre até".
- **WhatsApp**: nos dias comuns só alertas **urgentes** (vacina atrasada ou vencendo em
  até 7 dias, insumo acabando, 14+ dias sem visita, lembrete de campanha), cada um
  repetido no máximo a cada poucos dias; sem urgência, nada é enviado. **Segunda-feira**:
  resumo semanal completo. `alertas_whatsapp.py --teste [--semanal]` mostra sem enviar.

### Corrigido
- Aviso de visita no WhatsApp rodava numa thread (o PythonAnywhere não garante) — agora
  fica numa fila (`avisos_pendentes.json`) e sai logo após a resposta; se a conexão cair,
  sai na próxima requisição de visita ou na Task diária.
- `form_visita.html` e `form_manejo.html`: o bloco de scripts estava dentro do conteúdo e
  era desenhado **duas vezes** (com o envio novo, cada "Salvar" mandaria duas visitas).

### Colunas novas (no fim, migradas automaticamente)
- Gastos: `Produto`, `Qtd Sacos` · Visitas: `ID Envio`

## [4.1.1] — 2026-10-03

### Corrigido — modo escuro
- **Nova Visita**: caixas de status (sal, ração, pasto, água…) tinham fundo pastel fixo
  com o texto claro do tema — ilegível. Agora usam tons translúcidos da mesma cor.
- Revisão de todas as telas com verificador automático de contraste (17 telas, 0 problemas):
  títulos verde-escuro escritos direto no HTML (formulários, relatórios, importar,
  configurações), labels cinza `#444`, caixas de aviso amarelas, botões Resetar/Excluir,
  selos de status do painel e da lista de visitas, widget de cotação da Novilha,
  nome do sítio no menu, botão dourado "Baixar Excel".
- Ajustes centralizados no `base.html` (só valem com o tema escuro; o modo claro foi
  comparado antes/depois e ficou idêntico).

### Corrigido
- Lista de visitas mostrava "📝 nan" quando a visita não tinha observação.

## [4.1] — 2026-10-03

### Novo
- **Gráfico "Evolução do Rebanho"** no painel: cabeças no fim de cada mês, entradas
  (compras + nascimentos), saídas (vendas + mortes) e custo médio/cab pela média móvel
  (`calculos.calcular_evolucao_rebanho`, `/api/rebanho`).
- **Resumo mensal no WhatsApp** (`resumo_mensal.py`): no dia 1º, o mês anterior para a
  família — movimento do mês, rebanho, custo médio e resultado por dono.
- **Calendário sanitário por vacina** (`saude.py`), referência Triângulo Mineiro (IMA-MG,
  Embrapa): tipos "Vacina Raiva" (obrigatória, anual), "Vacina Clostridioses" (anual),
  "Vacina Brucelose" (campanha: vacinar até 30/06 e 31/12, declarar até 10/07 e 10/01) e
  lembretes da vermifugação estratégica 5-7-9. Registros antigos de "Vacinação" contam
  para raiva e clostridioses. Quadro de referência de vacinas reescrito com fontes.
- **Manejo — remédio/produto**: vacinas e vermifugação pedem o produto usado (coluna
  nova "Produto"), com sugestões do que já foi usado.
- **Exemplos de produtos** (pesquisa out/2026) no quadro de vacinas e como sugestões no
  campo "remédio/produto": raiva, clostridioses/botulismo, IBR/BVD/lepto, vermífugos do
  5-7-9 (ex.: Solution 3,5%, Dectomax, Ivomec Gold) e suplemento ADE (A, D3, E).
- **Manejo — "De quem é o bezerro?"** (coluna nova "Nascimento De"): o inverso de
  "Perda De"; a cabeça entra no estoque do dono, ou em terços se em branco.
- **Testes automáticos** (`tests/`, `python -m pytest`) rodando numa cópia dos dados,
  incluindo as 3 invariantes contábeis. `atualizar.sh` roda os testes no servidor.

### Corrigido
- **Backup diário** (`backup_automatico.py`) procurava a planilha na pasta do código, não
  em `~/gado-dados/` — no servidor abortava ou copiava um arquivo velho.
- **Limpeza dos backups do site** olhava a pasta errada; backups acumulavam sem limite.
- **Exportação Excel**: aba Manejo saía com colunas sem título (Perda De e as novas).
- Log do `alertas_whatsapp.py` criava `backups/` dentro da pasta do código.
- Prazo de vermifugação salvo com o padrão antigo (120 dias) passa ao novo (240 dias).
- Formulário de manejo sugere 1 cabeça em Nascimento/Morte (antes vinha o rebanho todo).
- Cotação IMEA: faltava `import sys` ao tentar instalar o navegador automaticamente.

### Outros
- `requirements.txt` trava a próxima versão MAIOR de cada biblioteca.
- Cache do app no celular (PWA) renovado (`gado-v3`) para carregar as telas novas.

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
