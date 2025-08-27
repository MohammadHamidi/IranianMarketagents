#!/usr/bin/env python3
"""
Selenium-based scraper for JavaScript-heavy Iranian e-commerce sites
Handles dynamic content loading and anti-bot measures
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from services.scraper.real_scraper import ProductData, ScrapingResult

logger = logging.getLogger(__name__)

@dataclass
class SeleniumScrapingConfig:
    """Configuration for Selenium scraping"""
    headless: bool = True
    wait_timeout: int = 10
    page_load_timeout: int = 30
    user_agent_rotation: bool = True
    proxy_rotation: bool = False
    anti_detection_measures: bool = True
    screenshot_on_error: bool = False

class IranianSeleniumScraper:
    """
    Advanced Selenium-based scraper for JavaScript-heavy Iranian e-commerce sites
    """

    def __init__(self, config: SeleniumScrapingConfig = None):
        self.config = config or SeleniumScrapingConfig()
        self.driver = None
        self.wait = None
        self.exchange_rate = 42000  # USD to Toman

        # Iranian e-commerce selectors for different sites
        self.selectors = {
            'digikala': {
                'product_container': '[data-product-index]',
                'title': '.d-block.pointer.text-dark-color',
                'price': '.d-flex.ai-center.jc-end.gap-1.color-700.text-h5',
                'url': 'a',
                'image': 'img',
                'next_page': '.pagination a:last-child'
            },
            'bazaar': {
                'product_container': '.product-item',
                'title': '.product-title',
                'price': '.price',
                'url': 'a',
                'image': '.product-image img',
                'next_page': '.pagination .next'
            },
            'torob': {
                'product_container': '.product-card',
                'title': '.product-name',
                'price': '.product-price',
                'url': '.product-link',
                'image': '.product-image',
                'next_page': '.load-more-btn'
            },
            'emalls': {
                'product_container': '.product-box',
                'title': '.product-title',
                'price': '.product-price',
                'url': '.product-link',
                'image': '.product-image img',
                'next_page': '.pagination .next'
            }
        }

        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]

    def _setup_driver(self):
        """Setup Chrome driver with anti-detection measures"""
        options = Options()

        if self.config.headless:
            options.add_argument('--headless')

        # Anti-detection measures
        if self.config.anti_detection_measures:
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

        # Random user agent
        if self.config.user_agent_rotation:
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')

        # Additional options for Iranian sites
        options.add_argument('--accept-lang=fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')

        # Create service and driver
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.wait = WebDriverWait(self.driver, self.config.wait_timeout)
        self.driver.set_page_load_timeout(self.config.page_load_timeout)

        logger.info("🚗 Chrome driver initialized with anti-detection measures")

    def _take_screenshot(self, filename: str):
        """Take screenshot for debugging"""
        if self.config.screenshot_on_error and self.driver:
            try:
                self.driver.save_screenshot(f"screenshots/{filename}")
                logger.info(f"📸 Screenshot saved: {filename}")
            except Exception as e:
                logger.warning(f"Failed to save screenshot: {e}")

    def _random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Add random delay to avoid detection"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _clean_price(self, price_text: str) -> int:
        """Extract numeric price from text"""
        import re
        if not price_text:
            return 0

        # Remove Persian numbers and convert to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        price_text = price_text.translate(persian_to_english)

        # Extract digits and commas
        match = re.search(r'[\d,]+', price_text.replace(',', ''))
        if match:
            return int(match.group(0).replace(',', ''))
        return 0

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc

    async def scrape_javascript_site(self, vendor: str, start_url: str, category: str = "mobile", max_products: int = 20) -> ScrapingResult:
        """
        Scrape JavaScript-heavy Iranian e-commerce site using Selenium
        """
        try:
            logger.info(f"🔍 Scraping {vendor} with Selenium: {start_url}")

            if not self.driver:
                self._setup_driver()

            products = []
            current_time = datetime.now(timezone.utc).isoformat()

            # Navigate to the site
            self.driver.get(start_url)
            self._random_delay(2, 4)

            # Wait for page to load and JavaScript to execute
            try:
                # Wait for body to be present (indicates page loaded)
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                logger.info(f"✅ Page loaded successfully for {vendor}")
            except TimeoutException:
                logger.warning(f"⚠️ Page load timeout for {vendor}, but continuing...")
                self._take_screenshot(f"{vendor}_timeout.png")

            # Try to detect the site type and get appropriate selectors
            domain = self._extract_domain(start_url)
            site_type = self._detect_site_type(domain)

            if site_type not in self.selectors:
                logger.warning(f"⚠️ Unknown site type for {domain}, using generic selectors")
                site_type = 'digikala'  # Fallback to Digikala selectors

            selectors = self.selectors[site_type]
            logger.info(f"🎯 Using selectors for site type: {site_type}")

            # Scroll down to load more products (common pattern for JS sites)
            self._scroll_to_load_products()

            # Extract products
            product_elements = []
            try:
                product_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors['product_container'])
                logger.info(f"📦 Found {len(product_elements)} product elements on {vendor}")
            except Exception as e:
                logger.warning(f"⚠️ Could not find product containers: {e}")
                self._take_screenshot(f"{vendor}_no_products.png")

            for i, element in enumerate(product_elements[:max_products]):
                try:
                    product_data = self._extract_product_data(element, selectors, vendor, current_time, i)
                    if product_data:
                        products.append(product_data)
                        logger.info(f"✅ Extracted product: {product_data.title}")

                except Exception as e:
                    logger.warning(f"⚠️ Error extracting product {i}: {e}")
                    continue

            logger.info(f"🎉 Successfully scraped {len(products)} products from {vendor}")

            return ScrapingResult(
                vendor=vendor,
                success=True,
                products_found=len(products),
                products=products
            )

        except Exception as e:
            logger.error(f"❌ Error scraping {vendor} with Selenium: {e}")
            self._take_screenshot(f"{vendor}_error.png")
            return ScrapingResult(
                vendor=vendor,
                success=False,
                products_found=0,
                products=[],
                error_message=str(e)
            )

    def _detect_site_type(self, domain: str) -> str:
        """Detect the type of Iranian e-commerce site"""
        site_mappings = {
            'digikala.com': 'digikala',
            'www.digikala.com': 'digikala',
            'bazaar.ir': 'bazaar',
            'www.bazaar.ir': 'bazaar',
            'torob.com': 'torob',
            'www.torob.com': 'torob',
            'emalls.ir': 'emalls',
            'www.emalls.ir': 'emalls'
        }
        return site_mappings.get(domain, 'digikala')

    def _scroll_to_load_products(self):
        """Scroll down to load more products on JavaScript-heavy sites"""
        try:
            # Scroll down multiple times to trigger lazy loading
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._random_delay(1, 2)

                # Try to click "load more" buttons if present
                try:
                    load_more_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".load-more, .load-more-btn, .show-more")
                    for button in load_more_buttons:
                        if button.is_displayed():
                            button.click()
                            self._random_delay(1, 2)
                            break
                except:
                    pass

        except Exception as e:
            logger.warning(f"⚠️ Error during scrolling: {e}")

    def _extract_product_data(self, element, selectors: Dict, vendor: str, current_time: str, index: int) -> Optional[ProductData]:
        """Extract product data from a single product element"""
        try:
            # Extract title
            title = ""
            try:
                title_element = element.find_element(By.CSS_SELECTOR, selectors['title'])
                title = title_element.text.strip()
            except:
                title = f"Product {index + 1}"

            # Extract Persian title (same as English for most sites)
            title_fa = title

            # Extract price
            price_toman = 0
            try:
                price_element = element.find_element(By.CSS_SELECTOR, selectors['price'])
                price_text = price_element.text.strip()
                price_toman = self._clean_price(price_text)
            except:
                pass

            # Extract URL
            product_url = ""
            try:
                url_element = element.find_element(By.CSS_SELECTOR, selectors['url'])
                href = url_element.get_attribute('href')
                if href:
                    product_url = urljoin(self.driver.current_url, href)
            except:
                pass

            # Extract image URL
            image_url = ""
            try:
                img_element = element.find_element(By.CSS_SELECTOR, selectors['image'])
                image_url = img_element.get_attribute('src') or img_element.get_attribute('data-src')
            except:
                pass

            # Skip if no price or title
            if price_toman == 0 or not title:
                return None

            # Calculate USD price
            price_usd = round(price_toman / self.exchange_rate, 2)

            # Generate product ID
            product_id = f"SEL{int(time.time())}{index}"

            return ProductData(
                product_id=product_id,
                title=title,
                title_fa=title_fa,
                price_toman=price_toman,
                price_usd=price_usd,
                vendor=vendor,
                vendor_name_fa=self._get_vendor_name_fa(vendor),
                availability=price_toman > 0,
                product_url=product_url,
                image_url=image_url,
                category="mobile",  # Will be expanded later
                last_updated=current_time
            )

        except Exception as e:
            logger.warning(f"⚠️ Error extracting product data: {e}")
            return None

    def _get_vendor_name_fa(self, vendor: str) -> str:
        """Get Persian name for vendor"""
        vendor_names = {
            'digikala.com': 'دیجی‌کالا',
            'bazaar.ir': 'بازار',
            'torob.com': 'ترب',
            'emalls.ir': 'ای‌مالز'
        }
        domain = self._extract_domain(vendor)
        return vendor_names.get(domain, vendor)

    def close(self):
        """Close the Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🛑 Selenium driver closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing driver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Async wrapper for easier use
class AsyncIranianSeleniumScraper:
    """Async wrapper for IranianSeleniumScraper"""

    def __init__(self, config: SeleniumScrapingConfig = None):
        self.config = config or SeleniumScrapingConfig()
        self.scraper = IranianSeleniumScraper(self.config)

    async def scrape_site(self, vendor: str, url: str, category: str = "mobile", max_products: int = 20) -> ScrapingResult:
        """Async wrapper for scraping"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.scraper.scrape_javascript_site, vendor, url, category, max_products)

    async def close(self):
        """Close the scraper"""
        if self.scraper:
            self.scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
