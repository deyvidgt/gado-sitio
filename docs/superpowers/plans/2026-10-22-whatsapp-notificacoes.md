# WhatsApp — preferências, eventos e resumo semanal: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada membro escolhe o que recebe no WhatsApp; Morte/Perda e Nascimento avisam na hora; o resumo semanal conta a semana e para de repetir ruído.

**Architecture:** Tudo passa por `alertas_whatsapp.enviar_para_familia`, que ganha filtro por `tipo` e versão sem valores. Os itens do relatório ganham a marca `valores`. Os avisos de evento usam a fila de pendentes que a visita já usa, que agora guarda `tipo`, `excluir` e `msg_sem_valores`.

**Tech Stack:** Python 3 / Flask / pandas / pytest; Jinja + JS puro em `templates/configuracoes.html`.

**Spec:** `docs/superpowers/specs/2026-10-22-whatsapp-notificacoes-design.md`

## Global Constraints

- Código, mensagens e UI em português; comentários explicam o porquê.
- Testes **nunca enviam** WhatsApp de verdade: simular `alertas_whatsapp.enviar_whatsapp` ou `enviar_para_familia`.
- Testes que gravam usam a fixture `dados_restaurados` (cópia temporária dos dados, ver `tests/conftest.py`).
- Sem chave `receber`, ou sem um tipo dentro dela, vale `true`: quem não mexer continua recebendo tudo. `alertas_ativos == false` desliga tudo.
- As chaves de `receber` são exatamente: `urgentes`, `semanal`, `visita`, `eventos`, `mensal`, `valores`.
- As chaves de `usuarios.json` são logins em minúsculas (`geane`, `deyvid`, `nilson`, `nd`). `excluir_usuario` chega como membro (`Mae`/`Deyvid`/`Nilson`) ou login. A comparação usa o mapa de `routes_animais._membro_logado` (`geane`/`mae` → `Mae`) e ignora maiúsculas.
- Não alterar colunas das abas do Excel (não precisa: nada novo é gravado no `.xlsx`).
- `python -m pytest` inteiro passando ao fim de cada task.

## Review Focus

- **`usuarios.json` antigo, sem `receber`:** tem que receber tudo como hoje. Teste em Task 1 (`test_sem_receber_recebe_tudo`).
- **Fila de pendentes gravada antes da atualização** (itens só com `msg`): ainda tem que ser enviada como visita. Teste em Task 1 (`test_fila_antiga_sem_tipo`).
- **Quem registrou a morte loga como `geane`, mas o aviso traz `Mae`:** essa pessoa não pode receber o próprio aviso. Teste em Task 1 (`test_excluir_por_membro_ou_login`).
- **Morte pela baixa de animal com 2 donos**, que grava 2 linhas no Manejo: são 2 avisos, um por dono, nunca zero. Teste em Task 5 (`test_baixa_morte_dois_donos_dois_avisos`).
- **Animal sem `Nascimento` ou com aba Animais vazia:** a brucelose não pode derrubar o relatório. Teste em Task 3 (`test_itens_sem_animais_nao_quebra`).

---

### Task 1: Preferências no envio (`quer_receber`, `enviar_para_familia`, fila)

**Files:**
- Modify: `alertas_whatsapp.py` (`enviar_para_familia`, `guardar_aviso_pendente`, `enviar_avisos_pendentes`)
- Modify: `tests/test_v42.py`, `tests/test_resumo_mensal.py`, `tests/test_fotos.py`, `tests/test_paginas.py`: os dublês `lambda msg: ...` passam a ser `lambda msg, **kw: ...`
- Test: `tests/test_whatsapp_prefs.py` (novo)

**Interfaces:**
- Produces:
  - `TIPOS_RECEBER = ("urgentes", "semanal", "visita", "eventos", "mensal", "valores")`
  - `receber_de(cfg_whatsapp: dict) -> dict[str, bool]` devolve as 6 chaves com os padrões preenchidos.
  - `quer_receber(cfg_whatsapp: dict, tipo: str | None) -> bool`. Com `tipo=None`, só olha `alertas_ativos`.
  - `enviar_para_familia(msg: str, excluir_usuario: str = "", tipo: str | None = None, msg_sem_valores: str | None = None) -> int`. `excluir_usuario` continua sendo o 2º parâmetro posicional, para não quebrar chamadas antigas.
  - `guardar_aviso_pendente(msg: str, tipo: str = "visita", excluir: str = "", msg_sem_valores: str | None = None) -> None`
  - `enviar_avisos_pendentes()` repassa `tipo`, `excluir` e `msg_sem_valores` de cada item. Item sem `tipo` vale como `"visita"`.

