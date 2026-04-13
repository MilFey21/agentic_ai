import os
import subprocess
import time
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from docker.models.containers import Container

from tests_integrational.docker_manager import (
    TEST_BACKEND_PORT,
    TEST_DB_NAME,
    TEST_DB_PASSWORD,
    TEST_DB_USER,
    TEST_POSTGRES_PORT,
    DockerManager,
)


BACKEND_DIR = Path(__file__).parent.parent
TEST_BACKEND_URL = f'http://localhost:{TEST_BACKEND_PORT}'


@dataclass
class DockerServices:
    postgres: Container
    minio: Container


@pytest.fixture(scope='session')
def docker_manager() -> DockerManager:
    manager = DockerManager()
    return manager


@pytest.fixture(scope='session')
def docker_services(docker_manager: DockerManager) -> DockerServices:
    postgres_container = docker_manager.ensure_postgres()
    minio_container = docker_manager.ensure_minio()

    return DockerServices(
        postgres=postgres_container,
        minio=minio_container,
    )


@pytest.fixture(scope='session')
def db_url() -> str:
    return f'postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@localhost:{TEST_POSTGRES_PORT}/{TEST_DB_NAME}'


@pytest.fixture(scope='session')
def db_schema(docker_services: DockerServices, db_url: str) -> None:
    env = {
        **os.environ,
        'DATABASE_URL': db_url,
        'LANGFLOW_SUPERUSER': 'test',
        'LANGFLOW_SUPERUSER_PASSWORD': 'test',
        'LANGFLOW_API_URL': 'http://localhost:7860',
        'LANGFLOW_DB_HOST': 'localhost',
        'LANGFLOW_DB_NAME': 'langflow_test',
        'LANGFLOW_DB_USER': 'test',
        'LANGFLOW_DB_PASSWORD': 'test',
    }
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if (
        result.returncode != 0
        and 'already exists' not in result.stderr.lower()
        and 'duplicate' not in result.stderr.lower()
    ):
        raise RuntimeError(f'Alembic migration failed: {result.stderr}')


@pytest.fixture(scope='session')
def backend_process(
    docker_services: DockerServices,
    db_schema: None,
    db_url: str,
) -> Generator[subprocess.Popen[bytes]]:
    env = {
        **os.environ,
        'DATABASE_URL': db_url,
        'ENVIRONMENT': 'local',
        'APP_VERSION': '0.1.0',
        'CORS_ORIGINS': '["http://localhost:3000","http://localhost:5173"]',
        'CORS_HEADERS': '["*"]',
        'LANGFLOW_SUPERUSER': 'test',
        'LANGFLOW_SUPERUSER_PASSWORD': 'test',
        'LANGFLOW_API_URL': 'http://localhost:7860',
        'LANGFLOW_DB_HOST': 'localhost',
        'LANGFLOW_DB_NAME': 'langflow_test',
        'LANGFLOW_DB_USER': 'test',
        'LANGFLOW_DB_PASSWORD': 'test',
        'PORT': str(TEST_BACKEND_PORT),
    }

    cmd = ['python', '-m', 'src.main']

    process = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=False,
    )

    max_wait = 30
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = httpx.get(f'{TEST_BACKEND_URL}/api/health', timeout=1.0)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        raise RuntimeError(
            f'Backend did not start in {max_wait}s. stdout: {stdout.decode()}, stderr: {stderr.decode()}',
        )

    yield process

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture
def clean_db(docker_services: DockerServices) -> Generator[None]:
    postgres_container = docker_services.postgres
    docker_manager = DockerManager()
    docker_manager.clear_postgres_data(postgres_container)
    return


@pytest.fixture
def http_client() -> Generator[httpx.Client]:
    with httpx.Client(base_url=TEST_BACKEND_URL, timeout=10.0) as client:
        yield client
