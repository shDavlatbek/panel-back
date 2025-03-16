#!/bin/bash

set -e

# Check if database environment variable is set to postgres
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for PostgreSQL..."

    # Wait for database to be ready
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.5
      echo "Still waiting for PostgreSQL..."
    done

    echo "PostgreSQL started!"
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