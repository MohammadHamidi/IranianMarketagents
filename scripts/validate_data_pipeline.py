#!/usr/bin/env python3
"""
Data Pipeline Validation Script
Run this to validate data flow from scraper to dashboard
"""

import asyncio
import json
import redis.asyncio as redis
import aiohttp
from datetime import datetime, timezone

async def validate_pipeline():
    """Validate the entire data pipeline"""
    print("🔍 Validating Iranian Price Intelligence Data Pipeline...")

    # Step 1: Check Redis connection and data
    try:
        redis_client = redis.from_url('redis://:iranian_redis_secure_2025@localhost:6379/1')
        await redis_client.ping()
        print("✅ Redis connection: OK")

        # Check for real data flag
        real_data_flag = await redis_client.get('real_data_available')
        print(f"📊 Real data flag: {'✅ SET' if real_data_flag else '❌ NOT SET'}")

        # Check product data
        product_keys = await redis_client.keys("product:*")
        print(f"📦 Products in Redis: {len(product_keys)}")

        if product_keys:
            # Sample a product
            sample_key = product_keys[0]
            sample_data = await redis_client.hgetall(sample_key)
            required_fields = ['product_id', 'canonical_title', 'price_toman', 'vendor']
            missing_fields = [f for f in required_fields if f.encode() not in sample_data]

            if missing_fields:
                print(f"⚠️  Sample product missing fields: {missing_fields}")
            else:
                print("✅ Product data structure: OK")

        # Check scraping summary
        summary = await redis_client.hgetall('scraping_summary')
        if summary:
            last_updated = summary.get(b'last_updated', b'').decode()
            vendors = summary.get(b'vendors', b'[]').decode()
            print(f"📅 Last scraping: {last_updated}")
            print(f"🏪 Vendors: {vendors}")
        else:
            print("⚠️  No scraping summary found")

        await redis_client.close()

    except Exception as e:
        print(f"❌ Redis check failed: {e}")
        return False

    # Step 2: Check API endpoints
    try:
        async with aiohttp.ClientSession() as session:
            # Health check
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    print("✅ API health: OK")
                else:
                    print(f"⚠️  API health: {response.status}")

            # Data status check
            async with session.get('http://localhost:8000/data/status') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 API real data flag: {data.get('real_data_flag', False)}")
                    print(f"📦 API product count: {data.get('product_count', 0)}")

            # Search test
            async with session.get('http://localhost:8000/products/search?query=mobile&limit=5') as response:
                if response.status == 200:
                    products = await response.json()
                    print(f"🔍 Search test: Found {len(products)} products")
                    if products:
                        sample_product = products[0]
                        print(f"📱 Sample: {sample_product.get('canonical_title', 'No title')}")
                else:
                    print(f"❌ Search test failed: {response.status}")

    except Exception as e:
        print(f"❌ API check failed: {e}")
        return False

    # Step 3: Check dashboard accessibility
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost') as response:
                if response.status == 200:
                    print("✅ Dashboard accessible: OK")
                else:
                    print(f"⚠️  Dashboard status: {response.status}")
    except Exception as e:
        print(f"⚠️  Dashboard check failed: {e}")

    print("\n🎯 Pipeline validation completed!")
    return True

if __name__ == "__main__":
    asyncio.run(validate_pipeline())
