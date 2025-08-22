#!/bin/bash

# Build script for the LDP (License Document Processing) application
# This script builds the Docker containers for production deployment

set -e  # Exit on any error

echo "🚀 Building LDP Application with React Frontend..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists, if not copy from example
if [ ! -f .env ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update the .env file with your actual configuration before deployment!"
fi

# Build the containers
echo "🔨 Building Docker containers..."
docker-compose build --no-cache

echo "✅ Build completed successfully!"
echo ""
echo "📌 To run the application:"
echo "   docker-compose up -d"
echo ""
echo "📌 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "📌 To stop the application:"
echo "   docker-compose down"
echo ""
echo "🌐 The application will be available at:"
echo "   - Frontend: http://localhost:8000/"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Flower (Celery Monitor): http://localhost:5555/"
