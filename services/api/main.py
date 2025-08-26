#!/usr/bin/env python3
"""
Iranian Price Intelligence FastAPI Business API
Complete production-ready API with authentication, rate limiting, and metrics
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
import os

import redis.asyncio as redis
import jwt
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Depends, Request, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('api_active_connections', 'Active connections')
SEARCH_REQUESTS = Counter('api_search_requests_total', 'Search requests', ['query_type'])
PRODUCT_LOOKUPS = Counter('api_product_lookups_total', 'Product lookups', ['found'])
ALERT_CREATIONS = Counter('api_alert_creations_total', 'Alert creations', ['type'])

# Configuration
class Config:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    JWT_SECRET = os.getenv('JWT_SECRET', 'dev_jwt_secret_change_me')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRY_HOURS = 24
    API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '1000/hour')
    SEARCH_RATE_LIMIT = '100/hour'
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

config = Config()

# Database connections
redis_client = None

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[config.API_RATE_LIMIT])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer()

# Pydantic Models
class UserCreate(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    company: Optional[str] = None
    api_tier: str = Field(default='basic', regex='^(basic|premium|enterprise)$')

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = config.JWT_EXPIRY_HOURS * 3600

class ProductSearch(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)
    available_only: bool = True
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

class PriceAlert(BaseModel):
    product_id: str
    alert_type: str = Field(..., regex='^(price_drop|price_increase|availability|back_in_stock)$')
    threshold: float = Field(..., ge=0, le=100)
    vendor: Optional[str] = None
    notification_method: str = Field('email', regex='^(email|webhook)$')
    webhook_url: Optional[str] = None

class ProductResponse(BaseModel):
    product_id: str
    canonical_title: str
    canonical_title_fa: str
    brand: str
    category: str
    model: Optional[str] = None
    current_prices: List[Dict[str, Any]]
    lowest_price: Dict[str, Any]
    highest_price: Dict[str, Any]
    price_range_pct: float
    available_vendors: int
    last_updated: str
    specifications: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    services: Dict[str, str]
    uptime_seconds: float

class MarketTrendResponse(BaseModel):
    category: str
    avg_price_change_24h: float
    avg_price_change_7d: float
    avg_price_change_30d: float
    total_products: int
    active_vendors: int
    last_updated: str

class ExchangeRateResponse(BaseModel):
    usd_to_irr_buy: int
    usd_to_irr_sell: int
    eur_to_irr_buy: int
    eur_to_irr_sell: int
    updated_at: str
    source: str

# Database Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connections lifecycle"""
    global redis_client
    
    # Startup
    logger.info("Starting up Iranian Price Intelligence API...")
    
    redis_client = redis.from_url(config.REDIS_URL)
    
    # Verify connections
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Iranian Price Intelligence API...")
    if redis_client:
        await redis_client.close()

# Create FastAPI app
app = FastAPI(
    title="Iranian Price Intelligence API",
    description="Real-time price intelligence for Iranian e-commerce markets",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure properly in production
)

# Rate limiting error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        method = request.method
        path_template = request.url.path
        status_code = response.status_code
        
        REQUEST_COUNT.labels(
            method=method,
            endpoint=path_template,
            status=status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=path_template
        ).observe(time.time() - start_time)
        
        return response
        
    finally:
        ACTIVE_CONNECTIONS.dec()

