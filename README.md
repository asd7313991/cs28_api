# cs28-api

FastAPI + MySQL 5.7 + Redis backend for CS28.

## Quickstart

```bash
cp .env.example .env
# edit .env for MySQL/Redis

pip install -e .
# or: python -m pip install -e .

# (Optional) Pre-create schema:
mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS cs28 DEFAULT CHARSET utf8mb4;"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- On startup:
  - Auto create tables.
  - Ensure default lottery `jnd28` exists.
  - Warm Redis with last 200 results from MySQL.
  - Start APScheduler jobs:
    - Collector: fetches results from `COLLECTOR_JND28_URL` every `COLLECTOR_POLL_SECONDS`.
    - Current-issue ticker: refreshes `allow_bet` every 1s.

## HTTP APIs
- `GET /lottery/current?code=jnd28`
- `GET /lottery/last?code=jnd28`
- `GET /lottery/history?code=jnd28&limit=30`

Redis-first reads, DB fallback.

## Redis Keys
```
cs28:lottery:{code}:last_result   # JSON string
cs28:lottery:{code}:history       # list of JSON strings (LPUSH newest)
cs28:lottery:{code}:current_issue # hash
```
