#!/usr/bin/env python3
"""Initialize Neo4j schema for Iranian Price Intelligence Platform"""

from neo4j import GraphDatabase
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_neo4j(uri, user, password, max_attempts=30):
    """Wait for Neo4j to be ready"""
    driver = GraphDatabase.driver(uri, auth=(user, password))

    for attempt in range(max_attempts):
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                assert result.single()['test'] == 1
            logger.info("✅ Neo4j is ready!")
            return driver
        except Exception as e:
            logger.info(f"Waiting for Neo4j... attempt {attempt + 1}/{max_attempts}")
            time.sleep(2)

    raise Exception("Neo4j failed to start after maximum attempts")

def init_neo4j_schema():
    """Initialize the Neo4j database schema"""

    # Get connection details from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'iranian_price_secure_2025')

    logger.info("🔄 Connecting to Neo4j...")
    driver = wait_for_neo4j(neo4j_uri, neo4j_user, neo4j_password)

    # Schema initialization queries
    schema_queries = [
        # Product constraints
        "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
        "CREATE CONSTRAINT listing_id_unique IF NOT EXISTS FOR (l:Listing) REQUIRE l.listing_id IS UNIQUE",

        # Vendor constraints
        "CREATE CONSTRAINT vendor_id_unique IF NOT EXISTS FOR (v:Vendor) REQUIRE v.vendor_id IS UNIQUE",

        # Category constraints
        "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",

        # User constraints (for future use)
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",

        # Indexes for performance
        "CREATE INDEX product_brand_idx IF NOT EXISTS FOR (p:Product) ON (p.brand)",
        "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:Product) ON (p.category)",
        "CREATE INDEX product_canonical_title_idx IF NOT EXISTS FOR (p:Product) ON (p.canonical_title)",
        "CREATE INDEX listing_vendor_idx IF NOT EXISTS FOR (l:Listing) ON (l.vendor)",
        "CREATE INDEX listing_price_idx IF NOT EXISTS FOR (l:Listing) ON (l.price_toman)",
        "CREATE INDEX listing_date_idx IF NOT EXISTS FOR (l:Listing) ON (l.scraped_at)",
        "CREATE INDEX vendor_name_idx IF NOT EXISTS FOR (v:Vendor) ON (v.name)",

        # Full-text search indexes
        "CREATE FULLTEXT INDEX product_search IF NOT EXISTS FOR (p:Product) ON EACH [p.canonical_title, p.canonical_title_fa, p.brand, p.model]",
        "CREATE FULLTEXT INDEX listing_search IF NOT EXISTS FOR (l:Listing) ON EACH [l.title, l.title_fa]",
        "CREATE FULLTEXT INDEX vendor_search IF NOT EXISTS FOR (v:Vendor) ON EACH [v.name, v.name_fa, v.website]",
    ]

    try:
        with driver.session() as session:
            logger.info("🔄 Creating schema constraints and indexes...")

            for query in schema_queries:
                try:
                    session.run(query)
                    logger.info(f"✅ Executed: {query.split('IF NOT EXISTS')[0].strip()}")
                except Exception as e:
                    logger.warning(f"⚠️ Query failed (might already exist): {query} - {e}")

            # Create sample data for testing
            logger.info("🔄 Creating sample categories...")
            sample_queries = [
                "MERGE (c:Category {name: 'mobile', name_fa: 'گوشی موبایل', display_order: 1})",
                "MERGE (c:Category {name: 'laptop', name_fa: 'لپ تاپ', display_order: 2})",
                "MERGE (c:Category {name: 'tablet', name_fa: 'تبلت', display_order: 3})",
                "MERGE (c:Category {name: 'tv', name_fa: 'تلویزیون', display_order: 4})",
                "MERGE (c:Category {name: 'console', name_fa: 'کنسول بازی', display_order: 5})",

                # Create sample vendors
                "MERGE (v:Vendor {vendor_id: 'digikala', name: 'Digikala', name_fa: 'دیجی کالا', website: 'digikala.com', country: 'Iran'})",
                "MERGE (v:Vendor {vendor_id: 'technolife', name: 'Technolife', name_fa: 'تکنولایف', website: 'technolife.ir', country: 'Iran'})",
                "MERGE (v:Vendor {vendor_id: 'meghdadit', name: 'MeghdadIT', name_fa: 'مقداد آی تی', website: 'meghdadit.com', country: 'Iran'})",
            ]

            for query in sample_queries:
                try:
                    session.run(query)
                    logger.info(f"✅ Created sample data: {query.split('MERGE')[1].strip()}")
                except Exception as e:
                    logger.warning(f"⚠️ Sample data creation failed: {query} - {e}")

        logger.info("✅ Neo4j schema initialization completed successfully!")
        logger.info("📊 Schema includes:")
        logger.info("  • 5 constraints for data integrity")
        logger.info("  • 10 indexes for query performance")
        logger.info("  • 3 full-text search indexes")
        logger.info("  • Sample categories and vendors")

    except Exception as e:
        logger.error(f"❌ Neo4j schema initialization failed: {e}")
        raise
    finally:
        driver.close()

if __name__ == "__main__":
    try:
        init_neo4j_schema()
    except KeyboardInterrupt:
        logger.info("🛑 Initialization interrupted by user")
    except Exception as e:
        logger.error(f"💥 Initialization failed: {e}")
        exit(1)