# Deploy on Render (Flask + Postgres)

This project is ready for Render using the included `render.yaml`.

## 1) Create the Render services

1. Push this repo to GitHub.
2. In Render: **New +** → **Blueprint** → select your repo.
3. Render will create:
   - A **Web Service** (runs Gunicorn)
   - A **PostgreSQL** database (if you attach one manually, just copy its `DATABASE_URL`)

## 2) Required environment variables

In Render → your Web Service → **Environment**:

- `DATABASE_URL`
  - Use the Postgres connection string from your Render database.
- `SECRET_KEY`
  - Any long random string.

Optional:
- `AUTO_CREATE_DB=false` (already set in `render.yaml`)
- Email (only if you want password reset emails to actually send):
  - `MAIL_SERVER`
  - `MAIL_PORT`
  - `MAIL_USE_TLS`
  - `MAIL_USE_SSL`
  - `MAIL_USERNAME`
  - `MAIL_PASSWORD`
  - `MAIL_DEFAULT_SENDER`

## 3) Migrations

Render free tier doesn't support `preDeployCommand`. This repo runs migrations automatically
at service start (before Gunicorn) via the `startCommand` in `render.yaml`.

## 4) Start command

Render runs:

- `python -m flask --app wsgi:app db upgrade && gunicorn wsgi:app --bind 0.0.0.0:$PORT`

## 5) Health check

A health endpoint is available:

- `/healthz`

You can use it for monitoring or troubleshooting.
