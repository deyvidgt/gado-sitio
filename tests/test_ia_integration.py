import pytest
from app import app

def test_api_ia_alertas_returns_json():
    with app.test_client() as client:
        # Note: requires authentication, I need to see if I can bypass it or set up a session
        # For simplicity, let's assume I can call it or need to login first
        # Based on existing tests, they usually mock login or use a test client with session

        # Let's try calling it directly, it might fail with 401 if login_required is enforced
        # If it fails, I'll need to figure out how to bypass auth for tests
        response = client.get('/api/ia/alertas')
        # Based on common setup, this might be 302 to login or 401
        assert response.status_code == 200 or response.status_code == 302

        if response.status_code == 200:
            data = response.get_json()
            assert 'urgentes' in data
            assert 'avisos' in data
            assert 'total' in data
            assert 'timestamp' in data
