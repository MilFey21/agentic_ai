import json
from enum import Enum

from pydantic import Field, PostgresDsn, field_validator

from src.base_config import BaseConfig


# ============================================================================
# OpenAI-compatible LLM Configuration
# All settings are loaded from environment variables with OPENAI_ prefix
# ============================================================================


class OpenAIConfig(BaseConfig):
    """
    Configuration for OpenAI-compatible LLM providers.
    
    Environment variables:
        OPENAI_API_KEY: API key (required)
        OPENAI_BASE_URL: Base URL for API (default: https://api.openai.com/v1)
        OPENAI_MODEL: Default model name (default: gpt-4o-mini)
        
        OPENAI_EVALUATOR_MODEL: Model for evaluator agent (optional)
        OPENAI_EVALUATOR_TEMPERATURE: Temperature for evaluator (default: 0.5)
        
        OPENAI_TUTOR_MODEL: Model for tutor agent (optional)
        OPENAI_TUTOR_TEMPERATURE: Temperature for tutor (default: 0.7)
    """

    # Core settings
    OPENAI_API_KEY: str = Field(default='', description='API key for OpenAI-compatible provider')
    OPENAI_BASE_URL: str = Field(
        default='https://api.openai.com/v1',
        description='Base URL for OpenAI-compatible API',
    )
    OPENAI_MODEL: str = Field(
        default='gpt-4o-mini',
        description='Default LLM model name',
    )

    # Evaluator agent settings
    OPENAI_EVALUATOR_MODEL: str = Field(
        default='',
        description='Model for evaluator agent (falls back to OPENAI_MODEL)',
    )
    OPENAI_EVALUATOR_TEMPERATURE: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description='Temperature for evaluator agent',
    )

    # Tutor agent settings
    OPENAI_TUTOR_MODEL: str = Field(
        default='',
        description='Model for tutor agent (falls back to OPENAI_MODEL)',
    )
    OPENAI_TUTOR_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description='Temperature for tutor agent',
    )


# Singleton instance
openai_settings = OpenAIConfig()


def get_api_key() -> str:
    """Get OpenAI API key."""
    if not openai_settings.OPENAI_API_KEY:
        raise ValueError('OPENAI_API_KEY environment variable is required')
    return openai_settings.OPENAI_API_KEY


def get_evaluator_config(**overrides) -> dict:
    """Get configuration for EvaluatorAgent."""
    config = {
        'llm_model': openai_settings.OPENAI_EVALUATOR_MODEL or openai_settings.OPENAI_MODEL,
        'temperature': openai_settings.OPENAI_EVALUATOR_TEMPERATURE,
        'base_url': openai_settings.OPENAI_BASE_URL,
    }
    config.update(overrides)
    return config


def get_tutor_config(**overrides) -> dict:
    """Get configuration for TutorAgent."""
    config = {
        'llm_model': openai_settings.OPENAI_TUTOR_MODEL or openai_settings.OPENAI_MODEL,
        'temperature': openai_settings.OPENAI_TUTOR_TEMPERATURE,
        'base_url': openai_settings.OPENAI_BASE_URL,
    }
    config.update(overrides)
    return config


def get_llm_analyzer_config(**overrides) -> dict:
    """
    Get configuration for LLMAnalyzer (used in validators/tools).
    
    Uses evaluator settings since analyzer is part of evaluation process.
    """
    config = {
        'model': openai_settings.OPENAI_EVALUATOR_MODEL or openai_settings.OPENAI_MODEL,
        'temperature': openai_settings.OPENAI_EVALUATOR_TEMPERATURE,
        'base_url': openai_settings.OPENAI_BASE_URL,
    }
    config.update(overrides)
    return config


# ============================================================================
# FastAPI Application Configuration
# ============================================================================


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
