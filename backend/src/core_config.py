import json
from enum import Enum

from pydantic import Field, PostgresDsn, field_validator

from src.base_config import BaseConfig


class Environment(str, Enum):
    LOCAL = 'local'
    STAGING = 'staging'
    PRODUCTION = 'production'


class Config(BaseConfig):
    ENVIRONMENT: Environment = Environment.PRODUCTION
    APP_VERSION: str = '0.1.0'
    APP_TITLE: str = 'WindChaserSecurity API'
    APP_DESCRIPTION: str = 'Backend API for AI Security Training Platform'

    DATABASE_URL: PostgresDsn

    CORS_ORIGINS: list[str] | str = Field(default=['http://localhost:3000', 'http://localhost:5173'])
    CORS_HEADERS: list[str] | str = Field(default=['*'])

    SHOW_DOCS_ENVIRONMENT: tuple[str, ...] = ('local', 'staging')

    @field_validator('CORS_ORIGINS', 'CORS_HEADERS', mode='before')
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [x.strip() for x in v.split(',')]
        return v

    @property
    def show_docs(self) -> bool:
        return self.ENVIRONMENT.value in self.SHOW_DOCS_ENVIRONMENT


settings = Config()
