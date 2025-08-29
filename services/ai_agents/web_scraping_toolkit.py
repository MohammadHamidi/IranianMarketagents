#!/usr/bin/env python3
"""
AI Agent Web Scraping Toolkit - State of the Art
Autonomous tools for AI agents to discover, analyze, and scrape any website
"""

import asyncio
import aiohttp
import json
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import redis.asyncio as redis
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from enhanced_driver_manager import driver_manager

# Import requests-based scraper as fallback
try:
    from requests_scraper import RequestsScraper
    REQUESTS_SCRAPER_AVAILABLE = True
except ImportError:
    REQUESTS_SCRAPER_AVAILABLE = False
    RequestsScraper = None

logger = logging.getLogger(__name__)

@dataclass
class WebsiteAnalysis:
    """Analysis result for a website"""
    domain: str
    website_type: str  # "spa", "traditional", "api", "protected"
    ecommerce_confidence: float  # 0.0 to 1.0
    product_selectors: Dict[str, str]
    pagination_info: Dict[str, Any]
    anti_bot_measures: List[str]
    recommended_tools: List[str]
    api_endpoints: List[str]
    content_language: str
    currency_detected: str

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

class WebsiteAnalyzer:
    """AI tool for analyzing websites to determine best scraping approach"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    async def init(self):
        """Initialize HTTP session"""
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        timeout = aiohttp.ClientTimeout(total=20)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def analyze_website(self, url: str) -> WebsiteAnalysis:
        """Analyze a website to determine optimal scraping strategy"""
        domain = urlparse(url).netloc

        try:
            # Use Iranian SSL config for Iranian sites
            if self._is_iranian_domain(domain):
                html = await self._analyze_iranian_site_with_fallbacks(url, domain)
            else:
                async with self.session.get(url) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            # Add status check for regular session
            if not self._is_iranian_domain(domain):
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

            # Detect website type
            website_type = self._detect_website_type(html, soup)

            # Calculate e-commerce confidence
            ecommerce_confidence = self._calculate_ecommerce_confidence(html, soup)

            # Find product selectors
            product_selectors = self._find_product_selectors(soup)

            # Detect pagination
            pagination_info = self._detect_pagination(soup)

            # Detect anti-bot measures
            anti_bot_measures = self._detect_anti_bot_measures(html, soup)

            # Recommend tools
            recommended_tools = self._recommend_tools(website_type, anti_bot_measures, ecommerce_confidence)

            # Look for API endpoints
            api_endpoints = self._find_api_endpoints(html, soup)

            # Detect language and currency
            content_language = self._detect_language(html, soup)
            currency_detected = self._detect_currency(html, soup)

            return WebsiteAnalysis(
                    domain=domain,
                    website_type=website_type,
                    ecommerce_confidence=ecommerce_confidence,
                    product_selectors=product_selectors,
                    pagination_info=pagination_info,
                    anti_bot_measures=anti_bot_measures,
                    recommended_tools=recommended_tools,
                    api_endpoints=api_endpoints,
                    content_language=content_language,
                    currency_detected=currency_detected
                )
                
        except Exception as e:
            logger.error(f"Failed to analyze {url}: {e}")
            return WebsiteAnalysis(
                domain=domain,
                website_type="unknown",
                ecommerce_confidence=0.0,
                product_selectors={},
                pagination_info={},
                anti_bot_measures=[],
                recommended_tools=["basic_http"],
                api_endpoints=[],
                content_language="unknown",
                currency_detected="unknown"
            )

    def _is_iranian_domain(self, domain: str) -> bool:
        """Check if domain is Iranian"""
        iranian_domains = [
            'emalls.ir', 'bamilo.com', 'okala.com', 'torob.com',
            'snapp.market', 'khodafez.com', 'timcheh.com', 'mahriha.com',
            'mobit.ir', 'mobile.ir', 'digikala.com'
        ]
        clean_domain = domain.replace('www.', '')
        return any(iranian_domain in clean_domain for iranian_domain in iranian_domains)

    def _create_iranian_ssl_contexts(self) -> Dict[str, Any]:
        """Create SSL contexts for Iranian sites with connectivity issues"""
        import ssl

        # Default relaxed SSL context for Iranian sites
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Site-specific configurations for known problematic sites
        return {
            'bamilo.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 5,
                    'limit_per_host': 2,
                    'ttl_dns_cache': 30,
                    'use_dns_cache': True,
                }
            },
            'khodafez.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 3,
                    'limit_per_host': 1,
                    'ttl_dns_cache': 60,
                    'use_dns_cache': True,
                }
            },
            'mahriha.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 3,
                    'limit_per_host': 1,
                    'ttl_dns_cache': 60,
                    'use_dns_cache': True,
                }
            },
            'default': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 10,
                    'limit_per_host': 3,
                    'ttl_dns_cache': 300,
                    'use_dns_cache': True,
                }
            }
        }

    def _get_iranian_ssl_config(self, domain: str) -> Dict[str, Any]:
        """Get SSL configuration for Iranian site"""
        # Remove www. prefix for matching
        clean_domain = domain.replace('www.', '')

        ssl_contexts = self._create_iranian_ssl_contexts()
        if clean_domain in ssl_contexts:
            return ssl_contexts[clean_domain]

        return ssl_contexts['default']

    def _create_aggressive_ssl_contexts(self) -> Dict[str, Any]:
        """Create very aggressive SSL contexts for stubborn Iranian sites"""
        import ssl

        # Ultra-relaxed SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Disable all SSL checks
        ssl_context.options |= ssl.OP_NO_SSLv2
        ssl_context.options |= ssl.OP_NO_SSLv3
        ssl_context.options |= ssl.OP_NO_TLSv1
        ssl_context.options |= ssl.OP_NO_TLSv1_1

        # Try to use TLS 1.3, 1.2, or fallback
        try:
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
        except AttributeError:
            # Older Python versions
            pass

        return {
            'bamilo.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 2,  # Very low connection limit
                    'limit_per_host': 1,
                    'ttl_dns_cache': 10,  # Short cache
                    'use_dns_cache': True,
                    'force_close': True,  # Force connection close
                },
                'timeout': 15,  # Shorter timeout
                'retries': 1,   # Single retry
            },
            'khodafez.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 1,  # Single connection
                    'limit_per_host': 1,
                    'ttl_dns_cache': 5,   # Very short cache
                    'use_dns_cache': False,  # Disable DNS cache
                    'force_close': True,
                },
                'timeout': 10,  # Very short timeout
                'retries': 0,   # No retries
            },
            'emalls.ir': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 3,
                    'limit_per_host': 1,
                    'ttl_dns_cache': 30,
                    'use_dns_cache': True,
                    'keepalive_timeout': 5,
                },
                'timeout': 20,
                'retries': 2,
            },
            'okala.com': {
                'ssl': ssl_context,
                'connector_kwargs': {
                    'limit': 3,
                    'limit_per_host': 1,
                    'ttl_dns_cache': 30,
                    'use_dns_cache': True,
                    'keepalive_timeout': 5,
                },
                'timeout': 20,
                'retries': 2,
            }
        }

    async def _analyze_iranian_site_with_fallbacks(self, url: str, domain: str) -> str:
        """Analyze Iranian site with multiple fallback strategies"""
        import requests
        from urllib3.exceptions import InsecureRequestWarning
        import warnings

        # Method 1: Try aggressive SSL configuration
        try:
            logger.info(f"🇮🇷 Trying aggressive SSL for {domain}")
            aggressive_configs = self._create_aggressive_ssl_contexts()
            clean_domain = domain.replace('www.', '')

            if clean_domain in aggressive_configs:
                config = aggressive_configs[clean_domain]
                connector = aiohttp.TCPConnector(
                    ssl=config['ssl'],
                    **config['connector_kwargs']
                )
                timeout = aiohttp.ClientTimeout(total=config['timeout'])
                session = aiohttp.ClientSession(connector=connector, timeout=timeout)

                try:
                    async with session.get(url) as response:
                        html = await response.text()
                        await session.close()
                        logger.info(f"✅ Aggressive SSL successful for {domain}")
                        return html
                except Exception as e:
                    logger.warning(f"⚠️ Aggressive SSL failed for {domain}: {e}")
                    await session.close()
            else:
                # Try regular Iranian SSL config
                ssl_config = self._get_iranian_ssl_config(domain)
                connector = aiohttp.TCPConnector(
                    ssl=ssl_config['ssl'],
                    **ssl_config['connector_kwargs']
                )
                timeout = aiohttp.ClientTimeout(total=30)
                session = aiohttp.ClientSession(connector=connector, timeout=timeout)

                try:
                    async with session.get(url) as response:
                        html = await response.text()
                        await session.close()
                        logger.info(f"✅ Regular SSL successful for {domain}")
                        return html
                except Exception as e:
                    logger.warning(f"⚠️ Regular SSL failed for {domain}: {e}")
                    await session.close()

        except Exception as e:
            logger.warning(f"⚠️ All aiohttp methods failed for {domain}: {e}")

        # Method 2: Try requests with SSL bypass
        try:
            logger.info(f"🌐 Trying requests fallback for {domain}")

            # Suppress SSL warnings
            warnings.filterwarnings('ignore', category=InsecureRequestWarning)

            # Try with verify=False
            response = requests.get(url, verify=False, timeout=15)
            response.raise_for_status()

            logger.info(f"✅ Requests fallback successful for {domain}")
            return response.text

        except Exception as e:
            logger.warning(f"⚠️ Requests fallback failed for {domain}: {e}")

        # Method 3: Try with different SSL versions
        try:
            logger.info(f"🔒 Trying SSL version fallback for {domain}")

            # Try with specific SSL version
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.protocol = ssl.PROTOCOL_TLS

            response = requests.get(url, verify=False, timeout=15)
            response.raise_for_status()

            logger.info(f"✅ SSL version fallback successful for {domain}")
            return response.text

        except Exception as e:
            logger.warning(f"⚠️ SSL version fallback failed for {domain}: {e}")

        # Method 4: Last resort - try without SSL entirely
        try:
            logger.info(f"🚨 Trying HTTP fallback for {domain}")
            http_url = url.replace('https://', 'http://')

            response = requests.get(http_url, timeout=15)
            response.raise_for_status()

            logger.info(f"✅ HTTP fallback successful for {domain}")
            return response.text

        except Exception as e:
            logger.error(f"❌ All fallback methods failed for {domain}: {e}")
            raise Exception(f"Cannot connect to {domain} with any SSL configuration")

    def _detect_website_type(self, html: str, soup: BeautifulSoup) -> str:
        """Detect if website is SPA, traditional, API-driven, etc."""
        # Check for SPA indicators
        spa_indicators = [
            'react', 'vue', 'angular', 'next.js', 'nuxt',
            '__NEXT_DATA__', '__NUXT__', 'ng-version'
        ]
        
        if any(indicator in html.lower() for indicator in spa_indicators):
            return "spa"
        
        # Check for heavy JavaScript
        scripts = soup.find_all('script')
        if len(scripts) > 10 and any(len(script.get_text()) > 1000 for script in scripts):
            return "spa"
        
        # Check for traditional server-rendered content
        if soup.find_all(['div', 'span', 'p'], class_=True):
            return "traditional"
        
        return "unknown"
    
    def _calculate_ecommerce_confidence(self, html: str, soup: BeautifulSoup) -> float:
        """Calculate confidence that this is an e-commerce site"""
        confidence = 0.0
        
        # E-commerce keywords
        ecommerce_keywords = [
            'price', 'buy', 'cart', 'shop', 'product', 'order',
            'قیمت', 'خرید', 'سبد', 'محصول', 'فروش', 'تومان', 'ریال'
        ]
        
        keyword_matches = sum(1 for keyword in ecommerce_keywords if keyword in html.lower())
        confidence += min(keyword_matches / len(ecommerce_keywords), 0.4)
        
        # Price patterns
        price_patterns = [
            r'\$\d+',
            r'\d+\s*تومان',
            r'\d+\s*ریال',
            r'\d{1,3}(,\d{3})*\s*(تومان|ریال)',
            r'price["\']?\s*:\s*\d+'
        ]
        
        price_matches = sum(1 for pattern in price_patterns if re.search(pattern, html))
        confidence += min(price_matches / len(price_patterns), 0.3)
        
        # Product-related HTML structures
        product_indicators = [
            soup.find_all(attrs={'class': re.compile('product|item|card', re.I)}),
            soup.find_all(attrs={'class': re.compile('price', re.I)}),
            soup.find_all(attrs={'id': re.compile('cart|basket', re.I)})
        ]
        
        structure_score = sum(min(len(indicator), 5) for indicator in product_indicators) / 15
        confidence += min(structure_score, 0.3)
        
        return min(confidence, 1.0)
    
    def _find_product_selectors(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Find CSS selectors for product elements"""
        selectors = {}
        
        # Common product container patterns
        product_containers = soup.find_all(attrs={'class': re.compile('product|item|card', re.I)})
        if product_containers:
            # Get the most common class
            classes = [elem.get('class', []) for elem in product_containers[:10]]
            flat_classes = [cls for sublist in classes for cls in sublist if cls]
            if flat_classes:
                most_common = max(set(flat_classes), key=flat_classes.count)
                selectors['product_container'] = f'.{most_common}'
        
        # Price selectors
        price_elements = soup.find_all(attrs={'class': re.compile('price|cost|amount', re.I)})
        if price_elements:
            price_classes = [elem.get('class', []) for elem in price_elements[:5]]
            flat_classes = [cls for sublist in price_classes for cls in sublist if cls]
            if flat_classes:
                most_common = max(set(flat_classes), key=flat_classes.count)
                selectors['price'] = f'.{most_common}'
        
        # Title selectors
        title_elements = soup.find_all(['h1', 'h2', 'h3', 'h4'], attrs={'class': re.compile('title|name|product', re.I)})
        if title_elements:
            selectors['title'] = title_elements[0].name
        
        # Image selectors
        product_images = soup.find_all('img', attrs={'class': re.compile('product|item', re.I)})
        if product_images:
            selectors['image'] = 'img'
        
        return selectors
    
    def _detect_pagination(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Detect pagination patterns"""
        pagination_info = {
            "type": "none",
            "selectors": {},
            "max_pages": 1
        }
        
        # Look for pagination elements
        pagination_patterns = [
            'pagination', 'pager', 'page-nav', 'next', 'prev',
            'صفحه', 'بعدی', 'قبلی'
        ]
        
        for pattern in pagination_patterns:
            elements = soup.find_all(attrs={'class': re.compile(pattern, re.I)})
            if elements:
                pagination_info["type"] = "traditional"
                pagination_info["selectors"]["next"] = f'[class*="{pattern}"]'
                break
        
        # Look for "Load More" buttons
        load_more = soup.find_all(text=re.compile('load more|بیشتر|ادامه', re.I))
        if load_more:
            pagination_info["type"] = "infinite_scroll"
        
        # Try to estimate max pages
        page_numbers = soup.find_all(text=re.compile(r'\d+'))
        if page_numbers:
            try:
                numbers = [int(re.search(r'\d+', text).group()) for text in page_numbers[-10:]]
                pagination_info["max_pages"] = max(numbers) if numbers else 1
            except:
                pass
        
        return pagination_info
    
    def _detect_anti_bot_measures(self, html: str, soup: BeautifulSoup) -> List[str]:
        """Detect anti-bot protection measures"""
        measures = []
        
        # Cloudflare
        if 'cloudflare' in html.lower() or 'cf-ray' in html.lower():
            measures.append("cloudflare")
        
        # CAPTCHA
        if 'captcha' in html.lower() or 'recaptcha' in html.lower():
            measures.append("captcha")
        
        # Rate limiting indicators
        if 'rate limit' in html.lower() or 'too many requests' in html.lower():
            measures.append("rate_limiting")
        
        # JavaScript challenges
        if 'please enable javascript' in html.lower():
            measures.append("js_required")
        
        # Heavy JavaScript (likely SPA that needs JS)
        scripts = soup.find_all('script')
        if len(scripts) > 15:
            measures.append("heavy_js")
        
        return measures
    
    def _recommend_tools(self, website_type: str, anti_bot_measures: List[str], ecommerce_confidence: float) -> List[str]:
        """Recommend scraping tools based on analysis"""
        tools = []
        
        # Low confidence sites
        if ecommerce_confidence < 0.3:
            return ["skip"]
        
        # Choose tools based on complexity
        if "cloudflare" in anti_bot_measures or "captcha" in anti_bot_measures:
            tools.extend(["selenium_stealth", "proxy_rotation"])
        elif website_type == "spa" or "heavy_js" in anti_bot_measures:
            tools.extend(["selenium", "playwright"])
        elif website_type == "traditional":
            tools.extend(["beautifulsoup", "scrapy"])
        else:
            tools.extend(["beautifulsoup", "requests"])
        
        # Always add API discovery
        tools.append("api_discovery")
        
        return tools
    
    def _find_api_endpoints(self, html: str, soup: BeautifulSoup) -> List[str]:
        """Find potential API endpoints"""
        endpoints = []
        
        # Look for API calls in JavaScript
        api_patterns = [
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.\w+\s*\(\s*["\']([^"\']+)["\']',
            r'\.get\s*\(\s*["\']([^"\']+)["\']',
            r'api["\']?\s*:\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html, re.I)
            endpoints.extend(matches)
        
        # Clean and filter endpoints
        clean_endpoints = []
        for endpoint in endpoints[:10]:  # Limit to 10
            if endpoint.startswith(('http', '/api', '/v1', '/v2')):
                clean_endpoints.append(endpoint)
        
        return clean_endpoints
    
    def _detect_language(self, html: str, soup: BeautifulSoup) -> str:
        """Detect content language"""
        # Check HTML lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag.get('lang')
        
        # Check for Persian/Farsi content
        persian_chars = len(re.findall(r'[\u0600-\u06FF]', html))
        english_chars = len(re.findall(r'[a-zA-Z]', html))
        
        if persian_chars > english_chars * 0.3:
            return "fa"
        elif english_chars > 0:
            return "en"
        
        return "unknown"
    
    def _detect_currency(self, html: str, soup: BeautifulSoup) -> str:
        """Detect currency used on the site"""
        currencies = {
            'تومان': 'IRR',
            'ریال': 'IRR', 
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP'
        }
        
        for symbol, code in currencies.items():
            if symbol in html:
                return code
        
        return "unknown"

class SeleniumScraper:
    """Advanced Selenium-based scraper with stealth capabilities"""
    
    def __init__(self, stealth_mode: bool = False):
        self.driver = None
        self.stealth_mode = stealth_mode
    
    def init_driver(self):
        """Initialize Chrome driver with enhanced compatibility and anti-detection measures"""
        try:
            # Use enhanced driver manager for automatic compatibility
            self.driver = driver_manager.get_webdriver(
                headless=True,
                stealth_mode=self.stealth_mode
            )
            
            if not self.driver:
                raise Exception("Enhanced driver manager failed to create driver")
            
            logger.info("✅ Enhanced Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Enhanced driver initialization failed: {e}")
            raise
    
    async def scrape_spa_site(self, url: str, analysis: WebsiteAnalysis) -> ScrapingResult:
        """Scrape Single Page Application with JavaScript rendering"""
        start_time = datetime.now()
        products = []
        errors = []
        
        try:
            self.init_driver()
            self.driver.get(url)
            
            # Wait for content to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                errors.append("Page load timeout")
                return self._create_result(False, products, "selenium", start_time, errors)
            
            # Wait for products to load
            if analysis.product_selectors.get('product_container'):
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, analysis.product_selectors['product_container']))
                    )
                except TimeoutException:
                    errors.append("Product containers not found")
            
            # Extract products
            products = self._extract_products_selenium(analysis)
            
        except Exception as e:
            errors.append(f"Selenium error: {str(e)}")
        finally:
            self.cleanup_driver()
        
        return self._create_result(len(products) > 0, products, "selenium", start_time, errors)
    
    def _extract_products_selenium(self, analysis: WebsiteAnalysis) -> List[Dict]:
        """Extract product data using Selenium"""
        products = []
        
        try:
            # Find product containers
            container_selector = analysis.product_selectors.get('product_container', '[class*="product"], [class*="item"]')
            containers = self.driver.find_elements(By.CSS_SELECTOR, container_selector)
            
            for container in containers[:20]:  # Limit to 20 products
                try:
                    product = {}
                    
                    # Extract title
                    title_selector = analysis.product_selectors.get('title', 'h1, h2, h3, h4, [class*="title"], [class*="name"]')
                    try:
                        title_elem = container.find_element(By.CSS_SELECTOR, title_selector)
                        product['title'] = title_elem.text.strip()
                    except NoSuchElementException:
                        continue
                    
                    # Extract price
                    price_selector = analysis.product_selectors.get('price', '[class*="price"], [class*="cost"]')
                    try:
                        price_elem = container.find_element(By.CSS_SELECTOR, price_selector)
                        product['price_text'] = price_elem.text.strip()
                        product['price_toman'] = self._extract_price_from_text(product['price_text'])
                    except NoSuchElementException:
                        product['price_text'] = ""
                        product['price_toman'] = 0
                    
                    # Extract image
                    try:
                        img_elem = container.find_element(By.TAG_NAME, 'img')
                        product['image_url'] = img_elem.get_attribute('src')
                    except NoSuchElementException:
                        product['image_url'] = ""
                    
                    # Extract link
                    try:
                        link_elem = container.find_element(By.TAG_NAME, 'a')
                        product['product_url'] = link_elem.get_attribute('href')
                    except NoSuchElementException:
                        product['product_url'] = ""
                    
                    if product.get('title') and product.get('price_toman', 0) > 0:
                        product['product_id'] = f"AUTO{uuid.uuid4().hex[:8]}"
                        product['last_updated'] = datetime.now(timezone.utc).isoformat()
                        products.append(product)
                    
                except Exception as e:
                    logger.warning(f"Error extracting product: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error finding products: {e}")
        
        return products
    
    def _extract_price_from_text(self, text: str) -> int:
        """Extract numeric price from text"""
        if not text:
            return 0
        
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
            if price < 1000:
                price *= 1000000
            elif price < 100000:
                price *= 1000
            return price if price >= 10000 else 0
        
        return 0

    def cleanup_driver(self):
        """Close Chrome driver and cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔒 Chrome driver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None

        # Cleanup enhanced driver manager resources
        try:
            driver_manager.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up driver manager: {e}")

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
                "user_agent": "selenium_chrome"
            }
        )

