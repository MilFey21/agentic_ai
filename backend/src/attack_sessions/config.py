from pathlib import Path

from pydantic import field_validator

from src.base_config import BaseConfig


class AttackSessionsConfig(BaseConfig):
    ATTACK_TEMPLATES_DIR: Path = Path(__file__).parent.parent / 'education_modules' / 'attacks'
    KITESURF_CUSTOMERS_CSV: Path = Path(__file__).parent.parent / 'education_modules' / 'attacks' / 'kitesurf_customers.csv'

    @field_validator('ATTACK_TEMPLATES_DIR', mode='before')
    @classmethod
    def validate_templates_dir(cls, v: str | Path) -> Path:
        return Path(v)

    @field_validator('KITESURF_CUSTOMERS_CSV', mode='before')
    @classmethod
    def validate_csv_path(cls, v: str | Path) -> Path:
        return Path(v)


# Configuration for templates that require file uploads
# Maps template name to (file_component_id, file_path_config_key)
TEMPLATE_FILE_CONFIG: dict[str, tuple[str, str]] = {
    'agentic_flow': ('File-M0vOp', 'KITESURF_CUSTOMERS_CSV'),
}


attack_sessions_settings = AttackSessionsConfig()
