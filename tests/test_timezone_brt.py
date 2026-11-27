import logging
from datetime import datetime, timezone


def test_log_formatter_renders_brasilia_time():
    from logging_config import _formatador_brt

    record = logging.LogRecord('teste', logging.INFO, __file__, 1, 'ok', (), None)
    record.created = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc).timestamp()
    assert _formatador_brt(record) == '15/01/2026 12:00:00'


def test_sync_timestamp_default_uses_brasilia_time():
    from models import SyncRegistro
    from extensions import _agora

    valor = SyncRegistro.processado_em.default.arg(None)
    assert valor.tzinfo is None
    assert abs((valor - _agora()).total_seconds()) < 5
