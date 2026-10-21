#!/usr/bin/env python3
"""Real Chromium checks of language, clipboard, mobile layout and no-JS content.

Run from a checkout: python3 tests/browser/smoke.py
No model evaluation. Serves only this local checkout on a loopback port.
"""
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_site import build

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@contextmanager
def server():
    with tempfile.TemporaryDirectory(prefix="qa-site-") as tmp:
        build(Path(tmp))
        with serve_directory(Path(tmp)) as address:
            yield address


@contextmanager
def serve_directory(directory):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(directory)))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def main():
    with server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"],
                                      reduced_motion="reduce", viewport={"width": 1280, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/?lang=zh&utm_source=smoke", wait_until="networkidle")
        assert page.locator("html").get_attribute("lang") == "zh-CN"
        page.locator(".nav-lang").click()
        page.wait_for_url("**/en/**")
        page.wait_for_load_state("networkidle")
        assert "utm_source=smoke" in page.url
        assert page.locator("html").get_attribute("lang") == "en"
        assert "QA" in page.title() or "AI" in page.title()
        assert page.locator(".zh-only:visible").count() == 0
        page.locator(".copy-btn").first.click()
        page.wait_for_function("navigator.clipboard.readText().then(t => t.includes(\"npx skills add fishzjp/qa-skills --skill '*'\"))")
        copied = page.evaluate("navigator.clipboard.readText()")
        assert not copied.startswith("$"), copied
        page.locator(".nav-lang").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("lang") == "zh-CN"
        assert "utm_source=smoke" in page.url
        # Reduced-motion preference must avoid hiding the page behind reveal animations.
        for width in (1280, 390):
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(base + "/en/", wait_until="networkidle")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Horizontal overflow at {width}px"
            page.locator("#install").scroll_into_view_if_needed()
            assert page.locator(".copy-btn").first.is_visible()
            page.locator(".copy-btn").first.focus()
            assert page.evaluate("document.activeElement.classList.contains('copy-btn')")
            shots = os.environ.get("QA_SITE_SCREENSHOT_DIR")
            if shots:
                out = Path(shots); out.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out / f"website-en-{width}.png"), full_page=True)
        assert not errors, errors
        context.close()
        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        page = nojs.new_page()
        page.goto(base, wait_until="networkidle")
        assert page.locator("#install").is_visible()
        assert page.locator("#install").evaluate("el => getComputedStyle(el.querySelector('.reveal')).opacity") == "1"
        assert page.locator(".copy-btn").first.is_visible()
        page.goto(base + "/en/", wait_until="networkidle")
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator(".zh-only:visible").count() == 0
        assert page.locator('link[rel="canonical"]').get_attribute('href').endswith('/en/')
        assert page.locator('.nav-lang').get_attribute('href') == '../'
        nojs.close()
        browser.close()
    print("PASS: Chromium language, query preservation, clipboard, keyboard focus, mobile layout and no-JS content.")


if __name__ == "__main__":
    main()
