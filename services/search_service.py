import aiohttp
import asyncio
from typing import List, Dict, Optional
import json
from urllib.parse import urlencode
import logging

class SearXNGSearchService:
    """
    Search service using your SearXNG instance for discovery
    Keeps existing scraping functionality separate
    """
    
    def __init__(self, searxng_url: str = "http://87.236.166.7:8080"):
        self.searxng_url = searxng_url.rstrip('/')
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_iranian_products(
        self, 
        query: str, 
        categories: List[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for Iranian products using SearXNG
        Returns structured results for further processing
        """
        try:
            # Enhance query with Iranian market terms
            enhanced_query = f"{query} Iran Iranian market price"
            if categories:
                enhanced_query += " " + " OR ".join(categories)
            
            params = {
                'q': enhanced_query,
                'format': 'json',
                'engines': 'google,bing,duckduckgo',  # Fallback engines
                'categories': 'general,shopping',
                'language': 'fa',  # Persian language preference
                'pageno': 1
            }
            
            search_url = f"{self.searxng_url}/search"
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_search_results(data.get('results', []), limit)
                else:
                    self.logger.error(f"SearXNG search failed: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            return []
    
    def _process_search_results(self, results: List[Dict], limit: int) -> List[Dict]:
        """Process and filter SearXNG results for Iranian market relevance"""
        processed = []
        iranian_domains = [
            'digikala.com', 'torob.com', 'emalls.ir', 'bamilo.com',
            'kalamarket.com', 'modiseh.com', 'shop.ir', 'irandryer.com'
        ]
        
        for result in results[:limit * 2]:  # Get extra to filter
            url = result.get('url', '')
            title = result.get('title', '')
            content = result.get('content', '')
            
            # Score relevance to Iranian market
            relevance_score = 0
            
            # Check for Iranian domains
            if any(domain in url for domain in iranian_domains):
                relevance_score += 3
            
            # Check for Persian text or Iranian terms
            iranian_terms = ['ایران', 'تومان', 'ریال', 'قیمت', 'خرید']
            if any(term in title + content for term in iranian_terms):
                relevance_score += 2
            
            # Check for price indicators
            price_terms = ['price', 'قیمت', 'تومان', 'ریال', '$', '€']
            if any(term in title + content for term in price_terms):
                relevance_score += 1
            
            if relevance_score > 0:  # Only include relevant results
                processed.append({
                    'url': url,
                    'title': title,
                    'content': content,
                    'relevance_score': relevance_score,
                    'source': 'searxng'
                })
        
        # Sort by relevance and return top results
        processed.sort(key=lambda x: x['relevance_score'], reverse=True)
        return processed[:limit]

    async def discover_new_sources(self, product_category: str) -> List[Dict]:
        """
        Discover new Iranian marketplace sources for a product category
        """
        discovery_queries = [
            f"{product_category} خرید آنلاین ایران",
            f"{product_category} فروشگاه اینترنتی",
            f"{product_category} مارکت پلیس ایران",
            f"قیمت {product_category} ایران",
        ]
        
        all_sources = []
        
        for query in discovery_queries:
            results = await self.search_iranian_products(query, limit=10)
            all_sources.extend(results)
        
        # Deduplicate by domain
        seen_domains = set()
        unique_sources = []
        
        for source in all_sources:
            domain = self._extract_domain(source['url'])
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_sources.append(source)
        
        return unique_sources
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
