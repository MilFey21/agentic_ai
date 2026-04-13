import json
import subprocess
import time

import docker
from docker.models.containers import Container


POSTGRES_IMAGE = 'postgres:16'
MINIO_IMAGE = 'minio/minio:latest'

TEST_POSTGRES_PORT = 15432
TEST_MINIO_PORT = 19000
TEST_BACKEND_PORT = 18000

TEST_DB_NAME = 'wcs_test'
TEST_DB_USER = 'test'
TEST_DB_PASSWORD = 'test'

TEST_MINIO_ROOT_USER = 'testminio'
TEST_MINIO_ROOT_PASSWORD = 'testminio123'

POSTGRES_CONTAINER_NAME = 'wcs-test-postgres'
MINIO_CONTAINER_NAME = 'wcs-test-minio'

TEST_NETWORK_NAME = 'wcs-test-network'


def _get_docker_host_from_context() -> str | None:
    """Получить DOCKER_HOST из активного Docker context."""
    try:
        result = subprocess.run(
            ['docker', 'context', 'inspect'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        context_info = json.loads(result.stdout)
        if context_info and isinstance(context_info, list) and len(context_info) > 0:
            endpoints = context_info[0].get('Endpoints', {})
            docker_endpoint = endpoints.get('docker', {})
            host = docker_endpoint.get('Host')
            if host:
                return host
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        KeyError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        pass
    return None


class DockerManager:
    def __init__(self) -> None:
        docker_host = _get_docker_host_from_context()
        if docker_host:
            self.client = docker.DockerClient(base_url=docker_host)
        else:
            self.client = docker.from_env()

    def ensure_network(self) -> None:
        try:
            self.client.networks.get(TEST_NETWORK_NAME)
        except docker.errors.NotFound:
            self.client.networks.create(TEST_NETWORK_NAME, driver='bridge')

    def ensure_postgres(self) -> Container:
        try:
            container = self.client.containers.get(POSTGRES_CONTAINER_NAME)
            if container.status != 'running':
                container.start()
        except docker.errors.NotFound:
            self.ensure_network()
            container = self.client.containers.run(
                POSTGRES_IMAGE,
                name=POSTGRES_CONTAINER_NAME,
                ports={'5432/tcp': TEST_POSTGRES_PORT},
                environment={
                    'POSTGRES_USER': TEST_DB_USER,
                    'POSTGRES_PASSWORD': TEST_DB_PASSWORD,
                    'POSTGRES_DB': TEST_DB_NAME,
                },
                network=TEST_NETWORK_NAME,
                detach=True,
                remove=False,
            )
            self._wait_for_postgres(container)
            return container
        else:
            return container

    def ensure_minio(self) -> Container:
        try:
            container = self.client.containers.get(MINIO_CONTAINER_NAME)
            if container.status != 'running':
                container.start()
        except docker.errors.NotFound:
            self.ensure_network()
            container = self.client.containers.run(
                MINIO_IMAGE,
                name=MINIO_CONTAINER_NAME,
                ports={'9000/tcp': TEST_MINIO_PORT, '9001/tcp': 19001},
                command='server /data --console-address ":9001"',
                environment={
                    'MINIO_ROOT_USER': TEST_MINIO_ROOT_USER,
                    'MINIO_ROOT_PASSWORD': TEST_MINIO_ROOT_PASSWORD,
                },
                network=TEST_NETWORK_NAME,
                detach=True,
                remove=False,
            )
            self._wait_for_minio(container)
            return container
        else:
            return container

    def _wait_for_postgres(self, container: Container, timeout: int = 30) -> None:
        start_time = time.time()
        while time.time() - start_time < timeout:
            exec_result = container.exec_run(
                ['pg_isready', '-U', TEST_DB_USER, '-d', TEST_DB_NAME],
            )
            if exec_result.exit_code == 0:
                return
            time.sleep(1)
        raise RuntimeError(f'PostgreSQL container {container.name} did not become ready in {timeout}s')

    def _wait_for_minio(self, container: Container, timeout: int = 30) -> None:
        start_time = time.time()
        while time.time() - start_time < timeout:
            exec_result = container.exec_run(
                ['curl', '-f', 'http://localhost:9000/minio/health/live'],
            )
            if exec_result.exit_code == 0:
                return
            time.sleep(1)
        raise RuntimeError(f'MinIO container {container.name} did not become ready in {timeout}s')

    def clear_postgres_data(self, container: Container) -> None:
        exec_result = container.exec_run(
            [
                'psql',
                '-U',
                TEST_DB_USER,
                '-d',
                TEST_DB_NAME,
                '-t',
                '-A',
                '-c',
                "SELECT string_agg(quote_ident(schemaname) || '.' || quote_ident(tablename), ', ') "
                'FROM pg_tables '
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') AND tablename != 'alembic_version';",
            ],
        )
        assert exec_result.exit_code == 0, f'Failed to get tables: {exec_result.output.decode("utf-8")}'
        tables = exec_result.output.decode('utf-8').strip()
        assert tables, 'No tables found'
        truncate_sql = f'TRUNCATE TABLE {tables} CASCADE;'
        exec_result = container.exec_run(
            [
                'psql',
                '-U',
                TEST_DB_USER,
                '-d',
                TEST_DB_NAME,
                '-c',
                truncate_sql,
            ],
        )
        assert exec_result.exit_code == 0, f'Failed to truncate tables: {exec_result.output.decode("utf-8")}'

    def clear_minio_data(self, container: Container) -> None:
        exec_result = container.exec_run(
            [
                'sh',
                '-c',
                'rm -rf /data/*',
            ],
        )
        assert exec_result.exit_code == 0, f'Failed to clear MinIO data: {exec_result.output.decode("utf-8")}'
