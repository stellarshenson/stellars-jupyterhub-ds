"""DEF-5 regression: the auth pages must not loop on a nested ?next=.

Default regime (regime-agnostic - logged-out behaviour). A logged-OUT browser
hitting the SPA landing must settle on a SINGLE un-nested /hub/login?next= URL, not
the ever-growing /hub/login?next=/hub/login?next=...%2Fhub%2Fhome chain that made
the site unusable before the fix (module-level prefetch side effects in App.tsx
running on the auth pages, 403 -> loginRedirect wrapping the URL forever).
"""

import re

import pytest
from playwright.sync_api import expect


@pytest.mark.acc_crit("functional-test-harness::No login redirect loop")
def test_logged_out_landing_does_not_loop(page, base_url):
    # logged out: no admin cookies injected (plain `page`, not `admin_page`).
    page.goto(f"{base_url}/hub/home", wait_until="domcontentloaded")

    # let any client-side auth redirect settle, then confirm it has STOPPED moving:
    # a loop keeps rewriting window.location, so the URL would still be changing.
    page.wait_for_timeout(2000)
    first = page.url
    page.wait_for_timeout(2000)
    assert page.url == first, f"URL still changing - redirect loop: {first} -> {page.url}"

    url = page.url
    # the DEF-5 signature is a nested / re-encoded ?next= chain - bounded now.
    assert url.count("next=") <= 1, f"nested next= (loop): {url}"
    assert "%252F" not in url and "%253F" not in url, f"double-encoded next= (loop): {url}"
    assert len(url) < 300, f"login URL pathologically long (nested next=): {len(url)} chars: {url}"

    # landed on the login surface with a usable form, not a blank loop.
    expect(page).to_have_url(re.compile(r"/hub/login"))
    expect(page.locator('input[type="password"]')).to_be_visible()
