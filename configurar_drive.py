#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
configurar_drive.py — autoriza o site a guardar as fotos no Google Drive (v4.4).

Roda UMA vez, no computador (precisa de navegador):

    python configurar_drive.py --client-secret client_secret.json

Abre o Google; entre com a conta DONA da pasta (nilsondavid45@gmail.com) e
autorize. O script grava drive_token.json — depois envie esse arquivo para
~/gado-dados/ no PythonAnywhere. Passo a passo completo: docs/FOTOS_DRIVE.md

Só usa a biblioteca padrão + requests (sem as bibliotecas do Google).
"""
import argparse
import http.server
import json
import os
import secrets
import socket
import sys
import urllib.parse
import webbrowser

import requests

from config import DRIVE_PASTA_PADRAO

ESCOPO = "https://www.googleapis.com/auth/drive"
URL_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"


def _ler_client_secret(caminho: str) -> tuple[str, str]:
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    bloco = dados.get("installed") or dados.get("web") or dados
    return bloco["client_id"], bloco["client_secret"]


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar_codigo(porta: int, estado: str) -> str:
    """Servidor local de uma requisição só: o Google redireciona para cá com ?code=."""
    recebido = {}

    class Tratador(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            recebido.update({k: v[0] for k, v in q.items()})
            ok = "code" in q and q.get("state", [""])[0] == estado
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "✅ Autorizado! Pode fechar esta aba e voltar ao terminal." if ok \
                else "❌ Não autorizado. Volte ao terminal."
            self.wfile.write(f"<h2 style='font-family:sans-serif'>{msg}</h2>".encode("utf-8"))

        def log_message(self, *a):
            pass

    with http.server.HTTPServer(("127.0.0.1", porta), Tratador) as srv:
        while "code" not in recebido and "error" not in recebido:
            srv.handle_request()
    if recebido.get("error"):
        sys.exit(f"❌ O Google recusou: {recebido['error']}")
    if recebido.get("state") != estado:
        sys.exit("❌ Resposta inesperada (state diferente). Rode de novo.")
    return recebido["code"]


def main():
    ap = argparse.ArgumentParser(description="Autoriza o site a usar a pasta de fotos no Google Drive.")
    ap.add_argument("--client-secret", default="client_secret.json",
                    help="JSON baixado do Google Cloud (credencial 'App para computador')")
    ap.add_argument("--pasta", default=DRIVE_PASTA_PADRAO, help="ID da pasta do Drive")
    ap.add_argument("--saida", default="drive_token.json", help="onde gravar a credencial")
    args = ap.parse_args()

    if not os.path.isfile(args.client_secret):
        sys.exit(f"❌ Não achei {args.client_secret}. Veja docs/FOTOS_DRIVE.md (passo 1).")
    client_id, client_secret = _ler_client_secret(args.client_secret)
    porta, estado = _porta_livre(), secrets.token_urlsafe(16)
    redirect_uri = f"http://127.0.0.1:{porta}"
    url = URL_AUTH + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": ESCOPO, "access_type": "offline", "prompt": "consent", "state": estado,
    })
    print("🌐 Abrindo o Google no navegador. Entre com a conta DONA da pasta e autorize.")
    print("   (Aviso 'app não verificado' é normal: Avançado → continuar.)")
    print(f"   Se o navegador não abrir, copie este link:\n   {url}\n")
    webbrowser.open(url)
    codigo = _esperar_codigo(porta, estado)

    r = requests.post(URL_TOKEN, data={
        "code": codigo, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=30)
    if r.status_code >= 400:
        sys.exit(f"❌ Falha ao trocar o código: {r.text[:300]}")
    tok = r.json()
    if not tok.get("refresh_token"):
        sys.exit("❌ O Google não mandou o refresh_token. Remova o acesso do app em "
                 "https://myaccount.google.com/permissions e rode de novo.")

    cred = {"client_id": client_id, "client_secret": client_secret,
            "refresh_token": tok["refresh_token"], "pasta_raiz": args.pasta}

    import drive  # aqui: drive importa db, que resolve a pasta de dados
    ok, msg = drive.Drive(cred).testar()
    print(("✅ " if ok else "⚠️  ") + msg)
    if not ok:
        print("   A conta autorizada consegue abrir essa pasta? (dona ou Editor)")
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(cred, f, indent=2)
    print(f"💾 Gravado em {os.path.abspath(args.saida)}")
    print("   Envie este arquivo para ~/gado-dados/ no PythonAnywhere e NÃO o coloque no Git.")


if __name__ == "__main__":
    main()
