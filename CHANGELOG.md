# Changelog — Sistema de Gestão de Gado (Sítio Santo Antonio)

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).

## [Não lançado]

### Melhorado
- **Telas mais fáceis de ler (v5.3):** inspirado nos aplicativos que a família já conhece,
  o que antes era só número virou **barra colorida com semáforo**:
  - **Pastos** deixou de ser tabela e virou um cartão por pasto, com cabeças, hectares,
    UA/ha e dias numa linha só, a **barra de lotação** ("78% da capacidade") e a etiqueta
    **Folgado / No limite / Lotado**. No mapa, o **preenchimento de cada pasto agora é
    verde, amarelo ou vermelho** conforme a lotação — dá para ver de relance de qual
    pasto é hora de tirar o gado.
  - **Painel**: a Lotação ganhou barra e a porcentagem da capacidade; o Rebanho por
    Categoria virou **barras proporcionais** (lê-se melhor que lista ou pizza no celular);
    o Estoque de Insumos mostra uma **barra de folga** que fica amarela abaixo de 15 dias
    e vermelha abaixo de 5.
  - **Tarefas**: contagem grande de **atrasadas / para hoje / próximas** no topo, e a
    linha da tarefa atrasada (ou de hoje) ganhou **fundo colorido**, que se enxerga melhor
    no sol do que só o texto vermelho.
  - **Tabelas no celular**: a primeira coluna agora fica parada ao rolar para o lado, então
    não se perde mais de qual linha é o número.
  - O semáforo sempre vem com a **palavra junto da cor** (Folgado/No limite/Lotado), para
    quem não distingue bem as cores ou está no sol.

### Adicionado
- **Lotes com painel econômico (v5.3):** nova aba **📦 Lotes** no menu. Cada compra (e cada
  nascimento) vira um lote e o sistema mostra, por lote: cabeças, **custo por cabeça**
  (compra + a parte dos gastos daquele período), quantas foram vendidas e por quanto,
  quantas ainda estão no pasto, **quanto o lote deu de resultado** e o **ganho por cabeça
  vendida** — responde "aquele caminhão de bois deu lucro?". As vendas e as mortes saem do
  lote mais antigo primeiro (FIFO) e os gastos são divididos entre os lotes que tinham gado
  no pasto naquele dia. Não precisa de brinco cadastrado nem de coluna nova: usa Compras,
  Gastos, Vendas e Manejo como já estão. É uma visão **aproximada e paralela** — o resultado
  oficial continua sendo o do painel (média móvel), e esta tela não grava nada.
- **Reprodução sem sensor (v5.3):** nova aba **🐮 Reprodução** no menu. Anote a **cobertura**
  (monta ou inseminação, com o touro) e depois o **resultado do toque** (Prenha/Vazia); o
  sistema conta os 285 dias de gestação e mostra, por vaca, o **parto previsto**, a partir de
  quando dá para fazer o toque (35 dias) e quando **secar** (60 dias antes do parto). O parto
  é fechado sozinho quando o bezerro é cadastrado com a **mãe**. Números do rebanho de cria:
  prenhas, taxa de prenhez e dias entre partos (IEP). Painel e WhatsApp avisam de parto
  chegando, toque atrasado e vaca sem notícia depois do parto previsto. Nenhuma coluna nova:
  são dois tipos novos de Manejo (**Cobertura** e **Diagnóstico de Gestação**) e não entram
  nas contas do rebanho.
- **Agenda de tarefas (v5.3):** nova aba **📋 Tarefas** no menu — anote o que precisa ser
  feito ("consertar a cerca do fundo"), para quando, quem faz e se repete (semanal a anual).
  Ao marcar **✅ Feito**, a tarefa que repete já cria a próxima sozinha. Atrasada fica em
  vermelho e não some. O painel mostra as dos próximos 7 dias e o WhatsApp avisa das
  atrasadas e das de hoje. Nova aba `Tarefas` no arquivo de dados (criada sozinha).
- **Comparador de proteinado/ração (v5.3):** nova página **🧮 Comparar preços** (botão no
  cartão de Insumos do painel). Põe lado a lado até 3 marcas (R$/saco, kg/saco, consumo
  g/cab/dia) e mostra o **R$/kg**, o **custo por cabeça/dia**, o **gasto do mês** e quanto
  a mais cada opção custaria — o saco mais barato nem sempre ganha. Mostra também o último
  preço que a família pagou (vem dos Gastos). Só calcula: nada é gravado na planilha.
- **Lotação e composição do rebanho (v5.3):** novo campo **Capacidade do pasto (UA/ha)** em
  ⚙️ Configurações → Rebanho (em branco = sem semáforo). Com ele, a coluna UA/ha da página
  **🗺️ Pastos** fica verde (até 70% da capacidade), amarela (70–100%) ou vermelha (acima), e
  o painel ganha o cartão **🌿 Lotação dos Pastos** com a UA/ha do sítio todo. Novo cartão
  **🐄 Rebanho por Categoria** (painel e Pastos) com as cabeças por categoria e por sexo —
  quem está no estoque mas sem brinco cadastrado aparece como "Sem cadastro".
