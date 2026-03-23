from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import AppSettings, load_source_config


def test_app_settings_reads_database_url():
    settings = AppSettings.model_validate(
        {
            "database_url": "sqlite:///data/papers.db",
            "feishu_bot_webhook": "https://example.invalid/hook",
        }
    )
    assert settings.database_url == "sqlite:///data/papers.db"


def test_load_source_config_reads_arxiv_categories(tmp_path: Path):
    config_file = tmp_path / "sources.yaml"
    config_file.write_text("arxiv:\n  enabled: true\n  categories:\n    - cs.CV\n")
    data = load_source_config(config_file)
    assert data["arxiv"]["categories"] == ["cs.CV"]
