#!/usr/bin/env python3
"""Initialize Neo4j schema for Iranian Price Intelligence Platform"""

from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_neo4j_schema():
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "iranian_price_secure_2025")
    )
    
    schema_queries = [
        # Product constraints
        "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
        "CREATE CONSTRAINT listing_id_unique IF NOT EXISTS FOR (l:Listing) REQUIRE l.listing_id IS UNIQUE",
        
        # Indexes for performance
        "CREATE INDEX product_brand_idx IF NOT EXISTS FOR (p:Product) ON (p.brand)",
        "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:Product) ON (p.category)",
        "CREATE INDEX listing_vendor_idx IF NOT EXISTS FOR (l:Listing) ON (l.vendor)",
        "CREATE INDEX listing_price_idx IF NOT EXISTS FOR (l:Listing) ON (l.price_toman)",
        
        # Full-text search indexes
        "CREATE FULLTEXT INDEX product_search IF NOT EXISTS FOR (p:Product) ON EACH [p.canonical_title, p.canonical_title_fa, p.brand, p.model]",
        "CREATE FULLTEXT INDEX listing_search IF NOT EXISTS FOR (l:Listing) ON EACH [l.title, l.title_fa]"
    ]
    
    try:
        with driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    logger.info(f"✅ Executed: {query}")
                except Exception as e:
                    logger.warning(f"⚠️ Query failed (might already exist): {query} - {e}")
        
        logger.info("✅ Neo4j schema initialization completed")
        
    except Exception as e:
        logger.error(f"❌ Neo4j schema initialization failed: {e}")
        raise
    finally:
        driver.close()

if __name__ == "__main__":
    init_neo4j_schema()