class APIDiscovery:
    """Tool for discovering and exploiting API endpoints"""
    
    def __init__(self):
        self.session = None
    
    async def init(self):
        """Initialize HTTP session"""
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def discover_api_endpoints(self, base_url: str, analysis: WebsiteAnalysis) -> List[str]:
        """Discover potential API endpoints"""
        discovered_endpoints = []
        
        # Common API paths
        common_paths = [
            '/api/products',
            '/api/search',
            '/api/v1/products',
            '/api/v2/products',
            '/products.json',
            '/search.json',
            '/catalog/products',
            '/rest/products'
        ]
        
        for path in common_paths:
            url = urljoin(base_url, path)
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            discovered_endpoints.append(url)
                            logger.info(f"✅ Found API endpoint: {url}")
            except:
                pass
        
        # Try endpoints found in analysis
        for endpoint in analysis.api_endpoints:
            if endpoint.startswith('/'):
                url = urljoin(base_url, endpoint)
            else:
                url = endpoint
                
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            discovered_endpoints.append(url)
                            logger.info(f"✅ Found API endpoint from analysis: {url}")
            except:
                pass
        
        return discovered_endpoints
    
    async def scrape_api_endpoint(self, endpoint: str, params: Dict = None) -> ScrapingResult:
        """Scrape data from an API endpoint"""
        start_time = datetime.now()
        products = []
        errors = []
        
        try:
            async with self.session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products = self._extract_products_from_api(data)
                else:
                    errors.append(f"API returned status {response.status}")
                    
        except Exception as e:
            errors.append(f"API scraping error: {str(e)}")
        
        return ScrapingResult(
            success=len(products) > 0,
            products_found=len(products),
            products=products,
            tool_used="api_discovery",
            execution_time=(datetime.now() - start_time).total_seconds(),
            errors=errors,
            metadata={"endpoint": endpoint, "params": params}
        )
    
    def _extract_products_from_api(self, data: Any) -> List[Dict]:
        """Extract product data from API response"""
        products = []
        
        # Handle different API response structures
        if isinstance(data, dict):
            # Look for common product list keys
            for key in ['products', 'items', 'data', 'results', 'product_list']:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
        
        if isinstance(data, list):
            for item in data[:20]:  # Limit to 20
                if isinstance(item, dict):
                    product = self._normalize_api_product(item)
                    if product:
                        products.append(product)
        
        return products
    
    def _normalize_api_product(self, item: Dict) -> Optional[Dict]:
        """Normalize API product data to standard format"""
        # Common field mappings
        title_fields = ['title', 'name', 'product_name', 'label', 'title_fa']
        price_fields = ['price', 'cost', 'amount', 'price_toman', 'final_price']
        url_fields = ['url', 'link', 'product_url', 'href']
        image_fields = ['image', 'img', 'picture', 'photo', 'image_url']
        
        product = {}
        
        # Extract title
        for field in title_fields:
            if field in item and item[field]:
                product['title'] = str(item[field]).strip()
                break
        
        if not product.get('title'):
            return None
        
        # Extract price
        for field in price_fields:
            if field in item:
                try:
                    price = float(item[field]) if item[field] else 0
                    product['price_toman'] = int(price)
                    break
                except (ValueError, TypeError):
                    continue
        
        # Extract URL
        for field in url_fields:
            if field in item and item[field]:
                product['product_url'] = str(item[field])
                break
        
        # Extract image
        for field in image_fields:
            if field in item and item[field]:
                product['image_url'] = str(item[field])
                break
        
        # Add metadata
        product['product_id'] = f"API{uuid.uuid4().hex[:8]}"
        product['last_updated'] = datetime.now(timezone.utc).isoformat()
        product['source'] = 'api'
        
        return product if product.get('price_toman', 0) > 0 else None

