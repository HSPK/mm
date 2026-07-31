"""Artwork download helpers."""

from __future__ import annotations

import http.client
import ipaddress
import os
import secrets
import socket
import ssl
import urllib.error
import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate


@dataclass(frozen=True)
class ArtworkPlan:
    source_url: str
    target: Path
    media_type: str
    status: str
    reason: str = ""


def plan_artwork(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool = False,
) -> ArtworkPlan:
    target = _artwork_target(item, "poster", candidate.poster_url if candidate else "")
    if not candidate or not candidate.poster_url:
        return ArtworkPlan("", target, item.media_type, "missing", "no artwork url")
    if target.exists() and not overwrite:
        return ArtworkPlan(candidate.poster_url, target, item.media_type, "exists", "target exists")
    return ArtworkPlan(candidate.poster_url, target, item.media_type, "ready")


def plan_artworks(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool = False,
) -> list[ArtworkPlan]:
    if not candidate:
        return [plan_artwork(item, candidate, overwrite=overwrite)]
    plans = [
        _plan_one(item, "poster", candidate.poster_url, overwrite=overwrite),
        _plan_one(item, "fanart", candidate.backdrop_url, overwrite=overwrite),
        _plan_one(item, "clearlogo", candidate.logo_url, overwrite=overwrite),
    ]
    return [plan for plan in plans if plan.source_url or plan.status == "missing"]


def _plan_one(
    item: ParsedMediaFile,
    kind: str,
    source_url: str,
    *,
    overwrite: bool,
) -> ArtworkPlan:
    target = _artwork_target(item, kind, source_url)
    if not source_url:
        return ArtworkPlan("", target, item.media_type, "missing", f"no {kind} url")
    if target.exists() and not overwrite:
        return ArtworkPlan(source_url, target, item.media_type, "exists", "target exists")
    return ArtworkPlan(source_url, target, item.media_type, "ready")


MAX_ARTWORK_BYTES = 25 * 1024 * 1024


def extract_embedded_artwork(
    paths: Iterable[Path],
    album_directory: Path,
) -> Path | None:
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return None
    for path in paths:
        try:
            audio = MutagenFile(path)
        except Exception:  # noqa: BLE001 - malformed media must not abort album processing
            continue
        data = _embedded_artwork_bytes(audio)
        if not data or len(data) > MAX_ARTWORK_BYTES:
            continue
        try:
            with Image.open(BytesIO(data)) as image:
                image_format = (image.format or "").lower()
                image.verify()
        except (OSError, ValueError):
            continue
        extension = {
            "jpeg": ".jpg",
            "jpg": ".jpg",
            "png": ".png",
            "webp": ".webp",
        }.get(image_format)
        if extension is None:
            continue
        target = album_directory / f"cover{extension}"
        _atomic_write_no_follow(target, data)
        return target
    return None


def _embedded_artwork_bytes(audio: object) -> bytes | None:
    for picture in getattr(audio, "pictures", None) or []:
        data = getattr(picture, "data", None)
        if isinstance(data, bytes) and data:
            return data
    tags = getattr(audio, "tags", None)
    if not tags:
        return None
    for value in tags.values():
        values = value if isinstance(value, list) else [value]
        for item in values:
            data = getattr(item, "data", None)
            if isinstance(data, bytes) and data:
                return data
            if item.__class__.__name__ == "MP4Cover":
                raw = bytes(item)
                if raw:
                    return raw
    return None


