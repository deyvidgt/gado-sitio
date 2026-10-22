# Fotos e histórico dos animais (Google Drive) — Design

**Data:** 2026-10-16 · **Versão alvo:** v4.4 · **Status:** ✅ entregue em 16/10/2026 (v4.4,
commit `f0b3cd7`; correções em `44734a2`). Guia de operação: `docs/FOTOS_DRIVE.md`.

> Pendências adiadas da revisão (decisão do usuário): regex de ID sem `$`, foto HEIC não
> exibível no navegador, Pillow fora do `requirements.txt`, `limpar_cache` sem try/except,
> "Enviado Em" vira datetime se o `.xlsx` for salvo no Excel, sem nova tentativa em 401,
> teste do Drive a cada execução dos alertas.

## 1. Objetivo

Cada animal com brinco (aba `Animais`) ganha uma **linha do tempo de fotos** na sua ficha,
servindo a três usos ao mesmo tempo:

- **Identificação** — foto de perfil, para reconhecer o animal se o brinco cair;
- **Evolução** — fotos datadas ao longo do tempo (crescimento/engorda);
- **Ocorrências** — machucado, doença, parto, tratamento.

Os arquivos ficam na pasta do Google Drive da família:
`https://drive.google.com/drive/folders/1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt`
(dona: conta `nilsondavid45@gmail.com`).

### Decisões tomadas com o usuário

| Pergunta | Decisão |
|---|---|
| Quem envia fotos | **Todos os usuários logados** (Mae, Deyvid, Nilson); cada foto guarda quem enviou |
| Uso das fotos | **Todos** (D): uma linha do tempo única, com campo *Tipo* e uma foto *Principal* |
| Sinal no sítio | **Envia na hora e, sem sinal, guarda no celular** e envia depois (como as visitas) |
| Armazenamento | **Abordagem 1**: Drive via OAuth da conta dona da pasta; site faz proxy (fotos privadas) |

### Critérios de sucesso

1. No celular, na ficha do animal, tirar uma foto e vê-la na linha do tempo em segundos (com sinal).
2. Sem sinal, a foto aparece como "⏳ aguardando sinal" e sobe sozinha quando a conexão volta, sem duplicar.
3. A foto principal aparece na ficha e como miniatura na lista de animais.
4. As fotos só são visíveis para quem está logado no site.
5. Sem o Drive configurado, o site continua funcionando normalmente (fotos desligadas).
6. Nenhum cálculo financeiro é afetado; as 3 invariantes contábeis seguem passando.

## 2. Arquitetura

```
celular ──(JPEG reduzido, id_envio)──► POST /api/fotos ──► fotos.py ──► drive.py ──► Google Drive
   │  sem sinal: IndexedDB (fila_fotos.js)                    │
   │                                                          └──► aba "Fotos" (gado_familia.xlsx)
   ◄── GET /fotos/<id>/mini · /fotos/<id> ◄── cache em ~/gado-dados/cache_fotos/ ◄── drive.py
```

### 2.1 `drive.py` — cliente mínimo da API do Drive

- Usa só `requests` (já é dependência). **Não** adiciona `google-api-python-client`.
- Lê `~/gado-dados/drive_token.json` (resolvido pela mesma pasta de dados de `db.py`), contendo
  `client_id`, `client_secret`, `refresh_token` e `pasta_raiz` (ID da pasta).
- `configurado() -> bool` — o arquivo existe e tem os campos.
- Renova o *access token* sozinho (`https://oauth2.googleapis.com/token`), guardando-o em memória até expirar.
- `pasta_animal(id_animal, nome) -> folder_id` — acha (pela `appProperties.animal`) ou cria a subpasta
  `A0003 - Amarelo 21` **dentro da pasta raiz**. Se o brinco mudar, a pasta é achada pelo ID e não por nome.
- `enviar(folder_id, nome, bytes, mime, props) -> file_id` — upload *multipart*, com `appProperties`
  (`id_envio`, `animal`, `id_foto`).
- `achar_por_envio(id_envio) -> file_id | None` — busca por `appProperties has {key='id_envio' ...}`.
- `baixar(file_id) -> bytes`; `lixeira(file_id)` (`trashed=true`, recuperável por 30 dias).
- `testar() -> (ok, mensagem)` — confere token e acesso à pasta raiz (nome da pasta).
- Erros de rede/HTTP viram a exceção `DriveErro` (mensagem em português).
- Escopo OAuth: `https://www.googleapis.com/auth/drive`, porque o escopo `drive.file` não acessa uma
  pasta já existente. Para compensar, o código **só opera dentro da pasta raiz fixa**.

### 2.2 `fotos.py` — regras de negócio

