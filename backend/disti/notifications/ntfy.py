"""Small, asynchronous ntfy notification transport."""

import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request


LOGGER = logging.getLogger(__name__)
HTTP_TIMEOUT_SECONDS = 10
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _enabled() -> bool:
    return os.getenv("DISTI_NTFY_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _publish(base_url: str, topic: str, title: str, message: str) -> None:
    """Publish one notification, containing all failures within the worker."""
    endpoint = f"{base_url.rstrip('/')}/{urllib.parse.quote(topic, safe='')}"
    body = f"{title}\n\n{message}".encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "text/plain; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            status = response.getcode()
            if not 200 <= status < 300:
                LOGGER.warning("ntfy notification failed with HTTP status %s", status)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Do not include the endpoint: a topic may itself be sensitive.
        LOGGER.warning("ntfy notification delivery failed: %s", type(exc).__name__)
    except Exception:
        # Notification transport must never take down application work.
        LOGGER.exception("Unexpected ntfy notification delivery failure")


def send_notification(title: str, message: str) -> None:
    """Queue an ntfy message and return immediately.

    Configuration is read for every call so device-local environment changes
    are respected by newly started application processes. Delivery occurs in a
    daemon thread and any network error is logged rather than propagated.
    """
    if not _enabled():
        return

    topic = os.getenv("DISTI_NTFY_TOPIC", "").strip()
    if not topic:
        LOGGER.warning("ntfy notifications are enabled but DISTI_NTFY_TOPIC is empty")
        return

    base_url = os.getenv("DISTI_NTFY_BASE_URL", "https://ntfy.sh").strip()
    if not base_url:
        LOGGER.warning("ntfy notifications are enabled but DISTI_NTFY_BASE_URL is empty")
        return

    try:
        threading.Thread(
            target=_publish,
            args=(base_url, topic, str(title), str(message)),
            name="disti-ntfy",
            daemon=True,
        ).start()
    except Exception:
        LOGGER.exception("Unable to start ntfy notification worker")
