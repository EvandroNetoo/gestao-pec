#!/usr/bin/env bash
# Para o script se der erro
set -o errexit

cd src

# Define o caminho das flags
# Nota: /tmp costuma persistir enquanto o container estiver rodando. 
# Se o container for DELETADO e recriado, ele rodará de novo (o que é o ideal).
STATIC_FLAG="/tmp/static_collected.flag"
MIGRATE_FLAG="/tmp/migration_done.flag"

# 1. Coleta de arquivos estáticos
if [ ! -f "$STATIC_FLAG" ]; then
    echo "First run: Collecting static files..."
    python manage.py collectstatic --noinput
    touch "$STATIC_FLAG"
else
    echo "Static files already collected. Skipping..."
fi

# 2. Migrações do Banco de Dados
if [ ! -f "$MIGRATE_FLAG" ]; then
    echo "First run: Running migrations..."
    python manage.py migrate --noinput
    touch "$MIGRATE_FLAG"
else
    echo "Migrations already applied. Skipping..."
fi

echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
