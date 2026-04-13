from unittest.mock import ANY

import httpx


def test_health_endpoint(http_client: httpx.Client, backend_process, clean_db) -> None:
    response = http_client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data == {
        'status': 'healthy',
    }


def test_root_endpoint(http_client: httpx.Client, backend_process, clean_db) -> None:
    response = http_client.get('/api/')
    assert response.status_code == 200
    data = response.json()
    assert data == {
        'message': 'WindChaserSecurity API',
        'status': 'running',
        'version': ANY,
    }
