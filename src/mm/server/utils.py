from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


def stream_file(file_path: Path, request: Request) -> StreamingResponse | FileResponse:
    """Stream a file with HTTP Range request support for video seeking."""
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_size = file_path.stat().st_size

    range_header = request.headers.get("range")

    # Always use streaming for video files to enable fast start
    is_video = content_type and content_type.startswith("video/")

    if not range_header:
        if is_video:
            # For video without Range header, stream the whole file
            # This allows the browser to start playing while downloading
            chunk_size = 2 * 1024 * 1024  # 2 MB chunks

            def full_file_iterator():
                with open(file_path, "rb") as f:
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
                    "Cache-Control": "public, max-age=3600",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            return FileResponse(
                file_path,
                media_type=content_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=3600",
                },
            )

    match = _RANGE_RE.match(range_header)
    if not match:
        raise HTTPException(416, "Invalid range header")

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else file_size - 1
    end = min(end, file_size - 1)

    if start >= file_size:
        raise HTTPException(416, "Range not satisfiable")

    length = end - start + 1
    chunk_size = 2 * 1024 * 1024  # 2 MB chunks for smoother streaming

    def file_iterator():
        with open(file_path, "rb") as f:
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
            "Cache-Control": "public, max-age=3600",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind proxy
        },
    )
