#!/usr/bin/env python3
"""
Enhanced scraper main entry point
"""

import asyncio
import os
import sys

async def main():
    """Main entry point - choose mode based on environment"""

    # Check if continuous scraping is enabled
    continuous_mode = os.getenv('ENABLE_CONTINUOUS_SCRAPING', 'false').lower() == 'true'

    if continuous_mode:
        print("🔄 Starting in continuous scraping mode...")
        from continuous_scraper import ContinuousScraper
        scraper = ContinuousScraper()
        try:
            await scraper.initialize()
            await scraper.run_continuously()
        finally:
            await scraper.cleanup()
    else:
        print("🚀 Starting in single-run mode...")
        from continuous_scraper import ContinuousScraper
        scraper = ContinuousScraper()
        try:
            await scraper.initialize()
            await scraper.run_scraping_cycle()
        finally:
            await scraper.cleanup()

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