- [x] **Step 1: Escrever os testes que falham.** Em `tests/test_whatsapp_prefs.py`, simular `carregar_usuarios` com 3 usuários e `enviar_whatsapp` com uma função que guarda `(telefone, msg)`:
  - `test_sem_receber_recebe_tudo`: usuário só com telefone e apikey → `quer_receber(cfg, t)` é True para os 6 tipos.
  - `test_alertas_ativos_false_vence`: `{"alertas_ativos": False, "receber": {"semanal": True}}` → `quer_receber(cfg, "semanal") is False` e `quer_receber(cfg, None) is False`.
  - `test_filtra_por_tipo`: `nilson` com `receber.semanal=False`; `enviar_para_familia("X", tipo="semanal") == 2` e o telefone do nilson não aparece entre os enviados.
  - `test_msg_sem_valores`: `geane` com `receber.valores=False`; `enviar_para_familia("COM R$", tipo="semanal", msg_sem_valores="SEM")` → geane recebe `"SEM"` e os outros `"COM R$"`.
  - `test_tipo_none_comportamento_antigo`: `tipo=None` ignora `receber` (nilson com `semanal=False` recebe).
  - `test_excluir_por_membro_ou_login`: `excluir_usuario="Mae"` não envia para `geane`; `excluir_usuario="deyvid"` não envia para `deyvid`.
  - `test_fila_antiga_sem_tipo`: gravar em `_pendentes_path()` o JSON `[{"msg": "velha", "criado": "2026-10-01T10:00:00"}]`, simular `enviar_para_familia` como `lambda msg, **kw: chamadas.append((msg, kw)) or 1` → `enviar_avisos_pendentes() == 1` e `chamadas[0][1]["tipo"] == "visita"`.
  - `test_fila_guarda_tipo_e_excluir`: `guardar_aviso_pendente("m", tipo="eventos", excluir="Deyvid", msg_sem_valores="s")` e depois enviar → kwargs `{"tipo": "eventos", "excluir_usuario": "Deyvid", "msg_sem_valores": "s"}`.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_whatsapp_prefs.py -v`: FAIL (`quer_receber` não existe).
- [x] **Step 3: Implementar** as interfaces acima em `alertas_whatsapp.py`. O membro de cada login sai de um dicionário `_LOGIN_MEMBRO = {"geane": "Mae", "mae": "Mae", "deyvid": "Deyvid", "nilson": "Nilson"}`, comparando em minúsculas. Atualizar os dublês nos 4 arquivos de teste já existentes.
- [x] **Step 4: Rodar.** `python -m pytest -q`: tudo PASS.
- [x] **Step 5: Commit.** `git commit -m "WhatsApp: preferencias por pessoa no envio e na fila de avisos"`

### Task 2: Tela e API de preferências

**Files:**
- Modify: `routes_api_extras.py` (`api_config_whatsapp`, `api_config_whatsapp_todos`)
- Modify: `templates/configuracoes.html` (bloco `#cfg-wpp-form`, `carregarCfgWpp`, `salvarCfgWpp`, `carregarTodosWpp`)
- Test: `tests/test_whatsapp_prefs.py`

**Interfaces:**
- Consumes: `alertas_whatsapp.receber_de`, `TIPOS_RECEBER`
- Produces:
  - `GET /api/config-whatsapp` → acrescenta `"receber": {6 chaves: bool}`.
  - `POST` aceita `"receber"` e grava só as chaves de `TIPOS_RECEBER`, como `bool`. Sem `receber` no corpo, mantém o que já estava salvo.
  - `/api/config-whatsapp-todos` → cada usuário ganha `"receber"`.

