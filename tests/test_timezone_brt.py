from pathlib import Path
import re


def test_log_formatter_renders_brasilia_time():
    from logging_config import _formatador_brt
    from datetime import datetime, timezone
    import logging
    record = logging.LogRecord('teste', logging.INFO, __file__, 1, 'ok', (), None)
    record.created = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc).timestamp()
    assert _formatador_brt(record) == '15/01/2026 12:00:00'


def test_sync_timestamp_default_uses_brasilia_time():
    from models import SyncRegistro
    from extensions import _agora
    valor = SyncRegistro.processado_em.default.arg(None)
    assert valor.tzinfo is None
    assert abs((valor - _agora()).total_seconds()) < 5


def test_production_does_not_use_server_local_now_directly():
    root = Path(__file__).parents[1]
    allowed = {'extensions.py', 'logging_config.py', 'agora.py'}
    pattern = re.compile(r'(?:datetime|pd\.Timestamp)\.(?:utcnow|now)\s*\(')
    violations = []
    for path in root.glob('*.py'):
        if path.name in allowed:
            continue
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if pattern.search(line):
                violations.append(f'{path.name}:{line_no}')
    assert violations == [], 'UTC/local time calls remain: ' + ', '.join(violations)
