#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Apply database migrations
python manage.py migrate

# Create superuser if not exists
python manage.py shell -c "
from django.contrib.auth.models import User
username = 'admin'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, 'admin@example.com', 'admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"

exec "$@" 