- [x] **Step 1: Testes que falham.** Usar o fixture `cliente` e copiar e restaurar `usuarios.json` da pasta de teste, com um fixture local `usuarios_restaurados`:
  - `test_api_grava_e_devolve_receber`: POST `{"telefone": "5534999", "apikey": "k", "bot_number": "+34644663262", "receber": {"semanal": False, "xyz": True}}` → GET devolve `receber["semanal"] is False`, `receber["visita"] is True` e não tem a chave `"xyz"`.
  - `test_api_post_sem_receber_mantem`: depois do teste acima, um POST sem `receber` → GET continua com `semanal False`.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_whatsapp_prefs.py -k api -v`: FAIL.
- [x] **Step 3: Implementar a API.** O POST hoje recria o dicionário `whatsapp` do zero, então `receber` precisa ser copiado de `cfg_atual` quando não vier no corpo.
- [x] **Step 4: Tela.** Dentro de `#cfg-wpp-form`, logo abaixo do checkbox `cfg-wpp-ativo`, entra o bloco "📱 O que você quer receber" com 6 checkboxes `id="cfg-wpp-rec-<tipo>"`. Os rótulos são exatamente: `🚨 Alertas urgentes (diário)`, `📅 Resumo semanal (segunda)`, `🏡 Aviso de visita`, `🐄 Morte / Nascimento`, `📊 Resumo mensal (dia 1º)`, `💰 Mostrar valores em R$`.
  - `carregarCfgWpp` preenche os checkboxes.
  - `salvarCfgWpp` manda `receber` no corpo.
  - `carregarTodosWpp` ganha a coluna "Recebe", com os tipos desligados ("sem semanal, sem R$"), ou "Tudo" quando nada está desligado.
  - Conferir na página com `python app.py`, no celular (largura 375 px) e no modo escuro.
- [x] **Step 5: Rodar.** `python -m pytest -q`: PASS.
- [x] **Step 6: Commit.** `git commit -m "Configuracoes: caixinhas do que cada um recebe no WhatsApp"`

### Task 3: Itens com valor, fim do ruído e brucelose por animal

**Files:**
- Modify: `alertas_whatsapp.py` (`montar_itens`, `montar_msg_urgente`, `montar_msg_semanal`, `main`)
- Test: `tests/test_whatsapp_semanal.py` (novo)

**Interfaces:**
- Consumes: `enviar_para_familia(..., tipo=, msg_sem_valores=)` (Task 1), `animais.carregar()`, `animais.janela_brucelose(df, df_man, hoje)`, `animais.fmt_brinco(cor, num)`
- Produces:
  - Cada item tem `"valores": bool`. `item(..., valores=False)` ganha o parâmetro; `fin:resumo` usa `valores=True`.
  - `montar_msg_urgente(itens, hoje=None, com_valores=True) -> str`
  - `montar_msg_semanal(itens, hoje=None, com_valores=True, semana=None) -> str`. O parâmetro `semana` é usado na Task 4.
  - Constante `BRUCELOSE_URGENTE_DIAS = 15`.

