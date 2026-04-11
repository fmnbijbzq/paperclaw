from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import AppSettings
from app.notifiers.feishu_bot import FeishuBotNotifier


def main() -> int:
    settings = AppSettings()
    webhook = settings.feishu_bot_webhook
    if not webhook:
        print("FEISHU_BOT_WEBHOOK is not set", file=sys.stderr)
        return 1

    notifier = FeishuBotNotifier(webhook, secret=settings.feishu_bot_secret)
    result = notifier.send(
        {
            "msg_type": "text",
            "content": {"text": "paperclaw webhook smoke test"},
        }
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
