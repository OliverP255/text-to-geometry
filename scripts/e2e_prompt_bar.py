#!/usr/bin/env python3
"""Drive the viewer prompt bar; mocks POST /chat so no GPU/LLM is required."""

from __future__ import annotations

import json
import os
import sys

from playwright.sync_api import sync_playwright

MOCK_BODY = json.dumps(
    {
        "ok": True,
        "code": "fn map(p: vec3f) -> f32 {\n  return sdSphere(p, 1.0);\n}\n",
    }
)


def main() -> int:
    base = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5001").rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_chat(route):
            route.fulfill(
                status=200,
                body=MOCK_BODY,
                headers={"Content-Type": "application/json"},
            )

        page.route("**/chat", handle_chat)
        page.goto(f"{base}/", wait_until="networkidle", timeout=60_000)

        page.wait_for_selector("#prompt-input", timeout=30_000)
        page.fill("#prompt-input", "a test sphere from e2e")
        page.click("#prompt-send")

        page.wait_for_function(
            """() => {
              const s = document.getElementById('status')?.innerText || '';
              return s.includes('wgsl') || s.includes('scene');
            }""",
            timeout=30_000,
        )

        status = page.inner_text("#status")
        browser.close()

    if "wgsl" not in status.lower() and "scene" not in status.lower():
        print("FAIL: status did not show scene/wgsl:", repr(status), file=sys.stderr)
        return 1

    print("OK:", status.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