def _safe_artwork_url(url: str) -> tuple[urllib.parse.ParseResult, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Artwork URL must use http or https")
    hostname = parsed.hostname.rstrip(".")
    if hostname.lower() == "localhost":
        raise ValueError("Artwork URL host is not allowed")
    try:
        addresses = {
            result[4][0]
            for result in socket.getaddrinfo(
                hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise ValueError("Artwork URL host could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or ip.is_multicast
        ):
            raise ValueError("Artwork URL resolves to a non-public address")
    return parsed, sorted(addresses)[0]


def download_artwork(plan: ArtworkPlan, *, timeout: float = 30.0) -> None:
    if plan.status != "ready":
        raise ValueError(f"Artwork plan is not ready: {plan.status}")
    plan.target.parent.mkdir(parents=True, exist_ok=True)
    data, content_type = _download_artwork_bytes(plan.source_url, timeout=timeout)
    if not content_type.startswith("image/"):
        raise ValueError("Artwork response is not an image")
    if len(data) > MAX_ARTWORK_BYTES:
        raise ValueError("Artwork response is too large")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (OSError, ValueError) as exc:
        raise ValueError("Artwork response could not be decoded as an image") from exc
    _atomic_write_no_follow(plan.target, data)


def _download_artwork_bytes(
    url: str,
    *,
    timeout: float,
    max_redirects: int = 3,
) -> tuple[bytes, str]:
    current = url
    for redirect_count in range(max_redirects + 1):
        parsed, address = _safe_artwork_url(current)
        connection = _pinned_connection(parsed, address, timeout)
        try:
            path = urllib.parse.urlunparse(("", "", parsed.path or "/", "", parsed.query, ""))
            connection.request("GET", path, headers={"User-Agent": "litemm/0.1"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                response.read()
                if not location or redirect_count >= max_redirects:
                    raise ValueError("Artwork redirect is invalid or exceeds the limit")
                current = urllib.parse.urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Artwork server returned HTTP {response.status}")
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].lower()
            declared = response.getheader("Content-Length")
            if declared and int(declared) > MAX_ARTWORK_BYTES:
                raise ValueError("Artwork response is too large")
            return response.read(MAX_ARTWORK_BYTES + 1), content_type
        except (OSError, http.client.HTTPException) as exc:
            raise RuntimeError(f"Could not download artwork: {exc}") from exc
        finally:
            connection.close()
    raise ValueError("Artwork redirect exceeds the limit")


def _pinned_connection(
    parsed: urllib.parse.ParseResult,
    address: str,
    timeout: float,
) -> http.client.HTTPConnection:
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    raw_socket = socket.create_connection((address, port), timeout=timeout)
    if parsed.scheme == "https":
        context = ssl.create_default_context()
        connection = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
        connection.sock = context.wrap_socket(raw_socket, server_hostname=host)
        return connection
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    connection.sock = raw_socket
    return connection


def _atomic_write_no_follow(target: Path, data: bytes) -> None:
    parent = target.parent.resolve()
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(parent, directory_flags)
    temp_name = f".{target.name}.{secrets.token_hex(8)}.tmp"
    file_fd: int | None = None
    try:
        file_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o644,
            dir_fd=directory_fd,
        )
        with os.fdopen(file_fd, "wb", closefd=True) as output:
            file_fd = None
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(
            temp_name,
            target.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        if file_fd is not None:
            os.close(file_fd)
        try:
            os.unlink(temp_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)


def _artwork_target(item: ParsedMediaFile, kind: str, source_url: str = "") -> Path:
    suffix = _url_suffix(source_url)
    if item.media_type == "tv":
        root = _tv_root(item.path)
        if kind == "poster" and item.season is not None:
            return root / f"season{item.season:02d}-poster{suffix}"
        return root / f"{kind}{suffix}"
    if item.media_type == "track":
        return item.path.parent / ("folder.jpg" if kind == "poster" else f"{kind}{suffix}")
    if item.media_type == "album":
        return item.path.parent / ("folder.jpg" if kind == "poster" else f"{kind}{suffix}")
    return item.path.parent / f"{kind}{suffix}"


def _tv_root(path: Path) -> Path:
    return path.parent.parent if path.parent.name.lower().startswith("season") else path.parent


def _url_suffix(source_url: str) -> str:
    suffix = Path(urllib.parse.urlparse(source_url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
