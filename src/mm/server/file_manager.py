from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import Request

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in _LOCAL_HOSTS


def open_in_file_manager(path: Path, *, select: bool = False) -> bool:
    try:
        if sys.platform == "darwin":
            command = ["open", "-R", str(path)] if select else ["open", str(path)]
        elif sys.platform == "win32":
            command = ["explorer", f"/select,{path}"] if select else ["explorer", str(path)]
        else:
            command = ["xdg-open", str(path.parent if select else path)]
        subprocess.run(command, check=sys.platform != "win32", timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False
