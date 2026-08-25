import os
import random

import pytest

pytestmark = pytest.mark.ui

if os.getenv("RUN_UI_TESTS") != "1":
    pytest.skip("Set RUN_UI_TESTS=1 and start the app to run Playwright UI tests", allow_module_level=True)

from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        executable_path = os.getenv("PLAYWRIGHT_EXECUTABLE_PATH")
        launch_options = {"headless": True}
        if executable_path:
            launch_options["executable_path"] = executable_path
        browser = playwright.chromium.launch(**launch_options)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser):
    context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(8_000)
    yield page
    context.close()


def unique_phone() -> str:
    return f"139{random.randint(10_000_000, 99_999_999)}"


def register(page: Page, role: str = "elderly") -> str:
    phone = unique_phone()
    page.goto(BASE_URL)
    page.get_by_role("tab", name="注册").click()
    if role == "family":
        page.locator('input[name="role"][value="family"]').check()
    page.locator("#register-name").fill("自动化测试用户")
    page.locator("#register-phone").fill(phone)
    page.locator("#register-password").fill("UiTest123")
    page.locator('input[name="consent"]').check()
    page.get_by_role("button", name="同意并注册").click()
    expect(page.get_by_role("heading", name="您好，自动化测试用户")).to_be_visible()
    return phone


def test_home_has_medical_boundary_and_large_controls(page: Page):
    page.goto(BASE_URL)
    expect(page.get_by_text("本平台仅用于日常情绪关怀")).to_be_visible()
    expect(page.get_by_role("button", name="增大字号")).to_be_visible()
    expect(page.get_by_role("button", name="高对比")).to_be_visible()


def test_font_size_control_changes_root_font(page: Page):
    page.goto(BASE_URL)
    before = page.evaluate("getComputedStyle(document.documentElement).fontSize")
    page.get_by_role("button", name="增大字号").click()
    after = page.evaluate("getComputedStyle(document.documentElement).fontSize")
    assert int(after.removesuffix("px")) > int(before.removesuffix("px"))


def test_high_contrast_mode_is_keyboard_accessible(page: Page):
    page.goto(BASE_URL)
    button = page.get_by_role("button", name="高对比")
    button.focus()
    page.keyboard.press("Enter")
    expect(button).to_have_attribute("aria-pressed", "true")
    assert page.locator("body").evaluate("element => element.classList.contains('high-contrast')")


def test_elderly_can_register_and_see_dashboard(page: Page):
    register(page, "elderly")
    expect(page.get_by_text("每天一分钟，关心多一点")).not_to_be_visible()
    expect(page.get_by_role("button", name="记录心情")).to_be_visible()
    expect(page.get_by_text("老人端")).to_be_visible()


def test_elderly_can_submit_mood_and_view_history(page: Page):
    register(page, "elderly")
    private_text = "今天和朋友散步，我很开心"
    page.get_by_test_id("mood-text").fill(private_text)
    page.get_by_test_id("mood-submit").click()
    expect(page.get_by_test_id("mood-text")).to_have_value("")
    expect(page.locator("#latest-mood")).to_have_text("积极")
    page.get_by_role("button", name="心情记录").click()
    expect(page.get_by_text(private_text)).to_be_visible()
    expect(page.locator("#mood-history").get_by_text("不构成医疗诊断", exact=False)).to_be_visible()


def test_family_registration_shows_confirmed_link_flow(page: Page):
    register(page, "family")
    page.get_by_role("button", name="家庭关怀").click()
    expect(page.get_by_role("heading", name="绑定老人账号")).to_be_visible()
    expect(page.get_by_text("需要老人本人登录确认")).to_be_visible()
    expect(page.locator("#target-picker")).to_be_disabled()


def test_logout_clears_session_and_returns_to_login(page: Page):
    register(page, "elderly")
    page.get_by_role("button", name="退出登录").click()
    expect(page.get_by_role("heading", name="欢迎回来")).to_be_visible()
    page.reload()
    expect(page.get_by_role("heading", name="欢迎回来")).to_be_visible()
