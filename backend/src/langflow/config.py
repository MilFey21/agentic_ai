from pydantic import HttpUrl

from src.base_config import BaseConfig


class LangflowConfig(BaseConfig):
    LANGFLOW_API_URL: HttpUrl = 'http://localhost:7860'
    LANGFLOW_SUPERUSER: str
    LANGFLOW_SUPERUSER_PASSWORD: str

    # LangFlow Database settings - values from docker-compose.yml environment
    LANGFLOW_DB_HOST: str
    LANGFLOW_DB_PORT: int = 5432
    LANGFLOW_DB_NAME: str
    LANGFLOW_DB_USER: str
    LANGFLOW_DB_PASSWORD: str

    @property
    def langflow_database_url(self) -> str:
        return f'postgresql+asyncpg://{self.LANGFLOW_DB_USER}:{self.LANGFLOW_DB_PASSWORD}@{self.LANGFLOW_DB_HOST}:{self.LANGFLOW_DB_PORT}/{self.LANGFLOW_DB_NAME}'


langflow_settings = LangflowConfig()
