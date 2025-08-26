#!/bin/bash

# Iranian Price Intelligence Platform Deployment Script

set -e

echo "🚀 Deploying Iranian Price Intelligence Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null
then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs/{api,scraper,matcher}
mkdir -p data

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo "🏃 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check service status
echo "📋 Checking service status..."
docker-compose ps

# Test API health
echo "🩺 Testing API health..."
curl -f http://localhost:8000/health || echo "⚠️ API health check failed"

echo "✅ Deployment completed!"
echo ""
echo "🌐 Access your services:"
echo "   API: http://localhost:8000"
echo ""
echo "📊 Next steps:"
echo "   1. Register a user account at http://localhost:8000/auth/register"
echo "   2. Start using the API endpoints"
echo "   3. Check logs with: docker-compose logs -f"