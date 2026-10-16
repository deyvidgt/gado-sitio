# Fotos dos animais no Google Drive — configuração (uma vez)

As fotos tiradas na ficha de cada animal vão para a pasta da família no Drive:
<https://drive.google.com/drive/folders/1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt>
(dona: **nilsondavid45@gmail.com**). Cada animal ganha uma subpasta (`A0003 - Amarelo 21`).

Sem esta configuração o site funciona normalmente — só a parte de fotos fica desligada.

## 1. Google Cloud (≈ 10 min, no computador)

1. Abra <https://console.cloud.google.com/> logado como **nilsondavid45@gmail.com**.
2. Crie um projeto: **Selecionar projeto → Novo projeto** → nome `Sitio Fotos` → Criar.
3. **APIs e serviços → Biblioteca** → procure **Google Drive API** → **Ativar**.
4. **APIs e serviços → Tela de permissão OAuth** (ou "Google Auth Platform"):
   - Tipo de usuário: **Externo** → nome do app `Sítio Santo Antonio`, e-mails de suporte/contato
     = o mesmo Gmail → Salvar.
   - Em **Público-alvo**, clique em **Publicar app** → confirme. O status deve ficar
     **Em produção**.
     > ⚠️ Se ficar em **Teste**, a autorização vence em 7 dias e as fotos param de subir.
5. **APIs e serviços → Credenciais → Criar credenciais → ID do cliente OAuth**:
   - Tipo de aplicativo: **App para computador** → nome `configurar_drive` → Criar.
   - Clique em **Fazer download do JSON** e salve na pasta do projeto como
     `client_secret.json` (ele já está no `.gitignore`).

## 2. Autorizar (≈ 2 min, no computador)

```bash
python configurar_drive.py --client-secret client_secret.json
```

- O navegador abre o Google: entre com **nilsondavid45@gmail.com**.
- Vai aparecer **"O Google não verificou este app"** → **Avançado → Acessar Sítio Santo Antonio
  (não seguro)** → marque o acesso ao Drive → **Continuar**. É normal para app de uso da família.
- No terminal deve aparecer `✅ Drive conectado — pasta ...` e o arquivo `drive_token.json`.

> As fotos ficam na cota de quem autorizou. Por isso autorize com a conta do Nilson
> (dona da pasta). Se outra conta autorizar, ela precisa ser **Editor** da pasta.

## 3. Instalar no PythonAnywhere

1. Aba **Files** → entre em `/home/<usuário>/gado-dados/` → **Upload a file** → `drive_token.json`.
2. Aba **Web** → **Reload**.
3. No site: **Configurações → 📷 Fotos → Testar conexão** → deve mostrar `Drive conectado`.

**Nunca** coloque `drive_token.json` nem `client_secret.json` no Git: com eles alguém poderia
mexer no Drive.

## Se parar de funcionar

- O WhatsApp de urgentes avisa "📷 Fotos: o Google Drive não está aceitando envios".
- As fotos tiradas nesse tempo **ficam guardadas nos celulares** e sobem sozinhas quando voltar.
- Causa mais comum: o acesso foi removido em <https://myaccount.google.com/permissions> ou o app
  voltou para "Teste". Refaça o passo 2 e envie o novo `drive_token.json`.

## Para recuperar uma foto excluída

Excluir no site manda o arquivo para a **lixeira do Drive** (fica 30 dias). Restaure por lá; para
voltar a aparecer no site seria preciso regravar a linha na aba `Fotos` do Excel (raro — peça ajuda).
