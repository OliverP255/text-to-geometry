"""Discord incoming webhook for new print jobs."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger(__name__)


def notify_new_print_job(
    *,
    job_id: str,
    material: str,
    quality: str,
    delivery_speed: str,
    user_email: str | None = None,
) -> None:
    url = (os.environ.get("DISCORD_PRINT_WEBHOOK_URL") or "").strip()
    if not url:
        return
    base = (os.environ.get("PUBLIC_APP_URL") or "http://127.0.0.1:5001").rstrip("/")
    admin_link = f"{base}/admin/print-jobs"
    lines = [
        "**New print job**",
        f"• Job: `{job_id}`",
        f"• Material: {material}",
        f"• Quality: {quality}",
        f"• Delivery: {delivery_speed}",
    ]
    if user_email:
        lines.append(f"• User: {user_email}")
    lines.append(f"• Admin: {admin_link}")
    payload = {"content": "\n".join(lines)}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                log.warning("Discord webhook returned %s", resp.status)
    except urllib.error.URLError as e:
        log.warning("Discord webhook failed: %s", e)
