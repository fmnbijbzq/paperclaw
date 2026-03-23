import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import AppSettings, DOTENV_PATH, load_source_config
from app.logging import configure_logging


def test_app_settings_reads_database_url():
    settings = AppSettings.model_validate(
        {
            "database_url": "sqlite:///data/papers.db",
            "feishu_bot_webhook": "https://example.invalid/hook",
        }
    )
    assert settings.database_url == "sqlite:///data/papers.db"


def test_app_settings_reads_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/env.db")
    settings = AppSettings()
    assert settings.database_url == "sqlite:///data/env.db"


def test_app_settings_uses_absolute_project_root_dotenv_path():
    expected = Path(__file__).resolve().parents[1] / ".env"
    assert DOTENV_PATH == expected
    assert DOTENV_PATH.is_absolute()
    assert AppSettings.model_config["env_file"] == DOTENV_PATH


def test_load_source_config_reads_arxiv_categories(tmp_path: Path):
    config_file = tmp_path / "sources.yaml"
    config_file.write_text("arxiv:\n  enabled: true\n  categories:\n    - cs.CV\n")
    data = load_source_config(config_file)
    assert data["arxiv"]["categories"] == ["cs.CV"]


def test_configure_logging_keeps_existing_root_handlers():
    root = logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    sentinel = logging.NullHandler()
    root.addHandler(sentinel)
    try:
        settings = AppSettings.model_validate({"database_url": "sqlite:///data/papers.db"})
        configure_logging(settings)
        assert sentinel in root.handlers
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_configure_logging_repeated_calls_update_existing_console_handler_level():
    root = logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    root.handlers = []
    try:
        settings_info = AppSettings.model_validate(
            {"database_url": "sqlite:///data/papers.db", "log_level": "INFO"}
        )
        configure_logging(settings_info)
        settings_error = AppSettings.model_validate(
            {"database_url": "sqlite:///data/papers.db", "log_level": "ERROR"}
        )
        configure_logging(settings_error)

        configured_handlers = [
            handler
            for handler in root.handlers
            if getattr(handler, "_paperclaw_console_handler", False)
        ]
        assert len(configured_handlers) == 1
        assert configured_handlers[0].level == logging.ERROR
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
