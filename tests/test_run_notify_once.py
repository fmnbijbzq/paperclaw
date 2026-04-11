from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_notify_once import main, run_notify_once_from_config


def test_project_root_contains_run_notify_once_script():
    assert Path("run_notify_once.py").exists()


def test_main_returns_zero_when_notification_cycle_succeeds(monkeypatch):
    monkeypatch.setattr("run_notify_once.run_notify_once_from_config", lambda: 0)

    assert main() == 0


def test_run_notify_once_from_config_builds_notifier(monkeypatch):
    captured: dict = {}

    class DummySettings:
        database_url = "sqlite:///tmp/papers.db"
        feishu_bot_webhook = "https://example.invalid/hook"
        feishu_bot_secret = "test-secret"
        log_level = "INFO"
        notify_batch_size = 3
        notify_send_mode = "per_paper"

    def fake_run_notification_cycle(*, database_url, notifier, batch_size, send_mode, destination):
        captured["database_url"] = database_url
        captured["notifier"] = notifier
        captured["batch_size"] = batch_size
        captured["send_mode"] = send_mode
        captured["destination"] = destination
        class Summary:
            attempted = 0
            succeeded = 0
            failed = 0

        return Summary()

    monkeypatch.setattr("run_notify_once.AppSettings", lambda: DummySettings())
    monkeypatch.setattr("run_notify_once.configure_logging", lambda settings: None)
    monkeypatch.setattr("run_notify_once.run_notification_cycle", fake_run_notification_cycle)

    result = run_notify_once_from_config()

    assert result == 0
    assert captured["database_url"] == "sqlite:///tmp/papers.db"
    assert captured["notifier"] is not None
    assert captured["notifier"].secret == "test-secret"
    assert captured["batch_size"] == 3
    assert captured["send_mode"] == "per_paper"
    assert captured["destination"] == "feishu"
