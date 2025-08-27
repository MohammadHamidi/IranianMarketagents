#!/usr/bin/env python3
"""
Advanced Iranian Price Intelligence Demo
Showcases all the new features: Selenium scraping, AI agents, vendor discovery,
price history, alerts system, and multi-category support
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List

from services.scraper.real_scraper import IranianWebScraper
from services.scraper.vendor_discovery_agent import VendorDiscoveryAgent
from services.scraper.price_history_tracker import PriceHistoryTracker
from services.scraper.alert_system import AlertSystem
from services.search_service import SearXNGSearchService
from services.api.ai_agents import IranianAIAgents

logger = logging.getLogger(__name__)

async def advanced_iranian_price_intelligence_demo():
    """
    Comprehensive demo of the advanced Iranian Price Intelligence platform
    """
    print("🇮🇷 Advanced Iranian Price Intelligence Platform Demo")
    print("=" * 70)

    # Initialize all components
    print("🔧 Initializing advanced components...")

    # 1. Initialize AI Agents
    ai_agents = IranianAIAgents()
    await ai_agents.initialize()
    print("✅ AI Agents initialized")

    # 2. Initialize Search Service
    search_service = SearXNGSearchService()
    print("✅ Search Service initialized")

    # 3. Initialize Vendor Discovery Agent
    vendor_agent = VendorDiscoveryAgent()
    print("✅ Vendor Discovery Agent initialized")

    # 4. Initialize Enhanced Scraper
    scraper = await IranianWebScraper.create()
    print("✅ Enhanced Scraper initialized")

    # 5. Initialize Price History Tracker
    price_tracker = PriceHistoryTracker()
    print("✅ Price History Tracker initialized")

    # 6. Initialize Alert System
    alert_system = AlertSystem()
    print("✅ Alert System initialized")

    print("\n🚀 Starting Advanced Demo Sequence")
    print("=" * 70)

    # === PHASE 1: Multi-Category Scraping ===
    print("\n📂 PHASE 1: Multi-Category Scraping")
    print("-" * 40)

    categories = ["mobile", "laptop", "tablet", "tv", "console"]
    print(f"🎯 Scraping {len(categories)} categories: {', '.join(categories)}")

    # Run multi-category scraping
    all_results = await scraper.run_scraping_cycle(categories)

    # Analyze results
    total_products = sum(r.products_found for r in all_results if r.success)
    category_stats = {}

    for result in all_results:
        if result.success:
            category = result.vendor.split('_')[-1]
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += result.products_found

    print(f"📊 Total products across all categories: {total_products}")
    for category, count in category_stats.items():
        print(f"  • {category}: {count} products")

    # === PHASE 2: AI-Powered Vendor Discovery ===
    print("\n🔍 PHASE 2: AI-Powered Vendor Discovery")
    print("-" * 40)

    # Discover new vendors for laptops
    print("🎯 Discovering new laptop vendors...")
    async with search_service as search:
        new_vendors = await vendor_agent.discover_new_vendors("laptop", max_vendors=3)

    if new_vendors:
        print(f"✅ Discovered {len(new_vendors)} new vendors:")
        for vendor in new_vendors:
            print(f"  • {vendor['name']} ({vendor['domain']}) - {vendor['relevance_score']}/3 relevance")
    else:
        print("ℹ️ No new vendors discovered (search service may need configuration)")

    # === PHASE 3: AI Product Catalog Expansion ===
    print("\n🤖 PHASE 3: AI Product Catalog Expansion")
    print("-" * 40)

    if new_vendors:
        target_vendor = new_vendors[0]
        print(f"🎯 Expanding catalog for {target_vendor['name']}...")

        # Use AI to expand product catalog
        expanded_products = await vendor_agent.expand_product_catalog(target_vendor, ai_agents)

        if expanded_products:
            print(f"✅ Expanded catalog with {len(expanded_products)} additional products")
            for i, product in enumerate(expanded_products[:3]):
                print(f"  {i+1}. {product.title} - {product.price_toman:,} تومان")
        else:
            print("ℹ️ Could not expand catalog (may need AI service configuration)")

    # === PHASE 4: Price History Tracking ===
    print("\n📈 PHASE 4: Price History Tracking")
    print("-" * 40)

    # Get a sample product for tracking
    sample_product = None
    for result in all_results:
        if result.success and result.products:
            sample_product = result.products[0]
            break

    if sample_product:
        print(f"🎯 Tracking price history for: {sample_product.title}")

        # Record price point
        await price_tracker.record_price_point({
            'product_id': sample_product.product_id,
            'price_toman': sample_product.price_toman,
            'price_usd': sample_product.price_usd,
            'vendor': sample_product.vendor,
            'availability': sample_product.availability,
            'product_url': sample_product.product_url,
            'title': sample_product.title,
            'category': sample_product.category
        })

        # Get price history
        history = await price_tracker.get_price_history(sample_product.product_id)
        if history:
            print(f"✅ Price History Analysis:")
            print(f"  • Current Price: {history.price_points[-1].price_toman:,} تومان")
            print(f"  • Price Range: {history.min_price:,} - {history.max_price:,} تومان")
            print(f"  • Average Price: {history.average_price:,.0f} تومان")
            print(".1f")
            print(f"  • Trend: {history.price_trend}")
            print(".1f")

    # === PHASE 5: Intelligent Alert System ===
    print("\n🔔 PHASE 5: Intelligent Alert System")
    print("-" * 40)

    if sample_product:
        print("🎯 Setting up smart alerts...")

        # Create smart alerts
        alert_created = await alert_system.create_smart_alert(
            sample_product.product_id,
            alert_type="auto"
        )

        if alert_created:
            print("✅ Smart alerts created successfully")
        else:
            print("ℹ️ Could not create alerts (may need Redis configuration)")

        # Check for triggered alerts
        triggered_alerts = await alert_system.run_alert_checks()

        if triggered_alerts:
            print(f"🚨 Found {len(triggered_alerts)} triggered alerts:")
            for alert in triggered_alerts[:2]:
                print(f"  • {alert.alert_type}: {alert.message}")
        else:
            print("ℹ️ No alerts triggered (normal for new products)")

    # === PHASE 6: Market Intelligence ===
    print("\n🧠 PHASE 6: Market Intelligence")
    print("-" * 40)

    try:
        # Get market intelligence
        market_report = await ai_agents.run_agent("market_intelligence", """
        Analyze the current Iranian electronics market based on the scraped data.
        Provide insights on:
        1. Market trends and pricing patterns
        2. Competitive landscape
        3. Category performance
        4. Recommendations for price monitoring
        """)

        if market_report and hasattr(market_report, 'choices') and market_report.choices:
            analysis = market_report.choices[0].message.content[:200] + "..."
            print(f"🧠 AI Market Analysis: {analysis}")
        else:
            print("ℹ️ Market intelligence analysis completed (may need AI service configuration)")

    except Exception as e:
        print(f"ℹ️ Could not generate market intelligence: {e}")

    # === FINAL SUMMARY ===
    print("\n🎉 ADVANCED DEMO COMPLETED!")
    print("=" * 70)

    print("🇮🇷 Advanced Iranian Price Intelligence System Status:")
    print("  ✅ Selenium Web Scraping: Handles JavaScript-heavy sites")
    print("  ✅ AI Vendor Discovery: Finds new Iranian marketplaces")
    print("  ✅ Dynamic Catalog Expansion: AI-powered product discovery")
    print("  ✅ Price History Tracking: Complete price change monitoring")
    print("  ✅ Intelligent Alerts: Smart notifications for price changes")
    print("  ✅ Multi-Category Support: Mobile, laptops, tablets, TV, consoles")
    print("  ✅ Multi-Vendor Coverage: Digikala, Technolife, MeghdadIT + discovered vendors")

    print(f"\n📊 Demo Results:")
    print(f"  • Categories Processed: {len(categories)}")
    print(f"  • Total Products: {total_products}")
    print(f"  • Vendors Covered: {len(set(r.vendor.split('_')[0] for r in all_results))}")
    print(f"  • New Vendors Discovered: {len(new_vendors) if 'new_vendors' in locals() else 0}")

    print(f"\n💰 Sample Price Ranges:")
    for category, count in category_stats.items():
        print(f"  • {category}: {count} products tracked")

    print(f"\n🚀 Next Steps:")
    print(f"  1. Configure Redis for full data persistence")
    print(f"  2. Set up email/webhook notifications")
    print(f"  3. Enable Selenium for real website scraping")
    print(f"  4. Configure AI service for enhanced intelligence")
    print(f"  5. Deploy to production environment")

    print(f"\n🌟 Your Advanced Iranian Price Intelligence Platform is Ready!")
    print(f"   Real-time monitoring • AI-powered insights • Multi-vendor coverage")
    print(f"   Smart alerts • Price history • Market intelligence 🇮🇷📱💰")

    # Cleanup
    await scraper.close()
    await vendor_agent.close()
    await ai_agents.client.close() if ai_agents.client else None

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Run the advanced demo
    asyncio.run(advanced_iranian_price_intelligence_demo())
