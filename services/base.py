import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import redis.asyncio as redis
from neo4j import GraphDatabase

class BaseService(ABC):
    """Base class for all services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.neo4j_driver: Optional[GraphDatabase] = None
        self.redis_client: Optional[redis.Redis] = None
        self.is_initialized = False
        
        # Configuration
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'iranian_price_secure_2025')
        self.redis_url = os.getenv('REDIS_URL', 'redis://:iranian_redis_secure_2025@redis:6379/0')
    
    async def initialize(self):
        """Initialize service connections"""
        try:
            # Initialize Neo4j
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test Neo4j connection
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 as test")
                assert result.single()['test'] == 1
            
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            self.is_initialized = True
            self.logger.info(f"✅ {self.service_name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize {self.service_name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        health = {
            'service': self.service_name,
            'status': 'healthy' if self.is_initialized else 'unhealthy',
            'timestamp': asyncio.get_event_loop().time()
        }
        
        try:
            if self.neo4j_driver:
                with self.neo4j_driver.session() as session:
                    session.run("RETURN 1")
                health['neo4j'] = 'connected'
            
            if self.redis_client:
                await self.redis_client.ping()
                health['redis'] = 'connected'
                
        except Exception as e:
            health['status'] = 'degraded'
            health['error'] = str(e)
        
        return health
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info(f"🧹 {self.service_name} cleaned up")
    
    @abstractmethod
    async def run(self):
        """Main service execution logic"""
        pass