#!/usr/bin/env python3
"""
Debug script to inspect HTML structure from Iranian websites
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def inspect_digikala():
    """Inspect Digikala HTML structure"""
    print("🔍 Inspecting Digikala HTML structure...")

    # SSL connector for handling certificate issues
    ssl_connector = aiohttp.TCPConnector(verify_ssl=False)

    async with aiohttp.ClientSession(connector=ssl_connector) as session:
        headers = {
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cache-Control": "max-age=0",
        }

        try:
            url = "https://www.digikala.com/search/category-mobile-phone/"
            print(f"Requesting: {url}")

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    print(f"✅ Successfully fetched {len(html)} bytes")

                    # Parse HTML
                    soup = BeautifulSoup(html, 'html.parser')

                    # Look for various product selectors
                    selectors_to_try = [
                        'div[data-product-index]',
                        '.product-list_ProductList__item__LiiNI',
                        '.d-block.pointer.text-dark-color',
                        '[data-testid="product-card"]',
                        '.product-card',
                        '.product',
                        'article',
                        'div[class*="product"]'
                    ]

                    print("\n🔍 Testing different selectors:")
                    for selector in selectors_to_try:
                        elements = soup.select(selector)
                        print(f"  {selector}: {len(elements)} elements")

                    # Show first few potential product elements
                    print("\n📄 First 500 characters of HTML:")
                    print(html[:500])
                    print("\n" + "="*50)

                    # Look for script tags that might contain JSON data
                    scripts = soup.find_all('script')
                    print(f"📜 Found {len(scripts)} script tags")

                    for i, script in enumerate(scripts):
                        if script.string and ('product' in script.string.lower() or 'mobile' in script.string.lower()):
                            print(f"  Script {i+1} (first 200 chars): {script.string[:200]}...")

                    # Look for API endpoints in the HTML
                    api_patterns = [
                        r'https://[^\s"]*api[^\s"]*',
                        r'https://[^\s"]*graphql[^\s"]*',
                        r'https://[^\s"]*search[^\s"]*'
                    ]

                    print("\n🔍 Looking for API endpoints:")
                    import re
                    for pattern in api_patterns:
                        matches = re.findall(pattern, html)
                        if matches:
                            print(f"  Found {len(matches)} potential API endpoints:")
                            for match in matches[:3]:
                                print(f"    {match}")

                    # Look for any JSON-like data
                    json_pattern = r'\{[^}]*"[^"]*product[^"]*"[^}]*\}'
                    json_matches = re.findall(json_pattern, html, re.IGNORECASE)
                    print(f"📄 Found {len(json_matches)} JSON-like objects with 'product'")

                    print("\n💡 This appears to be a Next.js app - content is loaded via JavaScript")
                    print("💡 Consider using Selenium or looking for API endpoints")

                else:
                    print(f"❌ HTTP {response.status}")

        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    await inspect_digikala()

if __name__ == "__main__":
    asyncio.run(main())
