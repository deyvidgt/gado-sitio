# Análise de concorrentes — o que falta no Sítio Santo Antonio

Data: 2026-11-01 · Levantamento feito sobre o código real do sistema (não sobre docs de handoff).

Comparação com **JetBov** (corte, referência nacional) e **Ideagri / Rúmina** (leite).
O objetivo é achar o que eles têm e você ainda não — e, no meio disso, separar o que
realmente serve um sítio familiar do que é peso de software corporativo.

---

## 1. O que você já tem (e está bom)

Levantado das rotas e módulos em produção:

**Rebanho e manejo**
- Cadastro por brinco (cor + nº), ID `A0001`, histórico individual, foto, genealogia
- Pesagem, GMD, crescimento, peso por foto (estimativa por medidas)
- BCS (escore de condição corporal) correlacionado com peso
- Pastos com mapa satélite, área, rotação, UA/ha vs capacidade
- Cochos, sal, volumosos, confinamento por lote
- Manejo offline no celular (IndexedDB + fila)

**Reprodução**
- Cobertura, diagnóstico de gestação, previsão de parto (285 d), toque (35 d), secagem (60 d)
- IATF, observação de cio, sugestões de descarte
- IEP, taxa de prenhez, consanguinidade (AVK), compatibilidade genética

**Sanidade**
- Calendário sanitário Triângulo Mineiro, vacinas por tipo, brucelose, vermifugação 5-7-9
- Doenças + carência (bloqueio de venda), medicações, quarentena
- Mastite, CCS/CPP, alertas dinâmicos

**Leite**
- Produção individual/total, acumulados, dias em lactação, curva de produção
- Nutrição, calculador de ração (Embrapa), necessidades por categoria
- Conforto térmico, colchão, tratamentos, comparativo entre vacas

**Financeiro**
- Média móvel perpétua, custo de venda, capital imobilizado, resultado por membro
- Fluxo de caixa, comparativo anual, lotes FIFO, insumos e previsão de compra
- Valor do rebanho em arrobas

**Infra**
- Multi-sítio, multi-dono, WhatsApp (urgentes/semanal/visita/eventos/mensal)
- PWA offline, backup diário, importação de Excel antigo, IA preditiva (morte/cio)

**Isso é mais do que a maioria dos produtores tem.** A lista abaixo é o que falta
para igualar os comerciais — não para você se sentir atrasado.

---

## 2. Lacunas reais, por ordem de retorno

### 🟢 Alto retorno — barato e resolve dor de verdade

#### 2.1 Desmama como evento (não só uma menção)

**Eles têm:** JetBov e Ideagri tratam desmama como manejo com data, peso e lote de destino.

**Você tem:** a palavra "desmama" aparece só no texto da vermifugação 5-7-9 (`saude.py`).
Não existe registro de desmama: nem data, nem peso à desmama, nem bezerro separando da mãe.

**Por que importa:** peso à desmama é o principal indicador de qualidade da cria, e é o
que decide se a vaca fica ou sai. Sem ele, a "sugestão de descarte" olha só IEP e
produção — metade do quadro.

**Sugestão:** novo tipo de Manejo `Desmama` com Brincos do bezerro e peso na Descrição.
Ler em `pesagem.py` como já faz com `Pesagem`. Custo: ~1 tipo de manejo + 1 leitura.
Sem aba nova.

---

#### 2.2 Estoque de medicamentos com validade

**Eles têm:** Ideagri e JetBov controlam entrada/saída de produto veterinário com validade.

**Você tem:** `medicacoes.py` registra aplicação e carência, mas **não tem estoque**
(nenhuma ocorrência de "estoque" no módulo). Você tem estoque para sal/proteinado/ração
(`insumos.py`), não para remédio.

**Por que importa:** remédio vencido aplicado é prejuízo e risco de resíduo — e você
já tem o bloqueio de venda por carência, então a fundação está pronta.

**Sugestão:** reaproveitar `insumos.py` (que já faz sacos em estoque + compras em Gastos
+ previsão de "acaba em"). Medicamento é o mesmo padrão com um campo `Validade` a mais e
alerta de vencimento em 30 dias. Não criar módulo novo.

---

#### 2.3 Simulador de venda já existe e não está ligado

**Eles têm:** JetBov vende "simulador de vendas" como recurso do plano Precisão.

**Você tem:** `ponto_corte.py` faz exatamente isso — "vendo hoje por R$X ou espero 30 dias
por R$Y?" — e **não tem rota nem tela**. Ninguém consegue usar.

**Sugestão:** ligar `/ponto-corte/<animal_id>` e um botão na ficha do animal.
Custo: uma rota de leitura. É o item mais barato da lista inteira.

---

#### 2.4 Relatórios avançados também estão prontos e sem rota

**Eles têm:** Ideagri tem 85+ modelos de relatório; JetBov tem relatórios personalizados.

**Você tem:** `relatorios_avancados.py` com 6 relatórios em PDF (anual, vendas por vaca,
sanitário, reprodutivo, leite, financeiro) — **módulo sem nenhuma rota ligada**.

**Sugestão:** uma rota `/relatorios/avancados/<tipo>` e um link na página de Relatórios.
É a Onda 14 que ficou pela metade.

---

### 🟡 Médio retorno — vale quando a dor aparecer

#### 2.5 Custo por animal individual

**Eles têm:** JetBov (plano Precisão) e Ideagri fazem custeio individual por animal.

**Você tem:** custo por **lote** (`lotes.py`, FIFO) e custo médio por cabeça global.
Não dá para responder "quanto custou essa vaca desde que nasceu".

