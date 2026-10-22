# WhatsApp — preferências por pessoa, aviso de Morte/Nascimento e resumo semanal útil

Data: 2026-10-22 · Arquivos principais: `alertas_whatsapp.py`, `resumo_mensal.py`,
`routes_api_extras.py`, `routes_registros.py`, `animais.py`, `templates/configuracoes.html`

## Objetivo

As notificações por WhatsApp (CallMeBot) hoje mandam o mesmo texto para todos e o resumo
semanal só mostra a situação atual, com linhas que se repetem toda semana sem mudar. Queremos:

1. Cada membro escolher o que recebe.
2. A família saber na hora quando morre ou nasce um animal.
3. O resumo de segunda contar o que aconteceu na semana e parar de repetir ruído.

Fora do escopo: aviso de venda/compra/gasto; mudanças no tratamento de falha de envio.

## 1. Preferências por pessoa

**Armazenamento** — em `usuarios.json`, dentro de `whatsapp`:

```json
"receber": {"urgentes": true, "semanal": true, "visita": true,
            "eventos": true, "mensal": true, "valores": true}
```

- Chave ausente (ou tipo ausente) = `true` → quem não mexer continua recebendo tudo.
- `alertas_ativos` continua como chave geral: `false` desliga tudo, independente de `receber`.
- Tipos: `urgentes` (Task diária, dias comuns), `semanal` (segunda), `visita` (aviso de visita
  nova), `eventos` (Morte/Perda e Nascimento), `mensal` (dia 1º). `valores` não é um tipo de
  mensagem: diz se a pessoa vê valores em R$.

**Envio** — `enviar_para_familia(msg, tipo=None, excluir_usuario="", msg_sem_valores=None)`:

