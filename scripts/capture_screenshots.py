import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "screenshots"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
EXECUTABLE = os.getenv("PLAYWRIGHT_EXECUTABLE_PATH")


def login(page, phone: str) -> None:
    page.goto(BASE_URL)
    page.get_by_test_id("login-phone").fill(phone)
    page.get_by_test_id("login-password").fill("Care1234")
    page.get_by_test_id("login-submit").click()
    expect(page.locator("#dashboard-view")).to_be_visible()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        options = {"headless": True}
        if EXECUTABLE:
            options["executable_path"] = EXECUTABLE
        browser = playwright.chromium.launch(**options)

        context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(BASE_URL)
        page.screenshot(path=OUTPUT / "01-login.png", full_page=True)
        login(page, "13800000001")
        page.screenshot(path=OUTPUT / "02-elderly-dashboard.png", full_page=True)
        page.get_by_role("button", name="心情记录").click()
        page.screenshot(path=OUTPUT / "03-mood-history.png", full_page=True)
        context.close()

        context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        login(page, "13800000002")
        page.screenshot(path=OUTPUT / "04-family-dashboard.png", full_page=True)
        context.close()
        browser.close()
    print(f"Saved screenshots to {OUTPUT}")


if __name__ == "__main__":
    main()