- `carregar() -> DataFrame` da aba `Fotos`.
- `enviar(id_animal, conteudo, data, tipo, legenda, enviado_por, id_envio) -> dict`:
  1. se o `id_envio` já existe na aba → devolve `{"duplicada": True}`;
  2. valida: o animal existe; é imagem de verdade (assinatura JPEG/PNG/WebP/HEIC); ≤ 8 MB;
     tipo ∈ {Perfil, Evolução, Ocorrência};
  3. procura arquivo órfão com o `id_envio` no Drive (`achar_por_envio`); se não houver, faz o upload;
  4. grava a linha na aba `Fotos` (posicional, `COLUNAS_FOTOS`);
  5. se for a 1ª foto do animal ou o tipo for *Perfil* e não houver principal → marca como `Principal`.
- `listar(id_animal)` — mais recente primeiro (Data, depois Enviado Em).
- `principal(id_animal)` / `principais() -> {id_animal: id_foto}` (para a lista de animais).
- `definir_principal(id_foto)` — garante **uma só** principal por animal.
- `editar(id_foto, tipo, legenda, data)`.
- `excluir(id_foto)` — backup (`fazer_backup_seguro`), lixeira do Drive, remove a linha.
  Se era a principal, a mais recente restante vira principal.
- Nomes no Drive: `AAAA-MM-DD_F00042.jpg`.

### 2.3 Aba `Fotos` (`config.py: COLUNAS_FOTOS`)

```
ID Foto · Animal · Data · Tipo · Legenda · Principal · Drive ID · Enviado Por · Enviado Em · ID Envio
```

- `ID Foto` sequencial `F00001`; `Animal` = ID do animal (`A0003`); `Data` em `dd/mm/aaaa`;
  `Principal` = `Sim` ou vazio; `Enviado Em` = `dd/mm/aaaa HH:MM`.
- `db.inicializar()` cria a aba quando faltar, sem tocar nas demais (mesmo mecanismo de migração).
- Colunas novas futuras vão **sempre no final**.

## 3. Telas

### 3.1 Ficha do animal (`templates/ficha_animal.html`)

- Foto principal grande no topo (ou espaço "Sem foto ainda" com o botão de câmera).
- Seção **📷 Fotos**: miniaturas agrupadas por data, com etiqueta do tipo, legenda e quem enviou.
- Botão **📷 Tirar foto**: `<input type="file" accept="image/*" capture="environment" multiple>`
  (também deixa escolher da galeria).
- Depois de escolher: mini formulário com **Tipo** (padrão *Evolução*), **Legenda** (com 🎤 de
  `voz_campos.js`) e **Data** (padrão hoje) → enviar.
- Tocar numa foto abre um visualizador com: ⭐ tornar principal · ✏️ editar · 🗑️ excluir
  (confirmação **na própria página**, sem `confirm()`).
- Fotos pendentes da fila do celular aparecem como "⏳ aguardando sinal", com a imagem local.
- Sem Drive configurado: "Fotos não configuradas — veja Configurações → Fotos".

### 3.2 Lista de animais (`templates/animais.html`)

- Miniatura redonda da principal ao lado do brinco; sem foto → bolinha na cor do brinco (como hoje).

### 3.3 Configurações → cartão "📷 Fotos" (em `templates/configuracoes.html`)

- Estado: "✅ Drive conectado — pasta *<nome>*" ou "❌ não configurado / token inválido".
- Botão **Testar conexão** (`drive.testar()`).

## 4. Envio e fila offline (`static/fila_fotos.js`)

Mesmo modelo de `static/fila_visitas.js`:

1. Reduz no celular (canvas): lado maior **1600 px**, JPEG qualidade ~0,82; gera `id_envio` (UUID).
   Se a redução falhar, envia o original (até 8 MB).
2. Tenta `POST /api/fotos` (multipart: `id_animal`, `foto`, `tipo`, `legenda`, `data`, `id_envio`,
   `csrf_token`), com tempo limite.
3. Falha de rede / tempo esgotado / `erro: "drive"` → guarda no IndexedDB `gado-offline`, store novo
   `fotos` (sobe a versão do banco de 1 para 2 **sem apagar** o store `visitas`).
4. Reenvio ao abrir qualquer página, no evento `online` e a cada minuto com pendências.
5. Selo no menu: "N fotos na fila".
6. Respostas `login`/`csrf` (401/403) mantêm a foto na fila e pedem para entrar de novo.

## 5. Rotas (novo `routes_fotos.py`, registrado em `app.py`)

| Rota | Método | Resposta |
|---|---|---|
| `/api/fotos` | POST | JSON `{ok, duplicada, id_foto}` ou `{ok:false, erro: login\|csrf\|drive\|invalida}`; nunca redireciona |
| `/fotos/<id_foto>` | GET | imagem inteira (login) |
| `/fotos/<id_foto>/mini` | GET | miniatura ~400 px (login) |
| `/fotos/<id_foto>/principal` | POST | define principal (login + CSRF) |
| `/fotos/<id_foto>/editar` | POST | tipo/legenda/data (login + CSRF) |
| `/fotos/<id_foto>/excluir` | POST | exclui (login + CSRF) |
| `/configuracoes/testar-drive` | POST | testa o Drive e volta para `/configuracoes` com flash (login + CSRF) |

