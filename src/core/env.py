from pathlib import Path

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = 'utf-8'
        case_sensitive = True

    # Core Settings
    SECRET_KEY: str = 'change-me-in-production'  # noqa: S105
    DEBUG: bool = False
    LOG_LEVEL: str = 'INFO'
    ALLOWED_HOSTS: list[str] = ['*']
    CSRF_TRUSTED_ORIGINS: list[str] = []
    
    @field_validator('ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', mode='before')
    @classmethod
    def parse_comma_separated_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v

    # Database
    DATABASE_URL: str = 'sqlite:///db.sqlite3'

    # Security Settings (Set to True in production with HTTPS)
    SESSION_COOKIE_SECURE: bool = False
    CSRF_COOKIE_SECURE: bool = False


env_settings = EnvSettings()
