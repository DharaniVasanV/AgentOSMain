import os
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def is_google_login_page(page: Page, page_title: str | None = None) -> bool:
    url = page.url.lower() if page.url else ""
    return "accounts.google.com" in url and any(k in url for k in ["/signin", "/v3/signin", "/servicelogin", "identifier"])


async def google_authenticate(page: Page) -> tuple[bool, str]:
    email = os.getenv("GOOGLE_AUTH_EMAIL")
    password = os.getenv("GOOGLE_AUTH_PASSWORD")
    if not email or not password:
        logger.info("GOOGLE_AUTH_EMAIL or GOOGLE_AUTH_PASSWORD not set in .env. Waiting for manual login in the browser window...")
        try:
            # Wait up to 2 minutes for the user to manually log in and redirect away from Google login
            await page.wait_for_url(lambda url: "accounts.google.com" not in url, timeout=120000)
            return True, ""
        except Exception:
            return False, "Manual login timed out. Please make sure to log in within 2 minutes."

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)

        # --- Email step ---
        email_sel = None
        for sel in ['input[name="identifier"]', 'input[type="email"]']:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=6000)
                email_sel = sel
                break
            except Exception:
                continue

        if not email_sel:
            return False, "Could not find Google email input field."

        await page.fill(email_sel, email)
        await page.wait_for_timeout(300)
        await page.keyboard.press("Enter")

        # Wait for navigation to password page
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_url(lambda url: "identifier" not in url.lower(), timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        # --- Password step ---
        # Google keeps a hidden password field on the email page — wait for the visible one
        pw_sel = None
        for sel in ['input[name="Passwd"]', 'input[name="password"]', 'input[type="password"]']:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=8000)
                pw_sel = sel
                break
            except Exception:
                continue

        if not pw_sel:
            return False, "Could not find Google password input field."

        await page.fill(pw_sel, password)
        await page.wait_for_timeout(300)
        await page.keyboard.press("Enter")

        # Wait for post-login redirect
        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_load_state("load", timeout=20000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        if await is_google_login_page(page):
            return False, "Authentication did not complete — still on login page."

        return True, ""

    except Exception as err:
        logger.exception("Google authentication flow failed")
        return False, str(err)
