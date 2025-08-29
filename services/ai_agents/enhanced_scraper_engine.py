#!/usr/bin/env python3
"""
Enhanced Scraper Engine - Improved Success Rates and Reliability
Intelligent retry mechanisms, better error handling, and advanced scraping strategies
"""

import asyncio
import aiohttp
import json
import logging
import random
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import redis.asyncio as redis
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from web_scraping_toolkit import (
    WebsiteAnalyzer,
    WebsiteAnalysis,
    SeleniumScraper,
    RequestsScraper,
    APIDiscovery,
    ScrapingResult
)

logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    """Enhanced product data structure"""
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
    brand: str = ""
    specs: Dict[str, Any] = None
    last_updated: str = ""

@dataclass
class EnhancedScrapingResult:
    """Enhanced scraping result with vendor information"""
    vendor: str
    success: bool
    products_found: int
    products: List[ProductData]
    tool_used: str
    execution_time: float = 0.0
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ScrapingStrategy:
    """Defines a scraping strategy with fallback options"""
    primary_tool: str
    fallback_tools: List[str]
    timeout_seconds: int = 30
    retry_attempts: int = 3
    custom_selectors: Dict[str, str] = None

@dataclass
class EnhancedScrapingResult:
    """Enhanced result with detailed metadata"""
    success: bool
    products_found: int
    products: List[Dict]
    tool_used: str
    strategy: str
    execution_time: float
    retry_count: int
    errors: List[str]
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]

