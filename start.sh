#!/usr/bin/env bash
set -o errexit

cd src

# Caminho para os arquivos de controle (geralmente em um volume persistente ou pasta temporária)
STATIC_FLAG="/tmp/static_collected.flag"
MIGRATE_FLAG="/tmp/migration_done.flag"

# 1. Coleta de arquivos estáticos
# Roda se a variável for 1 E se o arquivo de trava NÃO existir
if [ "${RUN_STATIC_COLLECTION_ON_START:-0}" = "1" ] && [ ! -f "$STATIC_FLAG" ]; then
    echo "Collecting static files for the first time..."
    python manage.py collectstatic --noinput
    touch "$STATIC_FLAG" # Cria o arquivo para marcar como feito
else
    echo "Skipping static file collection (already done or disabled)."
fi

# 2. Migrações do Banco de Dados
if [ "${RUN_MIGRATIONS_ON_START:-0}" = "1" ] && [ ! -f "$MIGRATE_FLAG" ]; then
    echo "Running migrations for the first time..."
    python manage.py migrate --noinput
    touch "$MIGRATE_FLAG" # Cria o arquivo para marcar como feito
else
    echo "Skipping migrations (already done or disabled)."
fi

echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