- `tipo` informado → pula quem tem `receber[tipo] == false`. `tipo=None` (botão "enviar
  agora", chamadas antigas) mantém o comportamento atual.
- Para quem tem `receber["valores"] == false` envia `msg_sem_valores` quando ela for dada;
  sem ela, envia `msg`.
- Helper `quer_receber(info_whatsapp, tipo) -> bool` centraliza a regra (testável).

**Chamadores atualizados**

| Origem | tipo | sem valores |
|---|---|---|
| `main()` dias comuns | `urgentes` | sim (mesmo filtro de itens com valor) |
| `main()` segunda / `--semanal` | `semanal` | sim |
| Fila de pendentes — visita | `visita` | não precisa |
| Fila de pendentes — morte/nascimento | `eventos` | sim |
| `resumo_mensal.py` | `mensal` | sim |
| Botão "enviar alertas agora" (`routes_api_extras`) | `None` | — |

**Itens com valor** — cada item de `montar_itens` ganha `"valores": bool` (hoje só `fin:resumo`).
`montar_msg_urgente` / `montar_msg_semanal` recebem `com_valores=True`; com `False` descartam
itens marcados. `main()` monta as duas versões e passa ambas.

**Estado de "já enviado"** — continua global (por chave de item), como hoje.

**Tela** — Configurações → WhatsApp ganha o bloco "O que você quer receber" com 6 caixinhas:
🚨 Alertas urgentes (diário) · 📅 Resumo semanal (segunda) · 🏡 Aviso de visita ·
🐄 Morte / Nascimento · 📊 Resumo mensal (dia 1º) · 💰 Mostrar valores em R$.
`GET /api/config-whatsapp` devolve `receber` (com os padrões preenchidos); `POST` aceita e
grava `receber` (só as 6 chaves conhecidas, booleanas). `/api/config-whatsapp-todos` devolve
`receber` e a lista "Status de todos os usuários" mostra um resumo (ex.: "só urgentes e visita").

## 2. Aviso de Morte/Perda e Nascimento

**Função nova** em `alertas_whatsapp.py`:

```python
avisar_manejo(tipo, qtd, brincos="", de="", descricao="", registrado_por="")
```

- Só age para `tipo in ("Morte/Perda", "Nascimento")`; outros tipos → nada.
- Monta duas versões e chama `guardar_aviso_pendente(msg, tipo="eventos",
  excluir=registrado_por, msg_sem_valores=...)`.
- Exemplos:
  - `🍼 *Nasceu* 1 bezerro — Amarelo 21 · de Mae` + `_registrado por Deyvid_`
  - `🚨 *Morte/Perda:* 1 cab. — Amarelo 21 · perda de Nilson` + descrição/motivo;
    versão com valores acrescenta `💸 ~R$ 3.111/cab. (custo médio atual)`, obtido de
    `calcular_resumo_financeiro(...)["ctcab"]` (sem "de": "rateada entre os três").
- Falha ao montar/guardar nunca derruba o registro (try/except + log, como a visita).

**Fila de pendentes** — cada item passa a ter `{"msg", "tipo", "excluir", "msg_sem_valores",
"criado"}`. Itens antigos (só `msg`) continuam funcionando: `tipo` ausente → `visita`.
O aviso de visita só ganha `tipo="visita"`; continua indo para todos, inclusive quem registrou
(comportamento atual).

**Pontos de chamada** (só criação; edição não avisa de novo):

1. `routes_registros.novo_manejo` — após `salvar_linha`, e o redirect passa a usar
   `_enviar_avisos_depois` para disparar o envio após a resposta.
2. `animais.cadastrar` — quando grava a linha de Nascimento.
3. `animais.dar_baixa` — quando grava a Morte/Perda (uma chamada por dono gravado).
   As rotas de `routes_animais.py` que chamam esses dois passam a usar `_enviar_avisos_depois`
   (ou equivalente) na resposta. Caminhos de voz que reutilizam essas funções herdam o aviso.

Se a conexão cair antes do envio, a Task diária esvazia a fila (comportamento já existente).

## 3. Resumo semanal útil

**Seção nova "📆 *Na semana*"** (últimos 7 dias, `hoje-7 < Data <= hoje`), montada por
`resumo_semana(dados, hoje) -> list[dict]` (itens com `valores` marcados quando têm R$):

- 🏡 Visitas: N (por Fulano, Ciclano) · 🌧️ chuva somada X mm (se houver)
- 🧾 Gastos: N lançamentos — R$ total *(valores)*
- 🛒 Compras: N cab. — R$ *(R$ só com valores)*; 💰 Vendas: N cab. — R$ *(idem)*
- 💉 Manejos: tipos feitos (ex.: "Vacina Aftosa (28 cab.), Vermífugo (28 cab.)"), sem
  Morte/Nascimento
- 🍼 Nascimentos: N · ⚰️ Mortes/perdas: N (só se houver)
- Nada nos 7 dias → "Semana sem registros."

Na versão sem valores, as linhas de compra/venda aparecem só com cabeças e a de gastos só com
a quantidade de lançamentos.

**Removido do semanal**
- `saude:<tipo>:sem` ("X: nenhum registro ainda") — deixa de ser gerado.
- `fin:negativo` ("Resultado realizado: R$ -…") — deixa de ser gerado.
- `fin:resumo` continua, marcado `valores=True`.

**Brucelose por animal** — `montar_itens` usa `animais.janela_brucelose(df_animais, df_m, hoje)`:
- situação "na janela" → item semanal `💉 Brucelose: Amarelo 21 — vacinar até 05/12/2026`;
  vira **urgente** quando faltam ≤ 15 dias para o fim da janela (240 dias de idade),
  chave `brucelose:<ID>`, `repetir=3`.
- "chegando" → item semanal `🗓️ Brucelose: Amarelo 21 entra na janela em N dias`.
- Erro ao ler Animais → log, segue sem o item.

**Resumo mensal sem valores** — `montar_resumo_mensal(dados, ano, mes, com_valores=True)`.
Com `False`: compras/vendas só com cabeças, sem linha de gastos em R$ (mostra nº de
lançamentos), rebanho só com cabeças, sem custo médio, capital e resultado por dono.
`main()` monta as duas e chama `enviar_para_familia(msg, tipo="mensal", msg_sem_valores=...)`.

## Testes (pytest, sem enviar nada — `enviar_whatsapp` simulado)

- `quer_receber`: padrão sem chave = true; `alertas_ativos=false` vence; tipo desmarcado.
- `enviar_para_familia`: filtra por tipo, pula `excluir_usuario`, manda `msg_sem_valores` a
  quem desligou valores, `tipo=None` = comportamento antigo.
- `/api/config-whatsapp`: grava e devolve `receber`; ignora chaves desconhecidas.
- `avisar_manejo`: Nascimento e Morte geram item na fila com tipo/excluir; outro tipo não.
- Os 3 caminhos de gravação (form de manejo, cadastro com origem Nascimento, baixa por morte)
  deixam o aviso na fila — numa cópia dos dados (conftest).
- Fila antiga (só `msg`) continua sendo enviada.
- `resumo_semana` com datas fixas: conta só os 7 dias; "Semana sem registros"; versão sem R$.
- Semanal não contém "nenhum registro ainda" nem "Resultado realizado".
- Brucelose: 200 dias (faltam 40) → semanal; 230 dias (faltam 10, ≤ 15) → urgente.
- `montar_resumo_mensal(com_valores=False)` não contém "R$".
- `python -m pytest` completo passando; `alertas_whatsapp.py --teste --semanal` e
  `resumo_mensal.py --teste` conferidos à mão.

## Documentação

- `CLAUDE.md`: linha de `alertas_whatsapp.py` menciona preferências e aviso de eventos.
- Aba Ajuda (`templates/ajuda.html`): parágrafo sobre as caixinhas do WhatsApp (print
  atualizado fica como pendência).
