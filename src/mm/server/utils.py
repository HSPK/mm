from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from mm.io import FileStorage

_RANGE_RE = re.compile(r"^bytes=(?:(\d+)-(\d*)|-(\d+))$")
_PRIVATE_CACHE_CONTROL = "private, max-age=3600"

# Browsers (especially Safari) reject the non-standard `audio/x-*` and
# `audio/mp4a-latm` MIME types that Python's `mimetypes` returns for common
# lossless/audio containers, surfacing as MEDIA_ERR_SRC_NOT_SUPPORTED (code 4).
# Force the standard, browser-playable types instead.
_MIME_OVERRIDES: dict[str, str] = {
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".aif": "audio/aiff",
    ".aiff": "audio/aiff",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".wma": "audio/x-ms-wma",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


def content_type_for(file_path: Path) -> str:
    """Resolve a browser-friendly Content-Type, overriding bad `mimetypes` guesses."""
    override = _MIME_OVERRIDES.get(file_path.suffix.lower())
    if override:
        return override
    return mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"


def stream_file(
    file_path: Path,
    request: Request,
    *,
    storage: FileStorage,
) -> Response:
    """Stream a file with HTTP Range request support for video seeking."""
    content_type = content_type_for(file_path)
    file_size = storage.get_size(file_path)

    range_header = request.headers.get("range")

    # Always use streaming for video files to enable fast start
    is_video = content_type and content_type.startswith("video/")

    if not range_header:
        if is_video:
            # For video without Range header, stream the whole file
            # This allows the browser to start playing while downloading
            chunk_size = 2 * 1024 * 1024  # 2 MB chunks

            def full_file_iterator():
                with storage.open(file_path, "rb") as f:
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data

            return StreamingResponse(
                full_file_iterator(),
                media_type=content_type,
                headers={
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": _PRIVATE_CACHE_CONTROL,
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            return FileResponse(
                file_path,
                media_type=content_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": _PRIVATE_CACHE_CONTROL,
                },
            )

    match = _RANGE_RE.fullmatch(range_header.strip())
    if not match:
        return _range_not_satisfiable(file_size)

    if file_size <= 0:
        return _range_not_satisfiable(file_size)
    if match.group(3):
        suffix_length = int(match.group(3))
        if suffix_length <= 0:
            return _range_not_satisfiable(file_size)
        start = max(0, file_size - suffix_length)
        end = file_size - 1
    else:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1
    end = min(end, file_size - 1)

    if start >= file_size or end < start:
        return _range_not_satisfiable(file_size)

    length = end - start + 1
    chunk_size = 2 * 1024 * 1024  # 2 MB chunks for smoother streaming

    def file_iterator():
        with storage.open(file_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        file_iterator(),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Accept-Ranges": "bytes",
            "Cache-Control": _PRIVATE_CACHE_CONTROL,
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind proxy
        },
    )


def _range_not_satisfiable(file_size: int) -> Response:
    return Response(
        status_code=416,
        headers={
            "Content-Range": f"bytes */{file_size}",
            "Accept-Ranges": "bytes",
            "Cache-Control": _PRIVATE_CACHE_CONTROL,
        },
    )
