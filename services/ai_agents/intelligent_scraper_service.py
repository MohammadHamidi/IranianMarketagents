#!/usr/bin/env python3
"""
Intelligent Scraper Service - AI Agent Integration
Connects the AI toolkit to the main API system
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlparse
import redis.asyncio as redis

from enhanced_scraper_engine import EnhancedScraperEngine, EnhancedScrapingResult

logger = logging.getLogger(__name__)

class IntelligentScraperService:
    """
    Service that integrates AI agents into the main system
    Provides intelligent, adaptive scraping capabilities
    """
    
    def __init__(self):
        self.enhanced_scraper = None
        self.redis_client = None
        self.discovered_sites = set()
        self.failed_sites = set()

    async def init(self):
        """Initialize the service"""
        self.redis_client = redis.from_url('redis://localhost:6379/0')
        self.enhanced_scraper = EnhancedScraperEngine(self.redis_client)

        await self.enhanced_scraper.init()

        # Load previously discovered sites
        await self._load_discovered_sites()

        logger.info("🤖 Intelligent Scraper Service initialized")

    async def close(self):
        """Clean up resources"""
        if self.enhanced_scraper:
            await self.enhanced_scraper.close()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def discover_and_scrape_websites(self, seed_urls: List[str] = None) -> Dict[str, any]:
        """
        Main function: Discover new websites and scrape them intelligently
        """
        if not seed_urls:
            seed_urls = await self._get_seed_urls()
        
        results = {
            "discovered_sites": 0,
            "successful_scrapes": 0,
            "total_products": 0,
            "failed_sites": [],
            "success_sites": [],
            "execution_time": 0
        }
        
        start_time = datetime.now()
        
        logger.info(f"🚀 Starting intelligent discovery and scraping for {len(seed_urls)} URLs")
        
        # Process each URL
        for url in seed_urls:
            domain = urlparse(url).netloc
            
            # Skip if we've already tried this recently
            if domain in self.failed_sites:
                logger.info(f"⏭️ Skipping {domain} (recently failed)")
                continue
            
            logger.info(f"🔍 Processing: {domain}")
            
            try:
                # Use enhanced scraper engine for intelligent scraping
                result = await self.enhanced_scraper.scrape_website_enhanced(url)

                if result.success and result.products_found > 0:
                    results["successful_scrapes"] += 1
                    results["total_products"] += result.products_found
                    results["success_sites"].append({
                        "domain": domain,
                        "products_found": result.products_found,
                        "tool_used": result.tool_used,
                        "execution_time": result.execution_time
                    })
                    
                    self.discovered_sites.add(domain)
                    logger.info(f"✅ {domain}: {result.products_found} products found using {result.tool_used}")
                    
                    # Store website info
                    await self._store_discovered_website(url, result)
                    
                else:
                    self.failed_sites.add(domain)
                    results["failed_sites"].append({
                        "domain": domain,
                        "errors": result.errors
                    })
                    logger.warning(f"❌ {domain}: {result.errors}")
                
            except Exception as e:
                self.failed_sites.add(domain)
                results["failed_sites"].append({
                    "domain": domain,
                    "errors": [str(e)]
                })
                logger.error(f"❌ Error processing {domain}: {e}")
            
            # Small delay between requests
            await asyncio.sleep(2)
        
        results["discovered_sites"] = len(self.discovered_sites)
        results["execution_time"] = (datetime.now() - start_time).total_seconds()
        
        # Update discovery summary
        await self._update_discovery_summary(results)
        
        logger.info(f"🎉 Discovery complete: {results['successful_scrapes']}/{len(seed_urls)} sites successful")
        logger.info(f"📊 Total products found: {results['total_products']}")
        
        return results
    
    async def scrape_specific_website(self, url: str) -> Dict[str, any]:
        """
        Scrape a specific website using AI agent
        Used for manual scraping requests from the API
        """
        logger.info(f"🎯 Manual scrape request for: {url}")
        
        try:
            result = await self.enhanced_scraper.scrape_website_enhanced(url)
            
            if result.success:
                domain = urlparse(url).netloc
                await self._store_discovered_website(url, result)
                
                return {
                    "success": True,
                    "domain": domain,
                    "products_found": result.products_found,
                    "tool_used": result.tool_used,
                    "execution_time": result.execution_time,
                    "products": result.products[:10]  # Return sample products
                }
            else:
                return {
                    "success": False,
                    "errors": result.errors,
                    "tool_used": result.tool_used
                }
                
        except Exception as e:
            logger.error(f"Error in manual scrape: {e}")
            return {
                "success": False,
                "errors": [str(e)],
                "tool_used": "error"
            }
    
    async def get_discovered_websites(self) -> List[Dict[str, any]]:
        """Get list of discovered websites"""
        websites = []
        
        try:
            # Get stored website data
            keys = await self.redis_client.keys("discovered_website:*")
            
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    website_info = json.loads(data)
                    websites.append(website_info)
            
            # Sort by last successful scrape
            websites.sort(key=lambda x: x.get('last_successful_scrape', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting discovered websites: {e}")
        
        return websites
    
    async def analyze_website_only(self, url: str) -> Dict[str, any]:
        """
        Analyze a website without scraping (for discovery preview)
        """
        try:
            # Use the enhanced scraper engine's analyzer
            analysis = await self.enhanced_scraper.analyzer.analyze_website(url)

            return {
                "success": True,
                "domain": urlparse(url).netloc,
                "website_type": analysis.get('website_type', 'unknown'),
                "ecommerce_confidence": analysis.get('ecommerce_confidence', 0.0),
                "recommended_tools": analysis.get('recommended_tools', []),
                "anti_bot_measures": analysis.get('anti_bot_measures', []),
                "content_language": analysis.get('content_language', 'fa'),
                "currency_detected": analysis.get('currency_detected', 'IRR')
            }

        except Exception as e:
            logger.error(f"Error analyzing website: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_seed_urls(self) -> List[str]:
        """Get seed URLs for discovery"""
        # Iranian e-commerce sites to discover
        seed_urls = [
            "https://www.emalls.ir",
            "https://www.mobit.ir",
            "https://www.mobile.ir",
            "https://www.bamilo.com",
            "https://www.snapp.market",
            "https://www.okala.com",
            "https://www.torob.com",
            "https://www.khodafez.com",
            "https://www.timcheh.com",
            "https://www.mahriha.com"
        ]
        
        # Add any previously successful sites
        stored_sites = await self.get_discovered_websites()
        for site in stored_sites:
            if site.get('url') and site['url'] not in seed_urls:
                seed_urls.append(site['url'])
        
        return seed_urls
    
    async def _load_discovered_sites(self):
        """Load previously discovered sites from Redis"""
        try:
            keys = await self.redis_client.keys("discovered_website:*")
            
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    website_info = json.loads(data)
                    domain = urlparse(website_info['url']).netloc
                    self.discovered_sites.add(domain)
            
            logger.info(f"📚 Loaded {len(self.discovered_sites)} previously discovered sites")
            
        except Exception as e:
            logger.error(f"Error loading discovered sites: {e}")
    
    async def _store_discovered_website(self, url: str, result):
        """Store discovered website information"""
        try:
            domain = urlparse(url).netloc
            
            website_info = {
                "url": url,
                "domain": domain,
                "discovery_date": datetime.now(timezone.utc).isoformat(),
                "last_successful_scrape": datetime.now(timezone.utc).isoformat(),
                "tool_used": result.tool_used,
                "products_found": result.products_found,
                "execution_time": result.execution_time,
                "status": "active",
                "total_scrapes": 1,
                "success_rate": 1.0
            }
            
            # Check if website already exists
            key = f"discovered_website:{domain}"
            existing_data = await self.redis_client.get(key)
            
            if existing_data:
                existing_info = json.loads(existing_data)
                website_info["discovery_date"] = existing_info.get("discovery_date", website_info["discovery_date"])
                website_info["total_scrapes"] = existing_info.get("total_scrapes", 0) + 1
                
                # Update success rate
                total_attempts = website_info["total_scrapes"]
                successful_attempts = existing_info.get("successful_scrapes", 0) + 1
                website_info["successful_scrapes"] = successful_attempts
                website_info["success_rate"] = successful_attempts / total_attempts
            else:
                website_info["successful_scrapes"] = 1
            
            await self.redis_client.set(key, json.dumps(website_info))
            
            logger.info(f"💾 Stored website info for {domain}")
            
        except Exception as e:
            logger.error(f"Error storing website info: {e}")
    
    async def _update_discovery_summary(self, results: Dict):
        """Update discovery summary in Redis"""
        try:
            summary = {
                "last_discovery_run": datetime.now(timezone.utc).isoformat(),
                "total_discovered_sites": len(self.discovered_sites),
                "successful_scrapes": results["successful_scrapes"],
                "total_products_found": results["total_products"],
                "execution_time": results["execution_time"],
                "failed_sites_count": len(results["failed_sites"]),
                "success_rate": results["successful_scrapes"] / len(self.discovered_sites) if self.discovered_sites else 0
            }
            
            await self.redis_client.set("ai_discovery:summary", json.dumps(summary))
            
        except Exception as e:
            logger.error(f"Error updating discovery summary: {e}")

# Integration with the main API
class AIAgentAPI:
    """API integration for AI agents"""
    
    def __init__(self):
        self.scraper_service = IntelligentScraperService()
    
    async def init(self):
        """Initialize the service"""
        await self.scraper_service.init()
    
    async def close(self):
        """Close the service"""
        await self.scraper_service.close()
    
    async def discover_websites(self, search_terms: List[str] = None) -> Dict[str, any]:
        """
        API endpoint: Discover new websites
        """
        try:
            results = await self.scraper_service.discover_and_scrape_websites()
            
            return {
                "status": "success",
                "message": f"Discovery completed: {results['successful_scrapes']} sites scraped successfully",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in website discovery: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results": {}
            }
    
    async def manual_scrape_website(self, url: str) -> Dict[str, any]:
        """
        API endpoint: Manually scrape a specific website
        """
        try:
            result = await self.scraper_service.scrape_specific_website(url)
            
            if result["success"]:
                return {
                    "status": "success",
                    "message": f"Successfully scraped {result['products_found']} products",
                    "result": result
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Scraping failed: {result['errors']}",
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Error in manual scraping: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {}
            }
    
    async def get_discovered_websites(self) -> Dict[str, any]:
        """
        API endpoint: Get list of discovered websites
        """
        try:
            websites = await self.scraper_service.get_discovered_websites()
            
            return {
                "status": "success",
                "websites": websites,
                "total_count": len(websites)
            }
            
        except Exception as e:
            logger.error(f"Error getting websites: {e}")
            return {
                "status": "error",
                "message": str(e),
                "websites": []
            }
    
    async def analyze_website(self, url: str) -> Dict[str, any]:
        """
        API endpoint: Analyze a website (preview before scraping)
        """
        try:
            analysis = await self.scraper_service.analyze_website_only(url)
            
            return {
                "status": "success",
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing website: {e}")
            return {
                "status": "error",
                "message": str(e),
                "analysis": {}
            }

async def main():
    """Test the intelligent scraper service"""
    service = IntelligentScraperService()
    
    try:
        await service.init()
        
        # Test discovery
        print("🚀 Testing AI-powered website discovery...")
        results = await service.discover_and_scrape_websites([
            "https://www.emalls.ir",
            "https://www.mobit.ir"
        ])
        
        print(f"✅ Discovery Results:")
        print(f"  - Successful scrapes: {results['successful_scrapes']}")
        print(f"  - Total products: {results['total_products']}")
        print(f"  - Execution time: {results['execution_time']:.2f}s")
        
        # Test manual scraping
        print("\n🎯 Testing manual scraping...")
        manual_result = await service.scrape_specific_website("https://www.mobit.ir")
        print(f"Manual scrape result: {manual_result}")
        
        # Test website analysis
        print("\n🔍 Testing website analysis...")
        analysis = await service.analyze_website_only("https://www.emalls.ir")
        print(f"Analysis result: {analysis}")
        
    finally:
        await service.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
