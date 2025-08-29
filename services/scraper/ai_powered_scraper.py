#!/usr/bin/env python3
"""
AI-Powered Iranian E-commerce Scraper
Replaces the old scraper with intelligent AI agents
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import AI agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai_agents'))
try:
    from intelligent_scraper_service import IntelligentScraperService
    AI_AGENTS_AVAILABLE = True
    logger.info("🤖 AI Agents loaded successfully")
except ImportError as e:
    logger.error(f"❌ AI Agents not available: {e}")
    AI_AGENTS_AVAILABLE = False
    IntelligentScraperService = None

class AIPoweredScraper:
    """AI-powered scraper using intelligent agents"""
    
    def __init__(self):
        self.intelligent_scraper = None
        self.redis_client = None
        
    async def initialize(self):
        """Initialize the AI scraper"""
        if not AI_AGENTS_AVAILABLE:
            raise Exception("AI Agents not available - cannot initialize scraper")
        
        # Initialize intelligent scraper service
        self.intelligent_scraper = IntelligentScraperService()
        await self.intelligent_scraper.init()
        
        # Connect to Redis
        self.redis_client = redis.from_url('redis://localhost:6379/0')
        await self.redis_client.ping()
        
        logger.info("🤖 AI-Powered Scraper initialized successfully")
    
    async def close(self):
        """Close connections"""
        if self.intelligent_scraper:
            await self.intelligent_scraper.close()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def run_discovery_and_scraping(self) -> Dict[str, Any]:
        """
        Run intelligent discovery and scraping of Iranian e-commerce sites
        """
        logger.info("🚀 Starting AI-powered discovery and scraping")
        
        try:
            # Use AI agents for discovery and scraping
            results = await self.intelligent_scraper.discover_and_scrape_websites()
            
            logger.info(f"✅ AI Discovery completed:")
            logger.info(f"  - Sites discovered: {results['discovered_sites']}")
            logger.info(f"  - Successful scrapes: {results['successful_scrapes']}")
            logger.info(f"  - Total products found: {results['total_products']}")
            logger.info(f"  - Execution time: {results['execution_time']:.2f}s")
            
            # Update summary in Redis for API consumption
            await self._update_scraping_summary(results)
            
            return {
                "status": "success",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ AI discovery and scraping failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def manual_scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Manually scrape a specific website using AI agents
        """
        logger.info(f"🎯 AI manual scrape for: {url}")
        
        try:
            result = await self.intelligent_scraper.scrape_specific_website(url)
            
            return {
                "status": "success" if result["success"] else "failed",
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ AI manual scrape failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_discovered_websites(self) -> List[Dict[str, Any]]:
        """Get list of discovered websites"""
        try:
            return await self.intelligent_scraper.get_discovered_websites()
        except Exception as e:
            logger.error(f"Error getting discovered websites: {e}")
            return []
    
    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """Analyze a website using AI agents"""
        try:
            return await self.intelligent_scraper.analyze_website_only(url)
        except Exception as e:
            logger.error(f"Error analyzing website: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_scraping_summary(self, results: Dict):
        """Update scraping summary for API consumption"""
        try:
            summary = {
                "last_scraping_run": datetime.now(timezone.utc).isoformat(),
                "total_products_found": results["total_products"],
                "successful_sites": results["successful_scrapes"],
                "discovered_sites": results["discovered_sites"],
                "execution_time": results["execution_time"],
                "status": "completed",
                "scraper_type": "ai_powered",
                "real_data_flag": True
            }
            
            await self.redis_client.set('ai_scraping:summary', json.dumps(summary))
            await self.redis_client.set('real_data_available', 'true')
            
            logger.info("📊 Updated scraping summary in Redis")
            
        except Exception as e:
            logger.error(f"Error updating summary: {e}")

async def main():
    """Main function for running the AI-powered scraper"""
    scraper = AIPoweredScraper()
    
    try:
        await scraper.initialize()
        
        # Run discovery and scraping
        results = await scraper.run_discovery_and_scraping()
        
        print("\n" + "="*60)
        print("🤖 AI-POWERED SCRAPING RESULTS")
        print("="*60)
        
        if results["status"] == "success":
            r = results["results"]
            print(f"✅ Status: SUCCESS")
            print(f"📊 Total Products Found: {r['total_products']}")
            print(f"🌐 Sites Successfully Scraped: {r['successful_scrapes']}")
            print(f"🔍 Sites Discovered: {r['discovered_sites']}")
            print(f"⏱️ Execution Time: {r['execution_time']:.2f} seconds")
            
            print(f"\n📈 Successful Sites:")
            for site in r["success_sites"]:
                print(f"  • {site['domain']}: {site['products_found']} products using {site['tool_used']}")
            
            if r["failed_sites"]:
                print(f"\n❌ Failed Sites:")
                for site in r["failed_sites"]:
                    print(f"  • {site['domain']}: {site['errors']}")
        
        else:
            print(f"❌ Status: FAILED")
            print(f"💬 Error: {results['error']}")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error running AI scraper: {e}")
    
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
