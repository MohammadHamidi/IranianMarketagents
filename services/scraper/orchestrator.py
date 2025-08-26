#!/usr/bin/env python3
"""
Iranian E-commerce Scraping Orchestrator
Custom system replicating Bright Data's approach without complex proxy management
Focused on Iranian sites with intelligent scraping method selection
"""

import asyncio
import aiohttp
import time
import json
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # ✅ correct package
import logging
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScrapingMethod(Enum):
    SIMPLE_HTTP = "simple_http"          # Basic requests for simple sites
    SELENIUM_BASIC = "selenium_basic"    # Selenium for JS sites
    UNDETECTED = "undetected"           # Undetected Chrome for tough sites

class SiteComplexity(Enum):
    SIMPLE = 1      # Static HTML, minimal JS
    MODERATE = 2    # Some JS, but mostly server-rendered
    COMPLEX = 3     # Heavy JS, SPA-like behavior
    VERY_COMPLEX = 4 # Advanced anti-bot, complex interactions

@dataclass
class SiteConfig:
    domain: str
    base_urls: List[str]
    complexity: SiteComplexity
    preferred_method: ScrapingMethod
    selectors: Dict[str, str]
    pagination_config: Dict
    rate_limit_delay: Tuple[int, int]  # (min, max) seconds
    custom_headers: Dict[str, str]
    requires_cookies: bool = False
    has_captcha: bool = False
    market_share: float = 0.0  # Priority weighting

@dataclass
class ScrapingResult:
    url: str
    method_used: ScrapingMethod
    success: bool
    response_time: float
    products_found: int
    data: List[Dict]
    error_message: Optional[str] = None
    retry_count: int = 0

