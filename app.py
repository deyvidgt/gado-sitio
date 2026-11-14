#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Sítio Santo Antonio v5.30.0
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

# ── 1) App e helpers compartilhados ──────────────────────────────────────────
from extensions import app  # noqa: F401

# ── 2) Autenticação ──────────────────────────────────────────────────────────
from routes_auth import *   # noqa: F401, F403

# ── 3) Dashboard ─────────────────────────────────────────────────────────────
from routes_dashboard import *  # noqa: F401, F403

# ── 3b) Dashboard — Páginas reorganizadas (v5.10) ────────────────────────────
from routes_financeiro_novo import *  # noqa: F401, F403

# ── 3c) Confinamento e Genética (v5.10) ──────────────────────────────────────
from routes_confinamento_genetica import *  # noqa: F401, F403

# ── 4) APIs JSON (base) ──────────────────────────────────────────────────────
from routes_api import *        # noqa: F401, F403

# ── 4b) APIs extras (calendário, whatsapp config) ────────────────────────────
from routes_api_extras import * # noqa: F401, F403

# ── 5) CRUD ──────────────────────────────────────────────────────────────────
from routes_registros import *  # noqa: F401, F403
from routes_transacoes import *  # noqa: F401, F403  — Comercialização (Compras+Vendas)

# ── 6) Importar / Exportar / Backup ──────────────────────────────────────────
from routes_importar_exportar import *  # noqa: F401, F403

# ── 7) Usuários e Configurações ──────────────────────────────────────────────
from routes_usuarios import *   # noqa: F401, F403

# ── 8) Visitas ao Sítio ──────────────────────────────────────────────────────
from routes_visitas import *    # noqa: F401, F403

# ── 9) Relatórios e PDF ──────────────────────────────────────────────────────
from routes_relatorios import * # noqa: F401, F403

# ── 10) Animais (brincos) e Comando de Voz ───────────────────────────────────
from routes_animais import *    # noqa: F401, F403

# v5.6 — Gráficos de crescimento (GMD) do animal
from routes_pesagem import *    # noqa: F401, F403

# v5.20 — Estimação de Peso por Foto / Biometria Bovina
from routes_estimar_peso import * # noqa: F401, F403

# v5.21 — Controle Físico de Pastagens e Indicadores Embrapa/ANCP
from routes_pastos_avancados import * # noqa: F401, F403
from routes_indicadores_embrapa import * # noqa: F401, F403

# v5.22 — Manejos de Curral e Apontamentos Rápidos (Pecuária de Precisão)
from routes_curral import * # noqa: F401, F403

# v5.23-5.24 — Módulos Avançados de Corte e Leite (Enfermaria, Alertas de Parto, Controle Leiteiro)
from routes_enfermaria import * # noqa: F401, F403
from routes_alertas_parto import * # noqa: F401, F403
from routes_controle_leite import * # noqa: F401, F403

# v5.25 — Assistente de Ração, Gestão Financeira Completa e Relatórios Gráficos de Rebanho
from routes_relatorios_graficos import * # noqa: F401, F403

# v5.30 — Zootecnia de Precisão (Indicadores Nutricionais, Estoque por UA/ha, Cio/Parto/Enfermaria, Calendário)
from routes_precisao import * # noqa: F401, F403

# v5.35 — Simulador de Custo de Produção e Viabilidade de Engorda (Boi Gordo)
from routes_simulador_engorda import * # noqa: F401, F403

# v5.40 — Gestão de Rebanho Avançada, Apontamentos de Curral e Faixas de Peso
from routes_precisao_avancada import * # noqa: F401, F403

# v4.4 — Fotos dos animais (Google Drive)
from routes_fotos import *      # noqa: F401, F403

# v4.5 — Ajuda (passo a passo; prints no Google Drive)
from routes_ajuda import *      # noqa: F401, F403

# v5.2 — Pastos com mapa
from routes_pastos import *     # noqa: F401, F403