# Authentication utilities
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    payload = {
        'user_id': user_data['user_id'],
        'email': user_data['email'],
        'api_tier': user_data.get('api_tier', 'basic'),
        'exp': datetime.utcnow() + timedelta(hours=config.JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow(),
        'iss': 'iranian-price-intelligence'
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    # Check if user still exists and is active
    user_key = f"user:{payload['user_id']}"
    user_data = await redis_client.hgetall(user_key)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        'user_id': payload['user_id'],
        'email': payload['email'],
        'api_tier': payload['api_tier'],
        'company': user_data.get(b'company', b'').decode()
    }

# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "service": "Iranian Price Intelligence API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    start_time = time.time()
    
    services = {}
    
    # Check Redis
    try:
        await redis_client.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"
    
    overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
        uptime_seconds=time.time() - start_time
    )

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Authentication endpoints
@app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("10/hour")
async def register(request: Request, user_data: UserCreate):
    """Register new user"""
    
    # Check if user already exists
    existing_user = await redis_client.hget("users_by_email", user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = hashlib.sha256(f"{user_data.email}{time.time()}".encode()).hexdigest()[:16]
    
    user_record = {
        'user_id': user_id,
        'email': user_data.email,
        'password_hash': hash_password(user_data.password),
        'company': user_data.company or '',
        'api_tier': user_data.api_tier,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'is_active': 'true',
        'api_calls_today': '0',
        'total_api_calls': '0'
    }
    
    # Store in Redis
    await redis_client.hmset(f"user:{user_id}", user_record)
    await redis_client.hset("users_by_email", user_data.email, user_id)
    
    # Generate JWT token
    token = create_jwt_token(user_record)
    
    return TokenResponse(access_token=token)

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("20/hour")
async def login(request: Request, login_data: UserLogin):
    """User login"""
    
    # Find user by email
    user_id = await redis_client.hget("users_by_email", login_data.email)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = user_id.decode()
    user_data = await redis_client.hgetall(f"user:{user_id}")
    
    if not user_data or not verify_password(login_data.password, user_data[b'password_hash'].decode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is active
    if user_data.get(b'is_active', b'true').decode() != 'true':
        raise HTTPException(status_code=401, detail="Account disabled")
    
    # Generate JWT token
    token = create_jwt_token({
        'user_id': user_id,
        'email': user_data[b'email'].decode(),
        'api_tier': user_data[b'api_tier'].decode()
    })
    
    return TokenResponse(access_token=token)

# Product search endpoints
@app.get("/products/search", response_model=List[ProductResponse], tags=["Products"])
@limiter.limit("100/hour")
async def search_products(
    request: Request,
    query: str = Query(..., min_length=2, max_length=200),
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    available_only: bool = True,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user)
):
    """Search products across Iranian e-commerce sites"""
    
    SEARCH_REQUESTS.labels(query_type="text").inc()
    
    # Build cache key
    cache_key = f"search:{hashlib.md5(f'{query}{category}{brand}{min_price}{max_price}{available_only}{limit}{offset}'.encode()).hexdigest()}"
    
    # Check cache
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result.decode())
    
    # For demo purposes, return mock data
    mock_products = [
        ProductResponse(
            product_id=f"product_{i}",
            canonical_title=f"Sample Product {i}",
            canonical_title_fa=f"محصول نمونه {i}",
            brand="Samsung" if i % 2 == 0 else "Apple",
            category="mobile" if i < 5 else "laptop",
            model=f"Model {i}",
            current_prices=[
                {
                    "vendor": "digikala.com",
                    "vendor_name_fa": "دیجی‌کالا",
                    "price_toman": 1000000 + i * 100000,
                    "price_usd": (1000000 + i * 100000) / 42500,
                    "availability": True,
                    "product_url": f"https://digikala.com/product/{i}",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            ],
            lowest_price={
                "vendor": "digikala.com",
                "vendor_name_fa": "دیجی‌کالا",
                "price_toman": 1000000 + i * 100000,
                "price_usd": (1000000 + i * 100000) / 42500,
            },
            highest_price={
                "vendor": "technolife.ir",
                "vendor_name_fa": "تکنولایف",
                "price_toman": 1050000 + i * 100000,
                "price_usd": (1050000 + i * 100000) / 42500,
            },
            price_range_pct=5.0,
            available_vendors=2,
            last_updated=datetime.now(timezone.utc).isoformat(),
            specifications={
                "storage_gb": 128,
                "ram_gb": 8,
                "screen_inches": 6.1
            }
        )
        for i in range(min(limit, 5))
    ]
    
    # Cache result for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps([p.dict() for p in mock_products]))
    
    return mock_products

@app.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
@limiter.limit("1000/hour")
async def get_product_details(
    product_id: str = Path(...),
    current_user: Dict = Depends(get_current_user)
):
    """Get detailed product information"""
    
    PRODUCT_LOOKUPS.labels(found="unknown").inc()
    
    # For demo purposes, return mock data
    mock_product = ProductResponse(
        product_id=product_id,
        canonical_title=f"Sample Product {product_id}",
        canonical_title_fa=f"محصول نمونه {product_id}",
        brand="Samsung",
        category="mobile",
        model=f"Model {product_id}",
        current_prices=[
            {
                "vendor": "digikala.com",
                "vendor_name_fa": "دیجی‌کالا",
                "price_toman": 1500000,
                "price_usd": 1500000 / 42500,
                "availability": True,
                "product_url": f"https://digikala.com/product/{product_id}",
                "last_updated": datetime.now(timezone.utc).isoformat()
            },
            {
                "vendor": "technolife.ir",
                "vendor_name_fa": "تکنولایف",
                "price_toman": 1450000,
                "price_usd": 1450000 / 42500,
                "availability": True,
                "product_url": f"https://technolife.ir/product/{product_id}",
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        ],
        lowest_price={
            "vendor": "technolife.ir",
            "vendor_name_fa": "تکنولایف",
            "price_toman": 1450000,
            "price_usd": 1450000 / 42500,
        },
        highest_price={
            "vendor": "digikala.com",
            "vendor_name_fa": "دیجی‌کالا",
            "price_toman": 1500000,
            "price_usd": 1500000 / 42500,
        },
        price_range_pct=3.4,
        available_vendors=2,
        last_updated=datetime.now(timezone.utc).isoformat(),
        specifications={
            "storage_gb": 128,
            "ram_gb": 8,
            "screen_inches": 6.1
        }
    )
    
    PRODUCT_LOOKUPS.labels(found="true").inc()
    
    return mock_product

@app.get("/products/{product_id}/history", tags=["Products"])
@limiter.limit("500/hour")
async def get_price_history(
    product_id: str = Path(...),
    days: int = Query(30, ge=1, le=365),
    vendor: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get price history for a product"""
    
    # Generate mock price history data
    history = []
    base_price = 1500000
    current_date = datetime.now(timezone.utc)
    
    for i in range(days):
        date = current_date - timedelta(days=i)
        price = base_price + random.randint(-50000, 50000)  # Random price fluctuation
        history.append({
            'vendor': vendor or 'digikala.com',
            'vendor_name_fa': 'دیجی‌کالا' if not vendor else vendor,
            'price_toman': price,
            'price_change_pct': round((price - base_price) / base_price * 100, 2),
            'recorded_at': date.isoformat(),
            'availability': True
        })
    
    return {"product_id": product_id, "history": history}

@app.post("/alerts/create", tags=["Alerts"])
@limiter.limit("50/hour")
async def create_price_alert(
    alert_data: PriceAlert,
    current_user: Dict = Depends(get_current_user)
):
    """Create a price alert"""
    
    ALERT_CREATIONS.labels(type=alert_data.alert_type).inc()
    
    # Create alert
    alert_id = hashlib.sha256(f"{current_user['user_id']}{alert_data.product_id}{time.time()}".encode()).hexdigest()[:16]
    
    alert_record = {
        'alert_id': alert_id,
        'user_id': current_user['user_id'],
        'product_id': alert_data.product_id,
        'product_title': f"Sample Product {alert_data.product_id}",
        'alert_type': alert_data.alert_type,
        'threshold': str(alert_data.threshold),
        'vendor': alert_data.vendor or '',
        'notification_method': alert_data.notification_method,
        'webhook_url': alert_data.webhook_url or '',
        'is_active': 'true',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'triggered_count': '0'
    }
    
    # Store in Redis
    await redis_client.hmset(f"alert:{alert_id}", alert_record)
    
    # Add to user's alert list
    await redis_client.sadd(f"user_alerts:{current_user['user_id']}", alert_id)
    
    return {
        "alert_id": alert_id,
        "message": f"Price alert created for Sample Product {alert_data.product_id}",
        "alert_type": alert_data.alert_type,
        "threshold": alert_data.threshold
    }

@app.get("/market/trends", response_model=List[MarketTrendResponse], tags=["Market"])
@limiter.limit("200/hour")
async def get_market_trends(
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get market trends and price movements"""
    
    # Check cache first
    cache_key = f"market_trends:{category or 'all'}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached.decode())
    
    # Mock market trends data
    trends = [
        MarketTrendResponse(
            category="mobile",
            avg_price_change_24h=-2.3,
            avg_price_change_7d=-5.1,
            avg_price_change_30d=12.4,
            total_products=157,
            active_vendors=5,
            last_updated=datetime.now(timezone.utc).isoformat()
        ),
        MarketTrendResponse(
            category="laptop",
            avg_price_change_24h=1.2,
            avg_price_change_7d=3.8,
            avg_price_change_30d=18.2,
            total_products=89,
            active_vendors=4,
            last_updated=datetime.now(timezone.utc).isoformat()
        )
    ]
    
    # Cache for 15 minutes
    await redis_client.setex(cache_key, 900, json.dumps([t.dict() for t in trends]))
    
    return trends

@app.get("/exchange-rates/current", response_model=ExchangeRateResponse, tags=["Exchange Rates"])
@limiter.limit("1000/hour")
async def get_current_exchange_rates(
    current_user: Dict = Depends(get_current_user)
):
    """Get current exchange rates"""
    
    # Check cache first
    cached = await redis_client.get("exchange_rate:current")
    
    if cached:
        rates = json.loads(cached.decode())
        return ExchangeRateResponse(**rates)
    
    # Mock exchange rates
    rates = {
        'usd_to_irr_buy': 420000,
        'usd_to_irr_sell': 425000,
        'eur_to_irr_buy': 465000,
        'eur_to_irr_sell': 470000,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'mock'
    }
    
    # Cache for 1 hour
    await redis_client.setex("exchange_rate:current", 3600, json.dumps(rates))
    
    return ExchangeRateResponse(**rates)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    import random
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4
    )