- [x] **Step 1: Testes que falham.** Simular `alertas_whatsapp.carregar_todas` com DataFrames montados no teste e `animais.carregar` com um DataFrame de animais (colunas `COLUNAS_ANIMAIS`, `Nascimento` em Timestamp):
  - `test_semanal_sem_ruido`: Manejo sem nenhuma Pesagem e venda com prejuízo → `montar_msg_semanal(itens)` não contém `"nenhum registro ainda"` nem `"Resultado realizado"`.
  - `test_semanal_sem_valores_tira_rs`: `montar_msg_semanal(itens, com_valores=False)` não contém `"R$"`; a versão com valores contém `"Rebanho:"`.
  - `test_brucelose_semanal_200_dias`: fêmea viva, Amarelo 21, nascida 200 dias antes de `hoje` → existe um item `brucelose:<ID>` com `urgente False` e o texto contém `"Amarelo 21"` e `"vacinar até"`.
  - `test_brucelose_urgente_230_dias`: 230 dias → `urgente True`, `repetir == 3`.
  - `test_brucelose_chegando`: 70 dias → item não urgente com o texto `"entra na janela em 20 dias"`.
  - `test_itens_sem_animais_nao_quebra`: `animais.carregar` levanta `Exception` → `montar_itens` devolve itens normalmente, sem nenhum item de brucelose.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_whatsapp_semanal.py -v`: FAIL.
- [x] **Step 3: Implementar.**
  - Remover a geração de `saude:<tipo>:sem` e de `fin:negativo`.
  - Brucelose: para cada saída de `janela_brucelose`, `faltam = 240 - idade_em_dias`.
    - Situação "na janela": texto `💉 Brucelose: {fmt_brinco} — {msg}`; `urgente = faltam <= BRUCELOSE_URGENTE_DIAS`, `repetir=3`.
    - Situação "chegando": texto `🗓️ Brucelose: {fmt_brinco} {msg}`, não urgente.
    - Tudo dentro de try/except com `logging.error`.
  - `main()`:
    - Monta a mensagem com valores e sem valores.
    - Dias comuns: `enviar_para_familia(msg, tipo="urgentes", msg_sem_valores=...)`.
    - Segunda: `tipo="semanal"`.
    - Com `--teste`, imprime a versão com valores e depois a sem valores, sob o título `--- sem valores ---`.
- [x] **Step 4: Rodar.** `python -m pytest -q`: PASS. Depois, `PYTHONIOENCODING=utf-8 python alertas_whatsapp.py --teste --semanal`: sem "Pesagem: nenhum registro".
- [x] **Step 5: Commit.** `git commit -m "WhatsApp: semanal sem linhas repetidas, valores por pessoa, brucelose por animal"`

### Task 4: Seção "Na semana"

**Files:**
- Modify: `alertas_whatsapp.py` (função nova `resumo_semana`; `main` e `montar_msg_semanal` passam a usá-la)
- Test: `tests/test_whatsapp_semanal.py`

**Interfaces:**
- Consumes: `montar_msg_semanal(..., semana=)` (Task 3)
- Produces: `resumo_semana(dados: dict[str, pd.DataFrame], hoje: datetime) -> list[dict]`. Cada linha é `{"texto": str, "texto_sem_valores": str}`. A janela vai de `hoje - 7 dias` (exclusivo) até `hoje` (inclusivo), comparando datas sem hora. Em `montar_msg_semanal`, a seção `📆 *Na semana*` entra depois de "Atenção" e antes do resto. Sem nenhuma linha, a seção mostra `Semana sem registros.`

Linhas, nesta ordem, cada uma só se houver registro:

| Linha | Com valores | Sem valores |
|---|---|---|
| Visitas | `🏡 Visitas: 2 (Deyvid, Nilson) · 🌧️ chuva 35 mm` (a chuva só aparece se a soma for > 0) | igual |
| Gastos | `🧾 Gastos: 3 lançamentos — R$ 1.250,00` | `🧾 Gastos: 3 lançamentos` |
| Compras | `🛒 Compras: 5 cab. — R$ 15.000,00` | `🛒 Compras: 5 cab.` |
| Vendas | `💰 Vendas: 4 cab. — R$ 14.000,00` | `💰 Vendas: 4 cab.` |
| Manejos | `💉 Manejos: Vacina Aftosa (28 cab.), Vermífugo (28 cab.)` (por Tipo, somando `Qtd Cabeças`, sem Nascimento e Morte/Perda) | igual |
| Nascimentos/mortes | `🍼 Nascimentos: 1 · ⚰️ Mortes/perdas: 1` (só a parte que for diferente de zero) | igual |

- [x] **Step 1: Testes que falham.**
  - `test_semana_conta_so_7_dias`: hoje = 2026-10-26. Gasto em 2026-10-19, que fica fora da janela por ser exclusivo, e gasto em 2026-10-20 de R$ 100 → a linha de gastos diz `1 lançamentos — R$ 100,00`.
  - `test_semana_vazia`: a mensagem contém `"Semana sem registros."`
  - `test_semana_sem_valores`: compra de 5 cab. → a versão sem valores tem `"🛒 Compras: 5 cab."` e nenhum `"R$"`.
  - `test_semana_manejo_e_nascimento`: Vacina Aftosa (28) e Nascimento (1) → a linha de manejos não cita Nascimento e existe a linha `🍼 Nascimentos: 1`.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_whatsapp_semanal.py -k semana -v`: FAIL.
