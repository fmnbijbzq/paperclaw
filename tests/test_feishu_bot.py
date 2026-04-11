from pathlib import Path
import sys

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.notifiers.feishu_bot import FeishuBotNotifier


def test_feishu_message_contains_new_paper_title():
    notifier = FeishuBotNotifier("https://example.invalid/hook")

    payload = notifier.build_payload(
        summary_title="Daily Digest",
        papers=[{"title": "Vision Paper", "paper_url": "https://example.test/paper"}],
    )

    assert payload["msg_type"] == "text"
    assert "Vision Paper" in str(payload)


def test_feishu_message_truncates_to_max_items():
    notifier = FeishuBotNotifier("https://example.invalid/hook", max_items=1)

    payload = notifier.build_payload(
        summary_title="Daily Digest",
        papers=[
            {"title": "Vision Paper", "paper_url": "https://example.test/paper-1"},
            {"title": "Second Paper", "paper_url": "https://example.test/paper-2"},
        ],
    )

    text = payload["content"]["text"]
    assert "Vision Paper" in text
    assert "Second Paper" not in text


def test_feishu_send_posts_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"StatusCode": 0})

    notifier = FeishuBotNotifier(
        "https://example.invalid/hook",
        transport=httpx.MockTransport(handler),
    )

    notifier.send({"msg_type": "text", "content": {"text": "hello"}})

    assert captured["url"] == "https://example.invalid/hook"
    assert "hello" in captured["body"]


def test_feishu_send_adds_signature_when_secret_is_configured():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"StatusCode": 0})

    notifier = FeishuBotNotifier(
        "https://example.invalid/hook",
        secret="test-secret",
        transport=httpx.MockTransport(handler),
    )

    notifier.send({"msg_type": "text", "content": {"text": "hello"}})

    assert '"timestamp"' in captured["body"]
    assert '"sign"' in captured["body"]
    assert '"msg_type":"text"' in captured["body"]


def test_feishu_notifier_notify_builds_and_sends_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"StatusCode": 0})

    notifier = FeishuBotNotifier(
        "https://example.invalid/hook",
        transport=httpx.MockTransport(handler),
    )

    class Summary:
        total_new = 1
        total_fetched = 2
        new_papers = [
            {
                "title": "Vision Paper",
                "paper_url": "https://example.test/paper",
            }
        ]

    notifier.notify(Summary())

    assert "Vision Paper" in captured["body"]
