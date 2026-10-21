#!/usr/bin/env python3
"""Browserbase adapter for Safe to Upgrade? — honest stub with fallback.

Intended design: changelog and migration-guide pages are fetched through
Browserbase (https://www.browserbase.com) with Stagehand driving the
browser, because some guides are JS-rendered and a plain HTTP GET does not
always return the content. That is the path when BROWSERBASE_API_KEY is
set in the environment.

What is true TODAY (and what this module does):
  * If BROWSERBASE_API_KEY is NOT set, `require_browserbase()` raises
    BrowserbaseNotConfigured and, when run as a script, prints a clear
    "not configured" message. Nothing in this project claims Browserbase
    was used when it was not.
  * If the key IS set, `fetch_page()` attempts to create a real
    Browserbase session via the public REST API
    (POST https://api.browserbase.com/v1/sessions) and reports the
    session result. Extracting page content through Stagehand from that
    session is NOT wired yet (see README "Remaining"), so after creating
    the session this module still falls back to a direct urllib fetch for
    the page content and says so explicitly.
  * `fetch_page()` therefore always either returns directly-fetched
    content (clearly labelled as fallback) or raises. It never returns
    content while pretending a browser fetched it.

The verdict pipeline itself (verdict.py) does not import this module;
fetching is an input step, verdicts are deterministic code.
"""

import json
import os
import sys
import urllib.error
import urllib.request

BROWSERBASE_API_ROOT = "https://api.browserbase.com/v1"
NOT_CONFIGURED_MESSAGE = (
    "Browserbase is not configured: BROWSERBASE_API_KEY is not set. "
    "Set it to use the Browserbase/Stagehand fetch path; until then the "
    "pipeline falls back to direct HTTP fetch."
)


class BrowserbaseNotConfigured(RuntimeError):
    """Raised when the Browserbase path is requested without an API key."""


def browserbase_configured():
    return bool(os.environ.get("BROWSERBASE_API_KEY"))


def require_browserbase():
    """Return the API key, or raise BrowserbaseNotConfigured."""
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not api_key:
        raise BrowserbaseNotConfigured(NOT_CONFIGURED_MESSAGE)
    return api_key


def create_session():
    """Create a Browserbase session via the public REST API.

    Returns the parsed session object. Raises BrowserbaseNotConfigured
    without a key, and urllib errors if the API call fails.
    """
    api_key = require_browserbase()
    request = urllib.request.Request(
        f"{BROWSERBASE_API_ROOT}/sessions",
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-BB-API-Key": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_direct(url):
    """Plain direct HTTP fetch — the fallback path, labelled as such."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "safe-to-upgrade-direct-fetch"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_page(url):
    """Fetch `url`, preferring Browserbase when configured.

    Returns (content, via) where `via` is always "direct-fallback" today:
    with no key, Browserbase is skipped with a printed notice; with a key,
    a session is created and reported, but Stagehand content extraction
    is not wired yet, so content still comes from the direct fetch.
    """
    if not browserbase_configured():
        print(f"[browserbase_fetch] {NOT_CONFIGURED_MESSAGE}",
              file=sys.stderr)
    else:
        try:
            session = create_session()
            print("[browserbase_fetch] Browserbase session created: "
                  f"id={session.get('id')} status={session.get('status')}. "
                  "Stagehand extraction is not wired yet; using direct "
                  "fetch for page content.", file=sys.stderr)
        except (urllib.error.URLError, BrowserbaseNotConfigured) as exc:
            print(f"[browserbase_fetch] Browserbase session failed "
                  f"({exc}); using direct fetch.", file=sys.stderr)
    return fetch_direct(url), "direct-fallback"


def main(argv):
    if len(argv) != 2:
        print("usage: python browserbase_fetch.py <url>")
        return 2
    url = argv[1]
    if not browserbase_configured():
        print("Falling back to direct fetch...")
    content, via = fetch_page(url)
    print(f"--- fetched via: {via} ({len(content)} chars) ---")
    print(content[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
