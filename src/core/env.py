from pathlib import Path

from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = 'utf-8'
        case_sensitive = True

    SECRET_KEY: str = 'change-me'  # noqa: S105
    DEBUG: bool = True
    ALLOWED_HOSTS: list[str] = []
    DATABASE_URL: str = 'sqlite:///db.sqlite3'


env_settings = EnvSettings()