- [x] **Step 3: Implementar** `resumo_semana`. Usar `_soma` e `fmt_r` no mesmo padrão de `resumo_mensal.py`. `main()` chama `resumo_semana(carregar_todas(), hoje)`; o `montar_itens` já carrega os dados, então reutilizar o mesmo dicionário em vez de abrir o `.xlsx` de novo.
- [x] **Step 4: Rodar.** `python -m pytest -q`: PASS. Depois, `python alertas_whatsapp.py --teste --semanal` mostra a seção.
- [x] **Step 5: Commit.** `git commit -m "WhatsApp: resumo semanal com o que aconteceu na semana"`

### Task 5: Aviso de Morte/Perda e Nascimento

**Files:**
- Modify: `alertas_whatsapp.py` (função nova `avisar_manejo`)
- Modify: `routes_registros.py` (`novo_manejo`)
- Modify: `animais.py` (`cadastrar`, `dar_baixa`)
- Modify: `routes_animais.py`: as 4 respostas que chamam `A.cadastrar`/`A.dar_baixa` (linhas ~120, 180, 269, 371/381) passam pelo `_enviar_avisos_depois`
- Test: `tests/test_whatsapp_eventos.py` (novo)

**Interfaces:**
- Consumes: `guardar_aviso_pendente(msg, tipo=, excluir=, msg_sem_valores=)` (Task 1); `routes_visitas._enviar_avisos_depois(resposta)` (já existe; importar de lá)
- Produces: `avisar_manejo(tipo: str, qtd: int, brincos: str = "", de: str = "", descricao: str = "", registrado_por: str = "") -> bool`. Retorna True se guardou o aviso. Nunca levanta exceção: em caso de erro, faz `logging.error` e retorna False.

Textos (exatos):
- Nascimento: `🍼 *Nasceu* {qtd} bezerro(s){ — brincos}{ · de {de}}` + linha `_registrado por {registrado_por}_`. É igual com e sem valores.
- Morte/Perda: `🚨 *Morte/Perda:* {qtd} cab.{ — brincos}` + ` · perda de {de}`, ou ` · rateada entre os três` quando não houver "de"; depois a descrição em linha própria, se houver, e `_registrado por …_`.
  - A versão com valores acrescenta `💸 ~{fmt_r(ctcab)}/cab. (custo médio atual)`, com o `ctcab` de `calcular_resumo_financeiro` sobre `carregar_todas()`. Se der erro aí, a linha some.
- `brincos` vem como `"Amarelo 21 #A0003, Azul 05 #A0010"`. Na mensagem sai sem o `#Axxxx`: `Amarelo 21, Azul 05`.

