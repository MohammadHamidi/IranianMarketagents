#!/bin/bash

echo "🚀 Starting Iranian Price Intelligence Platform with Real Data"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to find Python
find_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        echo "python"
    else
        echo "ERROR: Python not found. Please install Python 3."
        exit 1
    fi
}

PYTHON_CMD=$(find_python)
echo "🐍 Using Python command: $PYTHON_CMD"

# Start Docker services
echo "📦 Starting Docker services..."
docker-compose up -d redis neo4j postgres

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check Redis connection
echo "🔍 Testing Redis connection..."
docker-compose exec redis redis-cli -a iranian_redis_secure_2025 ping

# Check if we're running in Docker or locally
if [ -f "/.dockerenv" ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "🏠 Running inside Docker container"
    # Use Docker services
    echo "🕷️ Starting scraper service..."
    docker-compose up -d scraper-service

    echo "🌐 Starting API service..."
    docker-compose up -d api-service

    echo "⏳ Waiting for services to be ready..."
    sleep 30
else
    echo "💻 Running on local machine"
    # Start scraper in background (single run to populate data)
    echo "🕷️ Running initial scraping..."
    cd services/scraper
    $PYTHON_CMD continuous_scraper.py &
    SCRAPER_PID=$!

    # Wait for initial scraping to complete
    echo "⏳ Waiting for initial scraping (60 seconds)..."
    sleep 60

    # Start API service
    echo "🌐 Starting API service..."
    cd ../api
    $PYTHON_CMD main.py &
    API_PID=$!
fi

# Wait for API to start
sleep 10

# Test if real data is available
echo "🔍 Checking data status..."
if command_exists curl; then
    curl -s http://localhost:8000/data/status | $PYTHON_CMD -m json.tool
else
    echo "⚠️ curl not available, skipping data status check"
fi

echo "✅ Platform started with real data!"
echo "🌐 API: http://localhost:8000"
echo "📊 Health: http://localhost:8000/health"
echo "🔍 Data Status: http://localhost:8000/data/status"
echo "📚 Docs: http://localhost:8000/docs"

# If running locally, keep services running
if [ -z "$DOCKER_CONTAINER" ] && [ ! -f "/.dockerenv" ]; then
    echo "🔄 Keeping local services running... (Press Ctrl+C to stop)"
    # Keep services running
    if [ ! -z "$API_PID" ]; then
        wait $API_PID
    fi
else
    echo "🏁 Docker services are running in background"
    echo "   Use 'docker-compose logs -f' to see logs"
    echo "   Use 'docker-compose down' to stop services"
fi
