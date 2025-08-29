#!/usr/bin/env python3
"""
Iranian Price Intelligence Pipeline Orchestrator
Coordinates scraping, matching, and data processing workflows
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import redis.asyncio as redis
from neo4j import GraphDatabase
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """Main pipeline orchestrator for Iranian Price Intelligence"""
    
    def __init__(self):
        # Configuration from environment
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'iranian_price_secure_2025')
        self.redis_url = os.getenv('REDIS_URL', 'redis://:iranian_redis_secure_2025@redis:6379/3')
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        
        # Pipeline configuration
        self.daily_crawl_time = os.getenv('DAILY_CRAWL_TIME', '02:00')
        self.hourly_crawl_enabled = os.getenv('HOURLY_CRAWL_ENABLED', 'true').lower() == 'true'
        
        # Initialize components
        self.neo4j_driver = None
        self.redis_client = None
        
        # Pipeline statistics
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None,
            'last_successful_run': None,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
    
    async def initialize(self):
        """Initialize the pipeline orchestrator"""
        logger.info("🚀 Initializing Iranian Price Intelligence Pipeline...")
        
        try:
            # Initialize Neo4j connection
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test Neo4j connection
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 as test")
                assert result.single()['test'] == 1
            
            logger.info("✅ Neo4j connection established")
            
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Store pipeline info in Redis
            await self.redis_client.setex(
                "pipeline:service_info",
                3600,  # 1 hour cache
                json.dumps({
                    'service': 'iranian_price_pipeline',
                    'started_at': self.stats['start_time'],
                    'neo4j_uri': self.neo4j_uri,
                    'status': 'running',
                    'daily_crawl_time': self.daily_crawl_time,
                    'hourly_crawl_enabled': self.hourly_crawl_enabled
                })
            )
            
            logger.info("✅ Pipeline orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline orchestrator: {e}")
            raise
    
    async def update_exchange_rates(self):
        """Update current exchange rates from Iranian sources"""
        logger.info("💱 Updating currency exchange rates...")
        
        try:
            # Fetch current rates from Iranian sources
            current_rates = await self.fetch_iranian_exchange_rates()
            
            # Add timestamp
            current_rates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Store in Neo4j
            with self.neo4j_driver.session() as session:
                session.run("""
                    MERGE (er:ExchangeRate {exchange_rate_id: $rate_id})
                    SET er.date = date(),
                        er.usd_to_irr_buy = $usd_buy,
                        er.usd_to_irr_sell = $usd_sell,
                        er.eur_to_irr_buy = $eur_buy,
                        er.eur_to_irr_sell = $eur_sell,
                        er.source = $source,
                        er.updated_at = datetime()
                """, 
                    rate_id=datetime.now().strftime("%Y%m%d"),
                    usd_buy=current_rates['usd_buy'],
                    usd_sell=current_rates['usd_sell'],
                    eur_buy=current_rates['eur_buy'],
                    eur_sell=current_rates['eur_sell'],
                    source=current_rates['source']
                )
            
            # Cache in Redis for API
            await self.redis_client.setex(
                "exchange_rate:current", 
                3600,  # 1 hour cache
                json.dumps(current_rates)
            )
            
            logger.info(f"✅ Exchange rates updated: USD={current_rates['usd_sell']:,} IRR")
            
        except Exception as e:
            logger.error(f"❌ Failed to update exchange rates: {e}")
            raise
    
    async def fetch_iranian_exchange_rates(self) -> Dict:
        """Fetch exchange rates from Iranian sources"""
        
        # Try multiple sources for reliability
        sources = [
            {
                'name': 'bonbast',
                'url': 'https://api.bonbast.com/',
                'parser': self.parse_bonbast_rates
            },
            {
                'name': 'tgju',
                'url': 'https://call1.tgju.org/ajax.json',
                'parser': self.parse_tgju_rates
            }
        ]
        
        for source in sources:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source['url'], timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return source['parser'](data)
            except Exception as e:
                logger.warning(f"Failed to fetch from {source['name']}: {e}")
                continue
        
        # Fallback rates if all sources fail
        logger.warning("Using fallback exchange rates")
        return {
            'usd_buy': 420000,
            'usd_sell': 425000,
            'eur_buy': 465000,
            'eur_sell': 470000,
            'source': 'fallback'
        }
    
    def parse_bonbast_rates(self, data: Dict) -> Dict:
        """Parse Bonbast API response"""
        return {
            'usd_buy': int(data['usd1']),
            'usd_sell': int(data['usd2']),
            'eur_buy': int(data['eur1']),
            'eur_sell': int(data['eur2']),
            'source': 'bonbast'
        }
    
    def parse_tgju_rates(self, data: Dict) -> Dict:
        """Parse TGJU API response"""
        return {
            'usd_buy': int(data['current']['usd']['p']),
            'usd_sell': int(data['current']['usd']['s']),
            'eur_buy': int(data['current']['eur']['p']),
            'eur_sell': int(data['current']['eur']['s']),
            'source': 'tgju'
        }
    
    async def trigger_scraping_cycle(self):
        """Trigger a new scraping cycle"""
        logger.info("🔄 Triggering scraping cycle...")
        
        try:
            # Signal scraper service to start
            await self.redis_client.setex(
                "scraper:trigger",
                300,  # 5 minute TTL
                json.dumps({
                    'triggered_at': datetime.now(timezone.utc).isoformat(),
                    'cycle_type': 'scheduled',
                    'priority': 'normal'
                })
            )
            
            logger.info("✅ Scraping cycle triggered")
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger scraping cycle: {e}")
            raise
    
    async def trigger_matching_cycle(self):
        """Trigger a new product matching cycle"""
        logger.info("🔍 Triggering product matching cycle...")
        
        try:
            # Signal matcher service to start
            await self.redis_client.setex(
                "matcher:trigger",
                300,  # 5 minute TTL
                json.dumps({
                    'triggered_at': datetime.now(timezone.utc).isoformat(),
                    'cycle_type': 'scheduled',
                    'priority': 'normal'
                })
            )
            
            logger.info("✅ Product matching cycle triggered")
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger matching cycle: {e}")
            raise
    
    async def check_scraping_status(self) -> Dict[str, Any]:
        """Check the status of scraping operations"""
        try:
            # Get scraper service info
            scraper_info = await self.redis_client.get("scraper:service_info")
            if scraper_info:
                scraper_info = json.loads(scraper_info.decode())
            else:
                scraper_info = {'status': 'unknown'}
            
            # Get recent scraping results
            recent_results = await self.redis_client.keys("scraping_result:*")
            
            # Get pending products count
            pending_products = await self.redis_client.keys("pending_product:*")
            
            return {
                'scraper_status': scraper_info.get('status', 'unknown'),
                'recent_results_count': len(recent_results),
                'pending_products_count': len(pending_products),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check scraping status: {e}")
            return {'error': str(e)}
    
    async def check_matching_status(self) -> Dict[str, Any]:
        """Check the status of product matching operations"""
        try:
            # Get matcher service info
            matcher_info = await self.redis_client.get("matcher:service_info")
            if matcher_info:
                matcher_info = json.loads(matcher_info.decode())
            else:
                matcher_info = {'status': 'unknown'}
            
            # Get recent matching results
            recent_results = await self.redis_client.keys("match_result:*")
            
            # Get matcher statistics
            matcher_stats = await self.redis_client.get("matcher:stats")
            if matcher_stats:
                matcher_stats = json.loads(matcher_stats.decode())
            else:
                matcher_stats = {}
            
            return {
                'matcher_status': matcher_info.get('status', 'unknown'),
                'recent_results_count': len(recent_results),
                'matcher_stats': matcher_stats,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check matching status: {e}")
            return {'error': str(e)}
    
    async def run_daily_pipeline(self):
        """Run the complete daily pipeline"""
        logger.info("🌅 Starting daily pipeline execution...")
        
        start_time = datetime.now(timezone.utc)
        self.stats['total_runs'] += 1
        
        try:
            # Step 1: Update exchange rates
            await self.update_exchange_rates()
            
            # Step 2: Trigger scraping cycle
            await self.trigger_scraping_cycle()
            
            # Step 3: Wait for scraping to complete (with timeout)
            await asyncio.sleep(300)  # Wait 5 minutes for scraping
            
            # Step 4: Trigger product matching
            await self.trigger_matching_cycle()
            
            # Step 5: Wait for matching to complete
            await asyncio.sleep(180)  # Wait 3 minutes for matching
            
            # Step 6: Check final status
            scraping_status = await self.check_scraping_status()
            matching_status = await self.check_matching_status()
            
            # Step 7: Update statistics
            self.stats['successful_runs'] += 1
            self.stats['last_successful_run'] = datetime.now(timezone.utc).isoformat()
            
            # Step 8: Send success notification
            await self.send_pipeline_notification(
                'success',
                f"Daily pipeline completed successfully in {(datetime.now(timezone.utc) - start_time).total_seconds():.1f}s",
                {
                    'scraping_status': scraping_status,
                    'matching_status': matching_status
                }
            )
            
            logger.info("✅ Daily pipeline completed successfully")
            
        except Exception as e:
            self.stats['failed_runs'] += 1
            logger.error(f"❌ Daily pipeline failed: {e}")
            
            # Send failure notification
            await self.send_pipeline_notification(
                'failure',
                f"Daily pipeline failed: {str(e)}",
                {'error': str(e)}
            )
            
            raise
        
        finally:
            self.stats['last_run'] = datetime.now(timezone.utc).isoformat()
            
            # Update statistics in Redis
            await self.redis_client.setex(
                "pipeline:stats",
                3600,  # 1 hour cache
                json.dumps(self.stats)
            )
    
    async def run_hourly_pipeline(self):
        """Run lightweight hourly pipeline for priority updates"""
        logger.info("⏰ Starting hourly pipeline execution...")
        
        try:
            # Step 1: Update exchange rates
            await self.update_exchange_rates()
            
            # Step 2: Quick status check
            scraping_status = await self.check_scraping_status()
            matching_status = await self.check_matching_status()
            
            # Step 3: Trigger matching if there are pending products
            if scraping_status.get('pending_products_count', 0) > 0:
                await self.trigger_matching_cycle()
                logger.info("✅ Hourly pipeline completed with matching trigger")
            else:
                logger.info("✅ Hourly pipeline completed (no pending products)")
            
        except Exception as e:
            logger.error(f"❌ Hourly pipeline failed: {e}")
            raise
    
    async def send_pipeline_notification(self, status: str, message: str, details: Dict[str, Any]):
        """Send pipeline notification via email"""
        
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email notification")
            return
        
        try:
            subject = f"Iranian Price Intelligence Pipeline - {status.title()}"
            
            html_content = f"""
            <html dir="rtl">
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
                    .success {{ color: #28a745; }}
                    .failure {{ color: #dc3545; }}
                    .details {{ background-color: #e3f2fd; padding: 15px; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>گزارش اجرای خط لوله هوش قیمت ایران</h2>
                    <p>تاریخ: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="details">
                    <h3>وضعیت: <span class="{status}">{status.upper()}</span></h3>
                    <p>{message}</p>
                    
                    <h4>جزئیات:</h4>
                    <pre>{json.dumps(details, indent=2, ensure_ascii=False)}</pre>
                </div>
            </body>
            </html>
            """
            
            # Send email
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = self.admin_email
            
            html_part = MimeText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info("📧 Pipeline notification email sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send pipeline notification email: {e}")
    
    async def run_continuous_pipeline(self):
        """Run the pipeline orchestrator continuously"""
        logger.info("🔄 Starting continuous pipeline orchestration...")
        
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check if it's time for daily pipeline
                if current_time.hour == int(self.daily_crawl_time.split(':')[0]) and current_time.minute < 5:
                    await self.run_daily_pipeline()
                    await asyncio.sleep(3600)  # Wait 1 hour to avoid multiple runs
                
                # Check if it's time for hourly pipeline (during business hours)
                elif self.hourly_crawl_enabled and 5 <= current_time.hour <= 14 and current_time.minute == 0:
                    await self.run_hourly_pipeline()
                    await asyncio.sleep(60)  # Wait 1 minute
                
                # Regular status checks
                else:
                    # Check service health every 5 minutes
                    if current_time.minute % 5 == 0:
                        scraping_status = await self.check_scraping_status()
                        matching_status = await self.check_matching_status()
                        
                        # Log status
                        logger.info(f"📊 Status Check - Scraping: {scraping_status.get('scraper_status')}, Matching: {matching_status.get('matcher_status')}")
                    
                    await asyncio.sleep(60)  # Wait 1 minute
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous pipeline: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up pipeline orchestrator...")
        
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("✅ Cleanup completed")

async def main():
    """Main entry point"""
    orchestrator = PipelineOrchestrator()
    
    try:
        await orchestrator.initialize()
        await orchestrator.run_continuous_pipeline()
    except KeyboardInterrupt:
        logger.info("🛑 Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}")
        raise
    finally:
        await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
