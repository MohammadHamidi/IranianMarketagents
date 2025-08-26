# Iranian Price Intelligence Platform 🇮🇷

A comprehensive, enterprise-grade platform for monitoring and analyzing product prices across Iranian e-commerce platforms using advanced AI/ML techniques, real-time data collection, and intelligent product matching.

## 🌟 Features

- **Intelligent Scraping**: Automated data collection from major Iranian e-commerce sites
- **AI-Powered Matching**: ML-based product deduplication and canonicalization
- **Real-time Analytics**: Live price monitoring and trend analysis
- **Persian Language Support**: Native support for Persian text processing
- **Advanced Monitoring**: Comprehensive observability with Prometheus/Grafana
- **Scalable Architecture**: Microservices-based design with Docker orchestration
- **Security First**: Enterprise-grade security with authentication and rate limiting

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   API Gateway   │    │  Pipeline       │
│   (React/NGINX) │    │   (FastAPI)     │    │  Orchestrator   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scraper       │    │   Product       │    │   Monitoring    │
│   Service       │    │   Matcher       │    │   Stack         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j         │    │   Redis         │    │   PostgreSQL    │
│   (Graph DB)    │    │   (Cache/Queue) │    │   (User Data)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM available
- 20GB+ disk space
- Internet connection for initial setup

### 1. Clone and Setup

```bash
git clone <repository-url>
cd IranianMarketagents
chmod +x scripts/init_system.sh
```

### 2. Initialize System

```bash
./scripts/init_system.sh
```

This script will:
- ✅ Check system prerequisites
- ✅ Create necessary directories
- ✅ Initialize databases
- ✅ Build and start all services
- ✅ Run initial data collection
- ✅ Display system status

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8080 | - |
| **API Docs** | http://localhost:8001/docs | - |
| **Neo4j Browser** | http://localhost:7475 | neo4j/iranian_price_secure_2025 |
| **Grafana** | http://localhost:3002 | admin/admin |
| **Prometheus** | http://localhost:9091 | - |

**Note**: Ports have been configured to avoid conflicts with existing services on your system.

## 🔧 Configuration

### Environment Variables

Create `config/env/dev.env` for custom configuration:

```bash
# SMTP Configuration (for alerts)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAIL=admin@yourdomain.com

# Optional Webhooks
WEBHOOK_URLS=https://your-webhook.com/endpoint
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Service Configuration

Each service can be configured via environment variables or config files:

- **API Service**: Rate limits, authentication settings
- **Scraper Service**: Target sites, crawl intervals
- **Matcher Service**: ML model parameters, thresholds
- **Pipeline Service**: Execution schedules, notification settings

## 📊 Data Flow

1. **Data Collection**: Scraper service collects product data from Iranian e-commerce sites
2. **Data Processing**: Raw data is cleaned and normalized with Persian text processing
3. **Product Matching**: AI/ML algorithms match products across vendors and create canonical records
4. **Price Analysis**: Historical price tracking and trend analysis
5. **Alert Generation**: Automated notifications for significant price changes
6. **Data Storage**: Structured storage in Neo4j graph database with Redis caching

## 🎯 Supported E-commerce Sites

- **Digikala** (دیجی‌کالا) - Electronics, fashion, home goods
- **Snap** (اسنپ) - Groceries, electronics, fashion
- **Bamilo** (بامیلو) - Electronics, fashion, home goods
- **Takhfifan** (تخفیفان) - Deals and discounts
- **Divar** (دیوار) - Classifieds and local deals
- **Shaparak** (شاپرک) - Payment gateway integration

## 🔍 Product Matching Features

- **Persian Text Processing**: Advanced NLP for Persian product descriptions
- **Brand Recognition**: Intelligent brand name matching and normalization
- **Specification Matching**: ML-based matching of product specifications
- **Image Analysis**: Computer vision for product image matching
- **Price Validation**: Cross-vendor price consistency checking

## 📈 Monitoring & Analytics

### Metrics Collected

- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Products scraped, matches found, price changes detected
- **Performance Metrics**: Scraping speed, matching accuracy, API latency

### Dashboards

- **System Health**: Overall platform status and performance
- **Data Quality**: Scraping success rates and data accuracy
- **Business Intelligence**: Price trends, vendor analysis, product insights
- **Operational**: Service logs, error tracking, performance monitoring

## 🛡️ Security Features

- **Authentication**: JWT-based user authentication
- **Rate Limiting**: Configurable API rate limits
- **Input Validation**: Comprehensive input sanitization
- **HTTPS Support**: SSL/TLS encryption for all communications
- **Access Control**: Role-based access control (RBAC)
- **Audit Logging**: Complete audit trail for all operations

## 🔧 Development

### Local Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for dashboard)
cd services/dashboard
npm install

# Run services individually
python -m services.api.main
python -m services.scraper.main
python -m services.matcher.main
```

### Testing

```bash
# Run API tests
pytest services/api/tests/

# Run integration tests
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

### Code Quality

```bash
# Linting
flake8 services/
black services/

# Type checking
mypy services/

# Security scanning
bandit -r services/
```

## 📚 API Documentation

### Core Endpoints

- `GET /health` - Service health check
- `GET /products/search` - Search products
- `GET /products/{id}` - Get product details
- `GET /vendors` - List supported vendors
- `GET /analytics/trends` - Price trend analysis
- `POST /alerts` - Create price alerts

### Authentication

```bash
# Get access token
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8001/products/search?q=samsung"
```

## 🚀 Deployment

### Production Deployment

```bash
# Set production environment
export ENVIRONMENT=production

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or use Kubernetes
kubectl apply -f k8s/
```

### Scaling

```bash
# Scale services
docker-compose up -d --scale scraper-service=3
docker-compose up -d --scale matcher-service=2

# Monitor scaling
docker-compose ps
docker stats
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker logs with `docker-compose logs [service]`
2. **Database connection errors**: Verify database credentials and network connectivity
3. **Memory issues**: Increase Docker memory limits or reduce service concurrency
4. **Scraping failures**: Check target site accessibility and rate limiting

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api-service
docker-compose logs -f scraper-service

# View application logs
tail -f logs/api/app.log
tail -f logs/scraper/app.log
```

### Health Checks

```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:7475/browser/
redis-cli -h localhost -p 6380 -a iranian_redis_secure_2025 ping

# Check Docker service status
docker-compose ps
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write comprehensive tests
- Update documentation for new features
- Follow conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Hazm**: Persian text processing library
- **FastAPI**: Modern Python web framework
- **Neo4j**: Graph database technology
- **Prometheus**: Monitoring and alerting toolkit
- **Grafana**: Data visualization platform

## 📞 Support

- **Documentation**: [Wiki](wiki-link)
- **Issues**: [GitHub Issues](issues-link)
- **Discussions**: [GitHub Discussions](discussions-link)
- **Email**: support@iranianpriceintelligence.com

---

**Built with ❤️ for the Iranian e-commerce community**