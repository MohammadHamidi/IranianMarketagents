#!/usr/bin/env python3
"""
ACTUAL Web Scraper for Iranian E-commerce Sites
This scraper performs REAL HTTP requests and scrapes live data
"""

import asyncio
import aiohttp
import logging
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class ScrapedProduct:
    product_id: str
    title: str
    title_fa: str
    price_toman: int
    price_usd: float
    vendor: str
    vendor_name_fa: str
    product_url: str
    image_url: str
    category: str
    availability: bool
    last_updated: str

class ActualWebScraper:
    """REAL web scraper that makes actual HTTP requests to Iranian e-commerce sites"""
    
    def __init__(self):
        self.exchange_rate = 42000  # USD to Toman (update periodically)
        self.session = None
        self.redis_client = None
        
        # Real Iranian e-commerce sites to discover and scrape
        self.target_sites = [
            {
                "domain": "digikala.com",
                "name": "دیجی‌کالا", 
                "mobile_search_url": "https://www.digikala.com/search/category-mobile-phone/",
                "laptop_search_url": "https://www.digikala.com/search/category-laptop/",
                "selectors": {
                    "product_container": ".product-list_ProductList__item__LiiNI",
                    "title": "h3[data-testid='product-title']",
                    "price": ".variant-price-value",
                    "image": "img[data-testid='product-image']",
                    "link": "a[data-testid='product-card-link']"
                }
            },
            {
                "domain": "technolife.ir", 
                "name": "تکنولایف",
                "mobile_search_url": "https://www.technolife.ir/product-category/mobile/",
                "laptop_search_url": "https://www.technolife.ir/product-category/laptop/",
                "selectors": {
                    "product_container": ".product-item",
                    "title": ".product-title",
                    "price": ".price-current",
                    "image": ".product-image img",
                    "link": ".product-link"
                }
            },
            {
                "domain": "mobit.ir",
                "name": "موبایت",
                "mobile_search_url": "https://mobit.ir/phone/",
                "selectors": {
                    "product_container": ".product-box",
                    "title": ".product-title",
                    "price": ".price",
                    "image": ".product-img img",
                    "link": "a"
                }
            }
        ]
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def init(self):
        """Initialize HTTP session and Redis connection"""
        # Setup HTTP session with SSL verification disabled for problematic sites
        connector = aiohttp.TCPConnector(
            verify_ssl=False,
            limit=10,
            limit_per_host=3,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
        # Connect to Redis
        self.redis_client = redis.from_url('redis://localhost:6379/0')
        
        logger.info("🚀 Actual Web Scraper initialized - ready for REAL scraping!")

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()

    def extract_price_from_text(self, price_text: str) -> int:
        """Extract price in Toman from Persian/English text"""
        if not price_text:
            return 0
            
        # Remove Persian and English characters, keep only digits and commas
        price_clean = re.sub(r'[^\d,۰-۹]', '', price_text)
        
        # Convert Persian digits to English
        persian_to_english = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        
        for persian, english in persian_to_english.items():
            price_clean = price_clean.replace(persian, english)
        
        # Remove commas and convert to integer
        price_clean = price_clean.replace(',', '')
        
        try:
            price = int(price_clean)
            # If price is too small, might be in thousands or millions
            if price < 1000:
                price *= 1000000  # Convert millions to full number
            elif price < 100000:
                price *= 1000  # Convert thousands to full number
            return price
        except ValueError:
            return 0

    async def scrape_site_category(self, site: Dict, category: str) -> List[ScrapedProduct]:
        """Scrape products from a specific site and category"""
        products = []
        
        # Get the appropriate search URL for category
        if category == "mobile":
            url = site.get("mobile_search_url")
        elif category == "laptop":
            url = site.get("laptop_search_url")
        else:
            url = site.get("mobile_search_url")  # Default to mobile
            
        if not url:
            logger.warning(f"No search URL for {site['domain']} category {category}")
            return products

        try:
            logger.info(f"🌐 REAL scraping: {site['domain']} - {category}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return products
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find product containers using site-specific selectors
                selectors = site["selectors"]
                product_containers = soup.select(selectors["product_container"])
                
                logger.info(f"Found {len(product_containers)} product containers on {site['domain']}")
                
                for i, container in enumerate(product_containers[:20]):  # Limit to 20 products per page
                    try:
                        # Extract product information
                        title_elem = container.select_one(selectors["title"])
                        price_elem = container.select_one(selectors["price"])
                        image_elem = container.select_one(selectors["image"])
                        link_elem = container.select_one(selectors["link"])
                        
                        if not title_elem or not price_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        price_text = price_elem.get_text(strip=True)
                        price_toman = self.extract_price_from_text(price_text)
                        
                        if price_toman == 0:
                            continue
                            
                        # Get product URL
                        product_url = url  # Default to search page
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            if href.startswith('http'):
                                product_url = href
                            else:
                                product_url = urljoin(url, href)
                        
                        # Get image URL
                        image_url = ""
                        if image_elem and image_elem.get('src'):
                            src = image_elem.get('src')
                            if src.startswith('http'):
                                image_url = src
                            else:
                                image_url = urljoin(url, src)
                        
                        product = ScrapedProduct(
                            product_id=f"{site['domain'].split('.')[0].upper()[:3]}{str(uuid.uuid4())[:8]}",
                            title=title,
                            title_fa=title,  # For now, assume title is already in correct language
                            price_toman=price_toman,
                            price_usd=round(price_toman / self.exchange_rate, 2),
                            vendor=site["domain"],
                            vendor_name_fa=site["name"],
                            product_url=product_url,
                            image_url=image_url,
                            category=category,
                            availability=True,
                            last_updated=datetime.now(timezone.utc).isoformat()
                        )
                        
                        products.append(product)
                        logger.info(f"✅ Scraped: {title[:50]}... - {price_toman:,} تومان")
                        
                    except Exception as e:
                        logger.warning(f"Error scraping product {i}: {e}")
                        continue
                
                # Add delay between requests to be respectful
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Failed to scrape {site['domain']}: {e}")
            
        return products

    async def scrape_all_sites(self, categories: List[str] = ["mobile"]) -> Dict[str, List[ScrapedProduct]]:
        """Scrape all configured sites for specified categories"""
        all_results = {}
        
        for category in categories:
            logger.info(f"🔍 Starting REAL scraping for category: {category}")
            
            for site in self.target_sites:
                try:
                    products = await self.scrape_site_category(site, category)
                    key = f"{site['domain']}_{category}"
                    all_results[key] = products
                    
                    logger.info(f"✅ {site['domain']}: Found {len(products)} real products")
                    
                    # Store in Redis
                    await self.store_products_in_redis(products)
                    
                except Exception as e:
                    logger.error(f"Error scraping {site['domain']}: {e}")
                    
        return all_results

    async def store_products_in_redis(self, products: List[ScrapedProduct]):
        """Store scraped products in Redis"""
        for product in products:
            try:
                # Convert to API-compatible format
                product_data = {
                    "product_id": product.product_id,
                    "canonical_title": product.title,
                    "canonical_title_fa": product.title_fa,
                    "brand": self.extract_brand(product.title),
                    "category": product.category,
                    "model": product.title,
                    "current_prices": [{
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": product.price_usd,
                        "availability": product.availability,
                        "product_url": product.product_url,
                        "last_updated": product.last_updated
                    }],
                    "lowest_price": {
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": product.price_usd
                    },
                    "highest_price": {
                        "vendor": product.vendor,
                        "vendor_name_fa": product.vendor_name_fa,
                        "price_toman": product.price_toman,
                        "price_usd": product.price_usd
                    },
                    "price_range_pct": 0.0,
                    "available_vendors": 1,
                    "last_updated": product.last_updated,
                    "specifications": self.extract_specs(product.title)
                }
                
                # Store in Redis
                product_key = f"product:{product.product_id}"
                await self.redis_client.set(product_key, json.dumps(product_data))
                
            except Exception as e:
                logger.error(f"Error storing product {product.product_id}: {e}")

    def extract_brand(self, title: str) -> str:
        """Extract brand from product title"""
        title_lower = title.lower()
        brands = ["samsung", "apple", "iphone", "xiaomi", "huawei", "lg", "sony", "nokia", "oneplus", "oppo", "vivo"]
        
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        # Try to get first word as brand
        words = title.split()
        if words:
            return words[0]
            
        return "Unknown"

    def extract_specs(self, title: str) -> Dict:
        """Extract basic specifications from product title"""
        specs = {}
        
        # Try to extract storage
        storage_match = re.search(r'(\d+)\s*GB', title, re.IGNORECASE)
        if storage_match:
            specs["storage_gb"] = int(storage_match.group(1))
            
        # Try to extract screen size
        screen_match = re.search(r'(\d+\.?\d*)\s*inch', title, re.IGNORECASE)
        if screen_match:
            specs["screen_inches"] = float(screen_match.group(1))
            
        return specs

async def main():
    """Test the actual web scraper"""
    scraper = ActualWebScraper()
    
    try:
        await scraper.init()
        
        logger.info("🚀 Starting ACTUAL web scraping...")
        results = await scraper.scrape_all_sites(["mobile"])
        
        total_products = sum(len(products) for products in results.values())
        logger.info(f"🎉 REAL scraping completed! Found {total_products} actual products")
        
        # Update Redis flags
        await scraper.redis_client.set('real_data_available', 'true')
        await scraper.redis_client.set('scraping:summary', json.dumps({
            "total_products": total_products,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "vendors": list(set(site['domain'] for site in scraper.target_sites)),
            "categories": ["mobile"],
            "status": "success",
            "scraper_run_id": str(int(datetime.now().timestamp())),
            "real_data_flag": True
        }))
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
