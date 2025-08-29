#!/usr/bin/env python3
"""
Enhanced Data Pipeline Manager
Optimizes data flow, caching, and provides intelligent data management
"""

import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor
import aiofiles

logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    """Enhanced product data structure"""
    product_id: str
    canonical_title: str
    canonical_title_fa: str
    brand: str
    category: str
    model: Optional[str]
    current_prices: List[Dict[str, Any]]
    specifications: Optional[Dict[str, Any]]
    last_updated: str
    source: str
    metadata: Dict[str, Any]

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    timestamp: float
    ttl: int
    hits: int = 0
    last_accessed: float = 0

class EnhancedDataPipeline:
    """Intelligent data pipeline with advanced caching and optimization"""

    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Cache configuration
        self.cache_config = {
            "product_ttl": 3600,  # 1 hour
            "search_ttl": 1800,   # 30 minutes
            "analysis_ttl": 7200, # 2 hours
            "stats_ttl": 300,     # 5 minutes
        }

        # Performance tracking
        self.performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "redis_operations": 0,
            "processing_time": [],
        }

        # Data quality thresholds
        self.quality_thresholds = {
            "min_price_confidence": 0.8,
            "max_price_variance": 0.5,
            "min_product_completeness": 0.7,
        }

    async def init(self):
        """Initialize data pipeline"""
        if not self.redis:
            self.redis = redis.from_url('redis://localhost:6379/0')
        logger.info("✅ Enhanced data pipeline initialized")

    async def store_products(self, products: List[Dict], source: str, batch_size: int = 100) -> Dict[str, Any]:
        """Store products with intelligent batching and deduplication"""
        start_time = time.time()

        # Validate and normalize products
        normalized_products = []
        for product in products:
            normalized = self._normalize_product(product, source)
            if normalized and self._validate_product_quality(normalized):
                normalized_products.append(normalized)

        if not normalized_products:
            return {"stored": 0, "duplicates": 0, "errors": 0, "invalid": len(products)}

        # Process in batches
        stored_count = 0
        duplicate_count = 0
        error_count = 0

        for i in range(0, len(normalized_products), batch_size):
            batch = normalized_products[i:i + batch_size]

            try:
                # Check for duplicates and store batch
                batch_results = await self._store_product_batch(batch)
                stored_count += batch_results["stored"]
                duplicate_count += batch_results["duplicates"]
                error_count += batch_results["errors"]

            except Exception as e:
                logger.error(f"Error storing batch {i//batch_size}: {e}")
                error_count += len(batch)

        # Update statistics
        processing_time = time.time() - start_time
        await self._update_pipeline_stats("store_products", processing_time, stored_count)

        # Update search indexes
        await self._update_search_indexes(normalized_products)

        return {
            "stored": stored_count,
            "duplicates": duplicate_count,
            "errors": error_count,
            "invalid": len(products) - len(normalized_products),
            "processing_time": processing_time,
            "products_per_second": len(normalized_products) / processing_time if processing_time > 0 else 0
        }

    def _normalize_product(self, product: Dict, source: str) -> Optional[ProductData]:
        """Normalize product data structure"""
        try:
            # Generate consistent product ID
            product_id = self._generate_product_id(product)

            # Extract and normalize prices
            current_prices = self._normalize_prices(product.get('current_prices', []), source)

            # Create normalized product
            normalized = ProductData(
                product_id=product_id,
                canonical_title=product.get('canonical_title', ''),
                canonical_title_fa=product.get('canonical_title_fa', ''),
                brand=product.get('brand', 'unknown'),
                category=product.get('category', 'unknown'),
                model=product.get('model'),
                current_prices=current_prices,
                specifications=product.get('specifications'),
                last_updated=datetime.now(timezone.utc).isoformat(),
                source=source,
                metadata={
                    "original_data": product,
                    "normalized_at": datetime.now(timezone.utc).isoformat(),
                    "data_quality_score": self._calculate_data_quality(product)
                }
            )

            return normalized

        except Exception as e:
            logger.warning(f"Error normalizing product: {e}")
            return None

    def _normalize_prices(self, prices: List[Dict], source: str) -> List[Dict]:
        """Normalize price data with validation"""
        normalized_prices = []

        for price_info in prices:
            try:
                # Validate price data
                if not self._validate_price_data(price_info):
                    continue

                # Normalize currency and calculate USD equivalent
                normalized_price = {
                    "vendor": price_info.get("vendor", source),
                    "vendor_name_fa": price_info.get("vendor_name_fa", ""),
                    "price_toman": price_info.get("price_toman", 0),
                    "price_usd": price_info.get("price_usd", 0),
                    "availability": price_info.get("availability", True),
                    "product_url": price_info.get("product_url", ""),
                    "last_updated": price_info.get("last_updated", datetime.now(timezone.utc).isoformat()),
                    "confidence": price_info.get("confidence", 1.0),
                    "metadata": price_info.get("metadata", {})
                }

                normalized_prices.append(normalized_price)

            except Exception as e:
                logger.warning(f"Error normalizing price: {e}")
                continue

        return normalized_prices

    def _validate_price_data(self, price_data: Dict) -> bool:
        """Validate price data quality"""
        required_fields = ["price_toman", "vendor"]

        # Check required fields
        for field in required_fields:
            if field not in price_data or not price_data[field]:
                return False

        # Validate price is reasonable
        price = price_data.get("price_toman", 0)
        if price <= 0 or price > 1000000000:  # Max 1 billion toman (~$25k)
            return False

        return True

    def _validate_product_quality(self, product: ProductData) -> bool:
        """Validate overall product data quality"""
        try:
            # Check minimum required fields
            if not product.canonical_title or not product.brand or not product.category:
                return False

            # Check price quality
            if not product.current_prices:
                return False

            # Calculate completeness score
            completeness = self._calculate_data_quality(asdict(product))

            return completeness >= self.quality_thresholds["min_product_completeness"]

        except Exception as e:
            logger.warning(f"Error validating product quality: {e}")
            return False

    def _calculate_data_quality(self, product: Dict) -> float:
        """Calculate data quality score (0.0 to 1.0)"""
        score = 0.0
        total_weight = 0.0

        # Title quality (weight: 0.3)
        title = product.get('canonical_title', '')
        if title and len(title) > 10:
            score += 0.3
        total_weight += 0.3

        # Brand information (weight: 0.2)
        if product.get('brand') and product['brand'] != 'unknown':
            score += 0.2
        total_weight += 0.2

        # Price information (weight: 0.3)
        prices = product.get('current_prices', [])
        if prices:
            valid_prices = [p for p in prices if p.get('price_toman', 0) > 0]
            if valid_prices:
                score += 0.3
            total_weight += 0.3

        # Specifications (weight: 0.2)
        if product.get('specifications'):
            score += 0.2
        total_weight += 0.2

        return score / total_weight if total_weight > 0 else 0.0

    def _generate_product_id(self, product: Dict) -> str:
        """Generate consistent product ID"""
        # Use title, brand, and model for ID generation
        components = [
            product.get('canonical_title', ''),
            product.get('brand', ''),
            product.get('model', ''),
        ]

        # Create hash
        content = '|'.join(str(c) for c in components if c)
        product_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

        return f"ENHANCED{product_hash}"

    async def _store_product_batch(self, products: List[ProductData]) -> Dict[str, int]:
        """Store a batch of products with deduplication"""
        stored = 0
        duplicates = 0
        errors = 0

        try:
            # Prepare pipeline
            pipeline = self.redis.pipeline()

            for product in products:
                try:
                    product_key = f"product:{product.product_id}"
                    product_data = asdict(product)

                    # Check if product exists
                    existing = await self.redis.get(product_key)
                    if existing:
                        duplicates += 1
                        continue

                    # Store product
                    pipeline.setex(
                        product_key,
                        self.cache_config["product_ttl"],
                        json.dumps(product_data)
                    )

                    # Add to category index
                    category_key = f"category:{product.category}"
                    pipeline.sadd(category_key, product.product_id)

                    # Add to brand index
                    brand_key = f"brand:{product.brand}"
                    pipeline.sadd(brand_key, product.product_id)

                    stored += 1

                except Exception as e:
                    logger.warning(f"Error preparing product {product.product_id}: {e}")
                    errors += 1

            # Execute pipeline
            await pipeline.execute()

        except Exception as e:
            logger.error(f"Error storing product batch: {e}")
            errors += len(products)
            stored = 0

        return {"stored": stored, "duplicates": duplicates, "errors": errors}

    async def _update_search_indexes(self, products: List[ProductData]):
        """Update search indexes for new products"""
        try:
            for product in products:
                # Add to full-text search index
                search_key = f"search:{product.canonical_title.lower()}"
                await self.redis.sadd(search_key, product.product_id)

                # Add to category search
                cat_search_key = f"search:{product.category}:{product.canonical_title.lower()}"
                await self.redis.sadd(cat_search_key, product.product_id)

        except Exception as e:
            logger.warning(f"Error updating search indexes: {e}")

    async def search_products_enhanced(self, query: str, filters: Dict = None,
                                     limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Enhanced product search with intelligent caching"""
        start_time = time.time()

        # Create cache key
        cache_key = self._create_search_cache_key(query, filters, limit, offset)

        # Try cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            self.performance_stats["cache_hits"] += 1
            return cached_result

        self.performance_stats["cache_misses"] += 1

        # Perform search
        results = await self._perform_search(query, filters, limit, offset)

        # Cache results
        await self._cache_search_results(cache_key, results)

        # Update performance stats
        processing_time = time.time() - start_time
        await self._update_pipeline_stats("search", processing_time, len(results.get("products", [])))

        return results

    def _create_search_cache_key(self, query: str, filters: Dict, limit: int, offset: int) -> str:
        """Create cache key for search"""
        key_components = [query, str(limit), str(offset)]
        if filters:
            key_components.append(json.dumps(filters, sort_keys=True))

        content = "|".join(key_components)
        return f"search_cache:{hashlib.md5(content.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Get cached search result"""
        try:
            data = await self.redis.get(cache_key)
            if data:
                result = json.loads(data)
                # Update access time
                await self.redis.expire(cache_key, self.cache_config["search_ttl"])
                return result
        except Exception as e:
            logger.warning(f"Error getting cached result: {e}")

        return None

    async def _cache_search_results(self, cache_key: str, results: Dict):
        """Cache search results"""
        try:
            await self.redis.setex(
                cache_key,
                self.cache_config["search_ttl"],
                json.dumps(results)
            )
        except Exception as e:
            logger.warning(f"Error caching results: {e}")

    async def _perform_search(self, query: str, filters: Dict, limit: int, offset: int) -> Dict[str, Any]:
        """Perform actual product search"""
        try:
            products = []
            total_found = 0

            # Simple text-based search for now
            search_key = f"search:{query.lower()}"
            product_ids = await self.redis.smembers(search_key)

            if product_ids:
                # Get product details
                for product_id in list(product_ids)[offset:offset + limit]:
                    product_data = await self.redis.get(f"product:{product_id}")
                    if product_data:
                        product = json.loads(product_data)
                        products.append(product)

                total_found = len(product_ids)

            return {
                "query": query,
                "products": products,
                "total_found": total_found,
                "limit": limit,
                "offset": offset,
                "filters": filters or {},
                "search_time": time.time(),
                "cached": False
            }

        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return {
                "query": query,
                "products": [],
                "total_found": 0,
                "error": str(e)
            }

    async def _update_pipeline_stats(self, operation: str, processing_time: float, items_processed: int):
        """Update pipeline performance statistics"""
        try:
            self.performance_stats["processing_time"].append(processing_time)

            # Keep only last 100 measurements
            if len(self.performance_stats["processing_time"]) > 100:
                self.performance_stats["processing_time"] = self.performance_stats["processing_time"][-100:]

            # Store stats in Redis
            stats_key = "pipeline_stats"
            stats_data = {
                "operation": operation,
                "processing_time": processing_time,
                "items_processed": items_processed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_hit_ratio": self.performance_stats["cache_hits"] /
                                 max(1, self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"])
            }

            await self.redis.setex(stats_key, self.cache_config["stats_ttl"], json.dumps(stats_data))

        except Exception as e:
            logger.warning(f"Error updating pipeline stats: {e}")

    async def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health and performance metrics"""
        try:
            cache_hit_ratio = self.performance_stats["cache_hits"] / \
                            max(1, self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"])

            avg_processing_time = sum(self.performance_stats["processing_time"]) / \
                                max(1, len(self.performance_stats["processing_time"]))

            return {
                "status": "healthy",
                "cache_performance": {
                    "hit_ratio": cache_hit_ratio,
                    "total_hits": self.performance_stats["cache_hits"],
                    "total_misses": self.performance_stats["cache_misses"]
                },
                "processing_performance": {
                    "avg_processing_time": avg_processing_time,
                    "total_operations": len(self.performance_stats["processing_time"])
                },
                "redis_connection": await self._check_redis_health(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        try:
            await self.redis.ping()
            return {"status": "connected", "latency_ms": 0}
        except Exception as e:
            return {"status": "disconnected", "error": str(e)}

    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            # Redis handles TTL automatically, but we can add custom cleanup logic here
            logger.info("🧹 Cache cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cache cleanup: {e}")

    async def export_data_snapshot(self, filename: str) -> Dict[str, Any]:
        """Export current data snapshot for backup/analysis"""
        try:
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "products_count": 0,
                "categories": {},
                "brands": {},
                "performance_stats": self.performance_stats
            }

            # Count products by category and brand
            categories = await self.redis.keys("category:*")
            for cat_key in categories:
                category = cat_key.decode().split(":", 1)[1]
                count = await self.redis.scard(cat_key)
                snapshot["categories"][category] = count
                snapshot["products_count"] += count

            brands = await self.redis.keys("brand:*")
            for brand_key in brands:
                brand = brand_key.decode().split(":", 1)[1]
                count = await self.redis.scard(brand_key)
                snapshot["brands"][brand] = count

            # Save to file
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(snapshot, ensure_ascii=False, indent=2))

            return {
                "success": True,
                "filename": filename,
                "products_count": snapshot["products_count"],
                "categories_count": len(snapshot["categories"]),
                "brands_count": len(snapshot["brands"])
            }

        except Exception as e:
            logger.error(f"Error exporting data snapshot: {e}")
            return {"success": False, "error": str(e)}