# v5.3 — Comparador de proteinado/ração
from routes_insumos import *    # noqa: F401, F403

# v5.3 — Agenda de tarefas
from routes_tarefas import *    # noqa: F401, F403

# v5.3 — Reprodução (cobertura, toque, parto previsto)
from routes_reproducao import * # noqa: F401, F403

# v5.13 — IA preditiva (Onda 19): painel de previsões
from routes_ia import *         # noqa: F401, F403

# v5.13 — IoT básico (Onda 16): endpoints dos sensores
from routes_iot import *        # noqa: F401, F403

# v5.3 — Painel econômico por lote
from routes_lotes import *      # noqa: F401, F403

# v5.14 — Simulador de ponto de corte e relatórios avançados (Onda 14)
from routes_ponto_corte import *           # noqa: F401, F403
from routes_relatorios_avancados import *  # noqa: F401, F403

# v5.4 — Produção leiteira
from routes_leite import *      # noqa: F401, F403
from routes_volumosos import *  # noqa: F401, F403
from routes_alertas import *    # noqa: F401, F403

# v5.10 — Calculador de ração avançado
from routes_racao_avancada import *  # noqa: F401, F403

# v5.10 — Reconhecimento de animal e genealogia visual (BETA)
from routes_reconhecimento import *  # noqa: F401, F403

# Calendário operacional consolidado (somente leitura)
from routes_calendario import * # noqa: F401, F403

# v5.10 — Agenda unificada (Calendário + Tarefas)
from routes_agenda_unificada import * # noqa: F401, F403

# v5.10 Onda 2 — Histórico de doenças e carência
from routes_doencas import *    # noqa: F401, F403

# v5.16 — Bulas e embalagens dos remédios (Drive)
from routes_bulas import *      # noqa: F401, F403

# v5.10 Onda 3 — Previsão de partos
from routes_partos import *     # noqa: F401, F403

# v5.10 Onda 4 — Análise genética e consanguinidade
from routes_genetica import *   # noqa: F401, F403

# v5.7 — Histórico de medicações (medicacoes.py)
from routes_medicacoes import * # noqa: F401, F403
from routes_estoque_medicamentos import *  # noqa: F401, F403

# v5.8 — Indicadores (engorda, GMD, ração, mortalidade)
from routes_indicadores import * # noqa: F401, F403

# v5.10 Onda 5 — Conversão alimentar e eficiência nutricional
from routes_conversao_alimentar import *  # noqa: F401, F403

# v5.10 Onda 6 — Ocupação de pastos e rotação dinâmica
from routes_pastos_ocupacao import *  # noqa: F401, F403

# v5.10 — Gestão de cochos e salga
from routes_cochos import *         # noqa: F401, F403

# v5.11 Onda 8+ — Gráficos do sistema (Chart.js)
from routes_exportar_graficos import * # noqa: F401, F403

# ── Migração/criação do arquivo de dados ──────────────────────────────────────
# IMPORTANTE: roda em QUALQUER forma de entrada (wsgi/PythonAnywhere, .exe e dev).
# Antes só rodava em `python app.py`, então no servidor as colunas novas (ex.: "Perda De",
# caixa d'água, Ração) nunca eram criadas — os valores iam para colunas sem cabeçalho.
try:
    from db import inicializar
    inicializar()
    from extensions import db as db_sqla
    with app.app_context():
        db_sqla.create_all()
except Exception as _e:
    # Nunca derrubar o site por causa da migração; apenas registra.
    print(f"⚠️  Falha ao inicializar/migrar o banco: {_e}", flush=True)

# ── Inicialização (execução local direta) ─────────────────────────────────────
if __name__ == "__main__":
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

    from config import VERSAO
    print(f"\n🐄 Sítio Santo Antonio — Sistema de Gado v{VERSAO}")
    print(f"   Local:  http://localhost:{PORTA}")
    if url_publica:
        print(f"   Ngrok:  {url_publica}")
    print("   Para encerrar: Ctrl+C\n")

    app.run(debug=False, port=PORTA)
