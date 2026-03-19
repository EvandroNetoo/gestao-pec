#!/usr/bin/env bash
# exit on error
set -o errexit

cd src

if [[ "${RUN_COLLECTSTATIC_ON_START:-0}" == "1" ]]; then
	echo "Running collectstatic..."
	python manage.py collectstatic --noinput
else
	echo "Skipping collectstatic (set RUN_COLLECTSTATIC_ON_START=1 to enable)."
fi

if [[ "${RUN_MIGRATIONS_ON_START:-0}" == "1" ]]; then
	if python manage.py migrate --check >/dev/null 2>&1; then
		echo "No pending migrations."
	else
		echo "Running migrations..."
		python manage.py migrate --noinput
	fi
else
	echo "Skipping migrations (set RUN_MIGRATIONS_ON_START=1 to enable)."
fi

echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
