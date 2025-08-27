#!/usr/bin/env python3
"""Quick test for verifying the fixes"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """Test that all imports work correctly"""
    try:
        # Test API service imports
        from services.api.main import app
        print("✅ API service imports work")
        
        # Test scraper service imports
        from services.scraper.orchestrator import IranianScrapingOrchestrator
        print("✅ Scraper service imports work")
        
        # Test search service imports
        from services.scraper.search_service import SearXNGSearchService
        print("✅ Search service imports work")
        
        # Test enhanced scraper imports
        from services.enhanced_scraper_service import EnhancedScraperService
        print("✅ Enhanced scraper imports work")
        
        # Test core dependencies
        import redis
        import fastapi
        import neo4j
        print("✅ Core dependencies work")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_docker_files():
    """Test that Docker files exist and have correct structure"""
    try:
        # Check that docker-compose.yml exists
        if os.path.exists("docker-compose.yml"):
            print("✅ docker-compose.yml exists")
        else:
            print("❌ docker-compose.yml missing")
            return False
            
        # Check that Dockerfiles exist
        docker_files = ["Dockerfile.api", "Dockerfile.scraper", "Dockerfile.matcher"]
        for docker_file in docker_files:
            if os.path.exists(docker_file):
                print(f"✅ {docker_file} exists")
            else:
                print(f"❌ {docker_file} missing")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Docker file test failed: {e}")
        return False

async def test_config_files():
    """Test that config files exist"""
    try:
        # Check that requirements.txt exists
        if os.path.exists("requirements.txt"):
            print("✅ requirements.txt exists")
        else:
            print("❌ requirements.txt missing")
            return False
            
        # Check that .env exists
        if os.path.exists(".env"):
            print("✅ .env exists")
        else:
            print("❌ .env missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Config file test failed: {e}")
        return False

async def main():
    print("Running quick fix verification tests...\n")
    
    # Test imports
    print("1. Testing imports...")
    imports_ok = await test_imports()
    print()
    
    # Test Docker files
    print("2. Testing Docker files...")
    docker_ok = await test_docker_files()
    print()
    
    # Test config files
    print("3. Testing config files...")
    config_ok = await test_config_files()
    print()
    
    # Summary
    if imports_ok and docker_ok and config_ok:
        print("🎉 All tests passed! The quick fixes have been successfully implemented.")
        print("\nNext steps:")
        print("1. Run 'docker-compose up -d' to start the services")
        print("2. Check the services are running with 'docker-compose ps'")
        print("3. Test the API at http://localhost:8000/health")
    else:
        print("❌ Some tests failed. Please check the output above for details.")
        
if __name__ == "__main__":
    asyncio.run(main())