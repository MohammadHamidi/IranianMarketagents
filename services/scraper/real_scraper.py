#!/usr/bin/env python3
"""
Real Iranian E-commerce Scraper
Performs actual web scraping from Iranian e-commerce sites
"""

import asyncio
import aiohttp
import json
import logging
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    product_id: str
    title: str
    title_fa: str
    price_toman: int
    price_usd: float
    vendor: str
    vendor_name_fa: str
    availability: bool
    product_url: str
    image_url: str = ""
    category: str = "mobile"
    last_updated: str = ""

@dataclass
class ScrapingResult:
    vendor: str
    success: bool
    products_found: int
    products: List[ProductData]
    error_message: Optional[str] = None

class IranianWebScraper:
    """
    Real working scraper for Iranian e-commerce sites that actually performs web requests
    """
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        self.session = None
        self.headers = {
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        self.currency_pattern = re.compile(r'[\d,]+')
        self.exchange_rate = 42000  # USD to Toman
    
    @classmethod
    async def create(cls) -> "IranianWebScraper":
        scraper = cls()
        scraper.session = aiohttp.ClientSession()
        return scraper
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def _clean_price(self, price_text):
        """Extract numeric price from text with commas, currency symbols etc."""
        if not price_text:
            return 0
        
        # Extract digits and commas
        match = self.currency_pattern.search(price_text)
        if not match:
            return 0
        
        # Remove commas and convert to int
        try:
            return int(match.group(0).replace(',', ''))
        except ValueError:
            return 0
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def scrape_digikala_mobile(self) -> ScrapingResult:
        """Scrape Digikala mobile phones with real web requests"""
        try:
            logger.info("🔍 Scraping Digikala mobile phones...")
            
            products = []
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Set a random user agent for this request
            headers = self.headers.copy()
            headers["User-Agent"] = self._get_random_user_agent()
            
            # Make a request to Digikala's mobile phone category
            url = "https://www.digikala.com/search/category-mobile-phone/"
            logger.info(f"Requesting URL: {url}")
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Digikala: HTTP {response.status}")
                    return ScrapingResult(
                        vendor="digikala.com",
                        success=False,
                        products_found=0,
                        products=[],
                        error_message=f"HTTP error: {response.status}"
                    )
                
                html = await response.text()
                logger.info(f"Successfully fetched {len(html)} bytes from Digikala")
                
                # Parse the HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find product cards
                product_cards = soup.select('div[data-product-index]')
                logger.info(f"Found {len(product_cards)} product cards on Digikala")
                
                for i, card in enumerate(product_cards[:10]):  # Limit to 10 products
                    try:
                        # Extract product details
                        title_element = card.select_one('.d-block.pointer.text-dark-color')
                        title = title_element.text.strip() if title_element else f"Unknown Product {i+1}"
                        
                        # Try to extract Persian title, fall back to the same title
                        title_fa = title
                        
                        # Extract price
                        price_element = card.select_one('.d-flex.ai-center.jc-end.gap-1.color-700.text-h5')
                        price_text = price_element.text.strip() if price_element else "0"
                        price_toman = self._clean_price(price_text)
                        
                        # Extract product URL and ID
                        link_element = card.select_one('a')
                        product_url = f"https://www.digikala.com{link_element['href']}" if link_element and 'href' in link_element.attrs else ""
                        product_id = f"DK{str(uuid.uuid4())[:8]}"
                        
                        # Extract image URL
                        img_element = card.select_one('img')
                        image_url = img_element['src'] if img_element and 'src' in img_element.attrs else ""
                        
                        # Calculate USD price
                        price_usd = round(price_toman / self.exchange_rate, 2)
                        
                        # Create ProductData object
                        product = ProductData(
                            product_id=product_id,
                            title=title,
                            title_fa=title_fa,
                            price_toman=price_toman,
                            price_usd=price_usd,
                            vendor="digikala.com",
                            vendor_name_fa="دیجی‌کالا",
                            availability=price_toman > 0,
                            product_url=product_url,
                            image_url=image_url,
                            category="mobile",
                            last_updated=current_time
                        )
                        products.append(product)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Digikala product card: {e}")
                        continue
            
            logger.info(f"✅ Digikala: Successfully scraped {len(products)} real mobile products")
            return ScrapingResult(
                vendor="digikala.com",
                success=True,
                products_found=len(products),
                products=products
            )
            
        except Exception as e:
            logger.error(f"❌ Error scraping Digikala: {e}")
            return ScrapingResult(
                vendor="digikala.com",
                success=False,
                products_found=0,
                products=[],
                error_message=str(e)
            )
    
    async def scrape_technolife_mobile(self) -> ScrapingResult:
        """Scrape Technolife mobile phones with real web requests"""
        try:
            logger.info("🔍 Scraping Technolife mobile phones...")
            
            products = []
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Set a random user agent for this request
            headers = self.headers.copy()
            headers["User-Agent"] = self._get_random_user_agent()
            
            # Make a request to Technolife's mobile phone category
            url = "https://www.technolife.ir/product/list/164_13956_45/گوشی-موبایل"
            logger.info(f"Requesting URL: {url}")
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Technolife: HTTP {response.status}")
                    return ScrapingResult(
                        vendor="technolife.ir",
                        success=False,
                        products_found=0,
                        products=[],
                        error_message=f"HTTP error: {response.status}"
                    )
                
                html = await response.text()
                logger.info(f"Successfully fetched {len(html)} bytes from Technolife")
                
                # Parse the HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find product cards
                product_cards = soup.select('.product-box.product-small')
                logger.info(f"Found {len(product_cards)} product cards on Technolife")
                
                for i, card in enumerate(product_cards[:10]):  # Limit to 10 products
                    try:
                        # Extract product details
                        title_element = card.select_one('.font-12.text-truncate.line-height-1')
                        title = title_element.text.strip() if title_element else f"Unknown Product {i+1}"
                        
                        # Try to extract Persian title
                        title_fa = title  # Same as title for Technolife
                        
                        # Extract price
                        price_element = card.select_one('.rounded-right.bg-gray-dark.text-gray-dark-main.p-1.font-13')
                        price_text = price_element.text.strip() if price_element else "0"
                        price_toman = self._clean_price(price_text)
                        
                        # Extract product URL and ID
                        link_element = card.select_one('a')
                        product_url = link_element['href'] if link_element and 'href' in link_element.attrs else ""
                        product_id = f"TL{str(uuid.uuid4())[:8]}"
                        
                        # Extract image URL
                        img_element = card.select_one('img')
                        image_url = img_element['src'] if img_element and 'src' in img_element.attrs else ""
                        
                        # Calculate USD price
                        price_usd = round(price_toman / self.exchange_rate, 2)
                        
                        # Create ProductData object
                        product = ProductData(
                            product_id=product_id,
                            title=title,
                            title_fa=title_fa,
                            price_toman=price_toman,
                            price_usd=price_usd,
                            vendor="technolife.ir",
                            vendor_name_fa="تکنولایف",
                            availability=price_toman > 0,
                            product_url=product_url,
                            image_url=image_url,
                            category="mobile",
                            last_updated=current_time
                        )
                        products.append(product)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Technolife product card: {e}")
                        continue
            
            logger.info(f"✅ Technolife: Successfully scraped {len(products)} real mobile products")
            return ScrapingResult(
                vendor="technolife.ir",
                success=True,
                products_found=len(products),
                products=products
            )
            
        except Exception as e:
            logger.error(f"❌ Error scraping Technolife: {e}")
            return ScrapingResult(
                vendor="technolife.ir",
                success=False,
                products_found=0,
                products=[],
                error_message=str(e)
            )
    
    async def scrape_meghdadit_mobile(self) -> ScrapingResult:
        """Scrape MeghdadIT mobile phones with real web requests"""
        try:
            logger.info("🔍 Scraping MeghdadIT mobile phones...")
            
            products = []
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Set a random user agent for this request
            headers = self.headers.copy()
            headers["User-Agent"] = self._get_random_user_agent()
            
            # Make a request to MeghdadIT's mobile phone category
            url = "https://meghdadit.com/product-category/mobile/mobile-phones/"
            logger.info(f"Requesting URL: {url}")
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch MeghdadIT: HTTP {response.status}")
                    return ScrapingResult(
                        vendor="meghdadit.com",
                        success=False,
                        products_found=0,
                        products=[],
                        error_message=f"HTTP error: {response.status}"
                    )
                
                html = await response.text()
                logger.info(f"Successfully fetched {len(html)} bytes from MeghdadIT")
                
                # Parse the HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find product cards
                product_cards = soup.select('li.product')
                logger.info(f"Found {len(product_cards)} product cards on MeghdadIT")
                
                for i, card in enumerate(product_cards[:10]):  # Limit to 10 products
                    try:
                        # Extract product details
                        title_element = card.select_one('h2.woocommerce-loop-product__title')
                        title = title_element.text.strip() if title_element else f"Unknown Product {i+1}"
                        
                        # Try to extract Persian title, fall back to the same title
                        title_fa = title
                        
                        # Extract price
                        price_element = card.select_one('span.price')
                        price_text = price_element.text.strip() if price_element else "0"
                        price_toman = self._clean_price(price_text)
                        
                        # Extract product URL and ID
                        link_element = card.select_one('a.woocommerce-LoopProduct-link')
                        product_url = link_element['href'] if link_element and 'href' in link_element.attrs else ""
                        product_id = f"MI{str(uuid.uuid4())[:8]}"
                        
                        # Extract image URL
                        img_element = card.select_one('img')
                        image_url = img_element['src'] if img_element and 'src' in img_element.attrs else ""
                        
                        # Calculate USD price
                        price_usd = round(price_toman / self.exchange_rate, 2)
                        
                        # Create ProductData object
                        product = ProductData(
                            product_id=product_id,
                            title=title,
                            title_fa=title_fa,
                            price_toman=price_toman,
                            price_usd=price_usd,
                            vendor="meghdadit.com",
                            vendor_name_fa="مقداد آی‌تی",
                            availability=price_toman > 0,
                            product_url=product_url,
                            image_url=image_url,
                            category="mobile",
                            last_updated=current_time
                        )
                        products.append(product)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing MeghdadIT product card: {e}")
                        continue
            
            logger.info(f"✅ MeghdadIT: Successfully scraped {len(products)} real mobile products")
            return ScrapingResult(
                vendor="meghdadit.com",
                success=True,
                products_found=len(products),
                products=products
            )
            
        except Exception as e:
            logger.error(f"❌ Error scraping MeghdadIT: {e}")
            return ScrapingResult(
                vendor="meghdadit.com",
                success=False,
                products_found=0,
                products=[],
                error_message=str(e)
            )
    
    async def run_scraping_cycle(self) -> List[ScrapingResult]:
        """Run a complete scraping cycle across all Iranian vendors"""
        logger.info("🚀 Starting REAL Iranian e-commerce scraping cycle...")
        
        results = []
        
        # Scrape Digikala
        logger.info("🏪 Scraping Digikala...")
        digikala_result = await self.scrape_digikala_mobile()
        results.append(digikala_result)
        
        # Add delay between scrapes to be respectful
        await asyncio.sleep(2)
        
        # Scrape Technolife
        logger.info("🏪 Scraping Technolife...")
        technolife_result = await self.scrape_technolife_mobile()
        results.append(technolife_result)
        
        # Add delay between scrapes
        await asyncio.sleep(2)
        
        # Scrape MeghdadIT
        logger.info("🏪 Scraping MeghdadIT...")
        meghdadit_result = await self.scrape_meghdadit_mobile()
        results.append(meghdadit_result)
        
        # Summary
        total_products = sum(r.products_found for r in results if r.success)
        successful_vendors = sum(1 for r in results if r.success)
        
        logger.info("📊 " + "="*50)
        logger.info(f"📊 Scraping cycle completed!")
        logger.info(f"📊 Total products found: {total_products}")
        logger.info(f"📊 Successful vendors: {successful_vendors}/{len(results)}")
        logger.info("📊 " + "="*50)
        
        return results

# Main entry point
async def main():
    """Run the real Iranian web scraper"""
    scraper = await IranianWebScraper.create()
    try:
        results = await scraper.run_scraping_cycle()
        
        # Save results to JSON file
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f'iranian_scraping_results_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(result) for result in results], f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
