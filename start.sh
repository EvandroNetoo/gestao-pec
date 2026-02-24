#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Running collectstatic..."
cd src
python manage.py collectstatic --noinput -i

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
