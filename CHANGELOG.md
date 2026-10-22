# Changelog — Sistema de Gestão de Gado (Sítio Santo Antonio)

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).

## [Não lançado]

### Corrigido
- Datas dos formulários de edição (compra, gasto, venda, manejo): a data ISO do campo
  `date` do navegador é lida sem `dayfirst` — o log não enche mais de avisos do pandas.

### Planejado
- **WhatsApp** (design em `docs/superpowers/specs/2026-10-22-whatsapp-notificacoes-design.md`):
  cada membro escolhe o que recebe; aviso na hora de Morte/Perda e Nascimento; resumo
  semanal com "Na semana" e sem linhas repetidas; brucelose por animal.

## [4.5.1] — 2026-10-19

### Corrigido
- **Editar/excluir podia acertar o registro errado**: a lista vinha de um cache que não
  via gravações de outro processo (Task do WhatsApp, outro worker). O cache agora confere
  a versão do `.xlsx` no disco e recarrega quando ele muda.
- **Gravações simultâneas não se apagam mais**: uma gravação por vez (trava de arquivo) e
  salvamento atômico — se o servidor cair no meio do save, o `.xlsx` antigo fica inteiro.
- **Chave de sessão**: sem `GADO_SECRET_KEY`, o site usava a chave publicada no código
  (dava para forjar login). Agora gera uma aleatória em `<dados>/secret_key.txt`.
  ⚠️ Na primeira subida todos precisam entrar de novo uma vez.
- **Comparativo anual** (Relatórios) usava caixa como "Resultado": o ano em que se
  comprava gado aparecia com prejuízo mesmo com o gado no pasto. Agora o resultado é pela
  média móvel (receita − custo das vendidas − perdas), e o caixa aparece em coluna própria.
  A soma dos anos bate com o Resultado Total do painel.
- Cotas por membro que não somam o total da linha (planilha editada à mão) e venda maior
  que o rebanho quebravam a soma por membro; agora são ajustadas como no estoque global.
- Visita enviada offline dias depois usava o estoque de hoje como "gado esperado";
  agora usa o estoque do dia da visita.
- `/api/cotacao-scot` exigia login nenhum.
- "Enviar alertas à família" lento dizia "nenhum WhatsApp configurado".

### Desempenho
- `carregar_todas` lê o `.xlsx` uma vez só (eram 5 leituras).
- Resultado por membro e evolução do rebanho entram no cache; a evolução roda **uma**
  simulação (antes era uma por mês).

- **Editar venda com brincos dava erro** ("Nenhum animal vivo com brinco…"): o animal já
  estava Vendido. Agora os brincos que a venda já tinha são aceitos (vale também no Manejo).
- **Excluir uma venda** (ou tirar um brinco dela ao editar) devolve os animais para
  **Vivo**. Se o brinco já foi reaproveitado em outro animal vivo, avisa e não mexe.
- **Cotação do IMEA** não instala mais o Chromium durante a requisição (travava até
  3 min); mostra o comando para instalar. O resultado fica 3 h em cache e só um navegador
  abre por vez.

### Novo
- Aviso ao registrar venda com mais cabeças do que o rebanho registrado.
- **Preço da arroba** em ⚙️ Configurações → Rebanho (antes fixo em R$ 340 no código), com
  a arroba da última venda como dica. Vale para a estimativa do rebanho e as arrobas
  mínimas do painel.

## [4.5.0] — 2026-10-16

### Novo
- **Aba ❓ Ajuda** (menu, acima de Configurações): manual de todo o sistema com passo a passo
  e prints — celular para o dia a dia (visita, manejo, compra, gasto, venda, animal, fotos,
  voz) e computador para consultas, relatórios, backups e configurações. Inclui como as
  contas funcionam e problemas comuns.
- Os prints ficam no **Google Drive** (pasta *Ajuda - passo a passo*); o site acha cada um
  pela marca `ajuda=<nome>` e guarda no cache. Sem Drive, a página mostra só o texto.
  Para trocar prints: `python subir_prints_ajuda.py <pasta>`.
