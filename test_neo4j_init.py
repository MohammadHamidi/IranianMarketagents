#!/usr/bin/env python3
"""
Test script to verify Neo4j initialization
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_neo4j_init():
    """Test that the Neo4j initialization script can be imported and run"""
    try:
        # Import the initialization script
        from scripts.init_neo4j import init_neo4j_schema
        print("✅ Neo4j initialization script imported successfully")
        print("ℹ️  Note: This test only verifies import, not actual database connection")
        print("ℹ️  To test actual database connection, run: python scripts/init_neo4j.py")
        return True
    except Exception as e:
        print(f"❌ Failed to import Neo4j initialization script: {e}")
        return False

if __name__ == "__main__":
    success = test_neo4j_init()
    sys.exit(0 if success else 1)