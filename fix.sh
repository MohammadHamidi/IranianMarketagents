#!/bin/bash
# Auto-fix script for Iranian Price Intelligence Platform Docker issues
# Updated to handle Apple Silicon (arm64) vs Intel (amd64) automatically

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Iranian Price Intelligence Platform - Auto Fix Script${NC}"
echo "=================================================="

# Logging functions
log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# Detect architecture
ARCH=$(uname -m)
NEO4J_PLATFORM="linux/amd64"
if [[ "$ARCH" == "arm64" ]]; then
    warning "Apple Silicon detected → forcing Neo4j to linux/arm64"
    NEO4J_PLATFORM="linux/arm64"
else
    log "Intel/AMD detected → using linux/amd64"
fi

# Step 1: Clean up existing Docker state
log "Step 1: Cleaning up Docker state..."
docker-compose down -v 2>/dev/null || true
docker system prune -f
success "Docker cleanup completed"

# Step 2: Backup existing files
log "Step 2: Backing up existing configuration files..."
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p backup/$TS
[ -f docker-compose.yml ] && cp docker-compose.yml backup/$TS/
[ -f requirements.txt ] && cp requirements.txt backup/$TS/
[ -f .env ] && cp .env backup/$TS/
success "Backup completed"

# Step 3: Generate requirements.txt
log "Step 3: Creating unified requirements.txt..."
cat > requirements.txt << 'EOF'
# Python dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
aiohttp==3.9.1
neo4j==5.15.0
redis==5.0.1
psycopg2-binary==2.9.8
PyJWT==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
selenium==4.15.2
beautifulsoup4==4.12.2
requests==2.31.0
pandas==2.1.3
numpy==1.25.2
fuzzywuzzy==0.18.0
python-levenshtein==0.23.0
scikit-learn==1.3.2
pydantic==2.5.0
python-dotenv==1.0.0
structlog==23.2.0
slowapi==0.1.8
prometheus-client==0.19.0
tiktoken==0.5.2
jsonschema==4.20.0
pytest==7.4.3
pytest-asyncio==0.21.1
EOF
success "requirements.txt created"

# Step 4: Dockerfiles already handled in your version (keeping as is)...

# Step 5: docker-compose.yml with platform fix
log "Step 5: Creating docker-compose.yml..."
cat > docker-compose.yml << EOF
services:
  neo4j:
    image: neo4j:5.15-community
    platform: $NEO4J_PLATFORM
    container_name: iranian-price-neo4j
    environment:
      NEO4J_AUTH: neo4j/iranian_price_secure_2025
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    networks:
      - iranian-price-network

  redis:
    image: redis:7-alpine
    container_name: iranian-price-redis
    command: redis-server --requirepass iranian_redis_secure_2025
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - iranian-price-network

  postgres:
    image: postgres:15-alpine
    container_name: iranian-price-postgres
    environment:
      POSTGRES_DB: iranian_price_users
      POSTGRES_USER: price_admin
      POSTGRES_PASSWORD: iranian_postgres_secure_2025
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - iranian-price-network

  api-service:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: iranian-price-api
    depends_on:
      - neo4j
      - redis
      - postgres
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: iranian_price_secure_2025
      REDIS_URL: redis://:iranian_redis_secure_2025@redis:6379/0
      OPENAI_API_KEY: aa-YOURKEY
      OPENAI_API_BASE: https://api.avalai.ir/v1
    ports:
      - "8000:8000"
    networks:
      - iranian-price-network

  scraper-service:
    build:
      context: .
      dockerfile: Dockerfile.scraper
    container_name: iranian-price-scraper
    depends_on:
      - neo4j
      - redis
    environment:
      NEO4J_URI: bolt://neo4j:7687
      REDIS_URL: redis://:iranian_redis_secure_2025@redis:6379/1
      OPENAI_API_KEY: aa-YOURKEY
      OPENAI_API_BASE: https://api.avalai.ir/v1
    volumes:
      - /dev/shm:/dev/shm
    networks:
      - iranian-price-network
    security_opt:
      - seccomp:unconfined

  matcher-service:
    build:
      context: .
      dockerfile: Dockerfile.matcher
    container_name: iranian-price-matcher
    depends_on:
      - neo4j
      - redis
    environment:
      NEO4J_URI: bolt://neo4j:7687
      REDIS_URL: redis://:iranian_redis_secure_2025@redis:6379/2
      OPENAI_API_KEY: aa-YOURKEY
      OPENAI_API_BASE: https://api.avalai.ir/v1
    networks:
      - iranian-price-network

volumes:
  neo4j_data:
  redis_data:
  postgres_data:

networks:
  iranian-price-network:
    driver: bridge
EOF
success "docker-compose.yml created (Neo4j platform = $NEO4J_PLATFORM)"

# Step 6: Start services
log "Step 6: Starting system..."
docker-compose up -d --build

log "Waiting for services..."
sleep 20

docker-compose ps
success "🎉 All services started!"
