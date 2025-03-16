#!/bin/bash

# Helper script for Docker environments

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo "Commands:"
    echo "  dev           - Start development environment"
    echo "  prod          - Start production environment"
    echo "  test          - Start test environment"
    echo "  stop          - Stop all containers"
    echo "  down          - Stop and remove all containers"
    echo "  logs          - Show logs"
    echo "  backup        - Backup the database"
    echo "  migrate       - Run database migrations"
    echo "  createsuperuser - Create a superuser"
    echo "  help          - Show this help"
}

# Check if command is provided
if [ -z "$1" ]; then
    show_usage
    exit 1
fi

# Process command
case "$1" in
    dev)
        echo "Starting development environment..."
        docker-compose up -d
        ;;
    prod)
        echo "Starting production environment..."
        docker-compose -f docker-compose.prod.yml up -d
        ;;
    test)
        echo "Starting test environment..."
        cp .env.test .env
        cp nginx/conf.d/app.dev.conf nginx/conf.d/default.conf
        docker-compose -f docker-compose.prod.yml up -d
        ;;
    stop)
        echo "Stopping all containers..."
        docker-compose stop
        docker-compose -f docker-compose.prod.yml stop
        ;;
    down)
        echo "Stopping and removing all containers..."
        docker-compose down
        docker-compose -f docker-compose.prod.yml down
        ;;
    logs)
        echo "Showing logs..."
        docker-compose logs -f
        ;;
    backup)
        echo "Backing up the database..."
        docker-compose exec db pg_dump -U postgres panel_back_prod > backup-$(date +%Y%m%d%H%M%S).sql
        echo "Backup created: backup-$(date +%Y%m%d%H%M%S).sql"
        ;;
    migrate)
        echo "Running migrations..."
        docker-compose exec backend python manage.py migrate
        ;;
    createsuperuser)
        echo "Creating superuser..."
        docker-compose exec backend python manage.py createsuperuser
        ;;
    help)
        show_usage
        ;;
    *)
        echo "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

exit 0 