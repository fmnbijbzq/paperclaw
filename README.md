# Paperclaw

AI vision paper crawler for collecting AI vision papers from arXiv and OpenReview, storing them locally, and sending daily Feishu notifications.

## Setup

Create a virtual environment for Python 3.12+, then install the project dependencies:

```
python -m pip install -e .[dev]
```

## Configuration

1. Copy `.env.example` to `.env`
2. Set `DATABASE_URL`
3. Set `FEISHU_BOT_WEBHOOK` if you want Feishu notifications
4. Adjust `LOG_LEVEL`, `TIMEZONE`, and `MAX_NOTIFY_ITEMS` as needed

Edit `config/sources.yaml` to enable or tune sources such as:

- arXiv categories
- OpenReview venue filters
- per-source lookback windows

## Manual Run

From the repository root:

```
python run_once.py
```

## Cron Deployment

Example cron file: `scripts/setup_cron.example`

Example install command:

```
crontab scripts/setup_cron.example
```

Example cron entry:

```
0 8 * * * cd /root/workspace/paperclaw && /usr/bin/python3 run_once.py >> logs/cron.log 2>&1
```

## Running the tests

From the repository root:

```
pytest tests/test_run_once.py tests/test_pipeline.py tests/test_feishu_bot.py -q
```
