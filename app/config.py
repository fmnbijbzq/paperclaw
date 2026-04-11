from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
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
    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


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
