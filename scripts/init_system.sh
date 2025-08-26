#!/bin/bash

# Iranian Price Intelligence Platform - System Initialization Script
# This script sets up the complete platform infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLATFORM_NAME="Iranian Price Intelligence Platform"
VERSION="1.0.0"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE="config/env/dev.env"

# Logging
LOG_FILE="logs/system_init_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Header
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    $PLATFORM_NAME                    ║"
echo "║                        v$VERSION                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log "Starting system initialization..."

# Check prerequisites
check_prerequisites() {
    log "Checking system prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs/{api,scraper,matcher,pipeline,neo4j,redis,postgres}
    mkdir -p data/{neo4j,postgres,redis}
    mkdir -p config/{nginx,prometheus,grafana}
    mkdir -p scripts
    
    success "Directories created successfully"
}

# Set up environment variables
setup_environment() {
    log "Setting up environment variables..."
    
    if [ -f "$ENV_FILE" ]; then
        log "Loading environment from $ENV_FILE"
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    else
        warning "Environment file $ENV_FILE not found, using defaults"
    fi
    
    # Set default values
    export NEO4J_AUTH=${NEO4J_AUTH:-"neo4j/iranian_price_secure_2025"}
    export REDIS_PASSWORD=${REDIS_PASSWORD:-"iranian_redis_secure_2025"}
    export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-"iranian_postgres_secure_2025"}
    
    success "Environment variables configured"
}

# Initialize databases
init_databases() {
    log "Initializing databases..."
    
    # Start core services first
    log "Starting core database services..."
    docker-compose up -d neo4j redis postgres
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Initialize Neo4j
    log "Initializing Neo4j database..."
    if docker-compose exec -T neo4j cypher-shell -u neo4j -p iranian_price_secure_2025 \
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE" 2>/dev/null; then
        success "Neo4j database initialized"
    else
        warning "Neo4j initialization may have failed, continuing..."
    fi
    
    # Initialize PostgreSQL
    log "Initializing PostgreSQL database..."
    if docker-compose exec -T postgres psql -U price_admin -d iranian_price_users \
        -c "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE, email VARCHAR(100) UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" 2>/dev/null; then
        success "PostgreSQL database initialized"
    else
        warning "PostgreSQL initialization may have failed, continuing..."
    fi
    
    success "Database initialization completed"
}

# Build and start services
start_services() {
    log "Building and starting all services..."
    
    # Build all services
    log "Building Docker images..."
    docker-compose build --no-cache
    
    # Start all services
    log "Starting all services..."
    docker-compose up -d
    
    success "All services started successfully"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Health check attempt $attempt/$max_attempts..."
        
        # Check API health
        if curl -f http://localhost:8000/health &>/dev/null; then
            success "API service is healthy"
        else
            log "API service not ready yet..."
        fi
        
        # Check Neo4j health
        if docker-compose exec -T neo4j cypher-shell -u neo4j -p iranian_price_secure_2025 \
            "RETURN 1" &>/dev/null; then
            success "Neo4j service is healthy"
        else
            log "Neo4j service not ready yet..."
        fi
        
        # Check Redis health
        if docker-compose exec -T redis redis-cli -a iranian_redis_secure_2025 ping &>/dev/null; then
            success "Redis service is healthy"
        else
            log "Redis service not ready yet..."
        fi
        
        # Check if all services are healthy
        if docker-compose ps | grep -q "healthy"; then
            success "All services are healthy!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            warning "Some services may not be fully healthy, but continuing..."
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 10
    done
}

# Run initial data collection
initial_data_collection() {
    log "Running initial data collection..."
    
    # Trigger initial scraping cycle
    log "Triggering initial scraping cycle..."
    docker-compose exec -T redis redis-cli -a iranian_redis_secure_2025 \
        SET scraper:trigger '{"triggered_at":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","cycle_type":"initial","priority":"high"}'
    
    # Wait for initial processing
    log "Waiting for initial data processing..."
    sleep 120
    
    success "Initial data collection completed"
}

# Display system status
show_status() {
    log "Displaying system status..."
    
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    SYSTEM STATUS                           ${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    
    # Service status
    echo -e "\n${YELLOW}Service Status:${NC}"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    
    # Database connections
    echo -e "\n${YELLOW}Database Status:${NC}"
    echo "Neo4j: http://localhost:7474 (neo4j/iranian_price_secure_2025)"
    echo "Redis: localhost:6379 (password: iranian_redis_secure_2025)"
    echo "PostgreSQL: localhost:5432 (price_admin/iranian_postgres_secure_2025)"
    
    # API endpoints
    echo -e "\n${YELLOW}API Endpoints:${NC}"
    echo "Main API: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo "Health Check: http://localhost:8000/health"
    
    # Dashboard
    echo -e "\n${YELLOW}Dashboard:${NC}"
    echo "Web Interface: http://localhost"
    
    # Monitoring
    echo -e "\n${YELLOW}Monitoring:${NC}"
    echo "Prometheus: http://localhost:9090"
    echo "Grafana: http://localhost:3000 (admin/admin)"
    
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
}

# Main execution
main() {
    log "Starting $PLATFORM_NAME initialization..."
    
    check_prerequisites
    create_directories
    setup_environment
    init_databases
    start_services
    wait_for_health
    initial_data_collection
    show_status
    
    success "System initialization completed successfully!"
    log "Platform is ready for use."
    
    echo -e "\n${GREEN}🎉 $PLATFORM_NAME is now running!${NC}"
    echo -e "${BLUE}Check the logs directory for detailed information.${NC}"
    echo -e "${BLUE}Use 'docker-compose logs -f [service]' to monitor specific services.${NC}"
}

# Error handling
trap 'error "An error occurred. Check the logs for details."; exit 1' ERR

# Run main function
main "$@"
