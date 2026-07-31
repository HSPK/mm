from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def issue_media_ticket(
    secret: bytes,
    *,
    library_id: str,
    playback_id: str,
    ttl_seconds: int = 60,
) -> str:
    payload = {
        "library_id": library_id,
        "playback_id": playback_id,
        "expires": int(time.time()) + ttl_seconds,
    }
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret, encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def verify_media_ticket(
    secret: bytes,
    ticket: str,
    *,
    library_id: str,
    playback_id: str,
) -> bool:
    encoded, separator, signature = ticket.partition(".")
    if not separator:
        return False
    expected = _encode(hmac.new(secret, encoded.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(_decode(encoded))
        expires = int(payload["expires"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        payload.get("library_id") == library_id
        and payload.get("playback_id") == playback_id
        and expires >= int(time.time())
    )


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
