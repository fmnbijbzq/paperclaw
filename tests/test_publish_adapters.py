from __future__ import annotations

from app.publish import BilibiliPublisher, DouyinPublisher, XiaohongshuPublisher, get_publisher


def test_stub_publishers_report_not_integrated_as_failure():
    for publisher in [BilibiliPublisher(), XiaohongshuPublisher(), DouyinPublisher()]:
        result = publisher.publish(title="Draft", content="Content")

        assert result.success is False
        assert result.published_at is None
        assert result.error_message is not None
        assert "not yet integrated" in result.error_message


def test_publisher_registry_returns_non_integrated_stub_instances():
    result = get_publisher("bilibili").publish(title="Draft", content="Content")

    assert result.success is False