- **Pesagem por animal e GMD**: página **⚖️ Pesagem** (Animais) para pesar o rebanho no
  curral — um campo por brinco, mostra o ganho na hora. A ficha do animal ganhou o cartão
  **Peso**: último peso, @ estimadas, GMD do último período e desde a 1ª pesagem, e o
  gráfico do peso ao longo do tempo. A lista de animais mostra o último peso.
- Coluna **Pesos** no fim da aba Manejo (`"Amarelo 21 #A0003: 320 kg; …"`); a pesagem por
  voz também grava nela. Pesagens antigas da voz (peso só na descrição) são lidas.
- Painel: sem peso médio nas Configurações, a estimativa do rebanho usa a média pesada.
- **Vários sítios — fase 1: donos configuráveis.** Os sócios vêm de `"membros"` no
  `sitio_config.json` (chave, nome, emoji, cor do brinco, logins), de 2 a 8. Sem isso,
  continuam Geane/Deyvid/Nilson e os números do Santo Antonio não mudam. O rateio "em
  terços" virou "em partes iguais" (resto para o último dono, igual a antes). Um arquivo
  com colunas de outros donos é recusado ao iniciar (trocar donos só em sítio novo).

- **Vários sítios — fase 2: pasta por sítio, seletor e acesso.** Com `sitios.json` na
  pasta de dados, cada sítio tem a sua pasta (planilha, configurações, backups, fotos) e
  cada login só entra nos sítios dele; quem tem mais de um troca no seletor do topo.
  Usuários, senhas e a chave de sessão continuam na pasta principal. Aviso de WhatsApp
  de um sítio só vai para quem é dele. Sem `sitios.json`, tudo igual a antes.
- **Vários sítios — fase 3: administração.** Configurações → 🏡 Sítios (só administrador):
  criar sítio com os donos e marcar quem entra em cada um. Backup diário, WhatsApp diário
  e resumo mensal rodam para cada sítio (a mensagem começa com o nome do sítio).

### Segurança
- Com vários sítios, só o **administrador** (quem tem acesso ao 1º sítio, ou a lista
  `"admins"` do `sitios.json`) cria/exclui usuários e redefine senhas — antes qualquer
  login podia, e um parente de outro sítio poderia trocar a senha de quem é do Santo
  Antonio. A lista de usuários e os telefones do WhatsApp só mostram quem é do sítio.

- **Vários sítios — fase 4: painel da Família** (menu 👨‍👩‍👧, aparece com 2+ sítios):
  cabeças, capital no rebanho, vendas, perdas e resultado de cada sítio, lado a lado e
  somados. Qualquer pessoa da família vê; os lançamentos continuam dentro de cada sítio.

- **Peso estimado por foto** (ficha do animal → 📷 Estimar por foto): foto de lado com uma
  referência de tamanho conhecido (vara de 1 m); toca e arrasta os pontos — referência,
  ombro→nádega e profundidade do peito — e sai o peso pela fórmula de Schaeffer, com faixa
  de erro. Calibra sozinho com as pesagens de balança do sítio (3+ animais com foto e
  balança a até 15 dias). Fica como "Peso Estimado" no Manejo e não entra no GMD. Também
  aceita as duas medidas digitadas (fita métrica).

- **🗺️ Pastos com mapa**: mapa de satélite com cada pasto desenhado (toque nos cantos da
  cerca); a área em hectares é calculada pelo contorno. **Mover gado** — o rebanho todo ou
  só alguns brincos — grava "Movimentação de Pasto" no Manejo, na coluna nova **Pasto** (no
  fim). Cada pasto mostra cabeças, dias no pasto e lotação (UA/ha; "~" quando algum animal
  não tem pesagem de balança). Botão 📍 Onde estou (GPS). Precisa de internet para o mapa.

### Planejado
- Leite: produção por vaca/ordenha, lactação e secagem, entregas e preço do litro
  (liga só no sítio que tiver leite); reprodução (cobertura, prenhez, alerta de parto).
- Peso pela fita no peito (perímetro torácico direto).
- Lotes e pastos com mapa de satélite (área em ha, lotação UA/ha).
- Simulador Boi Gordo, calendário de eventos, reprodução, painel de lote e de sanidade.

### Corrigido
- Datas dos formulários de edição (compra, gasto, venda, manejo): a data ISO do campo
  `date` do navegador é lida sem `dayfirst` — o log não enche mais de avisos do pandas.

### Novo
- **WhatsApp — cada um escolhe o que recebe** (Configurações → WhatsApp): urgentes,
  resumo semanal, visita, morte/nascimento e resumo mensal, um a um.
- **Sem valores**: quem desmarca "Mostrar valores em R$" recebe as mensagens só com
  cabeças e contagens (semanal, mensal e aviso de perda).
- **Aviso na hora de Morte/Perda e Nascimento** — pelo formulário de Manejo, pela baixa
  do animal, pelo cadastro de nascimento e pela voz. Quem registrou não recebe.
- **Resumo semanal** com a seção "Na semana" (o que aconteceu) e sem linhas repetidas.
- **Brucelose por animal** nos alertas: cada bezerra na janela de 3 a 8 meses aparece.
- Pendente: trocar o print `p-config-2.png` da Ajuda pelo com as caixinhas novas.

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
