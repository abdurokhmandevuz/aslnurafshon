#!/usr/bin/env bash
set -euo pipefail

echo "Running migrations..."
python manage.py migrate --noinput

if [ -n "${BOT_TOKEN:-}" ]; then
  echo "Starting Telegram bot in polling mode..."
  BOT_WEBHOOK_URL= python -m bot.main &
else
  echo "BOT_TOKEN is not set; skipping bot"
fi

echo "Starting web server on port ${PORT:-8080}..."
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}" --workers 2 --timeout 120
