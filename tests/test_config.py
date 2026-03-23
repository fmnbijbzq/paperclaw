import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import AppSettings, load_source_config
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


def test_app_settings_loads_project_root_env_when_cwd_changes(monkeypatch, tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    env_file = project_root / ".env"
    original_text = env_file.read_text(encoding="utf-8") if env_file.exists() else None
    env_file.write_text("DATABASE_URL=sqlite:///data/from-dotenv.db\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    try:
        settings = AppSettings()
        assert settings.database_url == "sqlite:///data/from-dotenv.db"
    finally:
        if original_text is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(original_text, encoding="utf-8")


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