class AIScrapingAgent:
    """Main AI agent that orchestrates all scraping tools"""
    
    def __init__(self):
        self.analyzer = WebsiteAnalyzer()
        self.selenium_scraper = SeleniumScraper()
        self.api_discovery = APIDiscovery()
        self.requests_scraper = RequestsScraper() if REQUESTS_SCRAPER_AVAILABLE else None
        self.redis_client = None
    
    async def init(self):
        """Initialize all tools"""
        await self.analyzer.init()
        await self.api_discovery.init()
        
        if self.requests_scraper:
            await self.requests_scraper.init()
        
        # Connect to Redis
        self.redis_client = redis.from_url('redis://localhost:6379/0')
    
    async def close(self):
        """Close all connections"""
        await self.analyzer.close()
        await self.api_discovery.close()
        if self.requests_scraper:
            await self.requests_scraper.close()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def scrape_website_intelligently(self, url: str) -> ScrapingResult:
        """Intelligently scrape a website using the best tools"""
        logger.info(f"🤖 AI Agent analyzing website: {url}")
        
        # Step 1: Analyze the website
        analysis = await self.analyzer.analyze_website(url)
        
        logger.info(f"📊 Analysis complete:")
        logger.info(f"  - Website type: {analysis.website_type}")
        logger.info(f"  - E-commerce confidence: {analysis.ecommerce_confidence:.2f}")
        logger.info(f"  - Recommended tools: {analysis.recommended_tools}")
        logger.info(f"  - Anti-bot measures: {analysis.anti_bot_measures}")
        
        # Skip if low confidence
        if analysis.ecommerce_confidence < 0.3:
            logger.warning(f"⚠️ Low e-commerce confidence ({analysis.ecommerce_confidence:.2f}), skipping")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="analyzer",
                execution_time=0.0,
                errors=["Low e-commerce confidence"],
                metadata={"analysis": asdict(analysis)}
            )
        
        # Step 2: Try tools in order of recommendation
        for tool in analysis.recommended_tools:
            if tool == "skip":
                continue
            
            logger.info(f"🔧 Trying tool: {tool}")
            
            try:
                if tool == "api_discovery":
                    result = await self._try_api_scraping(url, analysis)
                elif tool in ["selenium", "selenium_stealth"]:
                    stealth = (tool == "selenium_stealth")
                    self.selenium_scraper.stealth_mode = stealth
                    result = await self.selenium_scraper.scrape_spa_site(url, analysis)
                elif tool in ["beautifulsoup", "scrapy", "requests"] and self.requests_scraper:
                    # Use requests-based scraper for traditional sites
                    result = await self.requests_scraper.scrape_website(url, analysis)
                else:
                    # Try requests scraper as fallback if available
                    if self.requests_scraper:
                        logger.info(f"🔄 Falling back to requests scraper for tool: {tool}")
                        result = await self.requests_scraper.scrape_website(url, analysis)
                    else:
                        # Last resort: try Selenium
                        result = await self.selenium_scraper.scrape_spa_site(url, analysis)
                
                if result.success and result.products_found > 0:
                    logger.info(f"✅ Success with {tool}: {result.products_found} products found")
                    
                    # Store results in Redis
                    await self._store_results(url, result, analysis)
                    
                    return result
                else:
                    logger.warning(f"❌ {tool} failed: {result.errors}")
            
            except Exception as e:
                logger.error(f"❌ Error with {tool}: {e}")
                continue
        
        # If all tools failed
        return ScrapingResult(
            success=False,
            products_found=0,
            products=[],
            tool_used="all_failed",
            execution_time=0.0,
            errors=["All scraping tools failed"],
            metadata={"analysis": asdict(analysis)}
        )
    
    async def _try_api_scraping(self, url: str, analysis: WebsiteAnalysis) -> ScrapingResult:
        """Try API-based scraping"""
        endpoints = await self.api_discovery.discover_api_endpoints(url, analysis)
        
        if not endpoints:
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="api_discovery",
                execution_time=0.0,
                errors=["No API endpoints found"],
                metadata={}
            )
        
        # Try each endpoint
        for endpoint in endpoints:
            result = await self.api_discovery.scrape_api_endpoint(endpoint)
            if result.success:
                return result
        
        return ScrapingResult(
            success=False,
            products_found=0,
            products=[],
            tool_used="api_discovery",
            execution_time=0.0,
            errors=["No working API endpoints"],
            metadata={"tried_endpoints": endpoints}
        )
    
    async def _store_results(self, url: str, result: ScrapingResult, analysis: WebsiteAnalysis):
        """Store scraping results in Redis"""
        try:
            domain = urlparse(url).netloc
            
            for product in result.products:
                # Convert to API-compatible format
                product_data = {
                    "product_id": product['product_id'],
                    "canonical_title": product['title'],
                    "canonical_title_fa": product['title'],
                    "brand": self._extract_brand(product['title']),
                    "category": "auto_discovered",
                    "model": product['title'],
                    "current_prices": [{
                        "vendor": domain,
                        "vendor_name_fa": domain,
                        "price_toman": product.get('price_toman', 0),
                        "price_usd": round(product.get('price_toman', 0) / 42000, 2),
                        "availability": True,
                        "product_url": product.get('product_url', url),
                        "last_updated": product['last_updated']
                    }],
                    "lowest_price": {
                        "vendor": domain,
                        "vendor_name_fa": domain,
                        "price_toman": product.get('price_toman', 0),
                        "price_usd": round(product.get('price_toman', 0) / 42000, 2)
                    },
                    "highest_price": {
                        "vendor": domain,
                        "vendor_name_fa": domain,
                        "price_toman": product.get('price_toman', 0),
                        "price_usd": round(product.get('price_toman', 0) / 42000, 2)
                    },
                    "price_range_pct": 0.0,
                    "available_vendors": 1,
                    "last_updated": product['last_updated'],
                    "specifications": None
                }
                
                product_key = f"product:{product['product_id']}"
                await self.redis_client.set(product_key, json.dumps(product_data))
            
            # Update flags
            await self.redis_client.set('real_data_available', 'true')
            
            summary = {
                "total_products": result.products_found,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "vendors": [domain],
                "categories": ["auto_discovered"],
                "status": "success",
                "scraper_run_id": str(int(datetime.now().timestamp())),
                "real_data_flag": True,
                "tool_used": result.tool_used
            }
            
            await self.redis_client.set('scraping:summary', json.dumps(summary))
            
            logger.info(f"✅ Stored {result.products_found} products from {domain}")
            
        except Exception as e:
            logger.error(f"Error storing results: {e}")
    
    def _extract_brand(self, title: str) -> str:
        """Extract brand from product title"""
        title_lower = title.lower()
        brands = ["samsung", "apple", "iphone", "xiaomi", "huawei", "lg", "sony", "nokia", "oneplus", "oppo", "vivo"]
        
        for brand in brands:
            if brand in title_lower:
                return brand.title()
        
        words = title.split()
        return words[0] if words else "Unknown"

async def main():
    """Test the AI scraping agent"""
    agent = AIScrapingAgent()
    
    try:
        await agent.init()
        
        # Test URLs
        test_urls = [
            "https://www.emalls.ir",
            "https://www.mobit.ir",
            "https://www.technolife.ir"
        ]
        
        for url in test_urls:
            logger.info(f"\n🚀 Testing AI agent on: {url}")
            result = await agent.scrape_website_intelligently(url)
            
            if result.success:
                print(f"✅ SUCCESS: Found {result.products_found} products using {result.tool_used}")
                for product in result.products[:3]:
                    print(f"  📱 {product['title'][:50]}... - {product.get('price_toman', 0):,} تومان")
            else:
                print(f"❌ FAILED: {result.errors}")
            
            print("-" * 80)
    
    finally:
        await agent.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
