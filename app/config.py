from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


class AppSettings(BaseSettings):
    database_url: str
    feishu_bot_webhook: str | None = None
    feishu_bot_secret: str | None = None
    log_level: str = "INFO"
    log_format: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    log_include_location: bool = False
    log_file: str | None = None
    timezone: str = "Asia/Shanghai"
    max_notify_items: int = 10
    api_key: str | None = None
    cors_allow_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(
        env_file=str(DOTENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        runtime_dotenv = Path.cwd() / ".env"
        dotenv_files = [str(DOTENV_PATH)]
        if runtime_dotenv != DOTENV_PATH:
            dotenv_files.append(str(runtime_dotenv))
        runtime_aware_dotenv = DotEnvSettingsSource(
            settings_cls,
            env_file=tuple(dotenv_files),
            env_file_encoding=settings_cls.model_config.get("env_file_encoding"),
        )
        return init_settings, env_settings, runtime_aware_dotenv, file_secret_settings


def load_source_config(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    loaded = yaml.safe_load(content)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("Source config must be a mapping")
    return loaded
