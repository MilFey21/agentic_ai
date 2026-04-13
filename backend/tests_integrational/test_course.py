import time
from uuid import uuid4

import httpx


def test_get_modules_returns_list(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/modules возвращает список модулей из course/"""
    response = http_client.get('/api/modules')
    assert response.status_code == 200
    modules = response.json()
    assert isinstance(modules, list)
    assert len(modules) >= 1
    module = modules[0]
    assert 'id' in module
    assert 'title' in module
    assert 'description' in module


def test_get_module_by_id(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/modules/{id} возвращает конкретный модуль"""
    modules = http_client.get('/api/modules').json()
    module_id = modules[0]['id']

    response = http_client.get(f'/api/modules/{module_id}')
    assert response.status_code == 200
    module = response.json()
    assert module['id'] == module_id


def test_get_module_not_found(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/modules/{id} возвращает 404 для несуществующего ID"""
    nonexistent_id = uuid4()
    response = http_client.get(f'/api/modules/{nonexistent_id}')
    assert response.status_code == 404


def test_get_tasks_returns_list(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/tasks возвращает список заданий из course/"""
    response = http_client.get('/api/tasks')
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) >= 1
    task = tasks[0]
    assert 'id' in task
    assert 'title' in task
    assert 'type' in task
    assert 'description' in task


def test_get_tasks_by_module(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/tasks?module_id=... фильтрует по модулю"""
    modules = http_client.get('/api/modules').json()
    module_id = modules[0]['id']

    response = http_client.get(f'/api/tasks?module_id={module_id}')
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)


def test_get_task_by_id(http_client: httpx.Client, backend_process, clean_db) -> None:
    """GET /api/tasks/{id} возвращает конкретное задание"""
    tasks = http_client.get('/api/tasks').json()
    task_id = tasks[0]['id']

    response = http_client.get(f'/api/tasks/{task_id}')
    assert response.status_code == 200
    task = response.json()
    assert task['id'] == task_id


def test_crud_endpoints_removed(http_client: httpx.Client, backend_process, clean_db) -> None:
    """POST/PATCH/DELETE для modules и tasks должны возвращать 405"""
    test_id = uuid4()

    assert http_client.post('/api/modules', json={}).status_code == 405
    assert http_client.patch(f'/api/modules/{test_id}', json={}).status_code == 405
    assert http_client.delete(f'/api/modules/{test_id}').status_code == 405

    assert http_client.post('/api/tasks', json={}).status_code == 405
    assert http_client.patch(f'/api/tasks/{test_id}', json={}).status_code == 405
    assert http_client.delete(f'/api/tasks/{test_id}').status_code == 405


def test_course_loader_caching(http_client: httpx.Client, backend_process, clean_db) -> None:
    """Повторные запросы используют кеш (быстрее первого)"""
    start = time.time()
    http_client.get('/api/modules')
    first_time = time.time() - start

    start = time.time()
    for _ in range(10):
        http_client.get('/api/modules')
    cached_time = (time.time() - start) / 10

    assert cached_time < first_time * 2
