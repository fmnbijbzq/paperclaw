# Paperclaw

AI vision paper crawler for collecting AI vision papers from arXiv and OpenReview, storing them locally, and sending Feishu notifications with a decoupled delivery loop.

## Setup

Use the `paperclaw` conda environment, then install the project dependencies:

```
conda run -n paperclaw python -m pip install -e .[dev]
```

## Configuration

1. Copy `.env.example` to `.env`
2. Set `DATABASE_URL`
3. Set `FEISHU_BOT_WEBHOOK` if you want Feishu notifications
4. Set `FEISHU_BOT_SECRET` as well if your Feishu bot has signature verification enabled
5. Set `NOTIFY_BATCH_SIZE` to control how many pending papers are processed per send cycle
6. Set `NOTIFY_SEND_MODE` to `combined` or `per_paper`
7. Adjust `LOG_LEVEL`, `TIMEZONE`, `LOG_FILE`, and `LOG_INCLUDE_LOCATION` as needed

Edit `config/sources.yaml` to enable or tune sources such as:

- arXiv categories
- OpenReview venue filters
- per-source lookback windows

## Manual Run

From the repository root:

```
conda run -n paperclaw python run_once.py
```

This command only fetches papers and stores them in the database. New papers stay pending for notification until the sender loop processes them.

To run one notification cycle manually:

```
conda run -n paperclaw python run_notify_once.py
```

`run_notify_once.py` scans papers that have not yet been successfully delivered to Feishu, sends up to `NOTIFY_BATCH_SIZE` papers, and writes one record per paper attempt into the `notifications` table. Successful attempts are marked with `success=true`; failed attempts are kept for retry in the next cycle.

## Notification Behavior

- `combined` mode: one Feishu message contains the current batch of papers
- `per_paper` mode: one Feishu message per paper, still limited by `NOTIFY_BATCH_SIZE`
- Each send attempt is persisted in `notifications`
- A paper is considered pending until it has at least one successful notification record for destination `feishu`
- Failed attempts remain retryable in the next sender cycle

## Logs

- Fetch logs show which source was scanned, how many papers were fetched, and whether each paper was inserted as new or already existed
- Notification logs show which papers were picked for the current cycle and whether each send attempt succeeded or failed
- If `LOG_FILE` is configured, both fetch and notification logs can be persisted to disk

## Cron Deployment

Example cron file: `scripts/setup_cron.example`

Example install command:

```
crontab scripts/setup_cron.example
```

Example cron entries:

```
0 8 * * * cd /root/workspace/paperclaw && /root/miniconda3/bin/conda run -n paperclaw python run_once.py >> logs/fetch.log 2>&1
*/10 * * * * cd /root/workspace/paperclaw && /root/miniconda3/bin/conda run -n paperclaw python run_notify_once.py >> logs/notify.log 2>&1
```

## Running the tests

From the repository root:

```
conda run -n paperclaw python -m pytest tests/test_run_once.py tests/test_pipeline.py tests/test_feishu_bot.py tests/test_notification_pipeline.py tests/test_run_notify_once.py -q
```

To run the live Feishu webhook integration test explicitly:

```
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' conda run -n paperclaw python -m pytest -q -m integration
```

To send a one-off webhook smoke test without running the full pipeline:

```
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' conda run -n paperclaw python scripts/send_test_feishu_message.py
```
