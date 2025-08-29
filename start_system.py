#!/usr/bin/env python3
"""Iranian Price Intelligence Platform - Startup Script"""

import subprocess
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemStarter:
    """System startup manager"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.docker_available = False
        self.services_ready = False

    def check_docker_availability(self) -> bool:
        """Check if Docker daemon is running"""
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Docker daemon is running")
                self.docker_available = True
                return True
            else:
                logger.error("❌ Docker daemon is not running")
                return False
        except FileNotFoundError:
            logger.error("❌ Docker is not installed")
            return False

    def check_docker_compose_availability(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ Docker Compose is available: {result.stdout.strip()}")
                return True
            else:
                logger.error("❌ Docker Compose is not working properly")
                return False
        except FileNotFoundError:
            logger.error("❌ Docker Compose is not installed")
            return False

    def start_databases(self) -> bool:
        """Start core database services"""
        logger.info("🔄 Starting core databases (Neo4j, Redis, PostgreSQL)...")

        try:
            result = subprocess.run([
                'docker-compose', 'up', '-d', 'neo4j', 'redis', 'postgres'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Database services started successfully")
                logger.info("⏳ Waiting for databases to initialize...")
                time.sleep(30)  # Give databases time to start
                return True
            else:
                logger.error(f"❌ Failed to start databases: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Database startup failed: {e}")
            return False

    def initialize_neo4j(self) -> bool:
        """Initialize Neo4j database schema"""
        logger.info("🔄 Initializing Neo4j database schema...")

        try:
            result = subprocess.run([
                sys.executable, 'scripts/init_neo4j.py'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Neo4j schema initialized successfully")
                return True
            else:
                logger.error(f"❌ Neo4j initialization failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Neo4j initialization error: {e}")
            return False

    def start_application_services(self) -> bool:
        """Start application services"""
        logger.info("🔄 Starting application services (API, Scraper, Matcher, Pipeline)...")

        try:
            result = subprocess.run([
                'docker-compose', 'up', '-d'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ All services started successfully")
                logger.info("⏳ Waiting for services to be ready...")
                time.sleep(20)  # Give services time to start
                return True
            else:
                logger.error(f"❌ Failed to start application services: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Application services startup failed: {e}")
            return False

    def run_system_tests(self) -> bool:
        """Run system tests to verify everything is working"""
        logger.info("🧪 Running system tests...")

        try:
            result = subprocess.run([
                sys.executable, 'test_system.py'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ System tests passed!")
                return True
            else:
                logger.warning(f"⚠️ Some system tests failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ System test execution failed: {e}")
            return False

    def show_service_status(self):
        """Show current service status"""
        logger.info("\n📊 SERVICE STATUS")
        logger.info("=" * 50)

        try:
            result = subprocess.run([
                'docker-compose', 'ps'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                print(result.stdout)
            else:
                logger.error("Could not get service status")

        except Exception as e:
            logger.error(f"Failed to get service status: {e}")

    def show_access_information(self):
        """Show how to access the system"""
        logger.info("\n🌐 ACCESS INFORMATION")
        logger.info("=" * 50)
        logger.info("📱 Web Dashboard: http://localhost:3000")
        logger.info("🔌 API Documentation: http://localhost:8000/docs")
        logger.info("🔍 API Health Check: http://localhost:8000/health")
        logger.info("🗄️ Neo4j Browser: http://localhost:7474 (neo4j/iranian_price_secure_2025)")
        logger.info("📊 Redis: localhost:6379 (password: iranian_redis_secure_2025)")
        logger.info("🗃️ PostgreSQL: localhost:5432 (price_admin/iranian_postgres_secure_2025)")

    def full_startup_sequence(self) -> bool:
        """Execute complete startup sequence"""
        logger.info("🚀 Starting Iranian Price Intelligence Platform")
        logger.info("=" * 60)

        # Step 1: Check prerequisites
        logger.info("\n1️⃣ Checking prerequisites...")
        if not self.check_docker_availability():
            logger.error("❌ Docker daemon is not running. Please start Docker Desktop first.")
            return False

        if not self.check_docker_compose_availability():
            logger.error("❌ Docker Compose is not available.")
            return False

        # Step 2: Start databases
        logger.info("\n2️⃣ Starting databases...")
        if not self.start_databases():
            logger.error("❌ Failed to start databases")
            return False

        # Step 3: Initialize Neo4j
        logger.info("\n3️⃣ Initializing Neo4j database...")
        if not self.initialize_neo4j():
            logger.error("❌ Failed to initialize Neo4j")
            return False

        # Step 4: Start application services
        logger.info("\n4️⃣ Starting application services...")
        if not self.start_application_services():
            logger.error("❌ Failed to start application services")
            return False

        # Step 5: Run tests
        logger.info("\n5️⃣ Running system tests...")
        test_success = self.run_system_tests()

        # Step 6: Show status and access info
        self.show_service_status()
        self.show_access_information()

        logger.info("\n" + "=" * 60)
        if test_success:
            logger.info("🎉 SYSTEM STARTUP COMPLETED SUCCESSFULLY!")
            logger.info("Your Iranian Price Intelligence Platform is now running.")
        else:
            logger.warning("⚠️ SYSTEM STARTED WITH SOME TEST FAILURES")
            logger.info("The system is running but some components may need attention.")

        logger.info("=" * 60)

        return test_success

def main():
    """Main startup function"""
    starter = SystemStarter()

    try:
        success = starter.full_startup_sequence()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Startup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
