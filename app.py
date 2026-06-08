#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Sítio Santo Antonio v3.4
==================================
Ponto de entrada do servidor Flask.
Toda a lógica foi dividida em módulos:

  extensions.py              → app Flask, cache, CSRF, auth helpers, filtros
  routes_dashboard.py        → dashboard principal + alertas WhatsApp
  routes_api.py              → APIs JSON (fluxo, chuvas, cotações, WhatsApp...)
  routes_registros.py        → CRUD compras, gastos, vendas, manejo, excluir
  routes_importar_exportar.py→ importar Excel antigo, exportar relatório, backup
  routes_usuarios.py         → configurações, senhas, usuários
  routes_visitas.py          → visitas ao sítio
  routes_relatorios.py       → página de relatórios + PDF

Para editar uma funcionalidade, abra o módulo correspondente — não este arquivo.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if getattr(sys, "frozen", False):
    BASE_DIR   = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

sys.path.insert(0, BUNDLE_DIR)

# ── 1) Criar app e helpers compartilhados ─────────────────────────────────────
from extensions import app  # noqa: F401 — importa e configura o app Flask

# ── 2) Rotas de autenticação (login/logout precisam existir antes dos outros) ──
from routes_auth import *   # noqa: F401, F403

# ── 3) Dashboard ──────────────────────────────────────────────────────────────
from routes_dashboard import *  # noqa: F401, F403

# ── 4) APIs JSON ──────────────────────────────────────────────────────────────
from routes_api import *        # noqa: F401, F403

# ── 5) CRUD — Compras, Gastos, Vendas, Manejo ─────────────────────────────────
from routes_registros import *  # noqa: F401, F403

# ── 6) Importar / Exportar / Backup ───────────────────────────────────────────
from routes_importar_exportar import *  # noqa: F401, F403

# ── 7) Usuários e Configurações ───────────────────────────────────────────────
from routes_usuarios import *   # noqa: F401, F403

# ── 8) Visitas ao Sítio ───────────────────────────────────────────────────────
from routes_visitas import *    # noqa: F401, F403

# ── 9) Relatórios e PDF ───────────────────────────────────────────────────────
from routes_relatorios import * # noqa: F401, F403

# ── Inicialização ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from db import inicializar
    inicializar()

    import webbrowser, threading
    PORTA = 5000
    NGROK_TOKEN = os.environ.get("NGROK_TOKEN", "")
    url_publica = None

    if NGROK_TOKEN:
        try:
            import ngrok
            ngrok.set_auth_token(NGROK_TOKEN)
            listener    = ngrok.forward(PORTA, authtoken=NGROK_TOKEN)
            url_publica = listener.url()
        except ImportError:
            print("⚠️  ngrok não instalado. Rode: pip install ngrok")
        except Exception as e:
            print(f"⚠️  ngrok não iniciou: {e}")

    def abrir_browser():
        webbrowser.open(f"http://localhost:{PORTA}")

    threading.Timer(1.2, abrir_browser).start()

    print("\n🐄 Sítio Santo Antonio — Sistema de Gado v3.4")
    print(f"   Local:  http://localhost:{PORTA}")
    if url_publica:
        print(f"   Ngrok:  {url_publica}")
    print("   Para encerrar: Ctrl+C\n")

    app.run(debug=False, port=PORTA)
