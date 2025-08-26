#!/bin/bash

# Iranian Price Intelligence Platform - Deployment Script
# This script provides easy deployment and management commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLATFORM_NAME="Iranian Price Intelligence Platform"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE="config/env/dev.env"

# Logging
LOG_FILE="logs/deploy_$(date +%Y%m%d_%H%M%S).log"
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

# Show usage
show_usage() {
    echo -e "${BLUE}Iranian Price Intelligence Platform - Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show service status"
    echo "  logs            Show service logs"
    echo "  update          Update and restart services"
    echo "  backup          Create database backup"
    echo "  restore         Restore database from backup"
    echo "  clean           Clean up containers and volumes"
    echo "  monitor         Show real-time monitoring"
    echo "  health          Check service health"
    echo "  init            Initialize system (first time setup)"
    echo ""
    echo "Options:"
    echo "  -s, --service   Target specific service"
    echo "  -f, --follow    Follow logs (for logs command)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs -f                  # Follow all logs"
    echo "  $0 logs -s api-service      # Show API service logs"
    echo "  $0 status                   # Show service status"
}

# Start services
start_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log "Starting service: $service"
        docker-compose up -d "$service"
        success "Service $service started"
    else
        log "Starting all services..."
        docker-compose up -d
        success "All services started"
    fi
}

# Stop services
stop_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log "Stopping service: $service"
        docker-compose stop "$service"
        success "Service $service stopped"
    else
        log "Stopping all services..."
        docker-compose down
        success "All services stopped"
    fi
}

# Restart services
restart_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log "Restarting service: $service"
        docker-compose restart "$service"
        success "Service $service restarted"
    else
        log "Restarting all services..."
        docker-compose restart
        success "All services restarted"
    fi
}

# Show service status
show_status() {
    log "Service Status:"
    echo ""
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Show resource usage
    log "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Show service logs
show_logs() {
    local service="$1"
    local follow="$2"
    
    if [ -n "$service" ]; then
        if [ "$follow" = "true" ]; then
            log "Following logs for service: $service"
            docker-compose logs -f "$service"
        else
            log "Showing logs for service: $service"
            docker-compose logs "$service"
        fi
    else
        if [ "$follow" = "true" ]; then
            log "Following all service logs"
            docker-compose logs -f
        else
            log "Showing all service logs"
            docker-compose logs
        fi
    fi
}

# Update services
update_services() {
    log "Updating services..."
    
    # Pull latest images
    docker-compose pull
    
    # Rebuild and restart
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    success "Services updated and restarted"
}

# Create backup
create_backup() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "Creating backup in: $backup_dir"
    
    # Backup Neo4j
    if docker-compose ps neo4j | grep -q "Up"; then
        log "Backing up Neo4j database..."
        docker-compose exec -T neo4j neo4j-admin dump --database=neo4j --to="$backup_dir/neo4j_backup.dump"
    fi
    
    # Backup PostgreSQL
    if docker-compose ps postgres | grep -q "Up"; then
        log "Backing up PostgreSQL database..."
        docker-compose exec -T postgres pg_dump -U price_admin iranian_price_users > "$backup_dir/postgres_backup.sql"
    fi
    
    # Backup Redis (if persistence is enabled)
    if docker-compose ps redis | grep -q "Up"; then
        log "Backing up Redis data..."
        docker-compose exec -T redis redis-cli -a iranian_redis_secure_2025 SAVE
        docker cp $(docker-compose ps -q redis):/data/dump.rdb "$backup_dir/redis_backup.rdb"
    fi
    
    # Create backup archive
    tar -czf "${backup_dir}.tar.gz" -C "$backup_dir" .
    rm -rf "$backup_dir"
    
    success "Backup created: ${backup_dir}.tar.gz"
}

# Restore backup
restore_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Please specify backup file to restore"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log "Restoring from backup: $backup_file"
    
    # Extract backup
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    # Stop services
    docker-compose down
    
    # Restore Neo4j
    if [ -f "$temp_dir/neo4j_backup.dump" ]; then
        log "Restoring Neo4j database..."
        docker-compose up -d neo4j
        sleep 30
        docker-compose exec -T neo4j neo4j-admin load --from="$temp_dir/neo4j_backup.dump" --database=neo4j --force
    fi
    
    # Restore PostgreSQL
    if [ -f "$temp_dir/postgres_backup.sql" ]; then
        log "Restoring PostgreSQL database..."
        docker-compose up -d postgres
        sleep 30
        docker-compose exec -T postgres psql -U price_admin -d iranian_price_users < "$temp_dir/postgres_backup.sql"
    fi
    
    # Restore Redis
    if [ -f "$temp_dir/redis_backup.rdb" ]; then
        log "Restoring Redis data..."
        docker-compose up -d redis
        docker cp "$temp_dir/redis_backup.rdb" $(docker-compose ps -q redis):/data/dump.rdb
        docker-compose restart redis
    fi
    
    # Start all services
    docker-compose up -d
    
    # Cleanup
    rm -rf "$temp_dir"
    
    success "Backup restored successfully"
}

# Clean up
cleanup() {
    log "Cleaning up containers and volumes..."
    
    # Stop and remove containers
    docker-compose down -v
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    # Remove unused networks
    docker network prune -f
    
    success "Cleanup completed"
}

# Show monitoring
show_monitoring() {
    log "Real-time monitoring (Press Ctrl+C to exit)..."
    
    # Show service status
    watch -n 2 'docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"'
}

# Check health
check_health() {
    log "Checking service health..."
    
    # Check API health
    if curl -f http://localhost:8000/health &>/dev/null; then
        success "API service: HEALTHY"
    else
        error "API service: UNHEALTHY"
    fi
    
    # Check Neo4j health
    if docker-compose exec -T neo4j cypher-shell -u neo4j -p iranian_price_secure_2025 "RETURN 1" &>/dev/null; then
        success "Neo4j service: HEALTHY"
    else
        error "Neo4j service: UNHEALTHY"
    fi
    
    # Check Redis health
    if docker-compose exec -T redis redis-cli -a iranian_redis_secure_2025 ping &>/dev/null; then
        success "Redis service: HEALTHY"
    else
        error "Redis service: UNHEALTHY"
    fi
    
    # Check PostgreSQL health
    if docker-compose exec -T postgres pg_isready -U price_admin -d iranian_price_users &>/dev/null; then
        success "PostgreSQL service: HEALTHY"
    else
        error "PostgreSQL service: UNHEALTHY"
    fi
    
    echo ""
    log "Health check completed"
}

# Initialize system
init_system() {
    log "Running system initialization..."
    
    if [ -f "scripts/init_system.sh" ]; then
        ./scripts/init_system.sh
    else
        error "Initialization script not found"
        exit 1
    fi
}

# Main execution
main() {
    local command="$1"
    local service=""
    local follow="false"
    
    # Parse options
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--service)
                service="$2"
                shift 2
                ;;
            -f|--follow)
                follow="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    case "$command" in
        start)
            start_services "$service"
            ;;
        stop)
            stop_services "$service"
            ;;
        restart)
            restart_services "$service"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service" "$follow"
            ;;
        update)
            update_services
            ;;
        backup)
            create_backup
            ;;
        restore)
            restore_backup "$1"
            ;;
        clean)
            cleanup
            ;;
        monitor)
            show_monitoring
            ;;
        health)
            check_health
            ;;
        init)
            init_system
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Error handling
trap 'error "An error occurred. Check the logs for details."; exit 1' ERR

# Check if command is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Run main function
main "$@"
