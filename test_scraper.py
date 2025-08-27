#!/usr/bin/env python3
"""Quick test for scraping functionality"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scraper.orchestrator import IranianScrapingOrchestrator

async def test_scraper():
    try:
        orchestrator = await IranianScrapingOrchestrator.create()
        print("✅ Scraper initialized successfully")
        
        # Test single site
        results = await orchestrator.scrape_with_simple_http(
            orchestrator.site_configs['technolife.ir'],
            ['https://technolife.ir/product_cat/mobile-tablet/']
        )
        
        print(f"✅ Scraping test completed: {len(results)} results")
        
        await orchestrator.close()
        
    except Exception as e:
        print(f"❌ Scraping test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scraper())