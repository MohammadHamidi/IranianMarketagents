#!/usr/bin/env python3
"""
Requests-Based Scraper - No Browser Dependencies
Lightweight scraper using requests and BeautifulSoup for AI agents
"""

import asyncio
import aiohttp
import json
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Result from scraping operation"""
    success: bool
    products_found: int
    products: List[Dict]
    tool_used: str
    execution_time: float
    errors: List[str]
    metadata: Dict[str, Any]

class RequestsScraper:
    """Lightweight scraper using requests and BeautifulSoup"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def init(self):
        """Initialize HTTP session"""
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def scrape_website(self, url: str, analysis: Dict = None) -> ScrapingResult:
        """Scrape website using requests and BeautifulSoup"""
        start_time = datetime.now()
        products = []
        errors = []
        
        try:
            logger.info(f"🌐 Scraping {url} with requests+BeautifulSoup")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    errors.append(f"HTTP {response.status}")
                    return self._create_result(False, products, "requests", start_time, errors)
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract products based on Iranian e-commerce patterns
                products = await self._extract_iranian_products(soup, url)
                
                logger.info(f"✅ Found {len(products)} products using requests scraper")
                
        except Exception as e:
            errors.append(f"Requests error: {str(e)}")
            logger.error(f"❌ Requests scraping failed: {e}")
        
        return self._create_result(len(products) > 0, products, "requests", start_time, errors)
    
    async def _extract_iranian_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract products from Iranian e-commerce sites"""
        products = []
        
        # Common Iranian e-commerce selectors
        product_selectors = [
            # Digikala patterns
            '[data-testid*="product"]',
            '.product-list-item',
            '.c-product-box',
            
            # Emalls patterns
            '.product-item',
            '.product-box',
            '.item-product',
            
            # Mobit patterns
            '.product-card',
            '.mobile-item',
            '.phone-item',
            
            # General patterns
            '[class*="product"]',
            '[class*="item"]',
            '[data-product-id]',
            '.card:has(img)',
            'article:has(img)'
        ]
        
        containers_found = []
        
        # Try each selector
        for selector in product_selectors:
            try:
                containers = soup.select(selector)[:20]  # Limit to 20
                if containers:
                    containers_found.extend(containers)
                    logger.info(f"📦 Found {len(containers)} containers with selector: {selector}")
                    break  # Use first successful selector
            except Exception as e:
                continue
        
        # If no specific selectors work, try generic approach
        if not containers_found:
            # Look for elements with images and text that might be products
            containers_found = self._find_product_like_elements(soup)
        
        # Extract product data from containers
        for container in containers_found[:15]:  # Limit to 15 products
            try:
                product = await self._extract_product_from_container(container, base_url)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"Error extracting product: {e}")
                continue
        
        return products
    
    def _find_product_like_elements(self, soup: BeautifulSoup) -> List:
        """Find elements that look like products using heuristics"""
        candidates = []
        
        # Look for elements with both images and price-like text
        for element in soup.find_all(['div', 'article', 'section', 'li']):
            try:
                # Must have an image
                if not element.find('img'):
                    continue
                
                # Must have price-like text
                text = element.get_text()
                has_price = bool(re.search(r'(\d{1,3}(,\d{3})*\s*(تومان|ریال)|\$\d+)', text))
                
                if has_price and len(text.strip()) > 10:
                    candidates.append(element)
                    
            except Exception:
                continue
        
        return candidates[:20]  # Limit results
    
    async def _extract_product_from_container(self, container, base_url: str) -> Optional[Dict]:
        """Extract product data from a container element"""
        try:
            product = {}
            
            # Extract title
            title = self._extract_title(container)
            if not title:
                return None
            
            product['title'] = title
            product['canonical_title'] = title
            product['canonical_title_fa'] = title
            
            # Extract price
            price_text = self._extract_price_text(container)
            price_toman = self._extract_price_from_text(price_text)
            
            if price_toman == 0:
                return None  # Skip items without valid prices
            
            product['price_text'] = price_text
            product['price_toman'] = price_toman
            product['price_usd'] = round(price_toman / 42000, 2)
            
            # Extract image
            product['image_url'] = self._extract_image_url(container, base_url)
            
            # Extract product URL
            product['product_url'] = self._extract_product_url(container, base_url)
            
            # Extract brand from title
            product['brand'] = self._extract_brand(title)
            
            # Add metadata
            product['product_id'] = f"AUTO{uuid.uuid4().hex[:8]}"
            product['category'] = "auto_discovered"
            product['model'] = title
            product['last_updated'] = datetime.now(timezone.utc).isoformat()
            product['source'] = 'requests_scraper'
            product['availability'] = True
            
            return product
            
        except Exception as e:
            logger.warning(f"Error extracting product data: {e}")
            return None
    
    def _extract_title(self, container) -> str:
        """Extract product title from container"""
        # Try different title selectors
        title_selectors = [
            'h1', 'h2', 'h3', 'h4',
            '[class*="title"]',
            '[class*="name"]',
            '[class*="product-name"]',
            'a[title]',
            '.title',
            '.name',
            '.product-title'
        ]
        
        for selector in title_selectors:
            try:
                element = container.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    if title and len(title) > 5:
                        return title[:100]  # Limit length
                    
                    # Try title attribute
                    title = element.get('title', '')
                    if title and len(title) > 5:
                        return title[:100]
            except:
                continue
        
        # Fallback: try to find longest meaningful text
        try:
            texts = [elem.get_text(strip=True) for elem in container.find_all(text=True)]
            meaningful_texts = [t for t in texts if len(t) > 10 and len(t) < 200]
            if meaningful_texts:
                return meaningful_texts[0][:100]
        except:
            pass
        
        return ""
    
    def _extract_price_text(self, container) -> str:
        """Extract price text from container"""
        # Price patterns to look for
        price_patterns = [
            r'\d{1,3}(,\d{3})*\s*تومان',
            r'\d{1,3}(,\d{3})*\s*ریال',
            r'\$\d+(,\d{3})*',
            r'\d{1,3}(,\d{3})*\s*T',  # Short for Toman
        ]
        
        # Try price-specific selectors first
        price_selectors = [
            '[class*="price"]',
            '[class*="cost"]',
            '[class*="amount"]',
            '.price',
            '.cost',
            '.amount'
        ]
        
        for selector in price_selectors:
            try:
                element = container.select_one(selector)
                if element:
                    text = element.get_text()
                    for pattern in price_patterns:
                        match = re.search(pattern, text)
                        if match:
                            return match.group()
            except:
                continue
        
        # Fallback: search all text in container
        try:
            all_text = container.get_text()
            for pattern in price_patterns:
                match = re.search(pattern, all_text)
                if match:
                    return match.group()
        except:
            pass
        
        return ""
    
    def _extract_price_from_text(self, text: str) -> int:
        """Extract numeric price from text"""
        if not text:
            return 0
        
        try:
            # Remove Persian characters and keep only digits
            cleaned = re.sub(r'[^\d۰-۹,.]', '', text)
            
            # Convert Persian digits
            persian_digits = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', 
                             '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
            
            for persian, english in persian_digits.items():
                cleaned = cleaned.replace(persian, english)
            
            # Extract largest number
            numbers = re.findall(r'\d+', cleaned.replace(',', ''))
            if numbers:
                price = max(int(num) for num in numbers)
                
                # Convert to Toman if necessary
                if price < 1000:
                    price *= 1000000  # Convert millions to full number
                elif price < 100000:
                    price *= 1000    # Convert thousands to full number
                
                return price if price >= 10000 else 0
                
        except Exception as e:
            logger.warning(f"Error parsing price '{text}': {e}")
        
        return 0
    
    def _extract_image_url(self, container, base_url: str) -> str:
        """Extract image URL from container"""
        try:
            img = container.find('img')
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    if src.startswith('http'):
                        return src
                    else:
                        return urljoin(base_url, src)
        except:
            pass
        return ""
    
    def _extract_product_url(self, container, base_url: str) -> str:
        """Extract product URL from container"""
        try:
            link = container.find('a')
            if link:
                href = link.get('href')
                if href:
                    if href.startswith('http'):
                        return href
                    else:
                        return urljoin(base_url, href)
        except:
            pass
        return base_url
    
    def _extract_brand(self, title: str) -> str:
        """Extract brand from product title"""
        title_lower = title.lower()
        brands = [
            "samsung", "apple", "iphone", "xiaomi", "huawei", "lg", "sony", 
            "nokia", "oneplus", "oppo", "vivo", "realme", "honor", "asus",
            "سامسونگ", "اپل", "شیائومی", "هواوی", "ال‌جی"
        ]
        
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        words = title.split()
        return words[0] if words else "Unknown"
    
    def _create_result(self, success: bool, products: List[Dict], tool: str, 
                      start_time: datetime, errors: List[str]) -> ScrapingResult:
        """Create scraping result"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ScrapingResult(
            success=success,
            products_found=len(products),
            products=products,
            tool_used=tool,
            execution_time=execution_time,
            errors=errors,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_agent": "requests_aiohttp"
            }
        )

async def test_requests_scraper():
    """Test the requests scraper"""
    scraper = RequestsScraper()
    
    try:
        await scraper.init()
        
        # Test Iranian e-commerce sites
        test_urls = [
            "https://www.emalls.ir",
            "https://www.mobit.ir",
            "https://www.mobile.ir"
        ]
        
        for url in test_urls:
            print(f"\n🧪 Testing requests scraper on: {url}")
            result = await scraper.scrape_website(url)
            
            if result.success:
                print(f"✅ SUCCESS: Found {result.products_found} products")
                for product in result.products[:3]:
                    print(f"  📱 {product['title'][:50]}... - {product.get('price_toman', 0):,} تومان")
            else:
                print(f"❌ FAILED: {result.errors}")
            
            print(f"⏱️ Execution time: {result.execution_time:.2f}s")
    
    finally:
        await scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_requests_scraper())
