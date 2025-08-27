#!/usr/bin/env python3
"""
Startup script for the Iranian Price Intelligence Platform
"""

import subprocess
import sys
import time
import os

def start_docker_services():
    """Start all Docker services"""
    print("🚀 Starting Docker services...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Docker services started successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Docker services: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_service_health(service_name, port, timeout=60):
    """Check if a service is responding on its port"""
    import socket
    import time
    
    print(f"🔍 Checking {service_name} health...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"✅ {service_name} is healthy on port {port}")
                return True
        except Exception:
            pass
        
        time.sleep(5)
    
    print(f"❌ {service_name} failed to become healthy within {timeout} seconds")
    return False

def main():
    """Main startup function"""
    print("🇮🇷 Iranian Price Intelligence Platform - Startup Script")
    print("=" * 60)
    
    # Start Docker services
    if not start_docker_services():
        print("❌ Failed to start Docker services. Exiting.")
        sys.exit(1)
    
    # Wait a moment for services to start
    print("⏳ Waiting for services to initialize...")
    time.sleep(10)
    
    # Check service health
    services = [
        ("Neo4j", 7474),
        ("Redis", 6379),
        ("PostgreSQL", 5432)
    ]
    
    all_healthy = True
    for service_name, port in services:
        if not check_service_health(service_name, port):
            all_healthy = False
    
    if not all_healthy:
        print("❌ Some services are not healthy. Check the logs above.")
        sys.exit(1)
    
    print("\n🎉 All services are running!")
    print("\nNext steps:")
    print("1. Initialize the Neo4j database:")
    print("   python scripts/init_neo4j.py")
    print("\n2. Start the API service:")
    print("   cd services/api && python3 main.py")
    print("\n3. Access the API documentation:")
    print("   http://localhost:8000/docs")
    print("\n4. View service logs:")
    print("   docker-compose logs -f")

if __name__ == "__main__":
    main()