#!/usr/bin/env python3
"""
Iranian Price Intelligence Product Matcher Service
Main entry point for processing scraped products
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import redis.asyncio as redis
from matcher import ProductMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatcherService:
    """Main service for product matching"""
    
    def __init__(self):
        # Configuration from environment
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'iranian_price_secure_2025')
        self.redis_url = os.getenv('REDIS_URL', 'redis://:iranian_redis_secure_2025@redis:6379/2')
        
        # Initialize components
        self.matcher = None
        self.redis_client = None
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'new_products': 0,
            'failed_matches': 0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
    
    async def initialize(self):
        """Initialize the service"""
        logger.info("🚀 Initializing Iranian Product Matcher Service...")
        
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Initialize Neo4j matcher
            self.matcher = ProductMatcher(
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_password=self.neo4j_password
            )
            logger.info("✅ Neo4j matcher initialized")
            
            # Store service info in Redis
            await self.redis_client.setex(
                "matcher:service_info",
                3600,  # 1 hour cache
                json.dumps({
                    'service': 'iranian_product_matcher',
                    'started_at': self.stats['start_time'],
                    'neo4j_uri': self.neo4j_uri,
                    'status': 'running'
                })
            )
            
            logger.info("✅ Matcher service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize matcher service: {e}")
            raise
    
    async def process_pending_products(self):
        """Process products waiting to be matched"""
        logger.info("🔍 Processing pending products...")
        
        try:
            # Get pending products from Redis
            pending_keys = await self.redis_client.keys("pending_product:*")
            
            if not pending_keys:
                logger.info("📭 No pending products to process")
                return
            
            logger.info(f"📦 Found {len(pending_keys)} pending products")
            
            processed_count = 0
            
            for key in pending_keys:
                try:
                    # Get product data
                    product_data_raw = await self.redis_client.get(key)
                    if not product_data_raw:
                        continue
                    
                    product_data = json.loads(product_data_raw.decode())
                    vendor = product_data.get('vendor', 'unknown')
                    
                    # Process through matcher
                    match_result = self.matcher.process_scraped_product(product_data, vendor)
                    
                    # Update statistics
                    self.stats['total_processed'] += 1
                    
                    if match_result.match_type == 'exact':
                        self.stats['exact_matches'] += 1
                    elif match_result.match_type == 'fuzzy':
                        self.stats['fuzzy_matches'] += 1
                    elif match_result.match_type == 'new_product':
                        self.stats['new_products'] += 1
                    
                    # Store result in Redis
                    result_key = f"match_result:{match_result.listing_id}"
                    await self.redis_client.setex(
                        result_key,
                        86400,  # 24 hour cache
                        json.dumps({
                            'listing_id': match_result.listing_id,
                            'product_id': match_result.product_id,
                            'match_confidence': match_result.match_confidence,
                            'match_type': match_result.match_type,
                            'matched_attributes': match_result.matched_attributes,
                            'processed_at': datetime.now(timezone.utc).isoformat()
                        })
                    )
                    
                    # Remove from pending queue
                    await self.redis_client.delete(key)
                    
                    processed_count += 1
                    
                    # Log progress
                    if processed_count % 10 == 0:
                        logger.info(f"📊 Processed {processed_count}/{len(pending_keys)} products")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process product {key}: {e}")
                    self.stats['failed_matches'] += 1
                    
                    # Move failed product to error queue
                    error_key = f"error_product:{key.replace('pending_product:', '')}"
                    await self.redis_client.setex(
                        error_key,
                        3600,  # 1 hour cache
                        json.dumps({
                            'error': str(e),
                            'product_data': product_data,
                            'failed_at': datetime.now(timezone.utc).isoformat()
                        })
                    )
                    
                    # Remove from pending queue
                    await self.redis_client.delete(key)
            
            logger.info(f"✅ Completed processing {processed_count} products")
            
            # Update statistics in Redis
            await self.redis_client.setex(
                "matcher:stats",
                300,  # 5 minute cache
                json.dumps(self.stats)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to process pending products: {e}")
            raise
    
    async def run_continuous_processing(self):
        """Run continuous product processing"""
        logger.info("🔄 Starting continuous product processing...")
        
        while True:
            try:
                await self.process_pending_products()
                
                # Wait before next processing cycle
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous processing: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up matcher service...")
        
        if self.matcher:
            self.matcher.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("✅ Cleanup completed")

async def main():
    """Main entry point"""
    service = MatcherService()
    
    try:
        await service.initialize()
        await service.run_continuous_processing()
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
    except Exception as e:
        logger.error(f"💥 Service failed: {e}")
        raise
    finally:
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())