import os
from typing import Optional
try:
    from pydantic import BaseSettings, Field
except ImportError:
    from pydantic_settings import BaseSettings
    from pydantic import Field

class Settings(BaseSettings):
    # Service Configuration
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Database Configuration
    NEO4J_URI: str = Field(default="bolt://neo4j:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="iranian_price_secure_2025", env="NEO4J_PASSWORD")
    
    REDIS_URL: str = Field(default="redis://:iranian_redis_secure_2025@redis:6379", env="REDIS_URL")
    
    POSTGRES_URL: str = Field(
        default="postgresql://price_admin:iranian_postgres_secure_2025@postgres:5432/iranian_price_users",
        env="POSTGRES_URL"
    )
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    JWT_SECRET: str = Field(default="dev_jwt_secret_change_me", env="JWT_SECRET")
    API_RATE_LIMIT: str = Field(default="1000/hour", env="API_RATE_LIMIT")
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:8080", env="CORS_ORIGINS")
    
    # Email Configuration
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: str = Field(default="", env="SMTP_USERNAME")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    ADMIN_EMAIL: str = Field(default="admin@example.com", env="ADMIN_EMAIL")
    
    # Scraping Configuration
    SEARXNG_URL: str = Field(default="http://87.236.166.7:8080", env="SEARXNG_URL")
    SCRAPING_DELAY_MIN: int = Field(default=2, env="SCRAPING_DELAY_MIN")
    SCRAPING_DELAY_MAX: int = Field(default=5, env="SCRAPING_DELAY_MAX")
    
    # Pipeline Configuration
    DAILY_CRAWL_TIME: str = Field(default="02:00", env="DAILY_CRAWL_TIME")
    HOURLY_CRAWL_ENABLED: bool = Field(default=True, env="HOURLY_CRAWL_ENABLED")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()