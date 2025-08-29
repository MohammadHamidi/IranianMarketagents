#!/usr/bin/env python3
"""
Enhanced WebDriver Manager - Intelligent Chrome/ChromeDriver Version Management
Automatically handles version compatibility and provides fallback mechanisms
"""

import os
import sys
import subprocess
import requests
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.utils import ChromeType
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    ChromeDriverManager = None
    ChromeType = None

logger = logging.getLogger(__name__)

class EnhancedDriverManager:
    """Intelligent ChromeDriver manager with auto-compatibility"""
    
    def __init__(self):
        self.chrome_version = None
        self.chromedriver_path = None
        self.temp_dir = None
        self.cache_dir = Path.home() / ".cache" / "iranian_scraper" / "chromedriver"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cached_versions = {}  # Cache ChromeDriver paths by version

    def _get_cached_chromedriver_path(self, version: str) -> Optional[Path]:
        """Get cached ChromeDriver path for version if it exists"""
        cached_path = self.cache_dir / f"chromedriver_{version}"
        if cached_path.exists() and cached_path.stat().st_size > 0:
            logger.info(f"✅ Found cached ChromeDriver for version {version}")
            return cached_path
        return None

    def _cache_chromedriver(self, version: str, source_path: Path) -> Path:
        """Cache ChromeDriver binary"""
        cached_path = self.cache_dir / f"chromedriver_{version}"
        try:
            shutil.copy2(source_path, cached_path)
            cached_path.chmod(0o755)  # Make executable
            logger.info(f"💾 Cached ChromeDriver for version {version}")
            return cached_path
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache ChromeDriver: {e}")
            return source_path

    def clear_cache(self):
        """Clear all cached ChromeDriver files"""
        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info("🧹 Cleared ChromeDriver cache")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clear cache: {e}")

    def get_chrome_version(self) -> Optional[str]:
        """Get installed Chrome version"""
        try:
            # macOS
            if sys.platform == "darwin":
                result = subprocess.run([
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 
                    '--version'
                ], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"🔍 Detected Chrome version: {version}")
                    return version
            
            # Linux
            elif sys.platform == "linux":
                commands = [
                    ['google-chrome', '--version'],
                    ['google-chrome-stable', '--version'],
                    ['chromium-browser', '--version']
                ]
                
                for cmd in commands:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            version = result.stdout.strip().split()[-1]
                            logger.info(f"🔍 Detected Chrome version: {version}")
                            return version
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
            
            # Windows
            elif sys.platform == "win32":
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                        r"Software\Google\Chrome\BLBeacon")
                    version, _ = winreg.QueryValueEx(key, "version")
                    logger.info(f"🔍 Detected Chrome version: {version}")
                    return version
                except WindowsError:
                    pass
                    
        except Exception as e:
            logger.warning(f"⚠️ Could not detect Chrome version: {e}")
        
        return None
    
    def get_compatible_chromedriver_version(self, chrome_version: str) -> str:
        """Get compatible ChromeDriver version for given Chrome version"""
        try:
            # Extract major version
            major_version = chrome_version.split('.')[0]
            
            # ChromeDriver version mapping
            version_mapping = {
                "139": "139.0.7258.154",
                "138": "138.0.7162.93", 
                "137": "137.0.6997.99",
                "136": "136.0.6909.99",
                "135": "135.0.6790.98",
                "134": "134.0.6717.69",
                "133": "133.0.6835.31",
                "132": "132.0.6834.83"
            }
            
            if major_version in version_mapping:
                compatible_version = version_mapping[major_version]
                logger.info(f"🎯 Compatible ChromeDriver version: {compatible_version}")
                return compatible_version
            
            # Fallback: use Chrome version as is
            logger.warning(f"⚠️ Unknown Chrome version {chrome_version}, using as-is")
            return chrome_version
            
        except Exception as e:
            logger.error(f"❌ Error getting compatible version: {e}")
            return chrome_version
    
    def download_compatible_chromedriver(self, version: str) -> Optional[str]:
        """Download compatible ChromeDriver version"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="chromedriver_")
            
            # Determine platform
            if sys.platform == "darwin":
                if "arm64" in os.uname().machine.lower():
                    platform = "mac-arm64"
                else:
                    platform = "mac-x64"
            elif sys.platform == "linux":
                platform = "linux64"
            elif sys.platform == "win32":
                platform = "win32"
            else:
                raise Exception(f"Unsupported platform: {sys.platform}")
            
            # Download URL
            base_url = "https://storage.googleapis.com/chrome-for-testing-public"
            download_url = f"{base_url}/{version}/{platform}/chromedriver-{platform}.zip"
            
            logger.info(f"📥 Downloading ChromeDriver {version} for {platform}")
            
            # Download
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()
            
            # Extract
            zip_path = os.path.join(self.temp_dir, "chromedriver.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Find extracted ChromeDriver
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if file == "chromedriver" or file == "chromedriver.exe":
                        chromedriver_path = os.path.join(root, file)
                        os.chmod(chromedriver_path, 0o755)
                        logger.info(f"✅ ChromeDriver downloaded: {chromedriver_path}")
                        return chromedriver_path
            
            raise Exception("ChromeDriver executable not found in downloaded package")
            
        except Exception as e:
            logger.error(f"❌ Error downloading ChromeDriver: {e}")
            return None
    
    def get_webdriver(self, headless: bool = True, stealth_mode: bool = False) -> Optional[webdriver.Chrome]:
        """Get configured Chrome WebDriver with auto-compatibility"""
        try:
            # Get Chrome version
            self.chrome_version = self.get_chrome_version()
            if not self.chrome_version:
                logger.warning("⚠️ Chrome version detection failed, using webdriver-manager")
                return self._get_webdriver_manager_fallback(headless, stealth_mode)
            
            # Get compatible ChromeDriver version
            compatible_version = self.get_compatible_chromedriver_version(self.chrome_version)

            # Check for cached ChromeDriver first
            cached_path = self._get_cached_chromedriver_path(compatible_version)
            if cached_path:
                self.chromedriver_path = str(cached_path)
            else:
                # Download and cache ChromeDriver
                temp_path = self.download_compatible_chromedriver(compatible_version)
                if temp_path:
                    # Cache the downloaded ChromeDriver
                    cached_path = self._cache_chromedriver(compatible_version, Path(temp_path))
                    self.chromedriver_path = str(cached_path)
                else:
                    logger.warning("⚠️ Failed to download compatible ChromeDriver, using webdriver-manager")
                    return self._get_webdriver_manager_fallback(headless, stealth_mode)
            
            # Configure Chrome options
            options = self._get_chrome_options(headless, stealth_mode)
            
            # Create service
            service = Service(executable_path=self.chromedriver_path)
            
            # Create WebDriver
            driver = webdriver.Chrome(service=service, options=options)
            
            # Apply stealth configurations
            if stealth_mode:
                self._apply_stealth_scripts(driver)
            
            logger.info("✅ Enhanced ChromeDriver initialized successfully")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Enhanced driver creation failed: {e}")
            logger.info("🔄 Falling back to webdriver-manager")
            return self._get_webdriver_manager_fallback(headless, stealth_mode)
    
    def _get_webdriver_manager_fallback(self, headless: bool, stealth_mode: bool) -> Optional[webdriver.Chrome]:
        """Fallback using webdriver-manager"""
        if not WEBDRIVER_MANAGER_AVAILABLE:
            logger.error("❌ Webdriver-manager not available")
            return None

        try:
            options = self._get_chrome_options(headless, stealth_mode)
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )

            if stealth_mode:
                self._apply_stealth_scripts(driver)

            logger.info("✅ Fallback ChromeDriver initialized")
            return driver

        except Exception as e:
            logger.error(f"❌ Fallback driver creation failed: {e}")
            return None
    
    def _get_chrome_options(self, headless: bool, stealth_mode: bool) -> Options:
        """Get configured Chrome options"""
        options = Options()
        
        # Basic options
        if headless:
            options.add_argument("--headless=new")
        
        # Performance options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Iranian-specific options
        options.add_argument("--accept-lang=fa-IR,fa,en-US,en")
        options.add_argument("--lang=fa-IR")
        
        # Stealth options
        if stealth_mode:
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Performance optimizations
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # Can be overridden if needed
        
        # Security options for Iranian sites
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        
        return options
    
    def _apply_stealth_scripts(self, driver: webdriver.Chrome):
        """Apply stealth JavaScript configurations"""
        try:
            # Hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Override plugins
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Override languages
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fa-IR', 'fa', 'en-US', 'en']
                });
            """)
            
        except Exception as e:
            logger.warning(f"⚠️ Could not apply stealth scripts: {e}")
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("🧹 Cleaned up temporary ChromeDriver files")
            except Exception as e:
                logger.warning(f"⚠️ Could not cleanup temp files: {e}")

# Global instance
driver_manager = EnhancedDriverManager()
