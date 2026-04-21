from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_once import main, run_pipeline_from_config


def test_project_root_contains_run_once_script():
    assert Path("run_once.py").exists()


def test_main_returns_zero_when_pipeline_succeeds(monkeypatch):
    monkeypatch.setattr("run_once.run_pipeline_from_config", lambda: 0)

    assert main() == 0


def test_run_pipeline_from_config_builds_enabled_sources_and_notifier(monkeypatch):
    captured: dict = {}

    class DummySettings:
        database_url = "sqlite:///tmp/papers.db"
        log_level = "INFO"
        timezone = "Asia/Shanghai"
        max_notify_items = 5

    def fake_run_pipeline(*, database_url, sources, notifier):
        captured["database_url"] = database_url
        captured["sources"] = sources
        captured["notifier"] = notifier
        class Summary:
            total_fetched = 0
            total_new = 0
            total_notified = 0
            per_source = {}

        return Summary()

    monkeypatch.setattr("run_once.AppSettings", lambda: DummySettings())
    monkeypatch.setattr(
        "run_once.load_source_config",
        lambda path: {
            "arxiv": {"enabled": True, "categories": ["cs.CV"]},
            "openreview": {"enabled": True, "venues": ["CVPR"]},
        },
    )
    monkeypatch.setattr("run_once.configure_logging", lambda settings: None)
    monkeypatch.setattr("run_once.run_pipeline", fake_run_pipeline)

    result = run_pipeline_from_config()

    assert result == 0
    assert captured["database_url"] == "sqlite:///tmp/papers.db"
    assert [source.name for source in captured["sources"]] == ["arxiv", "openreview"]
    assert captured["notifier"] is None


def test_run_pipeline_from_config_returns_non_zero_when_any_source_fails(monkeypatch):
    class DummySettings:
        database_url = "sqlite:///tmp/papers.db"
        log_level = "INFO"
        timezone = "Asia/Shanghai"
        max_notify_items = 5

    class Summary:
        total_fetched = 0
        total_new = 0
        total_notified = 0
        per_source = {"broken": {"status": "failed", "fetched": 0, "new": 0, "error": "boom"}}
        has_failures = True

    monkeypatch.setattr("run_once.AppSettings", lambda: DummySettings())
    monkeypatch.setattr("run_once.load_source_config", lambda path: {})
    monkeypatch.setattr("run_once.configure_logging", lambda settings: None)
    monkeypatch.setattr("run_once.run_pipeline", lambda **kwargs: Summary())

    assert run_pipeline_from_config() == 1


def test_cron_example_file_exists():
    assert Path("scripts/setup_cron.example").exists()


def test_feishu_smoke_test_script_exists():
    assert Path("scripts/send_test_feishu_message.py").exists()
