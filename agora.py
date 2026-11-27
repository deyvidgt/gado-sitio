"""Relógio oficial do sistema: horário de Brasília (BRT, UTC-3)."""
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    _TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    _TZ_BR = None


def agora() -> datetime:
    """Retorna horário BRT sem tzinfo, compatível com o banco legado."""
    if _TZ_BR is not None:
        return datetime.now(_TZ_BR).replace(tzinfo=None)
    from datetime import timedelta
    return datetime.utcnow() - timedelta(hours=3)
