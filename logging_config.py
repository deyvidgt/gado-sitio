#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuração de logging para auditoria e monitoramento.
v5.11 — Security enhancement
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    _TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    _TZ_BR = None


def _formatador_brt(record):
    """Converte o timestamp do LogRecord (epoch) para horário de Brasília."""
    dt = datetime.fromtimestamp(record.created, timezone.utc)
    if _TZ_BR is not None:
        dt = dt.astimezone(_TZ_BR)
    else:
        from datetime import timedelta
        dt = dt - timedelta(hours=3)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def configurar_logging(app, log_dir="logs"):
    """
    Configura logging de acesso, erros e segurança.

    Args:
        app: Aplicação Flask
        log_dir: Diretório para arquivos de log (padrão: logs/)
    """
    # Criar diretório se não existir
    os.makedirs(log_dir, exist_ok=True)

    # Nível de log (lê de variável de ambiente)
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # ── Logger de ACESSO (todas as requisições) ────────────────────────────────
    access_handler = RotatingFileHandler(
        os.path.join(log_dir, "access.log"),
        maxBytes=10_000_000,  # 10 MB
        backupCount=10,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_format = logging.Formatter(
        '[%(asctime)s] %(remote_addr)s - %(method)s %(path)s %(status_code)s'
    )
    access_format.converter = lambda timestamp: datetime.fromtimestamp(timestamp, _TZ_BR or timezone.utc).timetuple()
    access_handler.setFormatter(access_format)

    # ── Logger de SEGURANÇA (login, CSRF, etc) ────────────────────────────────
    security_handler = RotatingFileHandler(
        os.path.join(log_dir, "security.log"),
        maxBytes=10_000_000,
        backupCount=10,
        encoding="utf-8"
    )
    security_handler.setLevel(logging.WARNING)
    security_format = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s'
    )
    security_format.converter = lambda timestamp: datetime.fromtimestamp(timestamp, _TZ_BR or timezone.utc).timetuple()
    security_handler.setFormatter(security_format)

    # ── Logger de ERROS (exceptions, 500, etc) ────────────────────────────────
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=10_000_000,
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(security_format)

    # ── Configurar loggers da aplicação ────────────────────────────────────────

    # Flask logger (access)
    if not app.debug:
        app.logger.setLevel(logging.INFO)
        app.logger.addHandler(access_handler)
        app.logger.addHandler(error_handler)

    # Logger de segurança
    security_logger = logging.getLogger("security")
    security_logger.setLevel(log_level)
    security_logger.addHandler(security_handler)

    return {
        "access": logging.getLogger("access"),
        "security": security_logger,
        "error": logging.getLogger("error"),
    }


def log_acesso(app, request, response=None):
    """
    Registra acesso HTTP (depois de @app.after_request).

    Args:
        app: Aplicação Flask
        request: Flask request object
        response: Flask response object (opcional)
    """
    if app.debug:
        return

    logger = logging.getLogger("access")

    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        metodo = request.method
        caminho = request.path
        status = response.status_code if response else "?"
        usuario = getattr(request, "usuario_logado", "—")

        logger.info(f"{ip} | {usuario} | {metodo} {caminho} | {status}")
    except Exception as e:
        logging.getLogger("error").exception(f"Erro ao logar acesso: {e}")


def log_seguranca(nivel, mensagem, usuario="—", endereco_ip="—"):
    """
    Registra eventos de segurança (login falhado, CSRF, etc).

    Args:
        nivel: "warning" ou "error"
        mensagem: descrição do evento
        usuario: login do usuário (se aplicável)
        endereco_ip: IP de origem
    """
    logger = logging.getLogger("security")

    full_message = f"[{usuario} @ {endereco_ip}] {mensagem}"

    if nivel.lower() == "error":
        logger.error(full_message)
    else:
        logger.warning(full_message)


def log_erro(mensagem, excecao=None, usuario="—"):
    """
    Registra erro não tratado.

    Args:
        mensagem: descrição do erro
        excecao: objeto Exception (opcional)
        usuario: login do usuário (se aplicável)
    """
    logger = logging.getLogger("error")

    full_message = f"[{usuario}] {mensagem}"

    if excecao:
        logger.exception(full_message)
    else:
        logger.error(full_message)
