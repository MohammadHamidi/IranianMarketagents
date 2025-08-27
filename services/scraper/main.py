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

# Import the real web scraper
from real_scraper import IranianWebScraper, ProductData

# Redis connection
redis_client = None

async def store_products_in_redis(products: List[ProductData]):
    """Store scraped products in Redis"""
    try:
        pipe = redis_client.pipeline()

        for product in products:
            # Convert dataclass to dict
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
            pipe.expire(key, 86400)  # Expire in 24 hours to keep data available longer

        await pipe.execute()
        logger.info(f"✅ Stored {len(products)} real products in Redis")

        # Also store a summary for the API
        summary_key = "scraping_summary"
        summary_data = {
            'total_products': str(len(products)),
            'last_updated': datetime.now().isoformat(),
            'vendors': json.dumps(list(set(p.vendor for p in products)))
        }
        pipe.hset(summary_key, mapping=summary_data)
        pipe.expire(summary_key, 86400)  # Also keep summary available for 24 hours
        await pipe.execute()

    except Exception as e:
        logger.error(f"❌ Failed to store products in Redis: {e}")

async def main():
    """Main scraping function"""
    global redis_client

    try:
        # Connect to Redis using settings
        from config.settings import settings
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Connected to Redis")

        # Initialize the real web scraper
        scraper = await IranianWebScraper.create()

        # Run scraping cycle
        logger.info("🚀 Starting real Iranian e-commerce scraping...")
        results = await scraper.run_scraping_cycle()

        # Collect all products from successful scrapes
        all_products = []
        for result in results:
            if result.success and result.products:
                all_products.extend(result.products)
                logger.info(f"📦 Collected {len(result.products)} products from {result.vendor}")

        logger.info(f"📊 Total real products scraped: {len(all_products)}")

        # Store real data in Redis
        if all_products:
            await store_products_in_redis(all_products)
            logger.info("💾 Real product data stored in Redis successfully!")
        else:
            logger.warning("⚠️ No products were scraped successfully")

    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Close connections
        if redis_client:
            await redis_client.close()
        if scraper:
            await scraper.close()
            logger.info("🔌 Closed web scraper session")

# For testing without Docker
def test_scraper():
    """Test the scraper locally"""
    import asyncio
    from real_scraper import IranianWebScraper

    async def run_test():
        scraper = await IranianWebScraper.create()
        try:
            results = await scraper.run_scraping_cycle()

            print("🎉 Real Web Scraping Results:")
            for result in results:
                print(f"📦 {result.vendor}: {result.products_found} products")
                if result.success and result.products:
                    for product in result.products[:3]:  # Show first 3 products
                        print(f"  • {product.title} - {product.price_toman:,} تومان")
                else:
                    print(f"  ❌ Failed: {result.error_message}")

            return results
        finally:
            await scraper.close()

    return asyncio.run(run_test())

if __name__ == "__main__":
    # Check if running in Docker or locally
    import os
    if os.environ.get('DOCKER_CONTAINER') or os.path.exists('/.dockerenv'):
        print("Running scraper in Docker - connecting to Redis...")
        asyncio.run(main())
    else:
        print("Running scraper test locally...")
        test_scraper()