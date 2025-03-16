#!/bin/bash

set -e

# Check if database environment variable is set to postgres
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for PostgreSQL..."
    
    # Wait for the database to be ready
    sleep 5
    
    # Try simple connection to database to check availability
    echo "Checking database connection..."
    python -c "
import psycopg2
import time
import os

dbname = os.environ.get('DB_NAME', 'postgres')
user = os.environ.get('DB_USER', 'postgres')
password = os.environ.get('DB_PASSWORD', 'postgres')
host = os.environ.get('DB_HOST', 'db')
port = os.environ.get('DB_PORT', '5432')

print(f'Connecting to PostgreSQL at {host}:{port}...')

for i in range(30):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print('PostgreSQL is available!')
        break
    except psycopg2.OperationalError as e:
        print(f'PostgreSQL is unavailable - sleeping ({i+1}/30)')
        time.sleep(1)
"

    echo "PostgreSQL is ready!"
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if not exists
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
username = 'admin'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, 'admin@example.com', 'admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"

# Execute the command passed to docker
exec "$@" 