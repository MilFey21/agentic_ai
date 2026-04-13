import httpx
import pytest


@pytest.mark.xfail(reason='langflow is not available')  # TODO: add langflow mock server
def test_register_login_get_me_flow(
    http_client: httpx.Client,
    backend_process,
    clean_db,
) -> None:
    # 1. Регистрация пользователя
    register_payload = {
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'securepassword123',
    }
    register_response = http_client.post('/api/register', json=register_payload)
    assert register_response.status_code == 201, register_response.text
    register_data = register_response.json()

    assert register_data['username'] == 'testuser'
    assert register_data['email'] == 'testuser@example.com'
    assert 'id' in register_data
    user_id = register_data['id']

    # 2. Логин с username и password
    login_payload = {
        'username': 'testuser',
        'password': 'securepassword123',
    }
    login_response = http_client.post('/api/login', json=login_payload)
    assert login_response.status_code == 200, login_response.text
    login_data = login_response.json()

    assert 'access_token' in login_data
    assert login_data['token_type'] == 'bearer'
    access_token = login_data['access_token']

    # 3. Получение текущего пользователя с токеном
    me_response = http_client.get(
        '/api/me',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert me_response.status_code == 200, me_response.text
    me_data = me_response.json()

    assert me_data['id'] == user_id
    assert me_data['username'] == 'testuser'
    assert me_data['email'] == 'testuser@example.com'
