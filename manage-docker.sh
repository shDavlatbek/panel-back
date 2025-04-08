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

# Function to check if backend is running
check_backend_running() {
    local compose_file=$1
    local container_name
    
    if [ -n "$compose_file" ]; then
        container_name=$(docker compose -f $compose_file ps -q backend)
    else
        container_name=$(docker compose ps -q backend)
    fi
    
    if [ -z "$container_name" ]; then
        echo "Backend container is not running. Please start it first."
        return 1
    fi
    
    local container_status=$(docker inspect --format='{{.State.Status}}' $container_name)
    if [ "$container_status" != "running" ]; then
        echo "Backend container is not in running state. Current state: $container_status"
        return 1
    fi
    
    return 0
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
        docker compose up --build -d
        ;;
    prod)
        echo "Starting production environment..."
        docker compose -f docker-compose.prod.yml up --build -d
        ;;
    test)
        echo "Starting test environment..."
        cp .env.test .env
        cp nginx/conf.d/app.dev.conf nginx/conf.d/default.conf
        docker compose -f docker-compose.test.yml up --build -d
        ;;
    stop)
        echo "Stopping all containers..."
        docker compose stop
        docker compose -f docker-compose.prod.yml stop
        docker compose -f docker-compose.test.yml stop
        ;;
    down)
        echo "Stopping and removing all containers..."
        docker compose down
        docker compose -f docker-compose.prod.yml down
        docker compose -f docker-compose.test.yml down
        ;;
    logs)
        echo "Showing logs..."
        docker compose logs -f
        ;;
    backup)
        echo "Backing up the database..."
        if docker compose exec db pg_dump -U postgres panel_back_prod > backup-$(date +%Y%m%d%H%M%S).sql; then
            echo "Backup created: backup-$(date +%Y%m%d%H%M%S).sql"
        else
            echo "Backup failed. Make sure the database container is running."
        fi
        ;;
    migrate)
        echo "Running migrations..."
        if check_backend_running; then
            docker compose exec backend python manage.py migrate
        elif check_backend_running "docker-compose.prod.yml"; then
            docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
        elif check_backend_running "docker-compose.test.yml"; then
            docker compose -f docker-compose.test.yml exec backend python manage.py migrate
        else
            echo "Cannot run migrations. Backend container is not running in any environment."
            echo "Please start the environment first."
            exit 1
        fi
        ;;
    createsuperuser)
        echo "Creating superuser..."
        if check_backend_running; then
            docker compose exec backend python manage.py createsuperuser
        elif check_backend_running "docker-compose.prod.yml"; then
            docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
        elif check_backend_running "docker-compose.test.yml"; then
            docker compose -f docker-compose.test.yml exec backend python manage.py createsuperuser
        else
            echo "Cannot create superuser. Backend container is not running in any environment."
            echo "Please start the environment first."
            exit 1
        fi
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