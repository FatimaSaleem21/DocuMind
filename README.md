# docuMind

Upload financial PDFs, retrieve grounded answers via RAG. Django + DRF backend,
React frontend, Celery for background document processing, Postgres + pgvector for
embedding storage, and OpenAI for embeddings and chat.

## Architecture

- **Backend** — Django 4.2 / Django REST Framework, split-settings layout.
- **Async** — Celery worker (Redis broker) for PDF ingestion and embedding.
- **Vector store** — Postgres with the `pgvector` extension.
- **Chat** — server-sent events (SSE) stream answers token-by-token to the frontend.
- **Frontend** — React + Vite (`documind-frontend/`).

## Settings

Settings are split into a package:

- `docuMind/settings/base.py` — shared config; safe defaults for local dev.
- `docuMind/settings/production.py` — `DEBUG=False`, secrets and hosts read from
  the environment (boot fails loudly if they're missing), WhiteNoise for static
  files, and HTTPS hardening (SSL redirect, HSTS, secure cookies).

Select settings with `DJANGO_SETTINGS_MODULE`:

```bash
# local / CI (default)
export DJANGO_SETTINGS_MODULE=docuMind.settings.base

# production
export DJANGO_SETTINGS_MODULE=docuMind.settings.production
```

### Required environment variables (production)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key (no fallback in production) |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins — an explicit allowlist, **never** `CORS_ALLOW_ALL_ORIGINS` |
| `POSTGRES_*` | DB name / user / password / host / port |
| `REDIS_URL` | Celery broker and result backend |
| `OPENAI_API_KEY` | Embeddings + chat |

## Running the server

The chat endpoint streams responses over SSE, so the WSGI server **must not use
sync workers**. A streaming response holds its worker for the full duration of the
stream; with the default `sync` class, a handful of concurrent chat sessions
exhausts the worker pool and every other request blocks or times out. This is the
same class of bug I debugged on Maiden Century's SSE endpoint — so it's a
deliberate, up-front choice here, not something to discover in production.

The `Procfile` uses `gthread` workers accordingly:

```
web: gunicorn docuMind.wsgi:application --worker-class=gthread --threads=4 --workers=2 --timeout=120 --bind 0.0.0.0:$PORT
worker: celery -A docuMind worker --loglevel=info --concurrency=2 --max-tasks-per-child=50
```

`gthread` (or `gevent`) lets a single worker hold many concurrent streaming
connections on separate threads instead of one connection monopolizing a process.
`--bind 0.0.0.0:$PORT` binds to the port the host injects (Railway/Render assign a
dynamic `$PORT`), rather than gunicorn's default 8000.

The Celery worker pins `--concurrency=2` because prefork otherwise forks one
process per CPU — on a 48-core host that's 48 copies of the app in memory, which
OOMs a small instance. `--max-tasks-per-child=50` recycles workers to reclaim any
memory creep from the PDF/embedding libraries.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # runtime deps (pinned)
pip install -r requirements-dev.txt      # ruff, etc.

# Postgres (with pgvector) + Redis are expected on localhost by default.
python manage.py migrate
python manage.py runserver
```

Before deploying, confirm the app boots under production settings:

```bash
DJANGO_SETTINGS_MODULE=docuMind.settings.production \
  SECRET_KEY=... ALLOWED_HOSTS=... CORS_ALLOWED_ORIGINS=... \
  python manage.py check --deploy
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on pushes and PRs to `main`:

- **lint** — `ruff` (backend) and `oxlint` (frontend)
- **test** — `python manage.py test` against Postgres/pgvector + Redis service containers
- **build** — frontend production build