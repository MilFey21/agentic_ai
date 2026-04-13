from src.base_config import BaseConfig


class AuthConfig(BaseConfig):
    JWT_SECRET: str = 'dev-secret-key-change-in-production'
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


auth_settings = AuthConfig()
