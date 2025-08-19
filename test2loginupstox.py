from playwright.sync_api import Playwright, sync_playwright
from urllib.parse import parse_qs, urlparse, quote
import pyotp
import requests
import time

# Configuration
API_KEY = "**************8"
SECRET_KEY = "*****"
RURL = "http://localhost:8000/api/broker/upstox/callback"

TOTP_KEY = "I7YOC3GRMOPMZAWLYCRXRAJFIXUDIBFE"
MOBILE_NO = "*****"
PIN = "***"

AUTH_URL = (
    f"https://api-v2.upstox.com/login/authorization/dialog"
    f"?response_type=code&client_id={API_KEY}&redirect_uri={quote(RURL)}"
)


def get_access_token(code: str) -> str:
    """Exchange authorization code for access token"""
    url = "https://api-v2.upstox.com/login/authorization/token"
    headers = {
        "accept": "application/json",
        "Api-Version": "2.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "code": code,
        "client_id": API_KEY,
        "client_secret": SECRET_KEY,
        "redirect_uri": RURL,
        "grant_type": "authorization_code",
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    token = response.json().get("access_token")
    print(f"✅ Access Token: {token}")
    return token


def run_browser(playwright: Playwright) -> str:
    """Automate Upstox login and capture code"""
    browser = playwright.chromium.launch(
        headless=False
    )  # Set headless=True for background run
    context = browser.new_context()
    page = context.new_page()

    with page.expect_request(f"{RURL}?code=*") as request_info:
        page.goto(AUTH_URL)
        print("📲 Entering mobile number...")
        page.fill("#mobileNum", MOBILE_NO)
        page.get_by_role("button", name="Get OTP").click()
        time.sleep(3)

        print("⌛ Waiting for OTP field to appear...")
        page.wait_for_selector("#otpNum", timeout=15000)

        time.sleep(2)
        otp = pyotp.TOTP(TOTP_KEY).now()
        print(f"🔐 TOTP: {otp}")
        page.type("#otpNum", otp, delay=100)
        page.evaluate("document.querySelector('#otpNum').blur()")
        page.wait_for_timeout(1000)

        print("➡️ Clicking Continue...")
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(3000)

        # Check for error messages
        error = page.query_selector(".MuiAlert-message, .errorText")
        if error:
            print("⚠️ OTP validation failed:", error.inner_text())
        else:
            print("⌛ Waiting for PIN field...")
            page.wait_for_selector("input[type='password']", timeout=20000)

        # Wait for Continue to be enabled and retry click if needed
        for i in range(3):
            try:
                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Continue").click(timeout=9000)
                break
            except Exception:
                print(f"⚠️ Retry clicking Continue (OTP step) [{i+1}/3]")

        print("🔒 Entering 6-digit PIN...")
        page.wait_for_selector("input[type='password']", timeout=20000)
        page.fill("input[type='password']", PIN)

        print("👉 Submitting PIN...")
        page.get_by_role("button", name="Continue").click()

        page.wait_for_load_state("networkidle")

    redirect_url = request_info.value.url
    print(f"✅ Redirect URL captured: {redirect_url}")

    parsed_url = urlparse(redirect_url)
    code = parse_qs(parsed_url.query)["code"][0]

    context.close()
    browser.close()
    return code


# === MAIN EXECUTION ===
with sync_playwright() as playwright:
    print("🚀 Launching browser to capture Upstox auth code...")
    auth_code = run_browser(playwright)
    access_token = get_access_token(auth_code)

    print(f"🎉 Done. Access token received: {access_token}")
