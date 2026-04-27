# Paperclaw

AI vision paper crawler for collecting AI vision papers from arXiv/OpenReview/CVF, storing them locally, and generating Feishu-ready + social-ready content artifacts.

## Setup

Use the `paperclaw` conda environment, then install the project dependencies:

```
conda run -n paperclaw python -m pip install -e .[dev]
```

If you prefer `uv` in this repo:

```
uv sync --extra dev
```

## Configuration

1. Copy `.env.example` to `.env`
2. Set `DATABASE_URL`
3. Set `FEISHU_BOT_WEBHOOK` if you want Feishu notifications
4. Set `FEISHU_BOT_SECRET` as well if your Feishu bot has signature verification enabled
5. Set `MAX_NOTIFY_ITEMS` to control how many pending papers are processed and sent in each notification cycle
6. Adjust `LOG_LEVEL`, `TIMEZONE`, `LOG_FILE`, and `LOG_INCLUDE_LOCATION` as needed

Edit `config/sources.yaml` to enable or tune sources such as:

- arXiv categories
- OpenReview venue filters
- CVF conferences (CVPR/ICCV/ECCV)
- per-source lookback windows

## Manual Run

From the repository root:

```
conda run -n paperclaw python run_once.py
```

This command fetches papers, stores them, and generates per-paper structured insights (`paper_insights`).

To run one notification cycle manually:

```
conda run -n paperclaw python run_notify_once.py
```

`run_notify_once.py` scans papers that have not yet been successfully delivered to Feishu, sends up to `MAX_NOTIFY_ITEMS` papers in one combined Feishu message, and writes one record per paper attempt into the `notifications` table. Successful attempts are marked with `success=true`; failed attempts are kept for retry in the next cycle.

## Content Pipeline (new)

Generate platform drafts (bilibili/xiaohongshu/douyin):

```
python scripts/run_content_pipeline.py --limit 3
```

This writes markdown drafts under:

```
outputs/editorial/YYYY-MM-DD/
```

Export reviewed/selected drafts to publish package folder:

```
python scripts/export_for_publish.py --date YYYY-MM-DD
```

This exports to:

```
outputs/exported/YYYY-MM-DD/
```

## Workflow: fetch -> insight -> editorial -> export

1. `python run_once.py` (fetch + upsert + insight)
2. `python scripts/run_content_pipeline.py --limit N` (compose platform drafts)
3. Human review drafts in `outputs/editorial/YYYY-MM-DD/`
4. `python scripts/export_for_publish.py --date YYYY-MM-DD` (export package)

## Notification Behavior

- Each cycle sends one combined Feishu message containing up to `MAX_NOTIFY_ITEMS` papers
- Each send attempt is persisted in `notifications`
- A paper is considered pending until it has at least one successful notification record for destination `feishu`
- Failed attempts remain retryable in the next sender cycle

## Logs

- Fetch logs show which source was scanned, how many papers were fetched, and whether each paper was inserted as new or already existed
- Insight logs show whether summary generation succeeded per paper
- Notification logs show which papers were picked for the current cycle and whether each send attempt succeeded or failed
- If `LOG_FILE` is configured, fetch/insight/notification logs can be persisted to disk

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

To run the newly added focused tests:

```
pytest tests/test_cvf_source.py tests/test_summarization_service.py tests/test_editorial_composer.py -q
```

To run the live Feishu webhook integration test explicitly:

```
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' conda run -n paperclaw python -m pytest -q -m integration
```

To send a one-off webhook smoke test without running the full pipeline:

```
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' conda run -n paperclaw python scripts/send_test_feishu_message.py
```
