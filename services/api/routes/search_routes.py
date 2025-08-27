from fastapi import APIRouter, HTTPException
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Updated imports
from scraper.orchestrator import IranianScrapingOrchestrator
from scraper.search_service import SearXNGSearchService
from services.enhanced_scraper_service import EnhancedScraperService

router = APIRouter()

@router.get("/discover/{product_name}")
async def discover_product(product_name: str, categories: str = None):
    """
    Discover products using SearXNG (no scraping)
    """
    try:
        categories_list = categories.split(',') if categories else None
        
        async with SearXNGSearchService() as search_service:
            results = await search_service.search_iranian_products(
                product_name, 
                categories_list
            )
        
        return {
            'product_name': product_name,
            'discovered_sources': len(results),
            'results': results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape-discovered")
async def scrape_discovered_products(request: dict):
    """
    Full pipeline: discover via SearXNG + scrape results
    """
    try:
        product_name = request.get('product_name')
        categories = request.get('categories', [])
        
        scraper = EnhancedScraperService()
        results = await scraper.discover_and_scrape_products(
            product_name, 
            categories
        )
        
        return {
            'product_name': product_name,
            'scraped_products': len(results),
            'results': results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "search"}
