#!/usr/bin/env python3
"""
Continuous scraper that runs every X minutes
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from real_scraper import IranianWebScraper, ProductData
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousScraper:
    def __init__(self):
        self.redis_client = None
        self.scraper = None
        self.interval_minutes = int(os.getenv('SCRAPING_INTERVAL_MINUTES', '30'))

    async def initialize(self):
        """Initialize connections"""
        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://:iranian_redis_secure_2025@localhost:6379/1')
        self.redis_client = redis.from_url(redis_url)
        await self.redis_client.ping()
        logger.info("✅ Connected to Redis")

        # Initialize scraper
        self.scraper = await IranianWebScraper.create()
        logger.info("✅ Scraper initialized")

    async def store_products_in_redis(self, products):
        """Store scraped products in Redis with proper keys"""
        try:
            pipe = self.redis_client.pipeline()

            for product in products:
                # Store individual product
                product_dict = {
                    'product_id': product.product_id,
                    'title': product.title,
                    'title_fa': product.title_fa,
                    'price_toman': str(product.price_toman),
                    'price_usd': str(product.price_usd),
                    'vendor': product.vendor,
                    'vendor_name_fa': product.vendor_name_fa,
                    'availability': '1' if product.availability else '0',
                    'product_url': product.product_url,
                    'image_url': product.image_url,
                    'category': product.category,
                    'last_updated': product.last_updated
                }

                key = f"product:{product.product_id}"
                pipe.hset(key, mapping=product_dict)
                pipe.expire(key, 3600)  # 1 hour expiry

            # Store summary for API
            summary_data = {
                'total_products': str(len(products)),
                'last_updated': datetime.now().isoformat(),
                'vendors': json.dumps(list(set(p.vendor for p in products))),
                'status': 'success'
            }
            pipe.hset('scraping_summary', mapping=summary_data)
            pipe.expire('scraping_summary', 3600)

            await pipe.execute()
            logger.info(f"✅ Stored {len(products)} products in Redis")

        except Exception as e:
            logger.error(f"❌ Failed to store in Redis: {e}")

    async def run_scraping_cycle(self):
        """Run one complete scraping cycle"""
        try:
            logger.info("🚀 Starting scraping cycle...")
            results = await self.scraper.run_scraping_cycle()

            # Collect all products
            all_products = []
            for result in results:
                if result.success and result.products:
                    all_products.extend(result.products)
                    logger.info(f"📦 {result.vendor}: {len(result.products)} products")

            logger.info(f"📊 Total products scraped: {len(all_products)}")

            if all_products:
                await self.store_products_in_redis(all_products)
                # Set flag that real data is available
                await self.redis_client.set('real_data_available', 'true', ex=7200)  # 2 hours
                return True
            else:
                logger.warning("⚠️ No products scraped")
                return False

        except Exception as e:
            logger.error(f"❌ Scraping cycle failed: {e}")
            return False

    async def run_continuously(self):
        """Run scraper continuously with interval"""
        logger.info(f"🔄 Starting continuous scraping (every {self.interval_minutes} minutes)")

        while True:
            try:
                success = await self.run_scraping_cycle()
                if success:
                    logger.info("✅ Scraping cycle completed successfully")
                else:
                    logger.warning("⚠️ Scraping cycle had issues")

                # Wait for next cycle
                wait_seconds = self.interval_minutes * 60
                logger.info(f"⏰ Waiting {self.interval_minutes} minutes for next cycle...")
                await asyncio.sleep(wait_seconds)

            except KeyboardInterrupt:
                logger.info("🛑 Stopping continuous scraper...")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def cleanup(self):
        """Cleanup resources"""
        if self.scraper:
            await self.scraper.close()
        if self.redis_client:
            await self.redis_client.close()

async def main():
    scraper = ContinuousScraper()
    try:
        await scraper.initialize()
        await scraper.run_continuously()
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
