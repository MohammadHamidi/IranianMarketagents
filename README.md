# Iranian Price Intelligence Platform

A comprehensive price intelligence platform for Iranian e-commerce markets.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd IranianMarketagents
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Initialize the Neo4j database:**
   ```bash
   python scripts/init_neo4j.py
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Services Overview

- **API Service**: Main API interface at `http://localhost:8000`
- **Scraper Service**: Web scraping engine for Iranian e-commerce sites
- **Matcher Service**: Product matching and deduplication
- **Pipeline Service**: Data processing pipeline
- **Dashboard**: Web dashboard at `http://localhost:3000`
- **Neo4j**: Graph database at `http://localhost:7474`
- **Redis**: Caching and queuing at `http://localhost:6379`
- **PostgreSQL**: User management at `http://localhost:5432`

### API Documentation

Once the API service is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Environment Configuration

Create a `.env` file in the root directory with your configuration:
```bash
# Environment
ENVIRONMENT=development
DEBUG=true

# Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=iranian_price_secure_2025

REDIS_URL=redis://:iranian_redis_secure_2025@localhost:6379

POSTGRES_URL=postgresql://price_admin:iranian_postgres_secure_2025@localhost:5432/iranian_price_users

# JWT Secret
JWT_SECRET=your_development_secret_key_change_in_production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## 🧪 Testing

### Run API Tests
```bash
cd services/api
pytest
```

### Test Scraping
```bash
python test_scraper.py
```

## 🛠️ Development

### Project Structure
```
IranianMarketagents/
├── services/
│   ├── api/          # FastAPI REST service
│   ├── scraper/      # Web scraping engine
│   ├── matcher/      # Product matching service
│   ├── pipeline/     # Data processing pipeline
│   └── dashboard/    # Web dashboard
├── config/           # Configuration files
├── scripts/          # Utility scripts
├── data/             # Data storage
├── logs/             # Log files
├── Dockerfile.*      # Service Dockerfiles
├── docker-compose.yml # Main orchestration
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

### Adding New Features

1. **Add new dependencies**: Update `requirements.txt`
2. **Add new services**: Create new directory in `services/`
3. **Update Docker configuration**: Modify `docker-compose.yml`
4. **Add database schema**: Update `scripts/init_neo4j.py`

## 📊 Monitoring

- **API Metrics**: `http://localhost:8000/metrics`
- **Health Check**: `http://localhost:8000/health`
- **Neo4j Browser**: `http://localhost:7474`

## 🔐 Security

- All services use secure passwords by default
- JWT tokens for API authentication
- Rate limiting on all endpoints
- CORS restrictions configured

## 📚 Documentation

- API Documentation: `http://localhost:8000/docs`
- Environment Variables: `.env` file
- Service Documentation: Each service directory