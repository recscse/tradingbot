"""
Corrected Upstox Automation Service
Only handles the login automation - lets existing callback handle token exchange
"""

import asyncio
import json
import logging
import os
import platform
import schedule
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import pyotp
import pytz  # ✅ Added pytz import
import requests
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import BrokerConfig
from services.upstox_service import (
    calculate_upstox_expiry,
    exchange_code_for_token,
    generate_upstox_auth_url,
)
from utils.logging_utils import log_structured

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global automation lock to prevent multiple concurrent refresh attempts
_sync_lock = threading.Lock()
_last_refresh_attempt = None
_refresh_in_progress = False
_last_refresh_status: Optional[Dict] = None


def _get_automation_lock():
    """
    Get or create the automation lock for the current event loop.
    This uses a loop-attribute pattern to ensure the lock is bound to the correct loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
        
    # Store the lock on the loop object itself to guarantee binding
    if not hasattr(loop, '_upstox_automation_global_lock'):
        loop._upstox_automation_global_lock = asyncio.Lock()
    return loop._upstox_automation_global_lock


class UpstoxAutomationService:
    """
    Automates Upstox login process only - lets existing callback handle token exchange
    """

    def __init__(self):
        # Load user credentials from environment
        self.mobile_no = os.getenv("UPSTOX_MOBILE", "")
        self.pin = os.getenv("UPSTOX_PIN", "")
        self.totp_key = os.getenv("UPSTOX_TOTP_KEY", "")

        # ✅ Add configurable headless mode
        self.headless_mode = os.getenv("UPSTOX_HEADLESS", "true").lower() == "true"

        # Store captured authorization code
        self._captured_auth_code = None

        # Validate critical configuration
        missing_vars = []
        if not self.mobile_no or self.mobile_no == "your_mobile_number":
            missing_vars.append("UPSTOX_MOBILE")
        if not self.pin or self.pin == "your_6_digit_pin":
            missing_vars.append("UPSTOX_PIN")

        # Fix for Railway/Docker: Ensure Playwright looks in the correct location
        if os.path.exists("/ms-playwright"):
            logger.info("Found /ms-playwright directory, setting PLAYWRIGHT_BROWSERS_PATH")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"

        if missing_vars:
            error_msg = f"Missing or invalid environment variables: {', '.join(missing_vars)}. Please configure them in .env file."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"✅ Upstox automation service initialized for mobile: {self.mobile_no[:4]}****{self.mobile_no[-2:]}"
        )

    def _get_instance_lock(self):
        """
        Get or create instance lock for the current event loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None

        # Use a unique attribute name per instance
        attr_name = f'_upstox_instance_lock_{id(self)}'
        if not hasattr(loop, attr_name):
            setattr(loop, attr_name, asyncio.Lock())
        return getattr(loop, attr_name)

    def get_admin_broker_config(self, db: Session) -> Optional[BrokerConfig]:
        """
        Fetch the admin user's Upstox broker configuration from database
        """
        try:
            from database.models import User

            admin_broker = (
                db.query(BrokerConfig)
                .join(User, BrokerConfig.user_id == User.id)
                .filter(
                    User.role == "admin",
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.access_token.isnot(None),
                    BrokerConfig.api_key.isnot(None),
                    BrokerConfig.api_secret.isnot(None),
                )
                .first()
            )

            if not admin_broker:
                logger.error(
                    "No active Upstox broker configuration found for admin user"
                )
                return None

            if not admin_broker.api_key or not admin_broker.api_secret:
                logger.error("Admin broker config missing API credentials")
                return None

            logger.info(
                f"Found admin broker config: ID {admin_broker.id}, User {admin_broker.user_id}"
            )
            return admin_broker

        except Exception as e:
            logger.error(f"Error fetching admin broker config: {e}")
            return None

    async def _run_playwright_with_proactor_loop(self, api_key: str, admin_user_id: int) -> bool:
        """
        Run Playwright in a separate thread with ProactorEventLoop for Windows compatibility
        """
        import concurrent.futures

        def run_in_new_loop():
            # Create new event loop with ProactorEventLoop policy
            if platform.system() == 'Windows':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(self._playwright_login_impl(api_key, admin_user_id))
            finally:
                new_loop.close()

        # CRITICAL FIX: Run in thread pool with reduced timeout to prevent blocking
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            try:
                return future.result(timeout=30)  # REDUCED to 30 seconds to prevent app freeze
            except concurrent.futures.TimeoutError:
                logger.error("⏰ Playwright automation timed out after 30 seconds")
                return False

    async def _playwright_login_impl(self, api_key: str, admin_user_id: int) -> bool:
        """
        Implementation of Playwright login automation
        """
        from playwright.async_api import async_playwright

        # Generate auth URL using existing service
        auth_url = generate_upstox_auth_url(api_key, user_id=admin_user_id)
        redirect_uri = os.getenv("UPSTOX_REDIRECT_URI")

        logger.info(f"Starting login automation for auth URL: {auth_url}")
        logger.info(f"Callback will handle token exchange at: {redirect_uri}")
        log_structured(event="LOGIN_AUTOMATION_START", message="Starting Playwright login automation", data={"auth_url": auth_url, "redirect_uri": redirect_uri})

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless_mode,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-blink-features=AutomationControlled",  # ✅ STEALTH: Hide automation flag
                    "--no-first-run",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-zygote",
                    "--disable-accelerated-2d-canvas",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                ],
            )
            
            # ✅ STEALTH: Use realistic User Agent and Viewport
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1,
            )
            
            # ✅ STEALTH: Add init script to mask webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()

            try:
                # Navigate to auth URL with timeout
                logger.info(f"Navigating to: {auth_url}")
                try:
                    await page.goto(auth_url, timeout=45000, wait_until="domcontentloaded") # Increased timeout
                except Exception as nav_err:
                     logger.error(f"Navigation timed out: {nav_err}")
                     # Try to proceed anyway, maybe it loaded enough
                
                logger.info("✅ Navigated to Upstox auth page")

                # Fill mobile number
                logger.info("🔢 Filling mobile number...")
                try:
                    await page.wait_for_selector("#mobileNum", timeout=20000)
                    await page.locator("#mobileNum").click()
                    await page.locator("#mobileNum").fill(self.mobile_no)
                    await page.get_by_role("button", name="Get OTP").click()
                    logger.info("✅ Mobile number entered, OTP requested")
                except Exception as e:
                    title = await page.title()
                    content = await page.content()
                    logger.error(f"❌ Failed to find mobile field. Page Title: {title}")
                    logger.error(f"❌ URL: {page.url}")
                    if "Cloudflare" in title or "Just a moment" in title:
                        logger.error("❌ BLOCKED BY CLOUDFLARE/CAPTCHA")
                    raise e

                # Wait for OTP field and fill TOTP
                logger.info("🔐 Waiting for OTP field...")
                try:
                    await page.wait_for_selector("#otpNum", timeout=20000)
                    await page.locator("#otpNum").click()
                    if self.totp_key:
                        otp = pyotp.TOTP(self.totp_key).now()
                        await page.locator("#otpNum").fill(otp)
                        logger.info("✅ TOTP entered")
                    else:
                        logger.error("❌ TOTP key not configured")
                        log_structured(event="LOGIN_AUTOMATION_FAILED", level="ERROR", message="TOTP key not configured")
                        return False

                    await page.get_by_role("button", name="Continue").click()
                except Exception as e:
                    logger.error(f"❌ Failed during OTP step: {e}")
                    raise e

                # Fill PIN
                try:
                    # Try different selectors for PIN as they can vary
                    logger.info("🔢 Waiting for PIN field...")
                    await page.wait_for_selector("input[type='password']", timeout=20000)
                    
                    # Some flows might ask for 'Enter 6-digit PIN' label
                    # We try a generic approach for the first password input found
                    await page.locator("input[type='password']").first.fill(self.pin)
                    logger.info("PIN entered")

                    # Click continue - this will trigger the redirect to callback
                    await page.get_by_role("button", name="Continue").click()
                except Exception as e:
                    logger.error(f"❌ Failed during PIN step: {e}")
                    raise e

                # Wait for redirect to happen and capture the authorization code
                logger.info("Waiting for redirect with authorization code...")

                try:
                    # INCREASED: 120 attempts × 500ms = 60 seconds max wait (was 30 seconds)
                    # Cloud environments like Railway can be slower
                    max_attempts = 120
                    attempt = 0
                    auth_code_found = False
                    last_url = ""

                    logger.info("⏳ Waiting for authorization redirect (max 30 seconds)...")

                    while attempt < max_attempts and not auth_code_found:
                        await page.wait_for_timeout(500)
                        current_url = page.url

                        # Log URL changes to debug where it might be stuck
                        if current_url != last_url:
                            logger.info(f"🔗 Automation at URL: {current_url[:100]}...")

                        if "code=" in current_url:
                            logger.info(f"✅ Auth redirect detected: {current_url[:100]}...")
                            await page.wait_for_timeout(1000)

                            final_url = page.url
                            if final_url == current_url and "code=" in final_url:
                                from urllib.parse import urlparse, parse_qs

                                parsed_url = urlparse(final_url)
                                query_params = parse_qs(parsed_url.query)

                                if "code" in query_params and query_params["code"]:
                                    auth_code = query_params["code"][0]
                                    logger.info(f"Authorization code captured: {auth_code[:10]}...")

                                    if len(auth_code) >= 1:
                                        self._captured_auth_code = auth_code
                                        auth_code_found = True
                                        logger.info("✅ Login automation completed - redirect detected")
                                        log_structured(event="LOGIN_AUTOMATION_COMPLETE", message="Login automation successful, redirect detected")
                                        return True
                                    else:
                                        logger.warning(f"Auth code format invalid: {len(auth_code)} chars")
                            else:
                                logger.info("URL still changing, waiting for stabilization...")

                        last_url = current_url
                        attempt += 1

                    if not auth_code_found:
                        logger.warning(f"No valid authorization code found after {max_attempts * 0.5} seconds - callback will handle token exchange")
                        logger.warning(f"Final URL was: {page.url[:200]}")
                        log_structured(event="LOGIN_AUTOMATION_WARNING", level="WARNING", message="Auth code not captured, fallback to callback")
                    return True

                except Exception as redirect_error:
                    logger.warning(f"Redirect capture failed: {redirect_error}")
                    logger.info("✅ Login automation completed - fallback to callback")
                    log_structured(event="LOGIN_AUTOMATION_WARNING", level="WARNING", message=f"Redirect capture failed: {str(redirect_error)}")
                    return True

            finally:
                await context.close()
                await browser.close()

    def _test_token_validity(self, access_token: str) -> bool:
        """
        Test if the access token is valid by making a simple API call to Upstox
        """
        try:
            import requests

            if not access_token or len(access_token.strip()) < 10:
                logger.warning("❌ Invalid token format - too short or empty")
                return False

            headers = {
                "Authorization": f"Bearer {access_token.strip()}",
                "Accept": "application/json",
            }
            test_url = "https://api.upstox.com/v2/user/profile"

            logger.debug(f"🔍 Testing token validity with API call to {test_url}")
            response = requests.get(test_url, headers=headers, timeout=15)

            if response.status_code == 200:
                try:
                    profile_data = response.json()
                    if profile_data.get("status") == "success":
                        logger.info(
                            f"✅ Token validation successful - User: {profile_data.get('data', {}).get('user_name', 'Unknown')}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"❌ Token validation failed - API response: {profile_data}"
                        )
                        return False
                except json.JSONDecodeError:
                    logger.warning("❌ Token validation failed - Invalid JSON response")
                    return False
            elif response.status_code == 401:
                logger.warning(
                    "❌ Token validation failed - Invalid/expired token (401)"
                )
                try:
                    error_data = response.json()
                    logger.warning(f"❌ Token error details: {error_data}")
                except:
                    logger.warning(f"❌ Token error response: {response.text[:200]}")
                return False
            elif response.status_code == 403:
                logger.warning("❌ Token validation failed - Access forbidden (403)")
                return False
            else:
                logger.warning(
                    f"❌ Token validation failed - Unexpected status: {response.status_code}"
                )
                logger.warning(f"❌ Response: {response.text[:200]}")
                return False

        except requests.RequestException as e:
            logger.error(f"❌ Token validation network error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            return False

    async def automate_login_only(self, api_key: str, admin_user_id: int) -> bool:
        """
        Automate ONLY the login process (mobile, OTP, PIN)
        Returns True if login was successful, False otherwise
        Does NOT handle token exchange - that's done by the callback endpoint
        """
        try:
            # Windows-specific: Set ProactorEventLoop policy for subprocess support
            if platform.system() == 'Windows':
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # Fallback if no loop is running (unlikely here)
                    loop = None

                if loop and not isinstance(loop, asyncio.ProactorEventLoop):
                    logger.info("Setting Windows ProactorEventLoop for Playwright subprocess support")
                    # We need to run Playwright in a new event loop with ProactorEventLoop
                    return await self._run_playwright_with_proactor_loop(api_key, admin_user_id)

            # For non-Windows or if already on ProactorEventLoop, use direct implementation
            return await self._playwright_login_impl(api_key, admin_user_id)

        except ImportError as e:
            logger.error(f"Playwright not available: {e}")
            logger.error("Browser automation requires Playwright installation")
            return False
        except Exception as e:
            logger.error(f"Login automation failed: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            if "browser" in str(e).lower() or "chromium" in str(e).lower():
                logger.error("Browser-related error - check if Chromium is properly installed")
            return False

    async def wait_for_token_refresh(
        self, broker: BrokerConfig, db: Session, timeout_seconds: int = 45
    ) -> Dict:
        """
        Wait for the callback endpoint to complete token refresh
        """
        start_time = time.time()
        original_token = broker.access_token

        while time.time() - start_time < timeout_seconds:
            # Refresh broker from database
            db.refresh(broker)

            # Check if token was updated
            if broker.access_token != original_token:
                logger.info(f"✅ Token refresh detected for broker {broker.id}")
                return {
                    "success": True,
                    "broker_id": broker.id,
                    "user_id": broker.user_id,
                    "expires_at": (
                        broker.access_token_expiry.isoformat()
                        if broker.access_token_expiry
                        else None
                    ),
                    "message": "Token refresh completed by callback endpoint",
                }

            # Check if there's an error
            if broker.last_error_message:
                logger.error(f"❌ Token refresh failed: {broker.last_error_message}")
                return {
                    "success": False,
                    "error": broker.last_error_message,
                    "broker_id": broker.id,
                }

            # Wait a bit before checking again
            await asyncio.sleep(2)

        # Timeout reached
        logger.error(f"⏰ Timeout waiting for token refresh for broker {broker.id}")
        return {
            "success": False,
            "error": f"Timeout waiting for token refresh (waited {timeout_seconds} seconds)",
            "broker_id": broker.id,
        }

    async def refresh_admin_upstox_token(self, emergency_bypass: bool = False) -> Dict:
        """
        Refresh the admin user's Upstox token with proper synchronization
        1. Automate login process
        2. Wait for callback to handle token exchange
        """
        global _refresh_in_progress, _last_refresh_attempt

        # Use loop-specific lock to prevent concurrent refresh attempts within the same loop
        automation_lock = _get_automation_lock()
        
        # Guard against calling outside a loop
        if automation_lock is None:
            logger.error("❌ Cannot refresh token: No active event loop found")
            return {"success": False, "error": "No active event loop"}

        async with automation_lock:
            # ✅ CRITICAL FIX: Always allow refresh if emergency_bypass=True or token is expired
            now = datetime.now()
            should_proceed = emergency_bypass
            
            log_structured(
                event="TOKEN_REFRESH_ATTEMPT", 
                message="Starting admin token refresh attempt",
                data={"emergency_bypass": emergency_bypass}
            )

            # Check if token is actually expired - always allow refresh for expired tokens
            try:
                db = SessionLocal()
                admin_broker = self.get_admin_broker_config(db)
                if admin_broker and admin_broker.access_token_expiry:
                    if admin_broker.access_token_expiry < now:
                        should_proceed = True
                        logger.info(
                            "🚨 Token expired - proceeding with emergency refresh"
                        )
                    # Test current token validity if near expiry
                    elif (
                        admin_broker.access_token_expiry - now
                    ).total_seconds() < 600:  # 10 minutes
                        try:
                            if not self._test_token_validity(admin_broker.access_token):
                                should_proceed = True
                                logger.info(
                                    "🚨 Token failed API validation - proceeding with refresh"
                                )
                        except Exception:
                            should_proceed = True
                            logger.info(
                                "🚨 Token validation error - proceeding with refresh"
                            )
                db.close()
            except Exception as e:
                logger.warning(f"Could not check token status: {e}")
                should_proceed = True  # Proceed if we can't verify

            # Use threading lock to protect global state check across loops/threads
            with _sync_lock:
                # Only check cooldown if not in emergency/expired mode
                if not should_proceed:
                    if (
                        _last_refresh_attempt
                        and (now - _last_refresh_attempt).seconds < 120
                    ):
                        logger.warning(
                            "⏳ Token refresh attempted recently, skipping duplicate request"
                        )
                        log_structured(event="TOKEN_REFRESH_SKIPPED", level="WARNING", message="Token refresh skipped due to cooldown")
                        return {
                            "success": False,
                            "error": "Token refresh attempted recently. Please wait before retrying.",
                            "retry_after_seconds": 120
                            - (now - _last_refresh_attempt).seconds,
                        }

                    if _refresh_in_progress:
                        logger.warning(
                            "⏳ Token refresh already in progress, skipping duplicate request"
                        )
                        log_structured(event="TOKEN_REFRESH_SKIPPED", level="WARNING", message="Token refresh skipped - already in progress")
                        return {
                            "success": False,
                            "error": "Token refresh already in progress",
                        }

                _refresh_in_progress = True
                _last_refresh_attempt = now

            try:
                return await self._perform_token_refresh()
            finally:
                with _sync_lock:
                    _refresh_in_progress = False

    async def _perform_token_refresh(self) -> Dict:
        """
        Internal method to perform the actual token refresh
        """
        global _last_refresh_status
        db = SessionLocal()
        try:
            logger.info("Starting admin-only Upstox token refresh")

            # Get admin broker configuration from database
            admin_broker = self.get_admin_broker_config(db)
            if not admin_broker:
                log_structured(event="TOKEN_REFRESH_FAILED", level="ERROR", message="No admin broker config found")
                return {
                    "success": False,
                    "error": "No admin Upstox broker configuration found in database",
                }

            # Check if token needs refresh
            now = datetime.now()
            tomorrow = now + timedelta(days=1)

            # Check if token needs refresh - Upstox tokens expire daily at 3:30 AM
            now = datetime.now()

            # First, test if the token actually works with Upstox API
            token_is_valid = self._test_token_validity(admin_broker.access_token)

            if not token_is_valid:
                logger.warning(
                    f"Admin token failed API validation despite expiry time: {admin_broker.access_token_expiry}"
                )
                logger.info("Token is invalid, forcing refresh...")
            else:
                # If token is valid and not expiring within 30 minutes, no refresh needed
                refresh_threshold = now + timedelta(minutes=30)

                if (
                    admin_broker.access_token_expiry
                    and admin_broker.access_token_expiry > refresh_threshold
                ):
                    logger.info(
                        f"Admin token is valid and not yet expired. Expires at: {admin_broker.access_token_expiry}"
                    )
                    log_structured(event="TOKEN_REFRESH_SKIPPED", message="Token is valid and not expired")
                    return {
                        "success": True,
                        "message": "Admin token is still valid, no refresh needed",
                        "expires_at": admin_broker.access_token_expiry.isoformat(),
                        "broker_id": admin_broker.id,
                    }

            logger.info(
                f"Admin token expires at: {admin_broker.access_token_expiry}, refreshing now"
            )

            # Clear any previous error messages
            admin_broker.last_error_message = None
            db.commit()

            # Step 1: Automate login process and capture auth code
            logger.info("🤖 Starting automated login...")
            self._captured_auth_code = None  # Clear any stale code
            login_success = await self.automate_login_only(
                admin_broker.api_key, admin_broker.user_id
            )

            if not login_success:
                error_msg = "Failed to complete automated login"
                admin_broker.last_error_message = error_msg
                db.commit()
                log_structured(event="TOKEN_REFRESH_FAILED", level="ERROR", message=error_msg)
                return {"success": False, "error": error_msg}

            # Step 2: WAIT for callback to handle token exchange (Verification)
            logger.info("⏳ Login successful - waiting for callback to complete token exchange...")
            
            result = await self.wait_for_token_refresh(admin_broker, db)

            if result["success"]:
                # Update config with automation timestamp
                if not admin_broker.config:
                    admin_broker.config = {}
                admin_broker.config["last_automated_refresh"] = (
                    datetime.now().isoformat()
                )
                db.commit()
                log_structured(event="TOKEN_REFRESH_SUCCESS", message="Token refresh completed successfully")
            else:
                log_structured(event="TOKEN_REFRESH_FAILED", level="ERROR", message=result.get("error", "Unknown error"))

            result_dict = {
                "success": result["success"],
                "message": f"Admin token refresh {'completed' if result['success'] else 'failed'}",
                "broker_id": admin_broker.id,
                "user_id": admin_broker.user_id,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }

            # Notify centralized WebSocket manager about token update
            if result["success"]:
                await self._notify_websocket_manager_about_token_refresh(admin_broker)

            # Update global status
            _last_refresh_status = result_dict

            return result_dict

        except Exception as e:
            logger.error(f"Error in refresh_admin_upstox_token: {e}")
            log_structured(event="TOKEN_REFRESH_ERROR", level="ERROR", message=str(e))
            
            error_result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            _last_refresh_status = error_result
            
            return error_result
        finally:
            db.close()

    async def _notify_websocket_manager_about_token_refresh(self, broker: BrokerConfig):
        """
        Notify the centralized WebSocket manager about successful token refresh
        """
        try:
            # Try to notify the centralized WebSocket manager (avoid circular imports)
            import importlib
            import sys

            if "services.centralized_ws_manager" in sys.modules:
                ws_module = sys.modules["services.centralized_ws_manager"]
                if hasattr(ws_module, "get_centralized_manager"):
                    manager = ws_module.get_centralized_manager()
                    if manager and hasattr(manager, "reload_admin_token"):
                        # Reload the token first
                        token_reloaded = await manager.reload_admin_token()
                        if token_reloaded:
                            logger.info(
                                "✅ WebSocket manager token reloaded successfully"
                            )

                            # Try to trigger reconnection but don't force it aggressively
                            if hasattr(manager, "force_reconnect"):
                                try:
                                    await manager.force_reconnect()
                                    logger.info(
                                        "✅ Triggered WebSocket force reconnection with new token"
                                    )
                                except Exception as reconnect_error:
                                    logger.warning(
                                        f"⚠️ Force reconnect failed: {reconnect_error}"
                                    )
                            else:
                                logger.info(
                                    "ℹ️ WebSocket manager will reconnect automatically on next attempt"
                                )
                        else:
                            logger.warning(
                                "❌ Failed to reload token in WebSocket manager"
                            )
                        return

            logger.info(
                "ℹ️ Centralized WebSocket manager not loaded yet - will reload token on next connection attempt"
            )

        except Exception as e:
            logger.warning(f"⚠️ Could not notify centralized WebSocket manager: {e}")

    # Keep other methods for backward compatibility...
    async def refresh_all_expired_tokens(self, admin_only: bool = True) -> Dict:
        """DEPRECATED: Use refresh_admin_upstox_token() instead"""
        logger.warning(
            "refresh_all_expired_tokens is deprecated. Use refresh_admin_upstox_token instead"
        )
        return await self.refresh_admin_upstox_token()

    async def refresh_user_tokens(self, user_id: int) -> Dict:
        """Refresh tokens for a specific user"""
        logger.info(f"User-specific token refresh requested for user {user_id}")

        db = SessionLocal()
        try:
            from database.models import User

            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role and user.role.lower() == "admin":
                logger.info(f"User {user_id} is admin, using admin token refresh")
                return await self.refresh_admin_upstox_token()
            else:
                logger.info(f"User {user_id} is not admin, automation not available")
                return {
                    "success": False,
                    "message": f"Automated token refresh only available for admin users. User {user_id} needs to manually refresh tokens.",
                    "user_id": user_id,
                    "requires_manual_refresh": True,
                }
        finally:
            db.close()


# Scheduler and other classes remain the same...
class UpstoxTokenScheduler:
    """Simple scheduler for daily token refresh"""

    def __init__(self):
        self.automation_service = UpstoxAutomationService()
        self.is_running = False
        self.scheduler_thread = None

    def _ist_to_system_time(self, ist_time_str: str) -> str:
        """
        Converts a time string (HH:MM) from IST to the system's local time.
        Handles date rollovers implicitly by returning HH:MM.
        """
        try:
            hours, minutes = map(int, ist_time_str.split(':'))
            
            # Current time in IST
            ist_tz = pytz.timezone('Asia/Kolkata')
            now_ist = datetime.now(ist_tz)
            
            # Target time today in IST
            target_ist = now_ist.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            # Convert to system's local timezone (naive datetime matching system clock)
            # We use astimezone(None) to convert to local system time
            target_system = target_ist.astimezone(None)
            
            system_time_str = target_system.strftime('%H:%M')
            logger.info(f"🕒 Timezone Adj: {ist_time_str} IST -> {system_time_str} System Time")
            return system_time_str
        except Exception as e:
            logger.error(f"Error converting timezone: {e}")
            return ist_time_str  # Fallback to original

    def start_scheduler(self):
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting Upstox token refresh scheduler...")
        
        # Convert IST schedule times to system time
        t_0345 = self._ist_to_system_time("03:45")
        t_0400 = self._ist_to_system_time("04:00")
        t_0600 = self._ist_to_system_time("06:00")
        t_0830 = self._ist_to_system_time("08:30")

        # Upstox tokens expire daily at 3:30 AM IST
        schedule.every().day.at(t_0345).do(self._run_refresh)  # 15 min after expiry
        schedule.every().day.at(t_0400).do(self._run_refresh)  # Backup refresh
        schedule.every().day.at(t_0600).do(self._run_refresh)  # Morning backup
        
        # ✅ NEW: Market open preparation check (Active Validation)
        schedule.every().day.at(t_0830).do(self.validate_and_refresh_if_needed)
        
        # Regular monitoring
        schedule.every(1).hours.do(self._check_and_refresh_expired)

        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        logger.info("✅ Scheduler started")

    def stop_scheduler(self):
        if not self.is_running:
            return
        logger.info("Stopping scheduler...")
        self.is_running = False
        schedule.clear()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("✅ Scheduler stopped")

    def _scheduler_loop(self):
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def _run_refresh(self):
        logger.info("⏰ Scheduled admin token refresh triggered")
        try:
            # Check if refresh is already in progress (global flag)
            global _refresh_in_progress
            if _refresh_in_progress:
                logger.warning(
                    "🔄 Token refresh already in progress, skipping scheduled refresh"
                )
                return

            def run_async_refresh():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.automation_service.refresh_admin_upstox_token()
                    )

                    if result["success"]:
                        logger.info(
                            f"✅ Scheduled admin refresh completed: {result.get('message', 'Token refreshed')}"
                        )
                    else:
                        logger.error(
                            f"❌ Scheduled admin refresh failed: {result.get('error')}"
                        )
                except Exception as e:
                    logger.error(f"❌ Exception during scheduled refresh: {e}")
                finally:
                    loop.close()

            refresh_thread = threading.Thread(target=run_async_refresh, daemon=True)
            refresh_thread.start()

        except Exception as e:
            logger.error(f"❌ Scheduled admin refresh failed: {e}")

    def validate_and_refresh_if_needed(self):
        """
        Active check: tests if the token actually works against the API.
        If invalid, triggers a refresh immediately.
        Scheduled for market open preparation (08:30 AM).
        """
        logger.info("🔍 Performing Pre-Market Token Validation (08:30 AM Check)...")
        self._check_and_refresh_expired(active_validation=True)

    def _check_and_refresh_expired(self, active_validation: bool = False):
        logger.info(f"🔍 Checking for expired admin tokens (Active Validation: {active_validation})...")
        try:
            from database.connection import SessionLocal
            from database.models import BrokerConfig, User

            db = SessionLocal()
            try:
                now = datetime.now()
                # 1. Check for expired tokens (Time-based)
                expired_admin_broker = (
                    db.query(BrokerConfig)
                    .join(User)
                    .filter(
                        BrokerConfig.broker_name.ilike("upstox"),
                        BrokerConfig.is_active == True,
                        BrokerConfig.access_token_expiry < now,
                        User.role.ilike("admin"),
                        BrokerConfig.api_key.isnot(None),
                        BrokerConfig.api_secret.isnot(None),
                    )
                    .first()
                )

                if expired_admin_broker:
                    logger.warning("🚨 Found expired admin token (Time-based) - triggering refresh")
                    self._run_refresh()
                    return

                # 2. Active Validation (API-based) - If requested or if token seems valid but might be revoked
                if active_validation:
                    admin_broker = (
                        db.query(BrokerConfig)
                        .join(User)
                        .filter(
                            BrokerConfig.broker_name.ilike("upstox"),
                            BrokerConfig.is_active == True,
                            User.role.ilike("admin"),
                        )
                        .first()
                    )
                    
                    if admin_broker and admin_broker.access_token:
                        logger.info(f"🧪 Testing token validity for {admin_broker.broker_name}...")
                        is_valid = self.automation_service._test_token_validity(admin_broker.access_token)
                        
                        if not is_valid:
                            logger.warning("🚨 Token is invalid (API Rejected) despite valid expiry time - triggering refresh")
                            self._run_refresh()
                        else:
                            logger.info("✅ Admin token is valid and active")
                    else:
                        logger.warning("⚠️ No active admin broker config found for validation")

                else:
                    logger.info(
                        "✅ No expired admin tokens found during monitoring check"
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in monitoring check: {e}")

    def trigger_manual_refresh(self):
        logger.info("🔄 Manual refresh triggered")
        self._run_refresh()


# Global functions
_scheduler = None


def get_upstox_scheduler() -> UpstoxTokenScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = UpstoxTokenScheduler()
    return _scheduler


def start_upstox_automation():
    try:
        scheduler = get_upstox_scheduler()
        scheduler.start_scheduler()
        logger.info("✅ Upstox automation service started")
        return scheduler
    except Exception as e:
        logger.error(f"❌ Failed to start Upstox automation: {e}")
        return None


def stop_upstox_automation():
    try:
        global _scheduler
        if _scheduler:
            _scheduler.stop_scheduler()
            logger.info("✅ Upstox automation service stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping Upstox automation: {e}")


async def refresh_upstox_tokens_now() -> Dict:
    try:
        service = UpstoxAutomationService()
        return await service.refresh_admin_upstox_token()
    except Exception as e:
        logger.error(f"Manual admin refresh failed: {e}")
        return {"success": False, "error": str(e)}


def get_automation_status() -> Dict:
    """Get the status of the last automation run"""
    global _last_refresh_status
    if _last_refresh_status:
        return _last_refresh_status
    return {"status": "unknown", "message": "No automation run recorded yet"}
