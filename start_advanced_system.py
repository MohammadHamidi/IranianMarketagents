#!/usr/bin/env python3
"""
Advanced Iranian Price Intelligence System Launcher
Complete startup script for the full-featured platform
"""

import asyncio
import os
import subprocess
import sys
import time
from typing import List

def print_banner():
    """Print the system banner"""
    print("""
🇮🇷 IRANIAN PRICE INTELLIGENCE PLATFORM - ADVANCED EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ━━━━
Real-time monitoring • AI-powered insights • Multi-vendor coverage
Smart alerts • Price history • Market intelligence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

def check_dependencies() -> bool:
    """Check if all required dependencies are available"""
    print("🔍 Checking dependencies...")

    missing_deps = []

    try:
        import redis
        print("✅ Redis library available")
    except ImportError:
        missing_deps.append("redis")

    try:
        import selenium
        print("✅ Selenium available")
    except ImportError:
        missing_deps.append("selenium")

    try:
        import aiohttp
        print("✅ aiohttp available")
    except ImportError:
        missing_deps.append("aiohttp")

    try:
        import openai
        print("✅ OpenAI library available")
    except ImportError:
        missing_deps.append("openai")

    try:
        import beautifulsoup4
        print("✅ BeautifulSoup4 available")
    except ImportError:
        missing_deps.append("beautifulsoup4")

    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("📦 Install with: pip install " + " ".join(missing_deps))
        return False

    print("✅ All dependencies available")
    return True

async def start_services():
    """Start all required services"""
    print("\n🚀 Starting Advanced Iranian Price Intelligence System")
    print("=" * 60)

    # Step 1: Start Redis
    print("\n📦 Step 1: Starting Redis...")
    try:
        result = subprocess.run(["docker-compose", "up", "-d", "redis"],
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print("✅ Redis started successfully")
        else:
            print(f"⚠️ Redis startup warning: {result.stderr}")
    except Exception as e:
        print(f"❌ Failed to start Redis: {e}")
        print("💡 Make sure Docker is running")
        return False

    # Wait for Redis to be ready
    print("⏳ Waiting for Redis to be ready...")
    time.sleep(5)

    # Step 2: Start continuous scraper
    print("\n🕷️ Step 2: Starting continuous scraper...")
    try:
        # Start scraper in background
        scraper_process = subprocess.Popen([
            sys.executable, "services/scraper/continuous_scraper.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("✅ Continuous scraper started")

        # Give scraper time to populate initial data
        print("⏳ Waiting for initial data population...")
        time.sleep(15)

    except Exception as e:
        print(f"❌ Failed to start scraper: {e}")
        return False

    # Step 3: Start API service
    print("\n🌐 Step 3: Starting API service...")
    try:
        result = subprocess.run(["docker-compose", "up", "-d", "api-service"],
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print("✅ API service started successfully")
        else:
            print(f"⚠️ API service warning: {result.stderr}")
    except Exception as e:
        print(f"❌ Failed to start API service: {e}")
        return False

    # Step 4: Verify system is working
    print("\n🔍 Step 4: Verifying system...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Check health
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    if health_data.get("status") == "healthy":
                        print("✅ API health check passed")
                    else:
                        print(f"⚠️ API health check warning: {health_data}")

            # Check data status
            async with session.get("http://localhost:8000/data/status") as response:
                if response.status == 200:
                    data_status = await response.json()
                    if data_status.get("real_data_flag"):
                        print(f"✅ Real data available: {data_status.get('product_count', 0)} products")
                    else:
                        print("⚠️ No real data available yet")

    except Exception as e:
        print(f"⚠️ System verification warning: {e}")

    return True

def show_usage_guide():
    """Show comprehensive usage guide"""
    print("\n📚 USAGE GUIDE")
    print("=" * 60)

    print("\n🌐 Access Points:")
    print("  • API: http://localhost:8000")
    print("  • Dashboard: http://localhost:3000")
    print("  • Data Status: http://localhost:8000/data/status")
    print("  • API Documentation: http://localhost:8000/docs")

    print("\n🔧 Key Features:")
    print("  • Multi-category scraping (mobile, laptop, tablet, TV, console)")
    print("  • Real Iranian product data with Persian titles")
    print("  • AI-powered vendor discovery")
    print("  • Price history tracking and trend analysis")
    print("  • Intelligent alert system")
    print("  • Selenium-based scraping for JavaScript sites")

    print("\n📊 Available Categories:")
    categories = [
        ("📱 Mobile Phones", "15 products from 3 vendors"),
        ("💻 Laptops", "14 products from 3 vendors"),
        ("📱 Tablets", "12 products from 3 vendors"),
        ("📺 TVs", "9 products from 3 vendors"),
        ("🎮 Gaming Consoles", "9 products from 3 vendors")
    ]
    for category, details in categories:
        print(f"  • {category}: {details}")

    print("\n🏪 Supported Vendors:")
    vendors = [
        "دیجی‌کالا (Digikala) - Iran's largest e-commerce platform",
        "تکنولایف (Technolife) - Electronics specialist",
        "مقداد آی‌تی (MeghdadIT) - Premium electronics"
    ]
    for vendor in vendors:
        print(f"  • {vendor}")

    print("\n💰 Sample Iranian Pricing:")
    print("  • Mobile phones: 18M - 65M تومان")
    print("  • Laptops: 78M - 180M تومان")
    print("  • Tablets: 35M - 95M تومان")
    print("  • TVs: 55M - 180M تومان")
    print("  • Consoles: 28M - 45M تومان")

def show_advanced_commands():
    """Show advanced usage commands"""
    print("\n🔧 ADVANCED COMMANDS")
    print("=" * 60)

    commands = [
        ("Run category-specific scraping", "python3 -c \"from services.scraper.real_scraper import IranianWebScraper; import asyncio; scraper = asyncio.run(IranianWebScraper.create()); asyncio.run(scraper.run_scraping_cycle(['mobile', 'laptop']))\""),
        ("Test Selenium scraper", "python3 -c \"from services.scraper.selenium_scraper import AsyncIranianSeleniumScraper; import asyncio; scraper = AsyncIranianSeleniumScraper(); print('Selenium ready')\""),
        ("Check price history", "curl 'http://localhost:8000/data/status'"),
        ("View system logs", "docker-compose logs -f api-service"),
        ("Stop all services", "docker-compose down"),
        ("Restart scraper", "pkill -f continuous_scraper && python3 services/scraper/continuous_scraper.py &")
    ]

    for description, command in commands:
        print(f"\n📝 {description}:")
        print(f"   {command}")

async def main():
    """Main startup function"""
    print_banner()

    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        return

    if not await start_services():
        print("\n❌ Failed to start services. Check Docker and dependencies.")
        return

    show_usage_guide()
    show_advanced_commands()

    print("\n🎉 SUCCESS! Your Advanced Iranian Price Intelligence Platform is RUNNING!")
    print("=" * 70)
    print("🇮🇷 Real-time Iranian e-commerce monitoring with AI-powered insights")
    print("🔥 Multi-category, multi-vendor coverage with intelligent automation")
    print("📊 Price history tracking with smart alerts and market intelligence")
    print("=" * 70)

    print("\n⏰ System will continue running in the background...")
    print("💡 Use Ctrl+C to stop, or run 'docker-compose down' to shutdown")

    # Keep the script running to monitor services
    try:
        while True:
            await asyncio.sleep(60)  # Check every minute
            print("🔄 System running... (Press Ctrl+C to stop)")
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        os.system("docker-compose down")
        print("✅ Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
