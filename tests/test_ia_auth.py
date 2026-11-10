import pytest
from app import app

def test_api_ia_alertas_authenticated():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['login'] = 'Deyvid'
            sess['usuario'] = 'Deyvid'
            sess['logado'] = True

        response = client.get('/api/ia/alertas')
        assert response.status_code == 200
        data = response.get_json()
        assert 'urgentes' in data
        assert 'avisos' in data
        assert 'total' in data
        assert 'timestamp' in data
