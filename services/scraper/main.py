#!/usr/bin/env python3
"""
Iranian Price Intelligence Scraper Service
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the orchestrator
from orchestrator import IranianScrapingOrchestrator

# Redis connection
redis_client = None

async def store_products_in_redis(products: List[Dict]):
    """Store scraped products in Redis"""
    try:
        pipe = redis_client.pipeline()
        
        for product in products:
            key = f"product:{product['product_id']}"
            pipe.hset(key, mapping=product)
            pipe.expire(key, 3600)  # Expire in 1 hour
        
        await pipe.execute()
        logger.info(f"Stored {len(products)} products in Redis")
    except Exception as e:
        logger.error(f"Failed to store products in Redis: {e}")

async def main():
    """Main scraping function"""
    global redis_client
    
    try:
        # Connect to Redis
        redis_client = redis.from_url("redis://redis:6379/1")
        await redis_client.ping()
        logger.info("Connected to Redis")
        
        # Initialize the orchestrator using async factory
        orchestrator = await IranianScrapingOrchestrator.create()
        
        # Execute comprehensive crawl
        logger.info("Starting comprehensive crawl")
        results = await orchestrator.execute_comprehensive_crawl()
        logger.info("Crawl completed")
        
        # Flatten results and store in Redis
        all_products = []
        for domain, site_results in results.items():
            for result in site_results:
                if result.success:
                    all_products.extend(result.data)
        
        logger.info(f"Total products scraped: {len(all_products)}")
        
        # Store in Redis
        if all_products:
            await store_products_in_redis(all_products)
        
        # Clean up
        await orchestrator.close()
        
        logger.info("Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        if redis_client:
            await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())