- [x] **Step 1: Testes que falham.** Usar `dados_restaurados` e o fixture `fila_avisos_vazia` (mover de `test_v42.py` para `conftest.py`).
  - `test_avisar_nascimento_vai_para_fila`: `avisar_manejo("Nascimento", 1, "Amarelo 21 #A0003", "Mae", registrado_por="Deyvid")` → a fila tem 1 item com `tipo == "eventos"` e `excluir == "Deyvid"`; a msg contém `"Amarelo 21"` e não contém `"#A0003"`.
  - `test_avisar_morte_com_e_sem_valores`: `msg` contém `"R$"` e `msg_sem_valores` não contém.
  - `test_avisar_outro_tipo_nao_faz_nada`: `avisar_manejo("Vacina Aftosa", 28)` → retorna False e a fila não existe.
  - `test_form_manejo_avisa`: POST `/manejo/novo` com `tipo=Nascimento`, `cabecas=1`, `nascimento_de=Mae` e CSRF, com `enviar_para_familia` simulado (`lambda msg, **kw`) → depois de `r.close()`, 1 chamada com `kw["tipo"] == "eventos"`.
  - `test_form_manejo_vacina_nao_avisa`: o mesmo POST com `tipo=Vacina Aftosa` e `produto=X` → 0 chamadas.
  - `test_cadastro_nascimento_avisa`: `animais.cadastrar([{... "Origem": "Nascimento" ...}], registrado_por="Deyvid")` → 1 item na fila.
  - `test_baixa_morte_dois_donos_dois_avisos`: cadastrar 2 animais de donos diferentes (cores de donos diferentes) com Origem "Compra", depois `dar_baixa([id1, id2], "Morto", registrar_morte=True)` (usar os nomes de parâmetro reais da função) → 2 itens na fila.
  - `test_editar_manejo_nao_avisa`: POST de edição de um Nascimento já existente → a fila não existe.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_whatsapp_eventos.py -v`: FAIL.
- [x] **Step 3: Implementar.**
  - `avisar_manejo` em `alertas_whatsapp.py`.
  - Chamá-la logo depois de cada `salvar_linha("Manejo", ...)` de Morte/Perda e de Nascimento em `animais.cadastrar` e `animais.dar_baixa`, e em `novo_manejo`. Nunca nas rotas de edição.
  - `novo_manejo` retorna `_enviar_avisos_depois(redirect(...))`.
  - As 4 respostas de `routes_animais.py` também passam pelo `_enviar_avisos_depois`.
- [x] **Step 4: Rodar.** `python -m pytest -q`: PASS.
- [x] **Step 5: Commit.** `git commit -m "WhatsApp: aviso na hora de Morte/Perda e Nascimento"`

### Task 6: Resumo mensal sem valores

**Files:**
- Modify: `resumo_mensal.py` (`montar_resumo_mensal`, `main`)
- Test: `tests/test_resumo_mensal.py`

**Interfaces:**
- Consumes: `enviar_para_familia(..., tipo=, msg_sem_valores=)` (Task 1)
- Produces: `montar_resumo_mensal(dados, ano, mes, com_valores: bool = True) -> str`

Com `com_valores=False`:
- Compras e vendas aparecem só com cabeças (`🛒 Compras: 5 cab`).
- A linha de gastos vira `🧾 Gastos: N lançamentos`.
- O rebanho mostra só `🐄 N cabeças`.
- Saem o custo médio, o capital e o "Resultado acumulado por dono".

- [x] **Step 1: Testes que falham.**
  - `test_mensal_sem_valores`: com os dados de teste já usados no arquivo, `montar_resumo_mensal(dados, ano, mes, com_valores=False)` não contém `"R$"` e contém `"cabeças"`.
  - Ajustar o teste de envio existente para conferir `kw["tipo"] == "mensal"` e que `kw["msg_sem_valores"]` não contém `"R$"`.
- [x] **Step 2: Rodar e ver falhar.** `python -m pytest tests/test_resumo_mensal.py -v`: FAIL.
- [x] **Step 3: Implementar** e chamar `enviar_para_familia(msg, tipo="mensal", msg_sem_valores=msg_sv)`. No `--teste`, imprimir as duas versões.
- [x] **Step 4: Rodar.** `python -m pytest -q`: PASS. Depois, `python resumo_mensal.py --teste`.
- [x] **Step 5: Commit.** `git commit -m "Resumo mensal: versao sem valores para quem desmarcou R$"`

### Task 7: Documentação

**Files:**
- Modify: `CLAUDE.md`
  - Linha de `alertas_whatsapp.py` na tabela: incluir preferências por pessoa (`receber`), aviso de Morte/Nascimento e "Na semana".
  - Tabela de `docs/`: o design do WhatsApp passa a "entregue" e entra a linha deste plano.
- Modify: `CHANGELOG.md`: trocar o item "Planejado" de [Não lançado] por "### Novo", com as 5 mudanças em linguagem de usuário.
- Modify: `templates/ajuda.html`: na seção de Configurações/WhatsApp, um parágrafo sobre as caixinhas e sobre o aviso de Morte/Nascimento. O print novo fica como pendência, registrada no CHANGELOG.

- [x] **Step 1: Editar os três arquivos.**
- [x] **Step 2:** `python -m pytest -q`: PASS (`test_paginas` abre `/ajuda`).
- [x] **Step 3: Commit.** `git commit -m "Docs: WhatsApp com preferencias e avisos de eventos"`
