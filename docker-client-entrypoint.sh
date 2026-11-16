#!/bin/bash
set -e

echo "Waiting for database..."
python - <<'PY'
import os
import time
import psycopg2

for attempt in range(60):
    try:
        connection = psycopg2.connect(
            host=os.environ["DB_HOST"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            dbname=os.environ["DB_NAME"],
            port=os.environ.get("DB_PORT", "5432"),
            connect_timeout=5,
        )
        connection.close()
        print("Database connection ready.")
        break
    except psycopg2.OperationalError:
        if attempt == 59:
            raise
        time.sleep(2)
PY

echo "Applying client migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Collecting client static files..."
mkdir -p /app/clients/staticfiles
python manage.py collectstatic --noinput --clear

if [[ -n "${DJANGO_SUPERUSER_USERNAME}" && -n "${DJANGO_SUPERUSER_PASSWORD}" && -n "${DJANGO_SUPERUSER_EMAIL}" ]]; then
    echo "Creating client superuser..."
    python manage.py createsuperuser --noinput || true
fi

exec "$@"
