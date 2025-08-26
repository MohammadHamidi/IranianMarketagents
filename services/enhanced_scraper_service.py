from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
import json
from typing import Dict, List, Optional
import logging
from .search_service import SearXNGSearchService

class EnhancedScraperService:
    """
    Enhanced scraper that uses SearXNG for discovery but maintains
    existing scraping capabilities
    """
    
    def __init__(self, searxng_url: str = "http://87.236.166.7:8080"):
        self.search_service = None
        self.searxng_url = searxng_url
        self.logger = logging.getLogger(__name__)
        
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver for scraping (unchanged)"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        return webdriver.Chrome(options=chrome_options)
    
    async def discover_and_scrape_products(
        self, 
        product_name: str, 
        categories: List[str] = None
    ) -> List[Dict]:
        """
        Complete workflow: Discovery via SearXNG + Scraping
        """
        results = []
        
        # 1. Use SearXNG for discovery
        async with SearXNGSearchService(self.searxng_url) as search_service:
            discovered_sources = await search_service.search_iranian_products(
                product_name, 
                categories
            )
        
        # 2. Scrape discovered sources
        driver = self.setup_driver()
        
        try:
            for source in discovered_sources:
                scraped_data = await self.scrape_product_page(
                    driver, 
                    source['url'], 
                    product_name
                )
                
                if scraped_data:
                    # Combine discovery metadata with scraped data
                    scraped_data.update({
                        'discovery_source': 'searxng',
                        'relevance_score': source['relevance_score'],
                        'original_title': source['title']
                    })
                    results.append(scraped_data)
                    
        finally:
            driver.quit()
        
        return results
    
    async def scrape_product_page(
        self, 
        driver: webdriver.Chrome, 
        url: str, 
        product_name: str
    ) -> Optional[Dict]:
        """
        Scrape individual product page (maintain existing logic)
        """
        try:
            driver.get(url)
            await asyncio.sleep(2)  # Wait for page load
            
            # Generic selectors for Iranian marketplaces
            price_selectors = [
                ".price", ".product-price", ".price-current",
                "[class*='price']", "[data-testid*='price']",
                ".toman", ".rial"  # Persian currency indicators
            ]
            
            title_selectors = [
                "h1", ".product-title", ".product-name",
                "[data-testid*='title']", ".title"
            ]
            
            # Extract product information
            product_data = {
                'url': url,
                'product_name': product_name,
                'scraped_at': asyncio.get_event_loop().time(),
                'source_domain': self._extract_domain(url)
            }
            
            # Extract title
            for selector in title_selectors:
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, selector)
                    product_data['title'] = title_element.text.strip()
                    break
                except:
                    continue
            
            # Extract price
            for selector in price_selectors:
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_element.text.strip()
                    product_data['price_raw'] = price_text
                    product_data['price_numeric'] = self._extract_numeric_price(price_text)
                    break
                except:
                    continue
            
            return product_data if 'title' in product_data else None
            
        except Exception as e:
            self.logger.error(f"Scraping error for {url}: {str(e)}")
            return None
    
    def _extract_numeric_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from Persian/English text"""
        import re
        
        # Remove Persian/Arabic numerals and convert to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        price_text = price_text.translate(persian_to_english)
        
        # Extract numbers
        numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', price_text.replace(',', ''))
        
        if numbers:
            try:
                return float(numbers[-1])  # Usually the last number is the price
            except ValueError:
                return None
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
