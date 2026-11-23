"""The copy buttons of the published page, in Chromium. The page (site/) is built by build.py and published;
it is not kept in this repository, so these tests skip without it or without Playwright."""
import functools
import re
import http.server
import threading
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
if not (SITE / "index.html").exists() or not (SITE / "data.js").exists():
    pytest.skip("site/ not built here", allow_module_level=True)
sync_api = pytest.importorskip("playwright.sync_api")

REFUSING_CLIPBOARD = """
Object.defineProperty(navigator, 'clipboard', {configurable: true,
  value: {writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError'))}});
document.execCommand = () => false;
"""
CAPTURING_CLIPBOARD = """
window.__copied = [];
Object.defineProperty(navigator, 'clipboard', {configurable: true,
  value: {writeText: t => { window.__copied.push(t); return Promise.resolve(); }}});
"""


@pytest.fixture(scope="module")
def url():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(SITE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()
    srv.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, url, script):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.add_init_script(script)
    page.route("**/fonts.g*/**", lambda r: r.abort())
    page.goto(url)
    return page


def test_a_refused_clipboard_never_says_copied(browser, url):
    page = open_page(browser, url, REFUSING_CLIPBOARD)
    page.fill("#sheet input.blank", "Dana")
    bt = page.locator("[data-hero-copy]")
    bt.click()
    sync_api.expect(bt).to_have_text(re.compile(r"^Press (Cmd|Ctrl)\+C$"))
    assert bt.inner_text() != "Copied"
    ta = page.locator("#sheet textarea.manual")
    sync_api.expect(ta).to_be_visible()
    value = ta.input_value()
    assert value.startswith("Hi Dana, I saw Utilitra is adding an AP Specialist")
    selected = page.evaluate("() => { const t = document.activeElement; return t.classList.contains('manual') && t.value.slice(t.selectionStart, t.selectionEnd); }")
    assert selected == value
    page.close()


def test_a_refused_clipboard_api_falls_back_to_execcommand(browser, url):
    page = open_page(browser, url, REFUSING_CLIPBOARD.replace("() => false", "() => true"))
    page.fill("#sheet input.blank", "Dana")
    page.locator("[data-hero-copy]").click()
    sync_api.expect(page.locator("[data-hero-copy]")).to_have_text("Copied")
    assert page.locator("textarea.manual").count() == 0
    page.close()


def test_a_name_with_replace_patterns_is_copied_as_typed(browser, url):
    page = open_page(browser, url, CAPTURING_CLIPBOARD)
    page.fill("#sheet input.blank", "Jo$&")
    page.locator("[data-hero-copy]").click()
    sync_api.expect(page.locator("[data-hero-copy]")).to_have_text("Copied")
    page.locator("#row-utilitra .emp").click()
    page.locator('#row-utilitra [data-copydraft="followup_2"]').click()
    copied = page.evaluate("window.__copied")
    assert copied[0].startswith("Hi Jo$&, I saw Utilitra")
    assert copied[1].startswith("One last note, Jo$&.")
    assert "{first_name}" not in "".join(copied)
    assert "Jo$&" in page.locator('#row-utilitra [data-draft="note"]').inner_text()
    page.close()