- Imagens servidas com `Cache-Control: private, max-age=604800`.
- Miniaturas geradas no servidor **só se o Pillow estiver disponível** (já vem no PythonAnywhere, via
  `matplotlib`); senão, `/mini` devolve a imagem inteira.
- Cache em disco `~/gado-dados/cache_fotos/` (`<id_foto>.jpg` e `<id_foto>_mini.jpg`), limitado a
  ~200 MB: ao passar do limite, apaga os arquivos acessados há mais tempo.
- O `sw.js` não cacheia `/fotos/*` (o navegador já cacheia pelo cabeçalho); sobe `CACHE_VERSION`.

## 6. Erros e situações-limite

- **Drive fora do ar / token revogado** → `erro: "drive"`; a foto **fica na fila** do celular. O alerta
  diário de urgentes do WhatsApp avisa (no máximo 1x/dia) se `drive.testar()` falhar.
- **Ordem**: Drive primeiro, Excel depois. Órfão no Drive é inofensivo; o reenvio o reaproveita pelo
  `id_envio` (`achar_por_envio`).
- **Animal com baixa (vendido/morto)**: fotos continuam visíveis; pasta no Drive nunca é apagada pelo site.
- **Animal excluído do cadastro**: as linhas da aba `Fotos` ficam (histórico); a ficha não existe mais,
  os arquivos ficam no Drive.
- **Concorrência**: gravação na aba usa o mesmo mecanismo de `db.py` das demais abas.

## 7. Segurança

- Todas as rotas exigem login; as que alteram exigem CSRF (mesmo padrão de `/api/visitas`).
- `drive_token.json` fica em `~/gado-dados/` (fora do Git) e entra no `.gitignore` por garantia;
  `cache_fotos/` também.
- `id_foto` validado por regex (`^F\d{5}$`) antes de qualquer uso em caminho de arquivo.
- O código só cria/lê/apaga arquivos com pai dentro da pasta raiz configurada.

## 8. Configuração (uma vez)

1. Google Cloud: criar projeto → ativar **Google Drive API** → tela de consentimento
   (tipo *Externo*) → publicar **Em produção** (em *Teste*, o token expira em 7 dias) → credencial
   **OAuth "App para computador"**.
2. No PC: `python configurar_drive.py` — pede/usa o `client_secret.json`, abre o navegador
   (fluxo *loopback*), o **Nilson entra com `nilsondavid45@gmail.com`** e autoriza (aviso "app não
   verificado" → *Avançado → continuar*). Gera `drive_token.json` com a pasta raiz já preenchida e
   testa o acesso.
3. Enviar `drive_token.json` para `~/gado-dados/` no PythonAnywhere.
4. Abrir **Configurações → Fotos → Testar conexão**.
5. Confirmar na implementação que `oauth2.googleapis.com` e `www.googleapis.com` estão liberados no
   plano gratuito do PythonAnywhere.

Passo a passo detalhado em `docs/FOTOS_DRIVE.md`.

## 9. Testes

- `tests/test_fotos.py` com **Drive falso** em memória (injetado em `fotos.py`):
  envio grava a linha na ordem de `COLUNAS_FOTOS`; reenvio com o mesmo `id_envio` não duplica;
  órfão no Drive é reaproveitado; uma só principal por animal; excluir a principal promove a próxima;
  arquivo que não é imagem é recusado; animal inexistente é recusado.
- `tests/test_paginas.py`: ficha, lista e Configurações abrem sem 500 **com e sem** Drive.
- `/api/fotos` sem login → 401 JSON; sem CSRF → 403 JSON.
- Suite completa (incluindo invariantes contábeis) passa.

## 10. Fora do escopo (v4.4)

Comando de voz para fotos, vídeo, reconhecimento automático do animal pela imagem, galeria geral do
rebanho, fotos de lotes/visitas (só animais com brinco por enquanto).

## 11. Arquivos afetados

Novos: `drive.py`, `fotos.py`, `routes_fotos.py`, `configurar_drive.py`, `static/fila_fotos.js`,
`tests/test_fotos.py`, `docs/FOTOS_DRIVE.md`.
Alterados: `config.py` (COLUNAS_FOTOS), `db.py` (aba Fotos), `app.py` (registrar rotas),
`templates/ficha_animal.html`, `templates/animais.html`, `templates/base.html` (selo da fila, script),
`routes_animais.py` (passar fotos ao template), `routes_usuarios.py` + `templates/configuracoes.html` (cartão Fotos), `sw.js`, `alertas_whatsapp.py`, `.gitignore`,
`CLAUDE.md` (tabela de arquitetura), `CHANGELOG.md`.
