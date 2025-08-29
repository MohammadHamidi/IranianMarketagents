#!/usr/bin/env python3
"""
REAL Iranian E-commerce Scraper - NO FAKE DATA
Either scrapes successfully or returns empty results
"""

import asyncio
import aiohttp
import logging
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass
import redis.asyncio as redis
from urllib.parse import urljoin
import time

logger = logging.getLogger(__name__)

@dataclass
class RealProduct:
    product_id: str
    title: str
    price_toman: int
    vendor: str
    vendor_name_fa: str
    product_url: str
    category: str
    last_updated: str

class RealIranianScraper:
    """
    REAL scraper for Iranian e-commerce sites
    NO FAKE DATA - only real scraped data or empty results
    """
    
    def __init__(self):
        self.session = None
        self.redis_client = None
        self.exchange_rate = 42000  # Update with real API
        
        # Headers to look like a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def init(self):
        """Initialize connections"""
        connector = aiohttp.TCPConnector(
            ssl=False,  # Some Iranian sites have SSL issues
            limit=5,
            limit_per_host=2,
            ttl_dns_cache=300,
        )
        
        timeout = aiohttp.ClientTimeout(total=20, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
        self.redis_client = redis.from_url('redis://localhost:6379/0')
        logger.info("🚀 Real Iranian Scraper initialized - NO FAKE DATA!")

    async def close(self):
        """Clean up"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.aclose()

    def extract_price_toman(self, text: str) -> int:
        """Extract price in Toman from text"""
        if not text:
            return 0
            
        # Remove all non-digit characters except Persian digits
        cleaned = re.sub(r'[^\d۰-۹,]', '', text)
        
        # Convert Persian digits
        persian_digits = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', 
                         '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
        
        for persian, english in persian_digits.items():
            cleaned = cleaned.replace(persian, english)
        
        # Remove commas and extract numbers
        cleaned = cleaned.replace(',', '')
        
        # Find the largest number (likely the price)
        numbers = re.findall(r'\d+', cleaned)
        if numbers:
            price = max(int(num) for num in numbers)
            
            # If price is too small, might need multiplication
            if price < 1000:
                price *= 1000000  # Convert millions
            elif price < 100000:
                price *= 1000  # Convert thousands
                
            return price if price >= 10000 else 0  # Minimum reasonable price
        
        return 0

    async def try_scrape_torob_api(self, query: str = "mobile") -> List[RealProduct]:
        """
        Try to use Torob's public search API for real Iranian prices
        Torob aggregates prices from many Iranian sites
        """
        products = []
        
        try:
            # Torob has a search API that might be accessible
            url = f"https://api.torob.com/v4/base-product/search/?query={query}"
            
            logger.info(f"🔍 Trying Torob API: {query}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data:
                        for item in data['results'][:20]:  # Limit to 20
                            try:
                                if 'priceList' in item and item['priceList']:
                                    price_info = item['priceList'][0]
                                    
                                    product = RealProduct(
                                        product_id=f"TOROB{uuid.uuid4().hex[:8]}",
                                        title=item.get('name1', 'Unknown Product'),
                                        price_toman=price_info.get('price', 0),
                                        vendor=price_info.get('shop', {}).get('title', 'Unknown'),
                                        vendor_name_fa=price_info.get('shop', {}).get('title', 'نامشخص'),
                                        product_url=price_info.get('url', ''),
                                        category=query,
                                        last_updated=datetime.now(timezone.utc).isoformat()
                                    )
                                    
                                    if product.price_toman > 0:
                                        products.append(product)
                                        logger.info(f"✅ Real product: {product.title[:40]}... - {product.price_toman:,} تومان")
                                        
                            except Exception as e:
                                logger.warning(f"Error parsing Torob product: {e}")
                                continue
                    
                    logger.info(f"✅ Torob API: Found {len(products)} REAL products")
                    
                else:
                    logger.warning(f"Torob API returned {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to access Torob API: {e}")
            
        return products

    async def try_scrape_simple_sites(self) -> List[RealProduct]:
        """
        Try to scrape simpler Iranian sites that might be accessible
        """
        products = []
        
        # Try some simpler Iranian tech sites
        simple_sites = [
            {
                "url": "https://www.emalls.ir/mobile",
                "name": "ایمالز",
                "domain": "emalls.ir"
            },
            {
                "url": "https://www.mobit.ir",
                "name": "موبایت", 
                "domain": "mobit.ir"
            }
        ]
        
        for site in simple_sites:
            try:
                logger.info(f"🔍 Trying to scrape: {site['domain']}")
                
                async with self.session.get(site['url']) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Look for common price patterns in HTML
                        price_patterns = [
                            r'(\d{1,3}(?:,\d{3})*)\s*تومان',
                            r'(\d{1,3}(?:,\d{3})*)\s*ریال',
                            r'price["\']?\s*:\s*["\']?(\d+)',
                            r'(\d+)\s*تومان'
                        ]
                        
                        for pattern in price_patterns:
                            matches = re.findall(pattern, html)
                            if matches:
                                logger.info(f"Found {len(matches)} price matches on {site['domain']}")
                                break
                                
                        # This is a basic attempt - real implementation would need
                        # proper HTML parsing and product extraction
                        
                    await asyncio.sleep(2)  # Be respectful
                    
            except Exception as e:
                logger.warning(f"Failed to scrape {site['domain']}: {e}")
                
        return products

    async def scrape_real_data(self) -> Dict[str, any]:
        """
        Main function to scrape REAL data from Iranian e-commerce sites
        Returns real data or empty results - NO FAKE DATA
        """
        all_products = []
        
        logger.info("🚀 Starting REAL Iranian e-commerce scraping - NO FAKE DATA!")
        
        # Try different approaches to get real data
        
        # Approach 1: Try Torob API (price comparison site)
        torob_products = await self.try_scrape_torob_api("mobile")
        all_products.extend(torob_products)
        
        # Approach 2: Try other query terms
        for query in ["samsung", "iphone", "xiaomi"]:
            products = await self.try_scrape_torob_api(query)
            all_products.extend(products[:5])  # Limit to avoid duplicates
            await asyncio.sleep(1)
        
        # Approach 3: Try direct site scraping (might fail)
        simple_products = await self.try_scrape_simple_sites()
        all_products.extend(simple_products)
        
        logger.info(f"📊 REAL scraping completed: {len(all_products)} genuine products found")
        
        if len(all_products) == 0:
            logger.warning("⚠️ NO REAL DATA FOUND - Will show empty results (NO FAKE DATA)")
            return {
                "success": True,
                "products_found": 0,
                "products": [],
                "message": "No real data available - scraping unsuccessful",
                "real_data_flag": False
            }
        
        # Store real products in Redis
        await self.store_real_products(all_products)
        
        return {
            "success": True,
            "products_found": len(all_products),
            "products": all_products,
            "message": f"Successfully scraped {len(all_products)} real products",
            "real_data_flag": True
        }

    async def store_real_products(self, products: List[RealProduct]):
        """Store REAL products in Redis"""
        
        logger.info(f"💾 Storing {len(products)} REAL products in Redis")
        
        for product in products:
            try:
                # Convert to API format
                product_data = {
                    "product_id": product.product_id,
                    "canonical_title": product.title,
                    "canonical_title_fa": product.title,
                    "brand": self.extract_brand(product.title),
                    "category": product.category,
                    "model": product.title,
                    "current_prices": [{
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": round(product.price_toman / self.exchange_rate, 2),
                        "availability": True,
                        "product_url": product.product_url,
                        "last_updated": product.last_updated
                    }],
                    "lowest_price": {
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": round(product.price_toman / self.exchange_rate, 2)
                    },
                    "highest_price": {
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": round(product.price_toman / self.exchange_rate, 2)
                    },
                    "price_range_pct": 0.0,
                    "available_vendors": 1,
                    "last_updated": product.last_updated,
                    "specifications": None
                }
                
                product_key = f"product:{product.product_id}"
                await self.redis_client.set(product_key, json.dumps(product_data))
                
            except Exception as e:
                logger.error(f"Error storing product {product.product_id}: {e}")
        
        # Update status flags
        await self.redis_client.set('real_data_available', 'true' if len(products) > 0 else 'false')
        
        summary = {
            "total_products": len(products),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "vendors": list(set(p.vendor for p in products)),
            "categories": list(set(p.category for p in products)),
            "status": "success" if len(products) > 0 else "no_data",
            "scraper_run_id": str(int(time.time())),
            "real_data_flag": len(products) > 0
        }
        
        await self.redis_client.set('scraping:summary', json.dumps(summary))
        
        logger.info(f"✅ Stored summary: {len(products)} real products from {len(summary['vendors'])} vendors")

    def extract_brand(self, title: str) -> str:
        """Extract brand from title"""
        title_lower = title.lower()
        brands = ["samsung", "apple", "iphone", "xiaomi", "huawei", "lg", "sony", "nokia", "oneplus", "oppo", "vivo"]
        
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        words = title.split()
        return words[0] if words else "Unknown"

async def main():
    """Test the real scraper"""
    scraper = RealIranianScraper()
    
    try:
        await scraper.init()
        
        # Run real scraping
        results = await scraper.scrape_real_data()
        
        if results['real_data_flag']:
            print(f"✅ SUCCESS: Found {results['products_found']} REAL products!")
            for product in results['products'][:5]:
                print(f"  📱 {product.title[:50]}... - {product.price_toman:,} تومان ({product.vendor})")
        else:
            print("⚠️ NO REAL DATA FOUND - Dashboard will show empty results")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print("❌ Scraping failed - NO FAKE DATA will be shown")
        
    finally:
        await scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