- Página pública `/privacidade` (exigida pelo Google para publicar o app do Drive).
- Cache de fotos limitado a 50 MB (disco do PythonAnywhere).

## [4.4.0] — 2026-10-16

### Novo
- **Fotos dos animais** (ficha do animal → 📷 Fotos): linha do tempo com data, tipo
  (Perfil / Evolução / Ocorrência), legenda e quem enviou; uma foto **principal** aparece
  na ficha e como miniatura na lista de animais. Qualquer usuário logado pode enviar.
- Os arquivos ficam na pasta do **Google Drive** da família (uma subpasta por animal); os
  dados de cada foto na nova aba `Fotos`. As fotos são privadas: o site busca no Drive e
  mostra só para quem está logado (com cache em `cache_fotos/`).
- **Sem sinal no sítio**: a foto é reduzida no celular e fica guardada até a internet
  voltar; o envio não duplica (`ID Envio`).
- Excluir manda a foto para a lixeira do Drive (30 dias). Configurações → 📷 Fotos testa a
  conexão; o WhatsApp de urgentes avisa se o Drive parar de aceitar envios.
- Configuração única: `configurar_drive.py` + `docs/FOTOS_DRIVE.md`.

## [4.3.0] — 2026-10-15

### Novo
- **Animais com brinco** (`animais.py`, página **Animais**): cadastro individual com
  brinco (cor + nº), dono, categoria, raça, pelagem, sinais, nascimento, mãe e origem.
  Cada dono tem a sua cor (padrão: Deyvid amarelo, Nilson azul, Geane vermelho —
  ajustável na página). Numeração 01–99 por cor; depois do 99 recomeça do 01, pulando
  os brincos de animais vivos. O ID interno (`A0001`…) nunca se repete e é o que liga o
  histórico — o brinco só é único entre os vivos.
- Ficha do animal com histórico (manejos e vendas com o brinco), crias e baixa
  (vendido / morreu). Conferência "com brinco × estoque" por dono e alerta de
  **brucelose por animal** (fêmeas de 3–8 meses, também no painel).
- **Compra → brincos**: opção "colocar brinco nos animais desta compra" abre uma tela
  com uma linha por cabeça, dono e próximo número já sugeridos.
- Campo **Brincos** no Manejo e na Venda ("amarelo 21, azul 12"). Na venda, os animais
  citados saem como Vendidos e o brinco fica livre.
- **Comando de voz** (`comando_voz.py`, página **Comando de Voz** e 🎤 no topo de todas
  as páginas): cadastro, nascimento (com mãe), vacinas, vermífugo, pesagem, tratamento,
  pasto, morte, compra, venda, gasto, visita e ficha, falados em português. Entende
  números falados ("vinte e um", "zero sete", "quinze mil"), "ontem"/"dia 12" e pergunta
  quando um nº sem cor bate em mais de um animal. Nada grava sem confirmar; modo
  **mãos livres** lê o resumo em voz alta e salva com "sim". Sem internet, o comando
  fica guardado no celular para conferir depois. A visita só preenche o formulário.
  Também responde perguntas: "quantas cabeças eu tenho", "quanto gado tem o Nilson",
  "quantas novilhas do Deyvid". Bateria de 86 frases em `tests/test_comando_voz.py`.
- 🎤 de **ditado** nos campos de texto livre (descrição, observações, sinais, produto,
  brincos…) e formulários preenchidos por link (`?prefill=1&campo=valor`,
  `static/voz_campos.js`).

### Regras financeiras
- O cadastro não mexe nas contas. Só o **Nascimento** com brinco grava a linha de
  Nascimento no Manejo, e a baixa por **morte** grava a Morte/Perda (Perda De = dono).
  Invariantes cobertas em `tests/test_animais.py`.

### Colunas novas (no fim, migradas automaticamente)
- Aba nova `Animais` · Manejo: `Brincos` · Vendas: `Brincos`

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
