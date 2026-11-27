from pathlib import Path


ROOT = Path(__file__).parents[1]


def _source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_offline_queue_has_single_indexeddb_store_and_migrates_iot_queue():
    source = _source("static/sync_offline.js")
    assert "DB_NOME = \"gado-offline\"" in source
    assert "fila_geral" in source
    assert "iot_fila_offline" in source
    assert "id_envio" in source
    assert "usuario" in source and "sitio" in source


def test_iot_manager_delegates_queue_to_canonical_sync():
    source = _source("static/js/iot_manager.js")
    assert "offlineSync.enqueue" in source
    assert "localStorage.setItem('iot_fila_offline'" not in source
    assert "offlineSync.sync" in source


def test_queue_removes_only_processed_or_duplicate_items():
    source = _source("static/sync_offline.js")
    assert "processado" in source
    assert "duplicado" in source
    assert "erro_transitorio" in source
    assert "invalido" in source
