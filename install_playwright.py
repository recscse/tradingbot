#!/usr/bin/env python3
"""
Playwright installer for Render deployment
Handles installation without requiring root access
"""

import subprocess
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_playwright():
    """Install Playwright browser for Render deployment"""
    
    # Set environment variables for container deployment
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/.playwright"
    os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "false"
    
    logger.info("🌐 Installing Playwright for Render deployment...")
    
    try:
        # Try to import playwright first
        from playwright.async_api import async_playwright
        logger.info("✅ Playwright already available")
        
        # Install browser without system dependencies (avoid root requirement)
        logger.info("📦 Installing Chromium browser (no deps)...")
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium", "--with-deps=false"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ Chromium browser installed successfully")
            return True
        else:
            logger.warning(f"⚠️ Browser installation output: {result.stdout}")
            logger.warning(f"⚠️ Browser installation error: {result.stderr}")
            
            # Try alternative installation method
            logger.info("🔄 Trying alternative installation...")
            os.makedirs("/tmp/.playwright", exist_ok=True)
            
            # Alternative: try just the browser binary
            result2 = subprocess.run([
                sys.executable, "-m", "playwright", "install-deps", "chromium"
            ], capture_output=True, text=True, timeout=300)
            
            if result2.returncode != 0:
                logger.warning("⚠️ Alternative installation also failed")
                logger.info("📝 Application will continue without browser automation")
                return False
            else:
                logger.info("✅ Alternative installation succeeded")
                return True
            
    except ImportError:
        logger.error("❌ Playwright not found in Python packages")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Installation timeout (5 minutes)")
        return False
    except Exception as e:
        logger.error(f"❌ Installation error: {e}")
        return False

def verify_installation():
    """Verify Playwright installation works"""
    try:
        import asyncio
        from playwright.async_api import async_playwright
        
        async def test():
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox', 
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--no-first-run',
                            '--disable-default-apps',
                            '--disable-extensions'
                        ]
                    )
                    await browser.close()
                    return True
            except Exception as e:
                logger.warning(f"⚠️ Browser verification failed: {e}")
                return False
        
        result = asyncio.run(test())
        if result:
            logger.info("✅ Playwright verification successful")
            return True
        else:
            logger.warning("⚠️ Playwright verification failed")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Verification error: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Playwright installation for Render...")
    
    # Install Playwright
    install_success = install_playwright()
    
    if install_success:
        # Verify installation
        verify_success = verify_installation()
        if verify_success:
            logger.info("🎉 Playwright setup completed successfully!")
            sys.exit(0)
        else:
            logger.warning("⚠️ Installation completed but verification failed")
            logger.info("📝 Browser automation may not work properly")
            sys.exit(0)  # Don't fail deployment for this
    else:
        logger.warning("⚠️ Playwright installation failed")
        logger.info("📝 Application will continue without browser automation")
        logger.info("📝 Token refresh will require manual authentication")
        sys.exit(0)  # Don't fail deployment for this