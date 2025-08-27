#!/usr/bin/env python3
"""Test script to verify that all imports work correctly"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        # Test core imports
        import redis
        import jwt
        from passlib.context import CryptContext
        from fastapi import FastAPI
        from neo4j import GraphDatabase
        print("✅ Core imports successful")
        
        # Test service imports
        from services.base import BaseService
        print("✅ BaseService import successful")
        
        # Test config imports
        from config.settings import settings
        print("✅ Settings import successful")
        
        # Test scraper imports
        from services.scraper.orchestrator import IranianScrapingOrchestrator
        print("✅ Scraper orchestrator import successful")
        
        # Test matcher imports
        from services.matcher.persian_processor import PersianTextProcessor
        print("✅ Persian processor import successful")
        
        print("\n🎉 All imports successful! The project is ready to run.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)