# Paperclaw

AI vision paper crawler that collects papers from arXiv, OpenReview, and CVF,
stores them in a local database, generates structured insights, and delivers
Feishu notifications.

Includes a **Next.js dashboard** for browsing papers, editorial drafts, pipeline
status, and export records.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Running the Full Stack](#running-the-full-stack)
- [Testing](#testing)
- [Content Pipeline](#content-pipeline)
- [Notification Behaviour](#notification-behaviour)
- [Cron Deployment](#cron-deployment)
- [Logs](#logs)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool          | Version  | Purpose                         |
| ------------- | -------- | ------------------------------- |
| Python        | >= 3.12  | Backend / crawler               |
| conda / uv    | recent   | Python environment management   |
| Node.js       | >= 18    | Frontend dashboard              |
| npm           | latest   | Frontend package manager        |

---

## Project Structure

```
paperclaw/
├── app/                  # Python backend (FastAPI + crawler pipeline)
│   ├── api/              # FastAPI REST API
│   ├── sources/          # arXiv / OpenReview / CVF adapters
│   ├── editorial/        # Content composition
│   └── notifiers/        # Feishu bot
├── frontend/             # Next.js 15 dashboard (see frontend/README.md)
├── config/               # YAML source configuration
├── scripts/              # Helper scripts
├── tests/                # Python backend tests
├── outputs/              # Generated content (editorial drafts, exports)
├── run_once.py           # Single-execution crawler entry point
├── run_notify_once.py    # Single-execution notification sender
└── pyproject.toml        # Python project metadata
```

---

## Backend Setup

### 1. Create the Python environment

Using **conda**:

```bash
conda run -n paperclaw python -m pip install -e .[dev]
```

Or using **uv**:

```bash
uv sync --extra dev
```

### 2. Configure environment variables

Copy the example env file and edit it:

```bash
cp .env.example .env   # if .env.example exists, otherwise create .env
```

| Variable                | Description                                        | Default          |
| ----------------------- | -------------------------------------------------- | ---------------- |
| `DATABASE_URL`          | SQLite path, e.g. `sqlite:///data/papers.db`       | *(required)*     |
| `FEISHU_BOT_WEBHOOK`    | Feishu webhook URL                                 | *(optional)*     |
| `FEISHU_BOT_SECRET`     | HMAC secret for Feishu signature verification      | *(optional)*     |
| `MAX_NOTIFY_ITEMS`      | Max papers per Feishu notification                 | `10`             |
| `LOG_LEVEL`             | Logging level                                      | `INFO`           |
| `TIMEZONE`              | IANA timezone                                      | `Asia/Shanghai`  |
| `LOG_FILE`              | Path to persist logs                               | *(optional)*     |

Edit `config/sources.yaml` to tune source settings:

- arXiv categories
- OpenReview venue filters
- CVF conferences (CVPR / ICCV / ECCV)
- Per-source lookback windows

### 3. Initialize the database

The database schema is created automatically on first run. To initialise
manually without fetching papers:

```bash
python -c "from app.storage import Database; import os; Database(os.environ.get('DATABASE_URL', 'sqlite:///data/papers.db')).create_schema()"
```

### 4. Run the backend

#### Crawler pipeline (single execution)

```bash
conda run -n paperclaw python run_once.py
```

This fetches papers from all enabled sources, upserts them into the database,
and generates per-paper structured insights.

#### Notification cycle

```bash
conda run -n paperclaw python run_notify_once.py
```

Sends up to `MAX_NOTIFY_ITEMS` pending papers in one combined Feishu message.

#### REST API server

```bash
conda run -n paperclaw uvicorn app.api.app:create_app --factory --reload
```

The API starts at **http://localhost:8000** by default.  
Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Frontend Setup

See **[frontend/README.md](frontend/README.md)** for full details.

### Quick start

```bash
cd frontend
npm install
npm run dev
```

The dashboard starts at **http://localhost:3000**.

### Available npm scripts

| Script            | Purpose                                  |
| ----------------- | ---------------------------------------- |
| `npm run dev`     | Dev server with hot-reload               |
| `npm run build`   | Production build                         |
| `npm run start`   | Serve production build                   |
| `npm run lint`    | ESLint (zero warnings)                   |
| `npm run test`    | Unit tests                               |
| `npm run clean`   | Delete `.next` cache directory           |

### Connecting to the backend

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Without this variable the frontend uses demo data (no backend required).

---

## Running the Full Stack

Open **two terminals** from the repository root:

```bash
# Terminal 1 — Backend API
conda run -n paperclaw uvicorn app.api.app:create_app --factory --reload

# Terminal 2 — Frontend dashboard
cd frontend && npm run dev
```

Then open **http://localhost:3000**.

---

## Testing

### Backend tests

```bash
conda run -n paperclaw python -m pytest tests/ -q
```

Run specific test files:

```bash
conda run -n paperclaw python -m pytest tests/test_pipeline.py -q
```

Run the live Feishu integration test:

```bash
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' \
  conda run -n paperclaw python -m pytest -q -m integration
```

### Frontend tests

```bash
cd frontend
npm run test
```

---

## Content Pipeline

1. **Fetch + store + generate insights:**
   ```bash
   python run_once.py
   ```

2. **Compose platform drafts** (bilibili / xiaohongshu / douyin):
   ```bash
   python scripts/run_content_pipeline.py --limit 3
   ```
   Drafts are written to `outputs/editorial/YYYY-MM-DD/`.

3. **Human review** — edit the drafts in `outputs/editorial/YYYY-MM-DD/`.

4. **Export for publishing:**
   ```bash
   python scripts/export_for_publish.py --date YYYY-MM-DD
   ```
   Exports to `outputs/exported/YYYY-MM-DD/`.

---

## Notification Behaviour

- Each cycle sends one combined Feishu message containing up to
  `MAX_NOTIFY_ITEMS` papers.
- Each send attempt is persisted in the `notifications` table.
- A paper is considered pending until it has at least one successful
  notification record for destination `feishu`.
- Failed attempts remain retryable in the next cycle.

---

## Cron Deployment

Example cron entries (see `scripts/setup_cron.example`):

```bash
# Fetch papers at 08:00 daily
0 8 * * * cd /root/workspace/paperclaw && /root/miniconda3/bin/conda run -n paperclaw python run_once.py >> logs/fetch.log 2>&1

# Send pending notifications every 10 minutes
*/10 * * * * cd /root/workspace/paperclaw && /root/miniconda3/bin/conda run -n paperclaw python run_notify_once.py >> logs/notify.log 2>&1
```

Install:

```bash
crontab scripts/setup_cron.example
```

---

## Logs

- **Fetch logs** — which source was scanned, how many papers fetched
- **Insight logs** — whether summary generation succeeded per paper
- **Notification logs** — which papers were picked and send success/failure
- If `LOG_FILE` is configured, logs persist to disk

---

## Troubleshooting

| Problem                              | Fix                                                        |
| ------------------------------------ | ---------------------------------------------------------- |
| Frontend shows stale pages           | `cd frontend && npm run clean && npm run dev`              |
| `npm run build` fails in frontend    | `rm -rf frontend/node_modules frontend/.next && cd frontend && npm install` |
| Port 3000 in use                     | `npx next dev -p 3001` (in `frontend/`)                   |
| Port 8000 in use                     | `uvicorn app.api.app:create_app --factory --port 8001`     |
| Database locked errors               | Ensure only one crawler process runs at a time             |
| Feishu messages not sending          | Check `FEISHU_BOT_WEBHOOK` in `.env`                       |
