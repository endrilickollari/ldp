#!/bin/bash

# Docker management script for LDP (Large Document Processing)

set -e

case "$1" in
    "build")
        echo "Building Docker services..."
        docker-compose build
        ;;
    "up")
        echo "Starting services..."
        docker-compose up -d
        echo "Services started! Available at:"
        echo "  - API: http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/docs"
        echo "  - Flower: http://localhost:5555"
        ;;
    "down")
        echo "Stopping services..."
        docker-compose down
        ;;
    "logs")
        if [ -n "$2" ]; then
            docker-compose logs -f "$2"
        else
            docker-compose logs -f
        fi
        ;;
    "init-db")
        echo "Initializing database..."
        docker-compose exec web python init_db.py
        ;;
    "migrate")
        echo "Running database migrations..."
        docker-compose exec web python migrate_db.py
        ;;
    "test")
        echo "Running tests..."
        docker-compose exec web python -m pytest
        ;;
    "shell")
        service=${2:-web}
        echo "Opening shell for $service service..."
        docker-compose exec "$service" bash
        ;;
    "restart")
        echo "Restarting services..."
        docker-compose restart
        ;;
    *)
        echo "Usage: $0 {build|up|down|logs [service]|init-db|migrate|test|shell [service]|restart}"
        echo ""
        echo "Commands:"
        echo "  build     - Build Docker images"
        echo "  up        - Start all services"
        echo "  down      - Stop all services"
        echo "  logs      - View logs (optionally for specific service)"
        echo "  init-db   - Initialize database"
        echo "  migrate   - Run database migrations"
        echo "  test      - Run tests"
        echo "  shell     - Open shell (default: web service)"
        echo "  restart   - Restart all services"
        exit 1
        ;;
esac
