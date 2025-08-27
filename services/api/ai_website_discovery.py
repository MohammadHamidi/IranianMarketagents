#!/usr/bin/env python3
"""
AI-powered Iranian e-commerce website discovery service
"""

import asyncio
import aiohttp
import json
import logging
import re
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WebsiteCandidate:
    """Represents a potential Iranian e-commerce website"""
    domain: str
    name: str
    url: str
    category: str
    confidence_score: float
    discovered_at: str
    indicators: List[str]  # What made us think this is an e-commerce site

@dataclass
class DiscoveryResult:
    """Result of website discovery process"""
    candidates: List[WebsiteCandidate]
    searched_sources: List[str]
    total_searched: int
    processing_time: float

class AIWebsiteDiscovery:
    """
    AI-powered service for discovering Iranian e-commerce websites
    """

    def __init__(self):
        self.session = None
        self.redis_client = None

        # Iranian TLDs and common patterns
        self.iranian_domains = [
            '.ir', '.com', '.net', '.org', '.co'
        ]

        # Keywords that indicate e-commerce sites (Persian and English)
        self.ecommerce_keywords = [
            # Persian keywords
            'فروشگاه', 'فروش', 'محصول', 'قیمت', 'سبد خرید', 'خرید',
            'کالا', 'سفارش', 'ارسال', 'پرداخت', 'تخفیف', 'فروشگاه آنلاین',
            'موبایل', 'لپ تاپ', 'تبلت', 'گوشی', 'گجت', 'الکترونیک',
            'دیجی کالا', 'تکنولایف', 'مقداد', 'اسنپ', 'بازار',

            # English keywords
            'shop', 'store', 'product', 'price', 'cart', 'buy', 'purchase',
            'order', 'shipping', 'payment', 'discount', 'online store',
            'mobile', 'laptop', 'tablet', 'phone', 'gadget', 'electronics',
            'market', 'mall', 'retail', 'commerce', 'shopping'
        ]

        # Sources to search for websites
        self.search_sources = [
            "https://www.google.com/search?q=site:.ir+فروشگاه+آنلاین+موبایل",
            "https://www.google.com/search?q=site:.ir+فروشگاه+الکترونیکی",
            "https://www.google.com/search?q=iranian+online+store+electronics",
            "https://www.bing.com/search?q=site:.ir+فروشگاه+موبایل",
            "https://search.yahoo.com/search?q=iran+online+shopping+electronics"
        ]

        # Known Iranian e-commerce sites (for reference)
        self.known_sites = {
            'digikala.com', 'technolife.ir', 'meghdadit.com', 'snap.ir',
            'bazaar.ir', 'torob.com', 'sheypoor.com', 'divar.ir'
        }

    async def initialize(self):
        """Initialize HTTP session and Redis connection"""
        connector = aiohttp.TCPConnector(verify_ssl=False, limit=10)
        self.session = aiohttp.ClientSession(connector=connector)

        redis_url = os.getenv('REDIS_URL', 'redis://:iranian_redis_secure_2025@localhost:6379/1')
        self.redis_client = redis.from_url(redis_url)
        await self.redis_client.ping()
        logger.info("✅ AI Website Discovery service initialized")

    async def close(self):
        """Close connections"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()

    async def discover_websites(self, search_terms: List[str] = None) -> DiscoveryResult:
        """
        Discover new Iranian e-commerce websites using AI-powered analysis
        """
        start_time = datetime.now(timezone.utc)

        if search_terms is None:
            search_terms = [
                "فروشگاه آنلاین ایران موبایل",
                "iranian online store electronics",
                "فروشگاه دیجیتال ایران",
                "persian online shopping"
            ]

        candidates = []
        searched_sources = []

        try:
            # Search from multiple sources
            for source_url in self.search_sources[:2]:  # Limit to avoid being blocked
                try:
                    source_candidates = await self._search_source(source_url)
                    candidates.extend(source_candidates)
                    searched_sources.append(source_url)
                    await asyncio.sleep(2)  # Respectful delay
                except Exception as e:
                    logger.warning(f"Error searching {source_url}: {e}")
                    continue

            # Analyze discovered domains
            unique_candidates = self._filter_candidates(candidates)

            # Score and rank candidates
            scored_candidates = await self._score_candidates(unique_candidates)

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = DiscoveryResult(
                candidates=scored_candidates,
                searched_sources=searched_sources,
                total_searched=len(searched_sources),
                processing_time=processing_time
            )

            # Store results in Redis for future reference
            await self._store_discovery_results(result)

            logger.info(f"✅ Website discovery completed: {len(scored_candidates)} candidates found")
            return result

        except Exception as e:
            logger.error(f"❌ Website discovery failed: {e}")
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return DiscoveryResult(
                candidates=[],
                searched_sources=searched_sources,
                total_searched=len(searched_sources),
                processing_time=processing_time
            )

    async def _search_source(self, source_url: str) -> List[WebsiteCandidate]:
        """Search a specific source for Iranian e-commerce websites"""
        candidates = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }

            async with self.session.get(source_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extract potential website links
                    links = soup.find_all('a', href=True)

                    for link in links:
                        href = link.get('href')
                        title = link.get_text(strip=True)

                        # Extract domain from URL
                        domain = self._extract_domain(href)
                        if domain and self._is_iranian_domain(domain):
                            candidate = WebsiteCandidate(
                                domain=domain,
                                name=title or domain.split('.')[0].title(),
                                url=f"https://www.{domain}",
                                category="unknown",
                                confidence_score=0.5,  # Initial score
                                discovered_at=datetime.now(timezone.utc).isoformat(),
                                indicators=["search_result"]
                            )
                            candidates.append(candidate)

        except Exception as e:
            logger.warning(f"Error searching source {source_url}: {e}")

        return candidates

    async def _analyze_website(self, candidate: WebsiteCandidate) -> WebsiteCandidate:
        """Analyze a website to determine if it's an e-commerce site and gather more info"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
            }

            async with self.session.get(candidate.url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Analyze page content
                    page_text = soup.get_text().lower()
                    indicators = []

                    # Check for e-commerce indicators
                    for keyword in self.ecommerce_keywords:
                        if keyword.lower() in page_text:
                            indicators.append(f"keyword:{keyword}")

                    # Check for shopping cart elements
                    if soup.find(['div', 'a'], class_=re.compile(r'cart|basket|سبد')):
                        indicators.append("shopping_cart")

                    # Check for product listings
                    if soup.find(['div', 'section'], class_=re.compile(r'product|کالا|محصول')):
                        indicators.append("product_listing")

                    # Check for price patterns
                    price_patterns = [r'\d{1,3}(?:,\d{3})+', r'تومان', r'toman', r'ریال', r'rial']
                    for pattern in price_patterns:
                        if re.search(pattern, page_text):
                            indicators.append("price_pattern")

                    # Determine category
                    category = "general"
                    if any(word in page_text for word in ['موبایل', 'گوشی', 'mobile', 'phone']):
                        category = "mobile"
                    elif any(word in page_text for word in ['لپ تاپ', 'laptop']):
                        category = "laptop"
                    elif any(word in page_text for word in ['تبلت', 'tablet']):
                        category = "tablet"

                    # Calculate confidence score
                    base_score = 0.5
                    score_multiplier = 1.0

                    if len(indicators) > 3:
                        score_multiplier = 1.5
                    elif len(indicators) > 1:
                        score_multiplier = 1.2

                    # Boost score for Persian content
                    if any('\u0600' <= char <= '\u06FF' for char in page_text):
                        score_multiplier *= 1.1

                    confidence_score = min(base_score * score_multiplier, 0.95)

                    # Update candidate
                    candidate.category = category
                    candidate.confidence_score = confidence_score
                    candidate.indicators = indicators

                    # Try to get better name from page title
                    title_tag = soup.find('title')
                    if title_tag and len(title_tag.get_text(strip=True)) > len(candidate.name):
                        candidate.name = title_tag.get_text(strip=True)[:100]  # Limit length

        except Exception as e:
            logger.warning(f"Error analyzing {candidate.domain}: {e}")
            candidate.indicators = ["analysis_failed"]

        return candidate

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        if not url:
            return None

        # Handle relative URLs
        if url.startswith('/'):
            return None

        # Extract domain using regex
        domain_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)'
        match = re.search(domain_pattern, url)
        if match:
            return match.group(1).lower()
        return None

    def _is_iranian_domain(self, domain: str) -> bool:
        """Check if domain appears to be Iranian"""
        if not domain:
            return False

        # Check for Iranian TLD
        if any(domain.endswith(tld) for tld in ['.ir']):
            return True

        # Check for Persian words in domain
        persian_words = ['digikala', 'technolife', 'meghdad', 'snap', 'bazaar', 'torob']
        domain_lower = domain.lower()
        if any(word in domain_lower for word in persian_words):
            return True

        return False

    def _filter_candidates(self, candidates: List[WebsiteCandidate]) -> List[WebsiteCandidate]:
        """Filter and deduplicate candidates"""
        seen_domains = set()
        filtered = []

        for candidate in candidates:
            if candidate.domain not in seen_domains and candidate.domain not in self.known_sites:
                seen_domains.add(candidate.domain)
                filtered.append(candidate)

        return filtered

    async def _score_candidates(self, candidates: List[WebsiteCandidate]) -> List[WebsiteCandidate]:
        """Score and rank candidates by analyzing their websites"""
        logger.info(f"🔍 Analyzing {len(candidates)} website candidates...")

        # Analyze each candidate
        analyzed_candidates = []
        for i, candidate in enumerate(candidates[:10]):  # Limit analysis to top candidates
            logger.info(f"📊 Analyzing candidate {i+1}/{min(len(candidates), 10)}: {candidate.domain}")
            analyzed = await self._analyze_website(candidate)
            analyzed_candidates.append(analyzed)
            await asyncio.sleep(1)  # Respectful delay

        # Sort by confidence score
        analyzed_candidates.sort(key=lambda x: x.confidence_score, reverse=True)

        return analyzed_candidates

    async def _store_discovery_results(self, result: DiscoveryResult):
        """Store discovery results in Redis for future reference"""
        try:
            discovery_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_candidates': len(result.candidates),
                'searched_sources': result.searched_sources,
                'processing_time': result.processing_time,
                'top_candidates': [
                    {
                        'domain': candidate.domain,
                        'name': candidate.name,
                        'category': candidate.category,
                        'confidence_score': candidate.confidence_score,
                        'indicators': candidate.indicators
                    }
                    for candidate in result.candidates[:5]  # Store top 5
                ]
            }

            await self.redis_client.setex(
                f'website_discovery:{int(datetime.now(timezone.utc).timestamp())}',
                86400 * 7,  # 7 days
                json.dumps(discovery_data, ensure_ascii=False)
            )

        except Exception as e:
            logger.warning(f"Error storing discovery results: {e}")

    async def get_discovery_history(self, limit: int = 10) -> List[Dict]:
        """Get recent website discovery results"""
        try:
            keys = await self.redis_client.keys('website_discovery:*')
            if not keys:
                return []

            # Get most recent results
            recent_keys = sorted(keys, reverse=True)[:limit]
            results = []

            for key in recent_keys:
                data = await self.redis_client.get(key)
                if data:
                    results.append(json.loads(data.decode()))

            return results

        except Exception as e:
            logger.error(f"Error getting discovery history: {e}")
            return []

    async def suggest_websites_for_monitoring(self, min_score: float = 0.7) -> List[WebsiteCandidate]:
        """Suggest websites that should be added for monitoring"""
        try:
            # Get recent discoveries
            history = await self.get_discovery_history(limit=5)

            suggestions = []
            for discovery in history:
                for candidate in discovery.get('top_candidates', []):
                    if candidate['confidence_score'] >= min_score:
                        suggestions.append(WebsiteCandidate(
                            domain=candidate['domain'],
                            name=candidate['name'],
                            url=f"https://www.{candidate['domain']}",
                            category=candidate['category'],
                            confidence_score=candidate['confidence_score'],
                            discovered_at=discovery['timestamp'],
                            indicators=candidate['indicators']
                        ))

            # Remove duplicates
            seen_domains = set()
            unique_suggestions = []
            for suggestion in suggestions:
                if suggestion.domain not in seen_domains:
                    seen_domains.add(suggestion.domain)
                    unique_suggestions.append(suggestion)

            return unique_suggestions[:10]  # Return top 10

        except Exception as e:
            logger.error(f"Error getting website suggestions: {e}")
            return []</contents>
</xai:function_call