**Por que é médio:** para sítio familiar com rebanho pequeno, o custo médio já responde
quase tudo. O custo individual só compensa se você quiser decidir descarte por
rentabilidade real — e aí o rateio de gastos indiretos vira discussão longa.

**Sugestão:** só fazer se a pergunta "essa vaca se paga?" virar recorrente. O motor FIFO
de `lotes.py` já tem 80% do trabalho.

---

#### 2.6 Curva de lactação e projeção

**Eles têm:** Ideagri projeta lactação e compara com a curva esperada por raça/ordem de parto.

**Você tem:** produção por dia/semana/mês e dias em lactação. Não tem curva ajustada
nem projeção de pico/persistência.

**Sugestão:** você já tem os dados (Leite Produção + partos). Uma curva de Wood ajustada
por vaca sai em ~50 linhas e responde "essa vaca está produzindo abaixo do que deveria?".
Só vale se você tiver ≥10 vacas em lactação com registro diário — senão é ruído.

---

#### 2.7 Mão de obra e tarefas por pessoa

**Eles têm:** Ideagri manda roteiro de trabalho do escritório para o celular da equipe.

**Você tem:** `tarefas.py` com responsável e repetição, e visitas com quem foi.
O básico está lá.

**Sugestão:** nada a fazer. Você é família, não tem equipe contratada.

---

### 🔴 Baixo retorno para você — não copiar

| Recurso deles | Por que não serve |
|---|---|
| **GTA / NF-e / SISBOV** | Obrigação de escala comercial. Um sítio familiar vende para vizinho/frigorífico local; a GTA é emitida no órgão estadual, não no seu sistema. Integração com SEFAZ é projeto de meses. |
| **Balança Bluetooth + bastão RFID** | Você já tem IoT emulador e peso por foto. Comprar hardware de R$3-5 mil para 50 cabeças não se paga. |
| **API para ERP / consolidação multi-fazenda** | JetBov só oferece no plano Corporativo. Você já tem multi-sítio, que é a versão que importa. |
| **85+ modelos de relatório** | Você usa 6. Relatório que ninguém abre é custo de manutenção. |
| **Assistente de IA por voz ("Jay", "Rúmi")** | Você já tem `comando_voz.py` com regras — e regra acerta o que importa no seu vocabulário. IA generativa aqui só adiciona custo de API e erro silencioso. |
| **Monitoramento de pasto por satélite** | Você já calcula área, UA/ha e rotação no mapa. NDVI por satélite é caro e nublado demais no Triângulo Mineiro. |

---

## 3. O que eles têm que é conceito, não código

Duas ideias que valem mais que features:

**1. Escores personalizados por área/lote/animal** (JetBov)
Você já tem BCS e conforto térmico com score 1-5. A ideia de deixar o usuário **criar**
o escore (altura de pasto, umbigo, cerca, fezes) é barata: uma coluna de texto no Manejo
já registra qualquer coisa. Não precisa de tela nova — o `comando_voz` e a Descrição
livre já cobrem. **Só vale se você sentir falta de um escore específico.**

**2. Lista de trabalho do dia** (Ideagri, JetBov)
Você tem `tarefas.py` e o painel de alertas. O que eles fazem melhor é **juntar tudo numa
lista única ordenada por urgência**: vacina atrasada + vaca para inseminar + cocho vazio.
Você tem os três, mas espalhados. **Sugestão:** uma linha no topo do painel — "hoje você
tem N coisas" — linkando para o que já existe. Sem módulo novo.

---

## 4. Ordem sugerida

| # | O que | Esforço | Por quê primeiro |
|---|---|---|---|
| 1 | Ligar `ponto_corte.py` e `relatorios_avancados.py` | ~2 h | Código pronto, só falta rota. Zero risco. |
| 2 | Desmama como tipo de Manejo | ~3 h | Fecha o ciclo da cria, alimenta o descarte. |
| 3 | Estoque de medicamento com validade | ~1 dia | Reaproveita `insumos.py`. Evita aplicar remédio vencido. |
| 4 | Lista única do dia no painel | ~3 h | Junta o que já existe, sem módulo novo. |
| 5 | Curva de lactação | ~1 dia | Só se houver ≥10 vacas com registro diário. |

Os itens 1-4 somam menos de dois dias e resolvem 80% da distância para o JetBov
no que diz respeito ao seu uso real.

---

## 5. Onde você está à frente deles

Para equilibrar a análise:

- **Multi-dono com rateio por cabeça** — nenhum comercial faz isso. É específico da sua família.
- **Média móvel perpétua** com as 3 invariantes contábeis testadas. JetBov faz custeio,
  mas não com essa disciplina de teste.
- **WhatsApp integrado** (urgentes, semanal, mensal, visita) sem app próprio de mensageria.
- **Peso por foto** — estimativa por medidas sem balança. Comercial vende hardware.
- **Custo zero de licença.** JetBov cobra por cabeça/mês; Ideagri por fazenda/mês.

---

## Fontes

- JetBov — home, `/planos` (matriz de funcionalidades por plano) e LPs dos apps.
  `jetbov.com/funcionalidades` retorna 404; preços não são públicos.
- Ideagri — `ideagri.com.br` redireciona para `rumina.com.br/solucoes/ideagri/`
  (marca Rúmina). `ideagri.com.br/solucoes` retorna 404.

**Ressalva:** a comparação de leite se apoia numa única fonte acessível. Ideagri não
publica detalhamento de sanidade, nutrição e CCS/CPP nas páginas que respondem —
as lacunas de leite podem ser menores do que parecem aqui.