class EnhancedScraperEngine:
    """Advanced scraper engine with intelligent retry and optimization"""

    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self.analyzer = WebsiteAnalyzer()
        self.selenium_scraper = SeleniumScraper()
        self.requests_scraper = RequestsScraper()
        self.api_discovery = APIDiscovery()

        # Add missing attributes
        self.driver = None
        self.session = None
        self.exchange_rate = 42000  # USD to IRR

        # Import random locally for Iranian methods
        import random as random_module
        self.random = random_module

        # Iranian e-commerce specific configurations
        self.site_configs = self._load_site_configurations()

        # Performance tracking
        self.performance_stats = {}

        # Iranian SSL context for problematic sites
        self.iranian_ssl_contexts = self._create_iranian_ssl_contexts()

        # Alternative connection methods
        self.alternative_connectors = self._create_alternative_connectors()

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

        if clean_domain in self.iranian_ssl_contexts:
            return self.iranian_ssl_contexts[clean_domain]

        return self.iranian_ssl_contexts['default']

    def _create_alternative_connectors(self) -> Dict[str, Any]:
        """Create alternative connection methods for stubborn sites"""
        import ssl

        # HTTP connector (no SSL)
        http_connector = aiohttp.TCPConnector(
            ssl=False,
            limit=5,
            limit_per_host=2,
            ttl_dns_cache=60
        )

        # Ultra-aggressive SSL connector
        ultra_ssl_context = ssl.create_default_context()
        ultra_ssl_context.check_hostname = False
        ultra_ssl_context.verify_mode = ssl.CERT_NONE
        ultra_ssl_context.options |= ssl.OP_NO_SSLv2
        ultra_ssl_context.options |= ssl.OP_NO_SSLv3
        ultra_ssl_context.options |= ssl.OP_NO_TLSv1
        ultra_ssl_context.options |= ssl.OP_NO_TLSv1_1

        try:
            ultra_ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        except AttributeError:
            pass

        ultra_connector = aiohttp.TCPConnector(
            ssl=ultra_ssl_context,
            limit=1,
            limit_per_host=1,
            ttl_dns_cache=10,
            use_dns_cache=False,
            force_close=True
        )

        return {
            'http': http_connector,
            'ultra_ssl': ultra_connector,
        }

    async def init(self):
        """Initialize all scraper components"""
        await asyncio.gather(
            self.analyzer.init(),
            self.requests_scraper.init(),
            self.api_discovery.init()
        )
        logger.info("✅ Enhanced scraper engine initialized")

    def setup_selenium_driver(self, headless: bool = True):
        """Setup Selenium driver for Iranian sites"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        if headless:
            options.add_argument('--headless=new')

        # Iranian-friendly options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        try:
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("✅ Selenium driver initialized for Iranian scraping")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium driver: {e}")

    async def close(self):
        """Close all scraper components"""
        await asyncio.gather(
            self.analyzer.close(),
            self.requests_scraper.close(),
            self.api_discovery.close()
        )
        self.selenium_scraper.cleanup_driver()

    def _load_site_configurations(self) -> Dict[str, Any]:
        """Load site-specific configurations for Iranian e-commerce sites"""
        return {
            "digikala.com": {
                "product_selectors": {
                    "container": '[data-testid*="product"]',
                    "title": '[class*="title"]',
                    "price": '[class*="price"]',
                    "image": 'img[class*="image"]'
                },
                "pagination": {
                    "next": '.pagination .next',
                    "page_param": "page"
                },
                "strategies": ["api_discovery", "requests", "selenium"],
                "anti_bot_level": "medium"
            },
            "mobit.ir": {
                "product_selectors": {
                    "container": '[class*="product"]',
                    "title": 'h3, [class*="title"]',
                    "price": '[class*="price"]',
                    "image": 'img'
                },
                "pagination": {
                    "next": '.pagination .next',
                    "page_param": "p"
                },
                "strategies": ["requests", "selenium", "api_discovery"],
                "anti_bot_level": "low"
            },
            "technolife.ir": {
                "product_selectors": {
                    "container": '.product-item',
                    "title": '.product-title',
                    "price": '.price',
                    "image": '.product-image img'
                },
                "pagination": {
                    "next": '.next-page',
                    "page_param": "page"
                },
                "strategies": ["selenium", "requests", "api_discovery"],
                "anti_bot_level": "high"
            },
            "meghdadit.com": {
                "product_selectors": {
                    "container": '.product',
                    "title": '.product-title',
                    "price": '.product-price',
                    "image": '.product-image'
                },
                "pagination": {
                    "next": '.pagination .next',
                    "page_param": "page"
                },
                "strategies": ["requests", "selenium"],
                "anti_bot_level": "low"
            }
        }

    def _get_scraping_strategy(self, domain: str, analysis: WebsiteAnalysis) -> ScrapingStrategy:
        """Determine optimal scraping strategy based on site analysis"""

        # Use site-specific config if available
        site_config = self.site_configs.get(domain, {})

        # Determine primary tool based on analysis
        if analysis.website_type == "spa" and analysis.ecommerce_confidence > 0.8:
            primary_tool = "selenium"
        elif analysis.website_type == "api":
            primary_tool = "api_discovery"
        elif analysis.ecommerce_confidence > 0.6:
            primary_tool = "requests"
        else:
            primary_tool = "requests"  # Default fallback

        # Override with site-specific strategy if available
        if site_config.get("strategies"):
            primary_tool = site_config["strategies"][0]

        # Define fallback tools
        fallback_tools = []
        if primary_tool != "selenium":
            fallback_tools.append("selenium")
        if primary_tool != "requests":
            fallback_tools.append("requests")
        if primary_tool != "api_discovery":
            fallback_tools.append("api_discovery")

        # Adjust timeout based on anti-bot measures
        timeout = 30
        if "cloudflare" in analysis.anti_bot_measures:
            timeout = 60
        elif "heavy_js" in analysis.anti_bot_measures:
            timeout = 45

        return ScrapingStrategy(
            primary_tool=primary_tool,
            fallback_tools=fallback_tools,
            timeout_seconds=timeout,
            retry_attempts=3,
            custom_selectors=site_config.get("product_selectors")
        )

    async def scrape_with_strategy(self, url: str, strategy: ScrapingStrategy) -> EnhancedScrapingResult:
        """Execute scraping with intelligent strategy and fallbacks"""
        start_time = datetime.now()
        all_errors = []
        retry_count = 0

        # Try primary tool first
        result = await self._try_scraping_tool(url, strategy.primary_tool, strategy.custom_selectors)

        # If primary tool fails, try fallbacks with retries
        if not result.success and result.products_found == 0:
            for fallback_tool in strategy.fallback_tools:
                if retry_count >= strategy.retry_attempts:
                    break

                logger.info(f"🔄 Retrying with {fallback_tool} (attempt {retry_count + 1}/{strategy.retry_attempts})")
                retry_count += 1

                result = await self._try_scraping_tool(url, fallback_tool, strategy.custom_selectors)

                if result.success and result.products_found > 0:
                    logger.info(f"✅ Success with fallback tool: {fallback_tool}")
                    break
                else:
                    all_errors.extend(result.errors)

        # Calculate performance metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        performance_metrics = {
            "total_execution_time": execution_time,
            "retry_count": retry_count,
            "tools_attempted": [strategy.primary_tool] + strategy.fallback_tools[:retry_count],
            "success_rate": 1.0 if result.success else 0.0,
            "products_per_second": result.products_found / execution_time if execution_time > 0 else 0
        }

        return EnhancedScrapingResult(
            success=result.success,
            products_found=result.products_found,
            products=result.products,
            tool_used=result.tool_used,
            strategy=strategy.primary_tool,
            execution_time=execution_time,
            retry_count=retry_count,
            errors=all_errors if not result.success else [],
            metadata=result.metadata,
            performance_metrics=performance_metrics
        )

    async def _try_scraping_tool(self, url: str, tool: str, custom_selectors: Dict = None) -> ScrapingResult:
        """Try a specific scraping tool"""
        try:
            if tool == "selenium":
                return await self._scrape_with_selenium(url)
            elif tool == "requests":
                return await self._scrape_with_requests(url)
            elif tool == "api_discovery":
                return await self._scrape_with_api_discovery(url)
            elif tool == "iranian_http":
                # For Iranian tools, we need analysis - use a default one
                from web_scraping_toolkit import WebsiteAnalysis
                analysis = WebsiteAnalysis(
                    domain=urlparse(url).netloc,
                    website_type="traditional",
                    ecommerce_confidence=0.5,
                    product_selectors={},
                    pagination_info={},
                    anti_bot_measures=[],
                    recommended_tools=["requests"],
                    api_endpoints=[],
                    content_language="fa",
                    currency_detected="IRR"
                )
                return await self._scrape_with_iranian_http(url, analysis)
            elif tool == "iranian_selenium":
                from web_scraping_toolkit import WebsiteAnalysis
                analysis = WebsiteAnalysis(
                    domain=urlparse(url).netloc,
                    website_type="spa",
                    ecommerce_confidence=0.5,
                    product_selectors={},
                    pagination_info={},
                    anti_bot_measures=["javascript"],
                    recommended_tools=["selenium"],
                    api_endpoints=[],
                    content_language="fa",
                    currency_detected="IRR"
                )
                return await self._scrape_with_iranian_selenium(url, analysis)
            elif tool == "iranian_mobile":
                from web_scraping_toolkit import WebsiteAnalysis
                analysis = WebsiteAnalysis(
                    domain=urlparse(url).netloc,
                    website_type="traditional",
                    ecommerce_confidence=0.5,
                    product_selectors={},
                    pagination_info={},
                    anti_bot_measures=[],
                    recommended_tools=["requests"],
                    api_endpoints=[],
                    content_language="fa",
                    currency_detected="IRR"
                )
                return await self._scrape_with_iranian_mobile(url, analysis)
            else:
                return ScrapingResult(
                    success=False,
                    products_found=0,
                    products=[],
                    tool_used=tool,
                    execution_time=0,
                    errors=[f"Unknown tool: {tool}"],
                    metadata={}
                )
        except Exception as e:
            logger.error(f"Error with tool {tool}: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used=tool,
                execution_time=0,
                errors=[str(e)],
                metadata={}
            )

    async def _scrape_with_selenium(self, url: str) -> ScrapingResult:
        """Scrape using Selenium with enhanced error handling"""
        try:
            # Analyze website first
            analysis = await self.analyzer.analyze_website(url)

            # Convert analysis to proper format
            analysis_dict = {
                'domain': analysis.domain,
                'website_type': analysis.website_type,
                'ecommerce_confidence': analysis.ecommerce_confidence,
                'product_selectors': analysis.product_selectors,
                'pagination_info': analysis.pagination_info,
                'anti_bot_measures': analysis.anti_bot_measures,
                'recommended_tools': analysis.recommended_tools,
                'api_endpoints': analysis.api_endpoints,
                'content_language': analysis.content_language,
                'currency_detected': analysis.currency_detected
            }

            # Create analysis object for selenium scraper
            website_analysis = WebsiteAnalysis(
                domain=urlparse(url).netloc,
                website_type=analysis_dict.get('website_type', 'unknown'),
                ecommerce_confidence=analysis_dict.get('ecommerce_confidence', 0.0),
                product_selectors=analysis_dict.get('product_selectors', {}),
                pagination_info=analysis_dict.get('pagination_info', {}),
                anti_bot_measures=analysis_dict.get('anti_bot_measures', []),
                recommended_tools=analysis_dict.get('recommended_tools', []),
                api_endpoints=analysis_dict.get('api_endpoints', []),
                content_language=analysis_dict.get('content_language', 'fa'),
                currency_detected=analysis_dict.get('currency_detected', 'IRR')
            )

            return await self.selenium_scraper.scrape_spa_site(url, website_analysis)

        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="selenium",
                execution_time=0,
                errors=[str(e)],
                metadata={}
            )

    async def _scrape_with_requests(self, url: str) -> ScrapingResult:
        """Scrape using requests with enhanced error handling"""
        try:
            analysis = {"website_type": "traditional", "ecommerce_confidence": 0.7}
            return await self.requests_scraper.scrape_website(url, analysis)
        except Exception as e:
            logger.error(f"Requests scraping failed: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="requests",
                execution_time=0,
                errors=[str(e)],
                metadata={}
            )

    async def _scrape_with_api_discovery(self, url: str) -> ScrapingResult:
        """Try to discover and use API endpoints"""
        try:
            # First analyze the website to get proper analysis object
            analysis = await self.analyzer.analyze_website(url)

            # Convert analysis to proper format
            analysis_dict = {
                'domain': analysis.domain,
                'website_type': analysis.website_type,
                'ecommerce_confidence': analysis.ecommerce_confidence,
                'product_selectors': analysis.product_selectors,
                'pagination_info': analysis.pagination_info,
                'anti_bot_measures': analysis.anti_bot_measures,
                'recommended_tools': analysis.recommended_tools,
                'api_endpoints': analysis.api_endpoints,
                'content_language': analysis.content_language,
                'currency_detected': analysis.currency_detected
            }

            # Create proper analysis object
            website_analysis = WebsiteAnalysis(
                domain=urlparse(url).netloc,
                website_type=analysis_dict.get('website_type', 'unknown'),
                ecommerce_confidence=analysis_dict.get('ecommerce_confidence', 0.0),
                product_selectors=analysis_dict.get('product_selectors', {}),
                pagination_info=analysis_dict.get('pagination_info', {}),
                anti_bot_measures=analysis_dict.get('anti_bot_measures', []),
                recommended_tools=analysis_dict.get('recommended_tools', []),
                api_endpoints=analysis_dict.get('api_endpoints', []),
                content_language=analysis_dict.get('content_language', 'fa'),
                currency_detected=analysis_dict.get('currency_detected', 'IRR')
            )

            # Try API discovery
            api_endpoints = await self.api_discovery.discover_api_endpoints(url, website_analysis)

            if api_endpoints:
                # Try to use discovered APIs
                products = []
                for endpoint in api_endpoints[:3]:  # Limit to 3 endpoints
                    try:
                        api_result = await self.api_discovery.scrape_api_endpoint(endpoint)
                        if api_result.success and api_result.products:
                            products.extend(api_result.products)
                    except Exception as e:
                        logger.warning(f"API endpoint {endpoint} failed: {e}")
                        continue

                return ScrapingResult(
                    success=len(products) > 0,
                    products_found=len(products),
                    products=products,
                    tool_used="api_discovery",
                    execution_time=5.0,  # Estimated
                    errors=[],
                    metadata={"api_endpoints_discovered": len(api_endpoints)}
                )
            else:
                return ScrapingResult(
                    success=False,
                    products_found=0,
                    products=[],
                    tool_used="api_discovery",
                    execution_time=2.0,
                    errors=["No API endpoints found"],
                    metadata={}
                )

        except Exception as e:
            logger.error(f"API discovery failed: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="api_discovery",
                execution_time=0,
                errors=[str(e)],
                metadata={}
            )

    async def scrape_website_enhanced(self, url: str) -> ScrapingResult:
        """Enhanced scraping with intelligent strategy selection"""
        start_time = time.time()
        
        try:
            # Analyze website
            analysis = await self.analyzer.analyze_website(url)
            
            # Determine if this is an Iranian site
            is_iranian = self._is_iranian_domain(url)
            
            if is_iranian:
                logger.info(f"🇮🇷 Analyzing Iranian website: {url}")
                logger.info(f"🎯 Using Iranian-optimized strategy: {analysis.recommended_tools[0]} (confidence: {analysis.ecommerce_confidence:.2f})")
                
                # Use Iranian-specific strategy
                strategy = self._get_iranian_scraping_strategy(urlparse(url).netloc, analysis)
                return await self.scrape_with_strategy(url, strategy)
            else:
                logger.info(f"🔍 Analyzing website: {url}")
                logger.info(f"🎯 Using strategy: {analysis.recommended_tools[0]} (fallbacks: {analysis.recommended_tools[1:]})")
                
                # Use standard strategy
                strategy = ScrapingStrategy(
                    primary_tool=analysis.recommended_tools[0],
                    fallback_tools=analysis.recommended_tools[1:],
                    timeout_seconds=30,
                    retry_attempts=2
                )
                return await self.scrape_with_strategy(url, strategy)

        except Exception as e:
            logger.error(f"❌ Enhanced scraping failed for {url}: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="error",
                execution_time=time.time() - start_time,
                errors=[str(e)],
                metadata={"url": url}
            )

    def _update_performance_stats(self, domain: str, result: EnhancedScrapingResult):
        """Update performance statistics for domain"""
        if domain not in self.performance_stats:
            self.performance_stats[domain] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "avg_execution_time": 0,
                "avg_products_found": 0,
                "best_tool": None,
                "success_rate": 0.0
            }

        stats = self.performance_stats[domain]
        stats["total_attempts"] += 1

        if result.success:
            stats["successful_attempts"] += 1

        # Update averages
        stats["avg_execution_time"] = (
            (stats["avg_execution_time"] * (stats["total_attempts"] - 1)) + result.execution_time
        ) / stats["total_attempts"]

        if result.products_found > 0:
            stats["avg_products_found"] = (
                (stats["avg_products_found"] * (stats["total_attempts"] - 1)) + result.products_found
            ) / stats["total_attempts"]

        # Update success rate
        stats["success_rate"] = stats["successful_attempts"] / stats["total_attempts"]

        # Update best tool
        if result.success and (not stats["best_tool"] or result.products_found > stats["avg_products_found"]):
            stats["best_tool"] = result.tool_used

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "domains": self.performance_stats,
            "summary": {
                "total_domains": len(self.performance_stats),
                "total_attempts": sum(s["total_attempts"] for s in self.performance_stats.values()),
                "successful_attempts": sum(s["successful_attempts"] for s in self.performance_stats.values()),
                "overall_success_rate": sum(s["successful_attempts"] for s in self.performance_stats.values()) /
                                     max(1, sum(s["total_attempts"] for s in self.performance_stats.values()))
            }
        }

    # ==================== IRANIAN-SPECIFIC METHODS ====================

    async def _analyze_iranian_website(self, url: str) -> Dict[str, Any]:
        """Enhanced analysis specifically for Iranian websites"""
        domain = urlparse(url).netloc

        try:
            # First try the standard analysis
            analysis = await self.analyzer.analyze_website(url)

            # Convert to dictionary
            analysis_dict = {
                'domain': analysis.domain,
                'website_type': analysis.website_type,
                'ecommerce_confidence': analysis.ecommerce_confidence,
                'product_selectors': analysis.product_selectors,
                'pagination_info': analysis.pagination_info,
                'anti_bot_measures': analysis.anti_bot_measures,
                'recommended_tools': analysis.recommended_tools,
                'api_endpoints': analysis.api_endpoints,
                'content_language': analysis.content_language,
                'currency_detected': analysis.currency_detected
            }

            # Enhance with Iranian-specific patterns
            iranian_enhancements = await self._detect_iranian_patterns(url)

            # Merge enhancements
            analysis_dict.update({
                'iranian_patterns': iranian_enhancements,
                'persian_content_detected': iranian_enhancements.get('persian_ratio', 0) > 0.1,
                'toman_prices_detected': iranian_enhancements.get('toman_prices', False),
                'iranian_ecommerce_indicators': iranian_enhancements.get('ecommerce_indicators', 0)
            })

            return analysis_dict

        except Exception as e:
            logger.warning(f"❌ Iranian analysis failed for {domain}: {e}")
            return {
                'domain': domain,
                'website_type': 'unknown',
                'ecommerce_confidence': 0.0,
                'error': str(e),
                'iranian_patterns': {},
                'persian_content_detected': False,
                'toman_prices_detected': False,
                'iranian_ecommerce_indicators': 0
            }

    async def _detect_iranian_patterns(self, url: str) -> Dict[str, Any]:
        """Detect Iranian-specific patterns in website content"""
        patterns = {
            'persian_ratio': 0.0,
            'toman_prices': False,
            'rial_prices': False,
            'iranian_domains': False,
            'ecommerce_indicators': 0,
            'persian_brands': [],
            'iranian_cities': []
        }

        try:
            # Quick HTTP fetch for pattern detection
            headers = {'User-Agent': random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ])}

            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()

                    # Persian content ratio
                    persian_chars = len(re.findall(r'[\u0600-\u06FF]', html))
                    total_chars = len(html)
                    patterns['persian_ratio'] = persian_chars / max(1, total_chars)

                    # Iranian price patterns
                    toman_pattern = r'(\d{1,3}(?:,\d{3})*)\s*تومان'
                    rial_pattern = r'(\d{1,3}(?:,\d{3})*)\s*ریال'

                    patterns['toman_prices'] = bool(re.search(toman_pattern, html))
                    patterns['rial_prices'] = bool(re.search(rial_pattern, html))

                    # Iranian e-commerce indicators
                    iranian_indicators = [
                        'دیجی‌کالا', 'دیجی کالا', 'technolife', 'تکنولایف',
                        'mobit', 'موبیت', 'meghdadit', 'مقداد',
                        'سبد خرید', 'خرید آنلاین', 'فروشگاه آنلاین',
                        'قیمت', 'تخفیف', 'پیشنهاد ویژه'
                    ]

                    patterns['ecommerce_indicators'] = sum(1 for indicator in iranian_indicators if indicator in html)

                    # Iranian brands detection
                    iranian_brands = [
                        'سامسونگ', 'شیائومی', 'هواوی', 'اپل', 'ایفون',
                        'ایسوس', 'لنوو', 'ایسر', 'اچ‌پی'
                    ]
                    patterns['persian_brands'] = [brand for brand in iranian_brands if brand in html]

                    # Iranian cities
                    iranian_cities = ['تهران', 'اصفهان', 'مشهد', 'شیراز', 'تبریز', 'کرج']
                    patterns['iranian_cities'] = [city for city in iranian_cities if city in html]

        except Exception as e:
            logger.debug(f"Pattern detection failed for {url}: {e}")

        return patterns

    def _adjust_iranian_confidence(self, analysis: WebsiteAnalysis, domain: str, url: str) -> float:
        """Adjust confidence score based on Iranian market patterns"""
        base_confidence = analysis.ecommerce_confidence
        iranian_patterns = {}  # Default to empty dict since this attribute doesn't exist in WebsiteAnalysis

        # Iranian domain boost
        if self._is_iranian_domain(domain):
            base_confidence += 0.3

        # Persian content boost
        if iranian_patterns.get('persian_content_detected', False):
            base_confidence += 0.2

        # Toman price boost
        if iranian_patterns.get('toman_prices', False):
            base_confidence += 0.25

        # Iranian e-commerce indicators boost
        indicators = iranian_patterns.get('ecommerce_indicators', 0)
        if indicators > 0:
            base_confidence += min(0.2, indicators * 0.05)

        # Known Iranian vendor boost
        if self._is_known_iranian_vendor(domain):
            base_confidence += 0.4

        # Persian brands boost
        persian_brands = iranian_patterns.get('persian_brands', [])
        if persian_brands:
            base_confidence += min(0.15, len(persian_brands) * 0.05)

        # Cap at 1.0 and ensure minimum for Iranian sites
        adjusted_confidence = min(1.0, base_confidence)

        # For Iranian domains, ensure minimum confidence
        if self._is_iranian_domain(domain) and adjusted_confidence < 0.15:
            adjusted_confidence = 0.15

        logger.debug(f"🇮🇷 Confidence adjustment: {base_confidence:.2f} → {adjusted_confidence:.2f} for {domain}")

        return adjusted_confidence

    def _get_iranian_scraping_strategy(self, domain: str, analysis: WebsiteAnalysis) -> ScrapingStrategy:
        """Get optimal scraping strategy for Iranian websites"""
        iranian_patterns = {}  # Default to empty dict since this attribute doesn't exist in WebsiteAnalysis

        # Known Iranian vendors - use specific strategies
        if domain in ['digikala.com', 'www.digikala.com']:
            return ScrapingStrategy(
                primary_tool="selenium",
                fallback_tools=["iranian_http", "api_discovery"],
                timeout_seconds=60,
                retry_attempts=4,
                custom_selectors=self._get_digikala_selectors()
            )

        elif domain in ['technolife.ir', 'www.technolife.ir']:
            return ScrapingStrategy(
                primary_tool="selenium",
                fallback_tools=["iranian_http", "iranian_mobile"],
                timeout_seconds=45,
                retry_attempts=3,
                custom_selectors=self._get_technolife_selectors()
            )

        elif domain in ['mobit.ir', 'www.mobit.ir']:
            return ScrapingStrategy(
                primary_tool="iranian_http",
                fallback_tools=["selenium", "iranian_mobile"],
                timeout_seconds=30,
                retry_attempts=3,
                custom_selectors=self._get_mobiit_selectors()
            )

        # Generic Iranian e-commerce sites
        elif iranian_patterns.get('ecommerce_indicators', 0) > 2:
            return ScrapingStrategy(
                primary_tool="iranian_http",
                fallback_tools=["selenium", "iranian_mobile"],
                timeout_seconds=35,
                retry_attempts=3
            )

        # Heavy JavaScript sites
        elif analysis.website_type == 'spa':
            return ScrapingStrategy(
                primary_tool="selenium",
                fallback_tools=["iranian_http", "api_discovery"],
                timeout_seconds=50,
                retry_attempts=4
            )

        # Default strategy for unknown Iranian sites
        else:
            return ScrapingStrategy(
                primary_tool="iranian_http",
                fallback_tools=["selenium", "iranian_mobile"],
                timeout_seconds=30,
                retry_attempts=3
            )

    def _get_iranian_fallbacks(self, domain: str, analysis: WebsiteAnalysis) -> List[str]:
        """Get Iranian-specific fallback methods"""
        fallbacks = []

        # Always try Iranian-specific HTTP first
        fallbacks.append("iranian_http")

        # Add selenium if not heavily protected
        if len(analysis.anti_bot_measures) < 3:
            fallbacks.append("iranian_selenium")

        # Try mobile version for some sites
        if self._supports_mobile_version(domain):
            fallbacks.append("iranian_mobile")

        return fallbacks

    def _is_iranian_domain(self, domain: str) -> bool:
        """Check if domain is Iranian"""
        iranian_domains = [
            '.ir', 'digikala.com', 'technolife.ir', 'mobit.ir',
            'meghdadit.com', 'okala.com', 'torob.com', 'emalls.ir'
        ]
        return any(iranian_domain in domain for iranian_domain in iranian_domains)

    def _is_known_iranian_vendor(self, domain: str) -> bool:
        """Check if domain is a known Iranian e-commerce vendor"""
        known_vendors = [
            'digikala.com', 'www.digikala.com',
            'technolife.ir', 'www.technolife.ir',
            'mobit.ir', 'www.mobit.ir',
            'meghdadit.com', 'okala.com', 'emalls.ir'
        ]
        return domain in known_vendors

    def _categorize_iranian_domain(self, domain: str) -> str:
        """Categorize Iranian domain type"""
        if 'digikala' in domain:
            return "major_ecommerce"
        elif 'technolife' in domain or 'mobile' in domain:
            return "electronics_specialist"
        elif 'mobit' in domain or 'meghdadit' in domain:
            return "regional_ecommerce"
        else:
            return "unknown_iranian"

    def _supports_mobile_version(self, domain: str) -> bool:
        """Check if site supports mobile version"""
        mobile_supported = [
            'digikala.com', 'technolife.ir', 'mobit.ir'
        ]
        return any(supported in domain for supported in mobile_supported)

    def _get_digikala_selectors(self) -> Dict[str, List[str]]:
        """Get Digikala-specific selectors"""
        return {
            'product_containers': [
                '[data-product-id]', '.product-list-item', '.c-product-box',
                '.js-product-item', '[data-testid*="product"]'
            ],
            'title': [
                '.c-product-box__title', '.product-title', 'h2 a', 'h3 a',
                '[data-testid*="title"]', '.js-product-title'
            ],
            'price': [
                '.c-product-box__price', '.product-price', '.price-current',
                '[data-testid*="price"]', '.js-price', '.toman'
            ],
            'image': [
                '.c-product-box__img img', '.product-image img', 'img[alt*="product"]'
            ],
            'url': ['a', '.product-link'],
            'availability': ['.availability', '.stock-status', '.in-stock']
        }

    def _get_technolife_selectors(self) -> Dict[str, List[str]]:
        """Get Technolife-specific selectors"""
        return {
            'product_containers': [
                '.product-item', '.product', '.item',
                '.product-card', '.grid-item'
            ],
            'title': [
                '.product-title', '.title', 'h2', 'h3',
                '.product-name', '.item-title'
            ],
            'price': [
                '.price', '.product-price', '.cost', '.toman',
                '.price-current', '.final-price'
            ],
            'image': [
                '.product-image img', '.item-image img', 'img'
            ],
            'url': ['a', '.product-link', '.item-link'],
            'availability': ['.stock', '.available', '.موجود']
        }

    def _get_mobiit_selectors(self) -> Dict[str, List[str]]:
        """Get Mobit-specific selectors"""
        return {
            'product_containers': [
                '[class*="product"]', '.item', '.card',
                '.product-item', '.product-box'
            ],
            'title': [
                'h3', 'h4', '.title', '.product-title',
                '[class*="title"]', 'a[title]'
            ],
            'price': [
                '[class*="price"]', '.toman', '.rial',
                '.cost', '.amount', 'span:contains("تومان")'
            ],
            'image': [
                'img', '.image img', '.photo img'
            ],
            'url': ['a', '.link', '.product-link'],
            'availability': [
                '[class*="stock"]', '.available', '.موجود', '.ناموجود'
            ]
        }

    # ==================== IRANIAN-SPECIFIC SCRAPING METHODS ====================

    async def _scrape_with_iranian_http(self, url: str, analysis: WebsiteAnalysis) -> ScrapingResult:
        """Iranian-optimized HTTP scraping"""
        try:
            domain = urlparse(url).netloc

            # Initialize session if needed with Iranian SSL config
            if not self.session:
                ssl_config = self._get_iranian_ssl_config(domain)
                connector = aiohttp.TCPConnector(
                    ssl=ssl_config['ssl'],
                    **ssl_config['connector_kwargs']
                )
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )

            # Iranian-specific headers
            headers = {
                'User-Agent': self.random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ]),
                'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': f"https://{domain}/",
                'Cache-Control': 'no-cache',
            }

            async with self.session.get(url, headers=headers, timeout=25) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Use Iranian-specific selectors
                selectors = self._get_selectors_for_iranian_domain(domain)

                # Find product elements with Iranian patterns
                products = []
                for container_selector in selectors['product_containers']:
                    elements = soup.select(container_selector)
                    if elements:
                        logger.info(f"📦 Found {len(elements)} Iranian products with selector: {container_selector}")

                        for element in elements[:50]:  # Limit to 50 products
                            product = self._extract_iranian_product(element, selectors, domain)
                            if product:
                                products.append(product)

                        break  # Use first successful selector

                return ScrapingResult(
                    success=len(products) > 0,
                    products_found=len(products),
                    products=products,
                    tool_used="iranian_http",
                    execution_time=0.0,
                    errors=[],
                    metadata={"vendor": domain}
                )

        except Exception as e:
            logger.error(f"❌ Iranian HTTP scraping failed for {url}: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="iranian_http",
                execution_time=0.0,
                errors=[str(e)],
                metadata={"vendor": urlparse(url).netloc}
            )

    async def _scrape_with_iranian_selenium(self, url: str, analysis: WebsiteAnalysis) -> ScrapingResult:
        """Iranian-optimized Selenium scraping"""
        try:
            if not self.driver:
                self.setup_selenium_driver(headless=True)

            if not self.driver:
                raise Exception("Failed to initialize Selenium driver")

            domain = urlparse(url).netloc

            # Iranian-specific navigation
            logger.info(f"🤖 Iranian Selenium navigating to {url}")
            self.driver.get(url)

            # Wait for Iranian content to load
            await asyncio.sleep(3)

            # Handle Iranian anti-bot measures
            await self._handle_iranian_anti_bot(self.driver)

            # Use Iranian-specific selectors
            selectors = self._get_selectors_for_iranian_domain(domain)

            # Find product elements
            products = []
            for container_selector in selectors['product_containers']:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, container_selector)
                    if elements:
                        logger.info(f"📦 Found {len(elements)} Iranian products with selector: {container_selector}")

                        for element in elements[:50]:  # Limit to 50 products
                            product = self._extract_iranian_product_selenium(element, selectors, domain)
                            if product:
                                products.append(product)

                        break  # Use first successful selector
                except Exception as e:
                    logger.warning(f"⚠️ Selector failed: {container_selector} - {e}")
                    continue

            return ScrapingResult(
                success=len(products) > 0,
                products_found=len(products),
                products=products,
                tool_used="iranian_selenium",
                execution_time=0.0,
                errors=[],
                metadata={"vendor": domain}
            )

        except Exception as e:
            logger.error(f"❌ Iranian Selenium scraping failed for {url}: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="iranian_selenium",
                execution_time=0.0,
                errors=[str(e)],
                metadata={"vendor": urlparse(url).netloc}
            )

    async def _scrape_with_iranian_mobile(self, url: str, analysis: WebsiteAnalysis) -> ScrapingResult:
        """Scrape Iranian mobile version of websites"""
        try:
            # Convert to mobile URL
            mobile_url = url.replace('www.', 'm.') if 'www.' in url else url
            domain = urlparse(url).netloc

            # Initialize session if needed with Iranian SSL config
            if not self.session:
                ssl_config = self._get_iranian_ssl_config(domain)
                connector = aiohttp.TCPConnector(
                    ssl=ssl_config['ssl'],
                    **ssl_config['connector_kwargs']
                )
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )

            # Use mobile-specific headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Cache-Control': 'no-cache',
            }

            async with self.session.get(mobile_url, headers=headers, timeout=20) as response:
                if response.status != 200:
                    raise Exception(f"Mobile HTTP {response.status}")

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Use Iranian mobile-specific selectors
                selectors = self._get_selectors_for_iranian_domain(urlparse(mobile_url).netloc)

                # Find product elements with mobile-optimized patterns
                products = []
                for container_selector in selectors['mobile_containers']:
                    elements = soup.select(container_selector)
                    if elements:
                        logger.info(f"📱 Found {len(elements)} Iranian mobile products with selector: {container_selector}")

                        for element in elements[:50]:  # Limit to 50 products
                            product = self._extract_iranian_product(element, selectors, urlparse(mobile_url).netloc)
                            if product:
                                products.append(product)

                        break  # Use first successful selector

                return ScrapingResult(
                    success=len(products) > 0,
                    products_found=len(products),
                    products=products,
                    tool_used="iranian_mobile",
                    execution_time=0.0,
                    errors=[],
                    metadata={"vendor": urlparse(mobile_url).netloc}
                )

        except Exception as e:
            logger.error(f"❌ Iranian mobile scraping failed for {url}: {e}")
            return ScrapingResult(
                success=False,
                products_found=0,
                products=[],
                tool_used="iranian_mobile",
                execution_time=0.0,
                errors=[str(e)],
                metadata={"vendor": urlparse(url).netloc}
            )

    async def _handle_iranian_anti_bot(self):
        """Handle Iranian-specific anti-bot measures"""
        try:
            # Iranian-specific waiting patterns
            await asyncio.sleep(random.uniform(2, 4))

            # Check for Iranian CAPTCHAs
            iranian_captcha_selectors = [
                '.captcha', '#captcha', '[data-captcha]',
                '.recaptcha', '.cloudflare',
                ':contains("لطفا")', ':contains("انتظار")'  # Persian wait messages
            ]

            for selector in iranian_captcha_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.warning(f"⚠️ Iranian CAPTCHA detected: {selector}")
                        await asyncio.sleep(5)
                        break
                except:
                    continue

            # Iranian-specific mouse movement
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(50, 200), random.randint(50, 150))
            actions.perform()

        except Exception as e:
            logger.debug(f"⚠️ Iranian anti-bot handling error: {e}")

    async def _iranian_scroll_and_wait(self):
        """Iranian-specific scrolling to load dynamic content"""
        try:
            # Multiple scroll attempts for Iranian sites
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(random.uniform(1.5, 3))

                # Check for "Load More" in Persian
                load_more_selectors = [
                    '.load-more', '.show-more', '.بیشتر', '.ادامه',
                    '[data-load-more]', '.pagination-next',
                    'button:contains("بیشتر")', 'a:contains("ادامه")'
                ]

                for selector in load_more_selectors:
                    try:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                self.driver.execute_script("arguments[0].click();", button)
                                await asyncio.sleep(random.uniform(2, 4))
                                break
                    except:
                        continue

        except Exception as e:
            logger.debug(f"⚠️ Iranian scroll error: {e}")

    def _get_selectors_for_iranian_domain(self, domain: str) -> Dict[str, List[str]]:
        """Get appropriate selectors for Iranian domains"""
        if 'digikala' in domain:
            return self._get_digikala_selectors()
        elif 'technolife' in domain:
            return self._get_technolife_selectors()
        elif 'mobit' in domain:
            return self._get_mobiit_selectors()
        else:
            # Generic Iranian selectors
            return {
                'product_containers': [
                    '[class*="product"]', '[class*="item"]', '.card', '.box',
                    '.product-item', '.product-card', '[data-product]',
                    '[class*="کالا"]', '[class*="محصول"]'  # Persian product terms
                ],
                'title': [
                    'h1', 'h2', 'h3', '.title', '.name', '.product-title',
                    '[class*="title"]', 'a[title]',
                    '[class*="نام"]', '[class*="عنوان"]'  # Persian title terms
                ],
                'price': [
                    '[class*="price"]', '.toman', '.rial', '.cost', '.amount',
                    'span:contains("تومان")', 'span:contains("ریال")',
                    '[class*="قیمت"]', '[class*="مبلغ"]'  # Persian price terms
                ],
                'image': ['img', '.image img', '.photo img', '.pic img'],
                'url': ['a', '.link', '.product-link', '[href]'],
                'availability': [
                    '[class*="stock"]', '.available', '.موجود', '.ناموجود',
                    '[class*="موجودی"]'  # Persian availability terms
                ]
            }

    def _extract_iranian_product(self, element, selectors: Dict, domain: str) -> Optional[ProductData]:
        """Extract product data from Iranian e-commerce sites"""
        try:
            # Extract title with Persian support
            title = ""
            for title_selector in selectors.get('title', []):
                title_elem = element.select_one(title_selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Clean Persian text
                    title = self._clean_persian_text(title)
                    if title and len(title) > 2:
                        break

            if not title:
                return None

            # Extract price with Iranian currency support
            price_toman = 0
            for price_selector in selectors.get('price', []):
                price_elem = element.select_one(price_selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_toman = self._parse_iranian_price(price_text)
                    if price_toman > 0:
                        break

            # Skip if no valid price
            if price_toman == 0:
                return None

            # Extract image URL
            image_url = ""
            for img_selector in selectors.get('image', []):
                img_elem = element.select_one(img_selector)
                if img_elem:
                    src = img_elem.get('src') or img_elem.get('data-src')
                    if src:
                        image_url = src if src.startswith('http') else f"https://{domain}{src}"
                        break

            # Extract product URL
            product_url = ""
            for url_selector in selectors.get('url', []):
                url_elem = element.select_one(url_selector)
                if url_elem:
                    href = url_elem.get('href')
                    if href:
                        product_url = href if href.startswith('http') else f"https://{domain}{href}"
                        break

            # Calculate USD price (using current rate)
            price_usd = round(price_toman / self.exchange_rate, 2)

            # Generate product ID
            product_id = f"IRAN{hashlib.md5(f'{domain}{title}{price_toman}'.encode()).hexdigest()[:8]}"

            return ProductData(
                product_id=product_id,
                title=title,
                title_fa=title,  # Would need translation service
                price_toman=price_toman,
                price_usd=price_usd,
                vendor=domain,
                vendor_name_fa=self._get_iranian_vendor_name(domain),
                availability=True,  # Assume available if listed
                product_url=product_url,
                image_url=image_url,
                category="mobile",  # Default category
                last_updated=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.debug(f"⚠️ Error extracting Iranian product: {e}")
            return None

    async def _extract_iranian_product_selenium(self, element, selectors: Dict, domain: str) -> Optional[ProductData]:
        """Extract product data from Iranian sites using Selenium"""
        try:
            # Extract title
            title = ""
            for title_selector in selectors.get('title', []):
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, title_selector)
                    title = title_elem.text.strip()
                    title = self._clean_persian_text(title)
                    if title and len(title) > 2:
                        break
                except:
                    continue

            if not title:
                return None

            # Extract price
            price_toman = 0
            for price_selector in selectors.get('price', []):
                try:
                    price_elem = element.find_element(By.CSS_SELECTOR, price_selector)
                    price_text = price_elem.text.strip()
                    price_toman = self._parse_iranian_price(price_text)
                    if price_toman > 0:
                        break
                except:
                    continue

            if price_toman == 0:
                return None

            # Extract image
            image_url = ""
            for img_selector in selectors.get('image', []):
                try:
                    img_elem = element.find_element(By.CSS_SELECTOR, img_selector)
                    src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
                    if src:
                        image_url = src if src.startswith('http') else f"https://{domain}{src}"
                        break
                except:
                    continue

            # Extract URL
            product_url = ""
            for url_selector in selectors.get('url', []):
                try:
                    url_elem = element.find_element(By.CSS_SELECTOR, url_selector)
                    href = url_elem.get_attribute('href')
                    if href:
                        product_url = href if href.startswith('http') else f"https://{domain}{href}"
                        break
                except:
                    continue

            # Calculate USD price
            price_usd = round(price_toman / self.exchange_rate, 2)

            # Generate product ID
            product_id = f"IRAN{hashlib.md5(f'{domain}{title}{price_toman}'.encode()).hexdigest()[:8]}"

            return ProductData(
                product_id=product_id,
                title=title,
                title_fa=title,
                price_toman=price_toman,
                price_usd=price_usd,
                vendor=domain,
                vendor_name_fa=self._get_iranian_vendor_name(domain),
                availability=True,
                product_url=product_url,
                image_url=image_url,
                category="mobile",
                last_updated=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.debug(f"⚠️ Error extracting Iranian product with Selenium: {e}")
            return None

    def _clean_persian_text(self, text: str) -> str:
        """Clean and normalize Persian text"""
        if not text:
            return ""

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Convert Persian numbers to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        text = text.translate(persian_to_english)

        # Remove common Persian noise words
        noise_words = ['قیمت', 'تومان', 'ریال', 'خرید', 'فروش', 'تخفیف']
        for word in noise_words:
            text = text.replace(word, '')

        return text.strip()

    def _parse_iranian_price(self, price_text: str) -> int:
        """Parse Iranian price text with Persian number support"""
        if not price_text:
            return 0

        # Convert Persian digits to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        price_text = price_text.translate(persian_to_english)

        # Iranian price patterns
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*تومان',
            r'(\d{1,3}(?:,\d{3})*)\s*ریال',
            r'(\d{1,3}(?:,\d{3})*)\s*toman',
            r'(\d{1,3}(?:,\d{3})*)\s*rial',
            r'قیمت[:\s]*(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)'
        ]

        for pattern in patterns:
            match = re.search(pattern, price_text)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    price = int(price_str)

                    # Convert rial to toman if needed
                    if 'ریال' in price_text.lower() or 'rial' in price_text.lower():
                        if price > 100000:  # Likely needs conversion
                            price = price // 10

                    # Validate reasonable price range
                    if 10000 <= price <= 500000000:  # 10k to 500M toman
                        return price

                except ValueError:
                    continue

        return 0

    def _get_iranian_vendor_name(self, domain: str) -> str:
        """Get Persian name for Iranian vendor"""
        vendor_names = {
            'digikala.com': 'دیجی‌کالا',
            'www.digikala.com': 'دیجی‌کالا',
            'technolife.ir': 'تکنولایف',
            'www.technolife.ir': 'تکنولایف',
            'mobit.ir': 'موبیت',
            'www.mobit.ir': 'موبیت',
            'meghdadit.com': 'مقداد',
            'okala.com': 'اکالا',
            'emalls.ir': 'ایملز',
            'torob.com': 'ترب'
        }

        return vendor_names.get(domain, domain.split('.')[0].title())
