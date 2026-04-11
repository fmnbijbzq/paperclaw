from pathlib import Path
import os
import sys

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.notifiers.feishu_bot import FeishuBotNotifier

pytestmark = pytest.mark.integration


def test_feishu_webhook_live():
    webhook = os.getenv("FEISHU_BOT_WEBHOOK")
    if not webhook:
        pytest.skip("FEISHU_BOT_WEBHOOK not set")

    notifier = FeishuBotNotifier(webhook)
    result = notifier.send(
        {
            "msg_type": "text",
            "content": {"text": "paperclaw integration test"},
        }
    )

    assert result["StatusCode"] == 0
