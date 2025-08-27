#!/usr/bin/env python3
"""
Vendor Discovery Agent - Uses search service and AI agents to discover new Iranian vendors
and dynamically expand product catalogs based on market trends
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from services.search_service import SearXNGSearchService
from services.scraper.selenium_scraper import AsyncIranianSeleniumScraper
from services.scraper.real_scraper import ProductData

logger = logging.getLogger(__name__)

class VendorDiscoveryAgent:
    """
    AI-powered agent that discovers new Iranian e-commerce vendors
    and expands product catalogs dynamically
    """

    def __init__(self, redis_client=None, searxng_url: str = "http://87.236.166.7:8080"):
        self.redis_client = redis_client
        self.search_service = SearXNGSearchService(searxng_url)
        self.selenium_scraper = AsyncIranianSeleniumScraper()
        self.discovered_vendors = set()
        self.product_categories = {
            'mobile': ['گوشی موبایل', 'گوشی هوشمند', 'smartphone', 'mobile phone'],
            'laptop': ['لپ تاپ', 'نوت بوک', 'laptop', 'notebook'],
            'tablet': ['تبلت', 'tablet'],
            'tv': ['تلویزیون', 'smart tv', 'LED TV'],
            'console': ['کنسول بازی', 'playstation', 'xbox', 'gaming console'],
            'headphone': ['هدفون', 'هدست', 'earphone', 'headset'],
            'camera': ['دوربین', 'camera', 'DSLR'],
            'smartwatch': ['ساعت هوشمند', 'smartwatch', 'wearable']
        }

    async def discover_new_vendors(self, category: str = "mobile", max_vendors: int = 10) -> List[Dict]:
        """
        Discover new Iranian e-commerce vendors using search service
        """
        try:
            logger.info(f"🔍 Discovering new vendors for category: {category}")

            # Use search service to find vendor sources
            async with self.search_service as search:
                search_results = await search.discover_new_sources(category)

            # Filter and validate discovered vendors
            new_vendors = []
            known_domains = await self._get_known_vendor_domains()

            for result in search_results:
                domain = self._extract_domain(result['url'])

                # Skip if already known
                if domain in known_domains:
                    continue

                # Validate if it's a real e-commerce site
                if await self._validate_ecommerce_site(result['url'], category):
                    vendor_info = {
                        'domain': domain,
                        'name': result.get('title', domain),
                        'url': result['url'],
                        'category': category,
                        'source': result.get('source', 'search'),
                        'relevance_score': result.get('relevance_score', 0),
                        'discovered_at': datetime.now(timezone.utc).isoformat()
                    }

                    new_vendors.append(vendor_info)
                    self.discovered_vendors.add(domain)

                    # Store in Redis for future reference
                    if self.redis_client:
                        vendor_key = f"discovered_vendor:{domain}"
                        await self.redis_client.hset(vendor_key, mapping=vendor_info)
                        await self.redis_client.expire(vendor_key, 86400 * 30)  # 30 days

                if len(new_vendors) >= max_vendors:
                    break

            logger.info(f"✅ Discovered {len(new_vendors)} new vendors for {category}")
            return new_vendors

        except Exception as e:
            logger.error(f"❌ Error discovering vendors: {e}")
            return []

    async def expand_product_catalog(self, vendor_info: Dict, ai_agent) -> List[ProductData]:
        """
        Use AI agent to expand product catalog for a discovered vendor
        """
        try:
            logger.info(f"🤖 Expanding catalog for vendor: {vendor_info['domain']}")

            # Get existing products in this category
            existing_products = await self._get_existing_products(vendor_info['category'])

            # Ask AI agent to suggest new products to monitor
            task = f"""
            Based on the Iranian market trends and the following existing products in the {vendor_info['category']} category:

            {', '.join([p.title for p in existing_products[:10]])}

            Suggest 5-10 new trending products that should be monitored on {vendor_info['domain']}.
            Focus on:
            1. Popular Iranian market trends
            2. Seasonal products
            3. High-demand items with price volatility
            4. New product releases

            Return the suggestions as a JSON list with product names and categories.
            """

            response = await ai_agent.run_agent("product_discovery", task)

            # Parse AI response and generate product suggestions
            new_products = await self._parse_ai_product_suggestions(response, vendor_info)

            # Try to scrape actual products from the vendor site
            scraped_products = []
            if vendor_info['url']:
                try:
                    result = await self.selenium_scraper.scrape_site(
                        vendor_info['domain'],
                        vendor_info['url'],
                        vendor_info['category'],
                        max_products=15
                    )
                    if result.success:
                        scraped_products = result.products
                        logger.info(f"✅ Scraped {len(scraped_products)} products from {vendor_info['domain']}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not scrape {vendor_info['domain']}: {e}")

            # Combine AI suggestions with scraped products
            expanded_catalog = new_products + scraped_products

            # Store expanded catalog
            await self._store_expanded_catalog(vendor_info, expanded_catalog)

            logger.info(f"📦 Expanded catalog for {vendor_info['domain']}: {len(expanded_catalog)} products")
            return expanded_catalog

        except Exception as e:
            logger.error(f"❌ Error expanding catalog: {e}")
            return []

    async def monitor_market_trends(self, ai_agent) -> Dict:
        """
        Monitor market trends and suggest new categories/products to track
        """
        try:
            logger.info("📊 Monitoring market trends...")

            # Get current market data
            market_data = await self._get_market_overview()

            # Ask AI agent to analyze trends
            task = f"""
            Analyze the following Iranian e-commerce market data and identify trends:

            Current tracked categories: {list(self.product_categories.keys())}
            Market data: {market_data}

            Identify:
            1. Emerging product categories that should be tracked
            2. Seasonal trends affecting prices
            3. New vendor types entering the market
            4. Products with high price volatility potential

            Return analysis as JSON with specific recommendations.
            """

            response = await ai_agent.run_agent("market_intelligence", task)

            # Parse AI recommendations
            trends_analysis = await self._parse_trend_analysis(response)

            # Store trend analysis
            if self.redis_client:
                trend_key = f"market_trends:{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}"
                await self.redis_client.setex(trend_key, 86400, json.dumps(trends_analysis))

            return trends_analysis

        except Exception as e:
            logger.error(f"❌ Error monitoring trends: {e}")
            return {}

    async def _validate_ecommerce_site(self, url: str, category: str) -> bool:
        """
        Validate if a discovered URL is a real e-commerce site
        """
        try:
            # Quick check using selenium scraper
            result = await self.selenium_scraper.scrape_site(
                self._extract_domain(url),
                url,
                category,
                max_products=1
            )
            return result.success and len(result.products) > 0
        except:
            return False

    async def _get_known_vendor_domains(self) -> Set[str]:
        """Get list of already known vendor domains"""
        known_domains = {
            'digikala.com', 'technolife.ir', 'meghdadit.com',
            'bazaar.ir', 'torob.com', 'emalls.ir'
        }

        # Add discovered vendors from Redis
        if self.redis_client:
            discovered_keys = await self.redis_client.keys("discovered_vendor:*")
            for key in discovered_keys:
                domain = key.split(":")[1]
                known_domains.add(domain)

        return known_domains

    async def _get_existing_products(self, category: str) -> List[ProductData]:
        """Get existing products in a category"""
        if not self.redis_client:
            return []

        product_keys = await self.redis_client.keys("product:*")
        existing_products = []

        for key in product_keys[:50]:  # Limit for performance
            product_data = await self.redis_client.hgetall(key)
            if product_data.get(b'category', b'').decode() == category:
                existing_products.append(ProductData(
                    product_id=product_data.get(b'product_id', b'').decode(),
                    title=product_data.get(b'title', b'').decode(),
                    title_fa=product_data.get(b'title_fa', b'').decode(),
                    price_toman=int(product_data.get(b'price_toman', b'0').decode()),
                    price_usd=float(product_data.get(b'price_usd', b'0').decode()),
                    vendor=product_data.get(b'vendor', b'').decode(),
                    vendor_name_fa=product_data.get(b'vendor_name_fa', b'').decode(),
                    availability=bool(int(product_data.get(b'availability', b'1').decode())),
                    product_url=product_data.get(b'product_url', b'').decode(),
                    image_url=product_data.get(b'image_url', b'').decode(),
                    category=category,
                    last_updated=product_data.get(b'last_updated', b'').decode()
                ))

        return existing_products

    async def _parse_ai_product_suggestions(self, ai_response, vendor_info: Dict) -> List[ProductData]:
        """Parse AI agent response for product suggestions"""
        try:
            # Extract content from AI response
            if hasattr(ai_response, 'choices') and ai_response.choices:
                content = ai_response.choices[0].message.content
            else:
                content = str(ai_response)

            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())

                products = []
                for suggestion in suggestions.get('products', []):
                    product = ProductData(
                        product_id=f"AI{int(asyncio.get_event_loop().time())}{random.randint(100, 999)}",
                        title=suggestion.get('name', 'Unknown Product'),
                        title_fa=suggestion.get('name_fa', suggestion.get('name', 'Unknown Product')),
                        price_toman=0,  # Will be updated by scraper
                        price_usd=0,
                        vendor=vendor_info['domain'],
                        vendor_name_fa=vendor_info.get('name', vendor_info['domain']),
                        availability=False,  # Not yet scraped
                        product_url="",
                        image_url="",
                        category=suggestion.get('category', vendor_info['category']),
                        last_updated=datetime.now(timezone.utc).isoformat()
                    )
                    products.append(product)

                return products

        except Exception as e:
            logger.warning(f"⚠️ Could not parse AI suggestions: {e}")

        return []

    async def _get_market_overview(self) -> Dict:
        """Get current market overview data"""
        if not self.redis_client:
            return {}

        try:
            # Get basic market stats
            product_keys = await self.redis_client.keys("product:*")
            vendor_analysis = await self.redis_client.hgetall("scraping_summary")

            return {
                'total_products': len(product_keys),
                'last_update': vendor_analysis.get(b'last_updated', b'').decode() if vendor_analysis else None,
                'vendors': vendor_analysis.get(b'vendors', b'').decode() if vendor_analysis else None
            }
        except:
            return {}

    async def _parse_trend_analysis(self, ai_response) -> Dict:
        """Parse AI trend analysis response"""
        try:
            if hasattr(ai_response, 'choices') and ai_response.choices:
                content = ai_response.choices[0].message.content
            else:
                content = str(ai_response)

            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"analysis": content}

    async def _store_expanded_catalog(self, vendor_info: Dict, products: List[ProductData]):
        """Store expanded catalog in Redis"""
        if not self.redis_client:
            return

        catalog_key = f"expanded_catalog:{vendor_info['domain']}"
        catalog_data = {
            'vendor': vendor_info['domain'],
            'category': vendor_info['category'],
            'product_count': len(products),
            'products': [p.product_id for p in products],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

        await self.redis_client.setex(catalog_key, 86400 * 7, json.dumps(catalog_data))

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc

    async def close(self):
        """Close resources"""
        await self.selenium_scraper.close()
