#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

echo "Running migrations..."
python src/manage.py migrate --noinput

echo "Collecting static files..."
python src/manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn core.wsgi \
  --chdir src \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 8 \
  --timeout 0 \
  --log-level info \
  --access-logfile - \
  --error-logfile -