class IranianScrapingOrchestrator:
    """
    Main orchestrator that replicates Bright Data's intelligent scraping approach
    """
    
    def __init__(self):
        self.site_configs = self._load_iranian_site_configs()
        self.session_pools: Dict[str, aiohttp.ClientSession] = {}
        self.performance_stats = {}
        self.blocked_domains = set()
        
        # Iranian market user agents (realistic for Iranian users)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        ]

    # ✅ Async factory so we can await session pool init safely
    @classmethod
    async def create(cls) -> "IranianScrapingOrchestrator":
        self = cls()
        await self._initialize_session_pools()
        return self
    
    def _load_iranian_site_configs(self) -> Dict[str, SiteConfig]:
        """Load configurations for major Iranian e-commerce sites"""
        return {
            'digikala.com': SiteConfig(
                domain='digikala.com',
                base_urls=[
                    'https://www.digikala.com/categories/mobile-phone/',
                    'https://www.digikala.com/categories/laptop-notebook/',
                    'https://www.digikala.com/categories/tablet/'
                ],
                complexity=SiteComplexity.MODERATE,
                preferred_method=ScrapingMethod.SELENIUM_BASIC,
                selectors={
                    'product_list': '[data-cro-id="product-list"] article, .product-list_ProductList__item',
                    'product_title': '[data-cro-id="product-box-title"], .product-title_ProductTitle__title',
                    'product_price': '[data-cro-id="price-final"], .product-price_ProductPrice__price',
                    'product_link': 'a[href*="/product/"]',
                    'product_image': 'img',
                    'pagination_next': 'a[rel="next"], .pagination .next-page',
                    'availability': '[data-cro-id="availability"]'
                },
                pagination_config={
                    'type': 'infinite_scroll',
                    'scroll_pause': 2,
                    'max_pages': 40
                },
                rate_limit_delay=(2, 5),
                custom_headers={
                    'Accept-Language': 'fa-IR,fa;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                },
                requires_cookies=True,
                market_share=0.6  # Largest Iranian e-commerce
            ),
            
            'technolife.ir': SiteConfig(
                domain='technolife.ir',
                base_urls=[
                    'https://technolife.ir/product_cat/mobile-tablet/',
                    'https://technolife.ir/product_cat/laptop-computer/',
                ],
                complexity=SiteComplexity.SIMPLE,
                preferred_method=ScrapingMethod.SIMPLE_HTTP,
                selectors={
                    'product_list': '.product-item, li.product',
                    'product_title': '.product-title, h2.woocommerce-loop-product__title',
                    'product_price': '.price, .product-price .price',
                    'product_link': 'a.product-link, a.woocommerce-LoopProduct-link',
                    'product_image': '.product-image img, img.wp-post-image',
                    'pagination_next': '.pagination .next, a.next',
                    'availability': '.stock, .stock-status'
                },
                pagination_config={
                    'type': 'numbered_pages',
                    'max_pages': 20,
                    'url_pattern': '?paged={page}'
                },
                rate_limit_delay=(1, 3),
                custom_headers={
                    'Accept-Language': 'fa-IR,fa;q=0.9',
                    'Referer': 'https://technolife.ir/'
                },
                market_share=0.15
            ),
            
            'mobile.ir': SiteConfig(
                domain='mobile.ir',
                base_urls=['https://mobile.ir/phone'],
                complexity=SiteComplexity.COMPLEX,
                preferred_method=ScrapingMethod.UNDETECTED,
                selectors={
                    'product_list': '.product, .product-grid .product',
                    'product_title': '.product-name, h3 a',
                    'product_price': '.final-price, .product-price',
                    'product_link': 'a[href*="/product/"], a.product-url',
                    'product_image': 'img',
                    'load_more': '.load-more, .load-more-button'
                },
                pagination_config={
                    'type': 'load_more_button',
                    'max_clicks': 8
                },
                rate_limit_delay=(3, 7),
                custom_headers={
                    'Accept-Language': 'fa-IR,fa;q=0.9,en;q=0.8'
                },
                has_captcha=True,
                market_share=0.08
            ),
            
            'emalls.ir': SiteConfig(
                domain='emalls.ir',
                base_urls=['https://emalls.ir/categories/mobile','https://emalls.ir/categories/laptop'],
                complexity=SiteComplexity.SIMPLE,
                preferred_method=ScrapingMethod.SIMPLE_HTTP,
                selectors={
                    'product_list': '.product-item, .product-list .product-item',
                    'product_title': '.product-title a',
                    'product_price': '.product-price, .price',
                    'product_link': '.product-title a',
                    'product_image': '.product-image img'
                },
                pagination_config={
                    'type': 'numbered_pages',
                    'max_pages': 15
                },
                rate_limit_delay=(1, 3),
                custom_headers={},
                market_share=0.05
            ),
        }
    
    async def _initialize_session_pools(self):
        """Initialize different session pools for different scraping methods"""
        
        # HTTP Session Pool for simple requests
        connector = aiohttp.TCPConnector(
            limit=100,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session_pools['http'] = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fa-IR,fa;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
    
    def _get_selenium_driver(self, undetected: bool = False) -> webdriver.Chrome:
        """Create Selenium Chrome driver with Iranian-friendly settings"""
        
        if undetected:
            options = uc.ChromeOptions()
        else:
            options = Options()
        
        # Iranian-friendly Chrome options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--lang=fa-IR')
        options.add_argument('--accept-lang=fa-IR,fa,en')
        
        # Set Iranian timezone and locale
        prefs = {
            'intl.accept_languages': 'fa-IR,fa,en-US,en',
            'profile.default_content_setting_values.geolocation': 2
        }
        options.add_experimental_option('prefs', prefs)
        
        # Random user agent
        options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
        
        if undetected:
            driver = uc.Chrome(options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        # Safe CDP calls
        try:
            driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'Asia/Tehran'})
            driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 35.6892,  # Tehran
                'longitude': 51.3890,
                'accuracy': 100
            })
        except Exception:
            pass
        
        return driver
    
    async def scrape_with_simple_http(self, site_config: SiteConfig, urls: List[str]) -> List[ScrapingResult]:
        """Simple HTTP scraping for basic sites"""
        
        results = []
        session = self.session_pools['http']
        
        for url in urls:
            start_time = time.time()
            
            try:
                # Add custom headers for this site
                headers = {**session.headers}
                headers.update(site_config.custom_headers)
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract products using selectors
                        products = self._extract_products_with_selectors(soup, site_config, url)
                        
                        # Try JSON-LD fallback if empty
                        if not products:
                            products = self._extract_from_jsonld(soup, site_config, url)
                        
                        result = ScrapingResult(
                            url=url,
                            method_used=ScrapingMethod.SIMPLE_HTTP,
                            success=True,
                            response_time=time.time() - start_time,
                            products_found=len(products),
                            data=products
                        )
                        
                    else:
                        result = ScrapingResult(
                            url=url,
                            method_used=ScrapingMethod.SIMPLE_HTTP,
                            success=False,
                            response_time=time.time() - start_time,
                            products_found=0,
                            data=[],
                            error_message=f"HTTP {response.status}"
                        )
                
                results.append(result)
                
                # Rate limiting
                delay = random.uniform(*site_config.rate_limit_delay)
                await asyncio.sleep(delay)
                
            except Exception as e:
                result = ScrapingResult(
                    url=url,
                    method_used=ScrapingMethod.SIMPLE_HTTP,
                    success=False,
                    response_time=time.time() - start_time,
                    products_found=0,
                    data=[],
                    error_message=str(e)
                )
                results.append(result)
                logger.error(f"Simple HTTP scraping failed for {url}: {e}")
        
        return results
    
    def scrape_with_selenium(self, site_config: SiteConfig, urls: List[str], undetected: bool = False) -> List[ScrapingResult]:
        """Selenium scraping for JS-heavy sites"""
        
        results = []
        driver = None
        
        try:
            driver = self._get_selenium_driver(undetected=undetected)
            wait = WebDriverWait(driver, 15)
            
            for url in urls:
                start_time = time.time()
                
                try:
                    driver.get(url)
                    
                    # Wait for products to load
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, site_config.selectors['product_list'])))
                    
                    # Handle pagination if configured
                    if site_config.pagination_config['type'] == 'infinite_scroll':
                        self._handle_infinite_scroll(driver, site_config)
                    elif site_config.pagination_config['type'] == 'load_more_button':
                        self._handle_load_more_button(driver, site_config)
                    
                    # Extract products
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    products = self._extract_products_with_selectors(soup, site_config, url)
                    
                    if not products:
                        products = self._extract_from_jsonld(soup, site_config, url)
                    
                    result = ScrapingResult(
                        url=url,
                        method_used=ScrapingMethod.UNDETECTED if undetected else ScrapingMethod.SELENIUM_BASIC,
                        success=True,
                        response_time=time.time() - start_time,
                        products_found=len(products),
                        data=products
                    )
                    
                    results.append(result)
                    
                    # Rate limiting
                    delay = random.uniform(*site_config.rate_limit_delay)
                    time.sleep(delay)
                    
                except Exception as e:
                    result = ScrapingResult(
                        url=url,
                        method_used=ScrapingMethod.UNDETECTED if undetected else ScrapingMethod.SELENIUM_BASIC,
                        success=False,
                        response_time=time.time() - start_time,
                        products_found=0,
                        data=[],
                        error_message=str(e)
                    )
                    results.append(result)
                    logger.error(f"Selenium scraping failed for {url}: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        return results
    
    def _handle_infinite_scroll(self, driver, site_config: SiteConfig):
        """Handle infinite scroll pagination"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause_time = site_config.pagination_config.get('scroll_pause', 2)
        max_scrolls = site_config.pagination_config.get('max_pages', 10)
        
        for _ in range(max_scrolls):
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new products to load
            time.sleep(scroll_pause_time)
            
            # Calculate new scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break  # No more content
            
            last_height = new_height
    
    def _handle_load_more_button(self, driver, site_config: SiteConfig):
        """Handle load more button pagination"""
        max_clicks = site_config.pagination_config.get('max_clicks', 5)
        load_more_selector = site_config.selectors.get('load_more', '.load-more')
        
        for _ in range(max_clicks):
            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, load_more_selector)
                if load_more_button.is_displayed() and load_more_button.is_enabled():
                    driver.execute_script("arguments[0].click();", load_more_button)
                    time.sleep(3)  # Wait for content to load
                else:
                    break  # No more button or disabled
            except Exception:
                break  # Button not found
    
    def _extract_products_with_selectors(self, soup: BeautifulSoup, site_config: SiteConfig, source_url: str) -> List[Dict]:
        """Extract product data using CSS selectors"""
        
        products = []
        selectors = site_config.selectors
        
        # Find all product containers
        product_elements = soup.select(selectors['product_list'])
        
        for element in product_elements:
            try:
                # Extract basic product information
                title_elem = element.select_one(selectors.get('product_title', ''))
                price_elem = element.select_one(selectors.get('product_price', ''))
                link_elem = element.select_one(selectors.get('product_link', ''))
                image_elem = element.select_one(selectors.get('product_image', ''))
                availability_elem = element.select_one(selectors.get('availability', ''))
                
                # Build product data
                product = {
                    'title': title_elem.get_text(strip=True) if title_elem else '',
                    'title_persian': title_elem.get_text(strip=True) if title_elem else '',  # Same for Iranian sites
                    'price_text': price_elem.get_text(strip=True) if price_elem else '',
                    'product_url': self._resolve_url(link_elem.get('href') if link_elem else '', source_url),
                    'image_url': self._resolve_url(image_elem.get('src') if image_elem else '', source_url),
                    'availability_text': availability_elem.get_text(strip=True) if availability_elem else '',
                    'vendor': site_config.domain,
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'source_url': source_url
                }
                
                # Process price
                if product['price_text']:
                    product.update(self._parse_iranian_price(product['price_text']))
                
                # Process availability
                product['availability'] = self._parse_availability(product['availability_text'])
                
                # Only add if we have minimum required data
                if product['title'] and (product.get('price_irr') or product.get('price_toman')):
                    products.append(product)
                    
            except Exception as e:
                logger.warning(f"Failed to extract product from element: {e}")
                continue
        
        return products
    
    def _extract_from_jsonld(self, soup: BeautifulSoup, site_config: SiteConfig, source_url: str) -> List[Dict]:
        """Fallback: parse Product schema from JSON-LD."""
        out: List[Dict] = []
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or "{}")
                items = data if isinstance(data, list) else [data]
                for it in items:
                    if it.get('@type') in ('Product', 'Offer', 'AggregateOffer') or 'offers' in it:
                        title = it.get('name') or ''
                        offers = it.get('offers') or {}
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price_text = str(offers.get('price', '')) if offers else ''
                        url = it.get('url') or source_url
                        image = it.get('image') or ''
                        availability_text = (offers.get('availability','') if offers else '')
                        product = {
                            'title': title,
                            'title_persian': title,
                            'price_text': price_text,
                            'product_url': self._resolve_url(url, source_url),
                            'image_url': image if isinstance(image, str) else (image[0] if isinstance(image, list) and image else ''),
                            'availability_text': availability_text,
                            'vendor': site_config.domain,
                            'scraped_at': datetime.now(timezone.utc).isoformat(),
                            'source_url': source_url
                        }
                        if product['price_text']:
                            product.update(self._parse_iranian_price(product['price_text']))
                        product['availability'] = self._parse_availability(product['availability_text'])
                        if product['title'] and (product.get('price_irr') or product.get('price_toman')):
                            out.append(product)
            except Exception:
                continue
        return out
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs"""
        if not url:
            return ''
        
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
        else:
            return urljoin(base_url, url)
    
    def _parse_iranian_price(self, price_text: str) -> Dict:
        """Parse Iranian price text and extract Rial/Toman amounts"""
        
        # Remove Persian/Arabic digits and convert to English
        english_text = self._persian_to_english_digits(price_text)
        
        # Extract numbers
        numbers = re.findall(r'[\d,]+', english_text.replace(',', ''))
        
        result = {
            'price_irr': None,
            'price_toman': None,
            'original_currency': 'IRR'
        }
        
        if numbers:
            price = int(numbers[0].replace(',', ''))
            
            # Detect if it's Toman or Rial based on context
            if 'تومان' in price_text or 'تومن' in price_text:
                result['price_toman'] = price
                result['price_irr'] = price * 10
            else:
                # Assume Rial if no currency specified, but check magnitude
                if price < 1000000:  # Likely Toman
                    result['price_toman'] = price
                    result['price_irr'] = price * 10
                else:  # Likely Rial
                    result['price_irr'] = price
                    result['price_toman'] = price // 10
        
        return result
    
    def _persian_to_english_digits(self, text: str) -> str:
        """Convert Persian/Arabic digits to English"""
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        english_digits = '0123456789'
        
        translation_table = str.maketrans(
            persian_digits + arabic_digits,
            english_digits + english_digits
        )
        
        return text.translate(translation_table)
    
    def _parse_availability(self, availability_text: str) -> bool:
        """Parse availability text"""
        if not availability_text:
            return True  # Assume available if not specified
        
        availability_text = availability_text.lower()
        
        # Persian availability indicators
        unavailable_indicators = [
            'ناموجود', 'تمام شده', 'out of stock', 'unavailable',
            'اتمام موجودی', 'موجود نیست'
        ]
        
        available_indicators = [
            'موجود', 'available', 'in stock', 'آماده ارسال'
        ]
        
        for indicator in unavailable_indicators:
            if indicator in availability_text:
                return False
        
        for indicator in available_indicators:
            if indicator in availability_text:
                return True
        
        return True  # Default to available
    
    async def execute_comprehensive_crawl(self) -> Dict[str, List[ScrapingResult]]:
        """Execute comprehensive crawl of all Iranian e-commerce sites"""
        
        logger.info("🚀 Starting comprehensive Iranian e-commerce crawl")
        
        all_results = {}
        
        # Sort sites by market share (priority)
        sorted_sites = sorted(
            self.site_configs.items(),
            key=lambda x: x[1].market_share,
            reverse=True
        )
        
        for domain, site_config in sorted_sites:
            logger.info(f"🎯 Crawling {domain} (Market Share: {site_config.market_share*100:.1f}%)")
            
            try:
                # Select appropriate scraping method
                method = site_config.preferred_method
                
                if method == ScrapingMethod.SIMPLE_HTTP:
                    results = await self.scrape_with_simple_http(site_config, site_config.base_urls)
                
                elif method == ScrapingMethod.SELENIUM_BASIC:
                    results = self.scrape_with_selenium(site_config, site_config.base_urls, undetected=False)
                
                elif method == ScrapingMethod.UNDETECTED:
                    results = self.scrape_with_selenium(site_config, site_config.base_urls, undetected=True)
                
                all_results[domain] = results
                
                # Log results
                total_products = sum(r.products_found for r in results)
                successful_requests = sum(1 for r in results if r.success)
                
                logger.info(f"✅ {domain}: {total_products} products from {successful_requests}/{len(results)} successful requests")
                
            except Exception as e:
                logger.error(f"❌ {domain}: Crawl failed - {e}")
                all_results[domain] = []
        
        # Summary
        total_products = sum(
            sum(r.products_found for r in results) 
            for results in all_results.values()
        )
        
        logger.info(f"📊 Crawl completed: {total_products} total products from {len(all_results)} sites")
        
        return all_results
    
    async def close(self):
        """Clean up resources"""
        for session in self.session_pools.values():
            if hasattr(session, 'close'):
                await session.close()

# ✅ New proper entrypoint
async def main():
    orchestrator = await IranianScrapingOrchestrator.create()  # await factory
    try:
        results = await orchestrator.execute_comprehensive_crawl()
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        with open(f'iranian_crawl_results_{ts}.json', 'w', encoding='utf-8') as f:
            json.dump({d: [asdict(r) for r in rs] for d, rs in results.items()}, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"💾 Results saved to iranian_crawl_results_{ts}.json")
    finally:
        await orchestrator.close()

if __name__ == "__main__":
    asyncio.run(main())